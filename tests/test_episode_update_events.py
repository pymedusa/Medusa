# coding=utf-8
"""Regression tests for episode notifications after database commits."""
from __future__ import unicode_literals

import json
import threading

from medusa import app, db, ws
from medusa.common import SKIPPED, SNATCHED, UNAIRED, WANTED
from medusa.search import core
from medusa.server.api.v2 import internal, search
from medusa.tv.episode import Episode
from medusa.tv.series import Series

from mock.mock import Mock

import pytest


@pytest.fixture
def recorded_events(monkeypatch):
    """Record completed database writes and pushed WebSocket notifications in order."""
    events = []
    database = Mock()

    def commit(queries):
        events.append(('commit', len(queries)))
        return [[] for _ in queries]

    database.mass_action.side_effect = commit
    database.upsert.side_effect = lambda *args: events.append(('commit', 1))
    monkeypatch.setattr(db, 'DBConnection', Mock(return_value=database))

    def message(event, payload):
        return Mock(push=lambda: events.append((event, payload)))

    monkeypatch.setattr(ws, 'Message', message)
    return events, database


def make_episode(show_slug, season, episode_number, status=SKIPPED):
    """Provide episode data while exercising the real status-update method."""
    episode = Mock()
    episode.series.name = 'Example Show'
    episode.season = season
    episode.episode = episode_number
    episode.slug = 's{0:02d}e{1:02d}'.format(season, episode_number)
    episode.status = status
    episode.lock = threading.RLock()
    episode.manually_searched = False
    episode.get_sql.return_value = ['UPDATE tv_episodes SET status = ?', [status]]
    episode.to_json.side_effect = lambda: {
        'series': show_slug, 'season': season, 'episode': episode_number, 'status': episode.status
    }
    episode.mass_update_episode_status.side_effect = lambda new_status: Episode.mass_update_episode_status(episode, new_status)
    return episode


def test_preparing_status_batch_does_not_emit_before_commit(recorded_events):
    """Preparing an SQL statement alone must not advertise a persisted episode."""
    episode = make_episode('tvdb123', 1, 1)

    assert episode.mass_update_episode_status(WANTED)

    assert episode.status == WANTED
    assert recorded_events[0] == []


@pytest.mark.parametrize('write_fails', [False, True, 'uncommitted'])
def test_snatch_emits_all_episodes_only_after_commit(monkeypatch, recorded_events, write_fails):
    """A multi-episode snatch becomes visible only after its whole batch is saved."""
    events, database = recorded_events
    monkeypatch.setattr(app, 'ALLOW_HIGH_PRIORITY', False)
    monkeypatch.setattr(app, 'NZB_METHOD', 'blackhole')
    monkeypatch.setattr(app, 'USE_FAILED_DOWNLOADS', False)
    monkeypatch.setattr(app, 'USE_TRAKT', False)
    monkeypatch.setattr(core, '_download_result', Mock(return_value=True))
    monkeypatch.setattr(core, 'is_first_best_match', Mock(return_value=False))
    monkeypatch.setattr(core.history, 'log_snatch', Mock())
    monkeypatch.setattr(core.ui.notifications, 'message', Mock())
    monkeypatch.setattr(core.notifiers, 'notify_snatch', Mock())
    result = Mock()
    result.episodes = [make_episode('tvdb123', 1, 1), make_episode('tvdb123', 1, 2)]
    result.proper_tags = []
    result.result_type = 'nzb'
    result.manually_searched = True
    if write_fails == 'uncommitted':
        database.mass_action.side_effect = lambda queries: []
        core.snatch_result(result)
        assert events == []
    elif write_fails:
        database.mass_action.side_effect = OSError('write failed')
        with pytest.raises(OSError):
            core.snatch_result(result)
        assert events == []
    else:
        assert core.snatch_result(result) is True
        assert [event for event, _ in events] == ['commit', 'episodeUpdated', 'episodeUpdated']
        assert [payload['episode'] for _, payload in events[1:]] == [1, 2]
        assert all(payload['status'] == SNATCHED for _, payload in events[1:])


@pytest.mark.parametrize('write_fails', [False, True, 'uncommitted'])
def test_manual_status_batch_emits_each_show_after_commit(monkeypatch, recorded_events, write_fails):
    """Cross-show status changes emit only saved episodes after the shared transaction."""
    events, database = recorded_events
    first = make_episode('tvdb123', 1, 1)
    rejected = make_episode('tvdb123', 1, 2, UNAIRED)
    second = make_episode('tvdb124', 1, 1)
    series = {123: first.series, 124: second.series}
    monkeypatch.setattr(Series, 'find_by_identifier', Mock(side_effect=lambda identifier: series[identifier.id]))
    monkeypatch.setattr(Episode, 'find_by_series_and_episode', Mock(side_effect=lambda show, number: (
        second if show is second.series else first if number.episode == 1 else rejected
    )))
    handler = Mock()
    handler.request.body = json.dumps({
        'status': WANTED,
        'shows': [
            {'slug': 'tvdb123', 'episodes': ['s01e01', 's01e02']},
            {'slug': 'tvdb124', 'episodes': ['s01e01']}
        ]
    })
    if write_fails == 'uncommitted':
        database.mass_action.side_effect = lambda queries: []
        internal.InternalHandler.resource_update_episode_status(handler)
        assert events == []
    elif write_fails:
        database.mass_action.side_effect = OSError('write failed')
        with pytest.raises(OSError):
            internal.InternalHandler.resource_update_episode_status(handler)
        assert events == []
    else:
        internal.InternalHandler.resource_update_episode_status(handler)
        assert [event for event, _ in events] == ['commit', 'episodeUpdated', 'episodeUpdated']
        assert {payload['series'] for _, payload in events[1:]} == {'tvdb123', 'tvdb124'}
        assert all(payload['status'] == WANTED for _, payload in events[1:])
        handler._ok.assert_called_once_with(data={'count': 2})


@pytest.mark.parametrize('write_fails', [False, True, 'uncommitted'])
def test_backlog_status_updates_follow_each_segment_commit(monkeypatch, recorded_events, write_fails):
    """A queued backlog segment must publish statuses after its own write succeeds."""
    events, database = recorded_events
    first = make_episode('tvdb123', 1, 1)
    second = make_episode('tvdb123', 2, 1)
    monkeypatch.setattr(Series, 'find_by_identifier', Mock(return_value=first.series))
    monkeypatch.setattr(search, 'BacklogQueueItem', Mock())
    monkeypatch.setattr(app, 'forced_search_queue_scheduler', Mock())
    handler = Mock()
    handler._get_episode_segments.return_value = {1: [first], 2: [second]}
    data = {'showSlug': 'tvdb123', 'episodes': ['s01e01', 's02e01']}
    if write_fails == 'uncommitted':
        database.mass_action.side_effect = lambda queries: []
        search.SearchHandler._search_backlog(handler, data)
        assert events == []
    elif write_fails:
        database.mass_action.side_effect = OSError('write failed')
        with pytest.raises(OSError):
            search.SearchHandler._search_backlog(handler, data)
        assert events == []
        app.forced_search_queue_scheduler.action.add_item.assert_not_called()
    else:
        search.SearchHandler._search_backlog(handler, data)
        assert [event for event, _ in events] == ['commit', 'episodeUpdated', 'commit', 'episodeUpdated']
        assert [events[index][1]['season'] for index in (1, 3)] == [1, 2]


@pytest.mark.parametrize('write_fails', [False, True])
def test_single_episode_save_keeps_postcommit_notification(recorded_events, write_fails):
    """The existing individual-save path emits only after a successful database write."""
    events, database = recorded_events
    episode = make_episode('tvdb123', 1, 1)
    episode.subtitles = []
    if write_fails:
        database.upsert.side_effect = OSError('write failed')
        with pytest.raises(OSError):
            Episode.save_to_db(episode)
        assert events == []
    else:
        Episode.save_to_db(episode)
        assert [event for event, _ in events] == ['commit', 'episodeUpdated']
