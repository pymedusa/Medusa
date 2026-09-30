# coding=utf-8
"""Regression coverage for scan boundaries, concurrent jobs and deferred moves."""
from __future__ import unicode_literals

import os
import threading

from medusa import process_tv
from medusa.process_tv import ProcessResult

import pytest

from tests import test_process_tv_torrent_movement as torrent_tests


torrent_processing = torrent_tests.torrent_processing


@pytest.mark.parametrize('folder', [
    '_UNPACK_release', '_unpack_release', '.hidden', '@eaDir', '_FAILED_release', '_UNDERSIZED_release',
])
def test_rejected_scan_root_cannot_process_children(create_file, torrent_processing, folder):
    """Reject the selection itself, not just its first batch of files."""
    episode = create_file(os.path.join(folder, 'Season 1', 'show.s01e01.mkv'))
    state, _, move = torrent_processing
    result = ProcessResult(os.path.dirname(os.path.dirname(episode)), process_method='copy')

    result.process()

    assert state['processors'] == {}
    assert result.result is False
    assert result.missed_files
    move.assert_not_called()
    if folder.startswith(('_UNPACK_', '_unpack')):
        assert result.postpone_any is True


def test_root_without_media_still_discovers_healthy_children(create_file, torrent_processing):
    """An empty root is different from an invalid root."""
    episode = create_file('downloads/Show/Season 1/show.s01e01.mkv')
    state, _, move = torrent_processing
    result = ProcessResult(os.path.dirname(os.path.dirname(os.path.dirname(episode))), process_method='copy')

    result.process()

    state['processors'][episode].process.assert_called_once_with()
    assert result.succeeded is True
    move.assert_called_once()


@pytest.mark.parametrize('marker', ['_UNPACK_', '_unpack'])
def test_staging_retry_cannot_release_previous_torrent_deferral(create_file, torrent_processing, marker):
    """A sync postponement must survive a later retry with an unpacking directory."""
    episode = create_file('release/show.s01e01.mkv')
    pending = create_file('release/part2/show.s01e02.mkv')
    create_file('release/part2/show.s01e02.mkv.!sync')
    state, recent, move = torrent_processing
    root = os.path.dirname(episode)
    first = ProcessResult(root, process_method='copy')
    first.process()
    assert first.postpone_any is True

    # Both paths belong to this test's temporary release directory.
    os.rename(os.path.dirname(pending), os.path.join(root, marker + 'part2'))
    retry = ProcessResult(root, process_method='copy')
    retry.process()

    assert retry.postpone_any is True
    assert state['history'] == {os.path.basename(episode)}
    assert recent['torrent-hash'].pending_scans
    move.assert_not_called()


@pytest.mark.parametrize('same_scope,postponed', [(False, False), (False, True), (True, True)])
def test_overlapping_jobs_cannot_move_an_active_download(
        create_file, monkeypatch, torrent_processing, same_scope, postponed):
    """The queued and periodic processing entry points must share their execution guard."""
    episode = create_file('release/show.s01e01.mkv')
    other_episode = create_file('other/other.s01e01.mkv')
    if postponed:
        create_file('release/part2/show.s01e02.mkv')
        create_file('release/part2/show.s01e02.mkv.!sync')
    state, recent, move = torrent_processing
    state['hashes'][other_episode] = 'other-torrent'
    first = ProcessResult(os.path.dirname(episode), process_method='copy')
    second = ProcessResult(os.path.dirname(episode if same_scope else other_episode), process_method='copy')
    registered = threading.Event()
    release = threading.Event()
    attempted = threading.Event()
    finished = threading.Event()
    errors = []
    original_factory = process_tv.post_processor.PostProcessor

    def get_processor(*args):
        processor = original_factory(*args)
        if args[0] == episode:
            original_process = processor.process.side_effect

            def process():
                outcome = original_process()
                registered.set()
                if not release.wait(5):
                    raise RuntimeError('Test did not release the active job')
                return outcome

            processor.process.side_effect = process
        return processor

    monkeypatch.setattr(process_tv.post_processor, 'PostProcessor', get_processor)

    def run(result, is_second=False):
        if is_second:
            attempted.set()
        try:
            result.process()
        except Exception as error:
            errors.append(error)
        finally:
            if is_second:
                finished.set()

    worker = threading.Thread(target=run, args=(first,))
    other = threading.Thread(target=run, args=(second, True))
    worker.start()
    try:
        assert registered.wait(5)
        other.start()
        assert attempted.wait(5)
        assert not finished.wait(0.2), 'Another job completed while the first scan was still active'
        move.assert_not_called()
    finally:
        release.set()
        worker.join(5)
        if other.ident is not None:
            other.join(5)

    assert not worker.is_alive()
    assert not other.is_alive()
    assert errors == []
    moved = [call.args[0] for call in move.call_args_list]
    if postponed:
        assert 'torrent-hash' not in moved
        assert recent['torrent-hash'].pending_scans
    else:
        assert moved.count('torrent-hash') == 1
    if not same_scope:
        assert moved.count('other-torrent') == 1


def test_exception_keeps_registered_torrent_pending_and_releases_execution_guard(
        create_file, monkeypatch, torrent_processing):
    """A later job must neither deadlock nor move a torrent from an interrupted scan."""
    episode = create_file('release/show.s01e01.mkv')
    other_episode = create_file('other/other.s01e01.mkv')
    state, recent, move = torrent_processing
    state['hashes'][other_episode] = 'other-torrent'
    first = ProcessResult(os.path.dirname(episode), process_method='copy')
    original_get_files = ProcessResult._get_files

    def get_files(result, target):
        yield from original_get_files(result, target)
        if result is first:
            raise OSError('Test failure after successful first batch')

    monkeypatch.setattr(ProcessResult, '_get_files', get_files)

    with pytest.raises(OSError, match='Test failure'):
        first.process()
    second = ProcessResult(os.path.dirname(other_episode), process_method='copy')
    second.process()

    assert first.succeeded is False
    assert recent['torrent-hash'].pending_scans
    assert [call.args[0] for call in move.call_args_list] == ['other-torrent']


def test_staging_sibling_does_not_prevent_processing_healthy_download(create_file, torrent_processing):
    """Independent valid downloads still import while the scan keeps pending data in place."""
    episode = create_file('downloads/Good/show.s01e01.mkv')
    create_file('downloads/_UNPACK_release/Season 1/show.s01e02.mkv')
    state, _, move = torrent_processing
    result = ProcessResult(os.path.dirname(os.path.dirname(episode)), process_method='copy')

    result.process()

    assert list(state['processors']) == [episode]
    assert result.postpone_any is True
    move.assert_not_called()
