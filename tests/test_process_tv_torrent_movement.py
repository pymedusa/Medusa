# coding=utf-8
"""Keep partially processed torrents in place until their remaining media is ready."""
from __future__ import unicode_literals

import errno
import os

from medusa.post_processor import TorrentMoveCandidate
from medusa.process_tv import ProcessResult

from mock.mock import Mock

import pytest


def _move_candidate(*release_names):
    """Build a ready candidate as retained after a previous client move failure."""
    candidate = TorrentMoveCandidate()
    candidate.release_names.extend(release_names)
    return candidate


def _scan_scope(path, resource_name=None):
    """Identify one complete selection independently of a narrower request."""
    return os.path.normcase(os.path.abspath(path)), resource_name


@pytest.fixture
def torrent_processing(monkeypatch, app_config):
    """Retain real traversal and postponement while mocking library and client actions."""
    state = {'outcomes': {}, 'history': set(), 'hashes': {}, 'subtitles': set(), 'processors': {}}
    recent = app_config('RECENTLY_POSTPROCESSED', {})
    move = Mock(return_value=True)

    def get_processor(file_path, resource_name, process_method, is_priority):
        assert os.path.isfile(file_path)
        filename = os.path.basename(file_path)
        info_hash = state['hashes'].get(file_path, 'torrent-hash')

        def process():
            outcome = state['outcomes'].get(filename, True)
            if outcome:
                state['history'].add(filename)
                # Mirror PostProcessor's seed-move registration after a successful import.
                if not resource_name and process_method in ('copy', 'hardlink', 'symlink', 'reflink', 'keeplink'):
                    recent.setdefault(info_hash, TorrentMoveCandidate()).release_names.append(filename)
            return outcome

        processor = Mock(_output=[], info_hash=info_hash, **{'process.side_effect': process})
        processor.list_associated_files.return_value = [] if filename in state['subtitles'] else [file_path + '.srt']
        state['processors'][file_path] = processor
        return processor

    app_config('USE_TORRENTS', True)
    app_config('TORRENT_SEED_LOCATION', 'seed-location')
    app_config('POSTPONE_IF_SYNC_FILES', True)
    app_config('SYNC_FILES', ['!sync'])
    app_config('POSTPONE_IF_NO_SUBS', False)
    app_config('IGNORE_EMBEDDED_SUBS', True)
    app_config('UNPACK', False)
    app_config('KODI_LIBRARY_CLEAN_PENDING', False)
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', Mock(side_effect=get_processor))
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', lambda self, filename: filename in state['history'])
    monkeypatch.setattr(ProcessResult, 'subtitles_enabled', Mock(return_value=True))
    monkeypatch.setattr(ProcessResult, '_clean_up', Mock())
    monkeypatch.setattr(ProcessResult, 'delete_files', Mock())
    monkeypatch.setattr(ProcessResult, 'delete_folder', Mock())
    monkeypatch.setattr(ProcessResult, 'process_failed', Mock())
    monkeypatch.setattr(ProcessResult, 'move_torrent', move)
    return state, recent, move


@pytest.mark.parametrize('reason', ['sync', 'subtitles', 'unreadable'])
def test_pending_episode_keeps_successful_sibling_torrent_in_place(
        create_file, monkeypatch, app_config, torrent_processing, reason):
    """A successful root episode cannot move the torrent containing a pending child."""
    root_episode = create_file('release/show.s01e01.mkv')
    pending_episode = create_file('release/part2/show.s01e02.mkv')
    state, recent, move = torrent_processing
    if reason == 'sync':
        create_file('release/part2/show.s01e02.mkv.!sync')
    elif reason == 'subtitles':
        app_config('POSTPONE_IF_NO_SUBS', True)
        state['subtitles'].add(os.path.basename(pending_episode))
    else:
        original_scandir = os.scandir
        blocked = os.path.dirname(pending_episode)

        def scandir(path):
            if path == blocked:
                raise PermissionError(errno.EACCES, 'Directory access denied by test', path)
            return original_scandir(path)

        monkeypatch.setattr('medusa.process_tv.os.scandir', scandir)

    result = ProcessResult(os.path.dirname(root_episode), process_method='copy', process_single_resource=True)

    result.process()

    state['processors'][root_episode].process.assert_called_once_with()
    assert result.postpone_any is True
    move.assert_not_called()
    assert recent['torrent-hash'].pending_scans == {_scan_scope(os.path.dirname(root_episode))}
    assert os.path.isfile(root_episode)
    assert os.path.isfile(pending_episode)


@pytest.mark.parametrize('failure_first', [False, True])
def test_failed_episode_keeps_successful_sibling_torrent_in_place(
        create_file, torrent_processing, failure_first):
    """A failure before or after an imported episode must prevent torrent relocation."""
    root_episode = create_file('release/show.s01e01.mkv')
    child_episode = create_file('release/part2/show.s01e02.mkv')
    state, recent, move = torrent_processing
    failed_episode = root_episode if failure_first else child_episode
    state['outcomes'][os.path.basename(failed_episode)] = False
    result = ProcessResult(os.path.dirname(root_episode), process_method='copy', process_single_resource=True)

    result.process()

    assert result.succeeded is False
    assert len(state['history']) == 1
    move.assert_not_called()
    assert recent['torrent-hash'].pending_scans == {_scan_scope(os.path.dirname(root_episode))}


def test_successful_release_still_moves_torrent(create_file, torrent_processing):
    """Fully imported torrents retain the configured seeding-location behavior."""
    root_episode = create_file('release/show.s01e01.mkv')
    child_episode = create_file('release/part2/show.s01e02.mkv')
    state, recent, move = torrent_processing
    result = ProcessResult(os.path.dirname(root_episode), process_method='copy')

    result.process()

    assert result.succeeded is True
    assert result.postpone_any is False
    assert state['history'] == {os.path.basename(root_episode), os.path.basename(child_episode)}
    move.assert_called_once_with('torrent-hash', [os.path.basename(root_episode), os.path.basename(child_episode)])
    assert recent == {}


def test_successful_retry_moves_previously_postponed_torrent(create_file, torrent_processing):
    """Finishing the pending episode re-registers its torrent even if history skips its sibling."""
    root_episode = create_file('release/show.s01e01.mkv')
    pending_episode = create_file('release/part2/show.s01e02.mkv')
    sync_file = create_file('release/part2/show.s01e02.mkv.!sync')
    state, recent, move = torrent_processing
    root = os.path.dirname(root_episode)
    first = ProcessResult(root, process_method='copy')

    first.process()

    assert first.postpone_any is True
    move.assert_not_called()
    assert recent['torrent-hash'].pending_scans == {_scan_scope(root)}
    first_processor = state['processors'][root_episode]
    os.rename(sync_file, sync_file + '.done')

    retry = ProcessResult(root, process_method='copy')
    retry.process()

    assert retry.postpone_any is False
    assert retry.succeeded is True
    assert state['processors'][root_episode] is first_processor
    state['processors'][pending_episode].process.assert_called_once_with()
    move.assert_called_once_with('torrent-hash', [os.path.basename(root_episode), os.path.basename(pending_episode)])
    assert recent == {}


@pytest.mark.parametrize('existing_candidate', [False, True])
@pytest.mark.parametrize('same_torrent', [False, True])
def test_unrelated_success_cannot_move_still_pending_torrent(
        create_file, torrent_processing, existing_candidate, same_torrent):
    """A pending torrent cannot leak through the global move queue on a later request."""
    root_episode = create_file('release/show.s01e01.mkv')
    create_file('release/part2/show.s01e02.mkv')
    create_file('release/part2/show.s01e02.mkv.!sync')
    other_episode = create_file('other/other.s01e01.mkv')
    state, recent, move = torrent_processing
    if existing_candidate:
        recent['torrent-hash'] = _move_candidate('earlier.episode.mkv')
    first = ProcessResult(os.path.dirname(root_episode), process_method='copy')

    first.process()

    first_moves = list(move.call_args_list)
    state['hashes'][other_episode] = 'torrent-hash' if same_torrent else 'other-torrent-hash'
    second = ProcessResult(os.path.dirname(other_episode), process_method='copy')
    second.process()

    assert first.postpone_any is True
    assert first_moves == []
    assert second.succeeded is True
    if same_torrent:
        move.assert_not_called()
        assert os.path.basename(other_episode) in recent['torrent-hash'].release_names
    else:
        move.assert_called_once_with('other-torrent-hash', [os.path.basename(other_episode)])
    assert set(recent) == {'torrent-hash'}
    assert recent['torrent-hash'].pending_scans == {_scan_scope(os.path.dirname(root_episode))}


def test_pending_run_preserves_unrelated_completed_move_candidate(create_file, torrent_processing):
    """Deferring an incomplete torrent must preserve another torrent's failed move retry."""
    root_episode = create_file('release/show.s01e01.mkv')
    create_file('release/part2/show.s01e02.mkv')
    create_file('release/part2/show.s01e02.mkv.!sync')
    _, recent, move = torrent_processing
    recent['torrent-hash'] = _move_candidate('earlier.episode.mkv')
    recent['other-torrent-hash'] = _move_candidate('completed.episode.mkv')
    result = ProcessResult(os.path.dirname(root_episode), process_method='copy')

    result.process()

    assert result.postpone_any is True
    assert set(recent) == {'torrent-hash', 'other-torrent-hash'}
    assert recent['torrent-hash'].pending_scans == {_scan_scope(os.path.dirname(root_episode))}
    assert recent['other-torrent-hash'].pending_scans == set()
    assert recent['other-torrent-hash'].release_names == ['completed.episode.mkv']
    move.assert_not_called()


def test_completed_torrent_retains_failed_move_for_retry(create_file, torrent_processing):
    """A client move failure still preserves an otherwise completed torrent for retry."""
    episode = create_file('release/show.s01e01.mkv')
    _, recent, move = torrent_processing
    move.return_value = False
    result = ProcessResult(os.path.dirname(episode), process_method='copy')

    result.process()

    assert result.succeeded is True
    move.assert_called_once_with('torrent-hash', [os.path.basename(episode)])
    assert set(recent) == {'torrent-hash'}
    assert recent['torrent-hash'].pending_scans == set()
    assert recent['torrent-hash'].release_names == [os.path.basename(episode)]


def test_retry_preserves_completed_unrelated_torrent_from_pending_scan(create_file, torrent_processing):
    """A postponed sibling cannot permanently lose an already completed torrent's move."""
    completed_episode = create_file('downloads/completed.s01e01.mkv')
    pending_episode = create_file('downloads/pending/pending.s01e01.mkv')
    sync_file = create_file('downloads/pending/pending.s01e01.mkv.!sync')
    state, recent, move = torrent_processing
    state['hashes'][pending_episode] = 'other-torrent-hash'
    root = os.path.dirname(completed_episode)
    first = ProcessResult(root, process_method='copy')

    first.process()

    assert first.postpone_any is True
    assert recent['torrent-hash'].pending_scans == {_scan_scope(root)}
    completed_processor = state['processors'][completed_episode]
    move.assert_not_called()
    os.rename(sync_file, sync_file + '.done')

    retry = ProcessResult(root, process_method='copy')
    retry.process()

    assert retry.postpone_any is False
    assert retry.succeeded is True
    assert state['processors'][completed_episode] is completed_processor
    assert sorted(call[0] for call in move.call_args_list) == [
        ('other-torrent-hash', [os.path.basename(pending_episode)]),
        ('torrent-hash', [os.path.basename(completed_episode)]),
    ]
    assert recent == {}


@pytest.mark.parametrize('selection', ['resource', 'file'])
def test_narrow_success_cannot_clear_broad_scan_deferral(create_file, torrent_processing, selection):
    """Completing only one file does not prove that the previously scanned tree is ready."""
    root_episode = create_file('release/show.s01e01.mkv')
    create_file('release/part2/show.s01e02.mkv')
    create_file('release/part2/show.s01e02.mkv.!sync')
    _, recent, move = torrent_processing
    root = os.path.dirname(root_episode)
    first = ProcessResult(root, process_method='copy')
    first.process()
    path = root if selection == 'resource' else root_episode
    resource_name = os.path.basename(root_episode) if selection == 'resource' else None

    narrow = ProcessResult(path, process_method='copy')
    narrow.process(resource_name=resource_name)

    assert first.postpone_any is True
    assert narrow.postpone_any is False
    assert narrow.succeeded is True
    assert recent['torrent-hash'].pending_scans == {_scan_scope(root)}
    move.assert_not_called()


def test_successful_broader_scan_releases_child_scope_deferral(create_file, torrent_processing):
    """The next full download-root scan can complete an earlier path-only child request."""
    root_episode = create_file('downloads/release/show.s01e01.mkv')
    pending_episode = create_file('downloads/release/part2/show.s01e02.mkv')
    sync_file = create_file('downloads/release/part2/show.s01e02.mkv.!sync')
    state, recent, move = torrent_processing
    release = os.path.dirname(root_episode)
    first = ProcessResult(release, process_method='copy')
    first.process()
    assert first.postpone_any is True
    assert recent['torrent-hash'].pending_scans == {_scan_scope(release)}
    move.assert_not_called()
    first_processor = state['processors'][root_episode]
    os.rename(sync_file, sync_file + '.done')

    broader = ProcessResult(os.path.dirname(release), process_method='copy')
    broader.process()

    assert broader.postpone_any is False
    assert broader.succeeded is True
    assert state['processors'][root_episode] is first_processor
    move.assert_called_once_with('torrent-hash', [os.path.basename(root_episode), os.path.basename(pending_episode)])
    assert recent == {}
