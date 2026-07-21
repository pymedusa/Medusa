# coding=utf-8

from medusa.clients.torrent.qbittorrent import QBittorrentAPI

import pytest


class SearchResultStub(object):
    """Minimal search result stub for torrent client tests."""

    hash = 'aabbccdd'


def _state_requests(requests_mock):
    """Return POST requests made to torrent state endpoints."""
    return [
        request for request in requests_mock.request_history
        if request.method == 'POST' and '/api/v2/torrents/' in request.url
        and not request.url.endswith('/add')
    ]


def _mock_qbittorrent_auth(requests_mock, api_text='2.15.1'):
    """Mock auth and Web API version lookups performed during client construction."""
    requests_mock.post('http://localhost/api/v2/auth/login', text='Ok.', status_code=200)
    requests_mock.get('http://localhost/api/v2/app/webapiVersion', text=api_text)


def _make_qbittorrent_client(api=(2, 15, 1)):
    """Return a QBittorrentAPI instance without triggering constructor HTTP calls."""
    client = QBittorrentAPI.__new__(QBittorrentAPI)
    client.name = 'qBittorrent'
    client.host = 'http://localhost/'
    client.api = api
    client.auth = True
    client.session = None
    return client


def test_auth_v2_empty_204_response_is_success(requests_mock):
    # Given
    requests_mock.post('http://localhost/api/v2/auth/login', text='', status_code=204)
    requests_mock.get('http://localhost/api/v2/app/webapiVersion', text='2.14.0')

    # When
    client = QBittorrentAPI(host='http://localhost')

    # Then
    assert client.auth is True
    assert client.api == (2, 14, 0)


def test_auth_v2_legacy_ok_response_is_success(requests_mock):
    # Given
    requests_mock.post('http://localhost/api/v2/auth/login', text='Ok.', status_code=200)
    requests_mock.get('http://localhost/api/v2/app/webapiVersion', text='2.13.1')

    # When
    client = QBittorrentAPI(host='http://localhost')

    # Then
    assert client.auth == 'Ok.'
    assert client.api == (2, 13, 1)


def test_auth_v2_legacy_fails_response_is_invalid_credentials(requests_mock):
    # Given
    requests_mock.post('http://localhost/api/v2/auth/login', text='Fails.', status_code=200)

    # When
    client = QBittorrentAPI(host='http://localhost')

    # Then
    assert client.auth is None
    assert client.api is None


def test_auth_v2_401_response_is_invalid_credentials(requests_mock):
    # Given
    requests_mock.post('http://localhost/api/v2/auth/login', text='', status_code=401)

    # When
    client = QBittorrentAPI(host='http://localhost')

    # Then
    assert client.auth is None
    assert client.api is None


def test_auth_v2_404_falls_back_to_legacy_api(requests_mock):
    # Given
    requests_mock.post('http://localhost/api/v2/auth/login', status_code=404)
    requests_mock.post('http://localhost/login', status_code=200)
    requests_mock.get('http://localhost/version/api', text='17')

    # When
    client = QBittorrentAPI(host='http://localhost')

    # Then
    assert client.auth is True
    assert client.api == (1, 17, 0)


def test_add_torrent_uri_accepts_async_response(requests_mock, monkeypatch):
    # Given
    class Series(object):
        is_anime = False

    class Result(object):
        url = 'magnet:?xt=urn:btih:aabbcc'
        series = Series()

    monkeypatch.setattr('medusa.app.TORRENT_PATH', '')
    monkeypatch.setattr('medusa.app.TORRENT_LABEL', '')

    requests_mock.post('http://localhost/api/v2/auth/login', text='', status_code=200)
    requests_mock.get('http://localhost/api/v2/app/webapiVersion', text='2.14.0')
    client = QBittorrentAPI(host='http://localhost')
    client.api = (2, 14, 0)
    requests_mock.post(
        'http://localhost/api/v2/torrents/add',
        json={
            'success_count': 0,
            'failure_count': 0,
            'pending_count': 1,
            'added_torrent_ids': [],
        },
        status_code=202,
    )

    # When
    actual = client._add_torrent_uri(Result())

    # Then
    assert actual is True


def test_add_torrent_uri_accepts_legacy_ok_response(requests_mock, monkeypatch):
    # Given
    class Series(object):
        is_anime = False

    class Result(object):
        url = 'magnet:?xt=urn:btih:aabbcc'
        series = Series()

    monkeypatch.setattr('medusa.app.TORRENT_PATH', '')
    monkeypatch.setattr('medusa.app.TORRENT_LABEL', '')

    requests_mock.post('http://localhost/api/v2/auth/login', text='Ok.', status_code=200)
    requests_mock.get('http://localhost/api/v2/app/webapiVersion', text='2.13.1')
    client = QBittorrentAPI(host='http://localhost')
    requests_mock.post('http://localhost/api/v2/torrents/add', text='Ok.', status_code=200)

    # When
    actual = client._add_torrent_uri(Result())

    # Then
    assert actual is True


@pytest.mark.parametrize('api_version,torrent_paused,torrent_stopped,expected_endpoint', [
    ((2, 10, 0), False, False, 'resume'),
    ((2, 10, 0), True, False, 'pause'),
    ((2, 10, 0), False, True, 'pause'),
    ((2, 11, 2), False, False, 'start'),
    ((2, 15, 1), True, False, 'stop'),
    ((2, 15, 1), False, True, 'stop'),
])
def test_set_torrent_state_uses_single_endpoint_for_api_version(
        api_version, torrent_paused, torrent_stopped, expected_endpoint, requests_mock, monkeypatch):
    # Given
    monkeypatch.setattr('medusa.app.TORRENT_PAUSED', torrent_paused)
    monkeypatch.setattr('medusa.app.TORRENT_STOPPED', torrent_stopped)
    _mock_qbittorrent_auth(requests_mock, api_text='.'.join(str(part) for part in api_version))

    for endpoint in ('resume', 'pause', 'start', 'stop'):
        requests_mock.post(
            'http://localhost/api/v2/torrents/{0}'.format(endpoint),
            text='',
            status_code=200,
        )

    client = QBittorrentAPI(host='http://localhost')
    client.api = api_version
    client.auth = True

    # When
    actual = client._set_torrent_state(SearchResultStub())

    # Then
    assert actual is True
    state_requests = _state_requests(requests_mock)
    assert len(state_requests) == 1
    assert state_requests[0].url.endswith('/api/v2/torrents/{0}'.format(expected_endpoint))


def test_set_torrent_state_new_api_does_not_call_legacy_endpoints(requests_mock, monkeypatch):
    # Given
    monkeypatch.setattr('medusa.app.TORRENT_PAUSED', False)
    monkeypatch.setattr('medusa.app.TORRENT_STOPPED', False)
    _mock_qbittorrent_auth(requests_mock, api_text='2.15.1')
    requests_mock.post('http://localhost/api/v2/torrents/start', text='', status_code=200)

    client = QBittorrentAPI(host='http://localhost')
    client.api = (2, 15, 1)
    client.auth = True

    # When
    client._set_torrent_state(SearchResultStub())

    # Then
    state_requests = _state_requests(requests_mock)
    assert len(state_requests) == 1
    assert state_requests[0].url.endswith('/torrents/start')
    assert not any('/torrents/resume' in request.url for request in requests_mock.request_history)
    assert not any('/torrents/pause' in request.url for request in requests_mock.request_history)


def test_set_torrent_state_old_api_does_not_call_start_stop_endpoints(requests_mock, monkeypatch):
    # Given
    monkeypatch.setattr('medusa.app.TORRENT_PAUSED', False)
    monkeypatch.setattr('medusa.app.TORRENT_STOPPED', False)
    _mock_qbittorrent_auth(requests_mock, api_text='2.10.0')
    requests_mock.post('http://localhost/api/v2/torrents/resume', text='', status_code=200)

    client = QBittorrentAPI(host='http://localhost')
    client.api = (2, 10, 0)
    client.auth = True

    # When
    client._set_torrent_state(SearchResultStub())

    # Then
    state_requests = _state_requests(requests_mock)
    assert len(state_requests) == 1
    assert state_requests[0].url.endswith('/torrents/resume')
    assert not any('/torrents/start' in request.url for request in requests_mock.request_history)
    assert not any('/torrents/stop' in request.url for request in requests_mock.request_history)


@pytest.mark.parametrize('qbit_state,expected_status', [
    ('downloading', 'Downloading'),
    ('metaDL', 'Downloading'),
    ('stoppedDL', 'Paused'),
    ('pausedDL', 'Paused'),
    ('stalledUP', 'Completed'),
    ('stoppedUP', 'Completed'),
    ('error', 'Failed'),
])
def test_get_status_maps_qbittorrent_states(qbit_state, expected_status):
    # Given
    info_hash = 'aabbccdd'
    torrent = {
        'hash': info_hash,
        'state': qbit_state,
        'ratio': 0,
        'downloaded': 100,
        'size': 1000,
        'save_path': '/downloads',
        'content_path': '/downloads/show.mkv',
    }

    client = _make_qbittorrent_client()
    client._get_torrents = lambda **kwargs: [torrent]

    # When
    status = client.get_status(info_hash)

    # Then
    assert str(status) == expected_status


def test_get_status_unknown_state_does_not_raise():
    # Given
    info_hash = 'aabbccdd'
    torrent = {
        'hash': info_hash,
        'state': 'futureState',
        'ratio': 0,
        'downloaded': 0,
        'size': 0,
        'save_path': '/downloads',
    }

    client = _make_qbittorrent_client()
    client._get_torrents = lambda **kwargs: [torrent]

    # When
    status = client.get_status(info_hash)

    # Then
    assert status is not None
    assert status.progress == 0


def test_get_status_coerces_string_numeric_fields():
    # Given — some qBittorrent setups return numeric fields as strings
    info_hash = 'aabbccdd'
    torrent = {
        'hash': info_hash,
        'state': 'downloading',
        'ratio': '1.5',
        'downloaded': '250',
        'size': '1000',
        'save_path': '/downloads',
        'content_path': '/downloads/show.mkv',
    }

    client = _make_qbittorrent_client()
    client._get_torrents = lambda **kwargs: [torrent]

    # When
    status = client.get_status(info_hash)

    # Then
    assert str(status) == 'Downloading'
    assert status.ratio == 1.5
    assert status.progress == 25


def test_get_status_uses_progress_field_when_present():
    # Given
    info_hash = 'aabbccdd'
    torrent = {
        'hash': info_hash,
        'state': 'downloading',
        'ratio': 0.5,
        'progress': 0.42,
        'downloaded': 'unused',
        'size': 'unused',
        'save_path': '/downloads',
        'content_path': '/downloads/show.mkv',
    }

    client = _make_qbittorrent_client()
    client._get_torrents = lambda **kwargs: [torrent]

    # When
    status = client.get_status(info_hash)

    # Then
    assert status.progress == 42


def test_torrent_completed(requests_mock):
    # Given
    requests_mock.post(
        'http://localhost/api/v2/auth/login',
        text='Ok.',
        status_code=200,
    )
    requests_mock.get(
        'http://localhost/api/v2/app/webapiVersion',
        text='2.0.0',
    )
    requests_mock.get(
        'http://localhost/api/v2/torrents/info',
        json=[{
            'hash': 'aabbcc',
            'state': 'uploading',
            'ratio': 0,
            'downloaded': 1000,
            'size': 1000,
            'save_path': '/downloads',
            'content_path': '/downloads/show.mkv',
        }],
    )

    # When
    client = QBittorrentAPI(host='http://localhost')
    client.api = (2, 0, 0)
    client.auth = True

    actual = client.torrent_completed('aabbcc')

    # Then
    assert actual is True

    info_requests = [
        request for request in requests_mock.request_history
        if request.method == 'GET'
        and request.url.endswith('/api/v2/torrents/info')
    ]
    assert len(info_requests) == 1
