# coding=utf-8
"""Test /log route."""
from __future__ import unicode_literals
import json
import threading

from medusa.server.api.v2 import log
import pytest


@pytest.mark.parametrize('new_name, expected_name', [
    (None, 'API log test'),
    ('', 'API log test'),
    ('VUE', 'API log test :: [VUE]'),
])
def test_rename_thread_restores_original_name(monkeypatch, new_name, expected_name):
    """Temporarily add a thread label without changing the original name."""
    thread = threading.current_thread()
    monkeypatch.setattr(thread, 'name', 'API log test')

    with log.rename_thread(new_name):
        assert thread.name == expected_name

    assert thread.name == 'API log test'


@pytest.mark.parametrize('new_name', [None, '', 'VUE'])
@pytest.mark.parametrize('error_type', [RuntimeError, SystemExit])
def test_rename_thread_preserves_exceptions(monkeypatch, new_name, error_type):
    """Propagate errors and restore the thread name when the body fails."""
    thread = threading.current_thread()
    monkeypatch.setattr(thread, 'name', 'API log test')
    error = error_type('Logging failed')

    with pytest.raises(error_type) as caught:
        with log.rename_thread(new_name):
            raise error

    assert caught.value is error
    assert thread.name == 'API log test'


@pytest.mark.gen_test
async def test_log_get(http_client, create_url, auth_headers, logger, commit_hash):
    # given
    logger.info('Some {what} message', what='nice')
    url = create_url('/log')

    # when
    response = await http_client.fetch(url, **auth_headers)
    actual = json.loads(response.body)

    # then
    assert response.code == 200
    assert len(actual) == 1
    assert commit_hash == actual[0]['commit']
    assert 'INFO' == actual[0]['level']
    assert 'Some nice message' == actual[0]['message']
    assert 'thread' in actual[0]
    assert 'timestamp' in actual[0]
    assert '1' == response.headers['X-Pagination-Page']
    assert '20' == response.headers['X-Pagination-Limit']


@pytest.mark.gen_test
async def test_log_get_pagination(http_client, create_url, auth_headers, logger, commit_hash):
    # given
    logger.info('Some {what} message 1', what='nice')
    logger.info('Some {what} message 2', what='nice')
    logger.info('Some {what} message 3', what='nice')
    url = create_url('/log', limit=2, page=2)

    # when
    response = await http_client.fetch(url, **auth_headers)
    actual = json.loads(response.body)

    # then
    assert response.code == 200
    assert len(actual) == 1
    assert commit_hash == actual[0]['commit']
    assert 'INFO' == actual[0]['level']
    assert 'Some nice message 1' == actual[0]['message']
    assert 'thread' in actual[0]
    assert 'timestamp' in actual[0]
    assert '2' == response.headers['X-Pagination-Page']
    assert '2' == response.headers['X-Pagination-Limit']


@pytest.mark.gen_test
async def test_log_post(monkeypatch, http_client, create_url, auth_headers, logger, read_loglines):
    # given
    monkeypatch.setattr(log, 'log', logger)
    url = create_url('/log')
    body = {
        'message': 'Some %s {here}',
        'args': ['nice'],
        'kwargs': {
            'here': 'message'
        },
        'level': 'ERROR',
        'thread': 'Vue',
    }

    # when
    response = await http_client.fetch(url, method='POST', body=json.dumps(body), **auth_headers)
    actual = list(read_loglines)

    # then
    assert response.code == 201
    assert not response.body
    assert len(actual) == 1
    assert 'Some nice message' == actual[0].message
    assert 'ERROR' == actual[0].level_name
    assert 'VUE' == actual[0].extra
