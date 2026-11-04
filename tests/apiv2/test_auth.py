# coding=utf-8
"""Test /authentication route and authentication checks."""
from __future__ import unicode_literals

import json

import pytest


@pytest.mark.gen_test
async def test_no_api_key(http_client, create_url):
    # given
    expected = {'error': 'No authorization token.'}

    url = create_url('/log', api_key=None)

    # when
    response = await http_client.fetch(url, raise_error=False)

    # then
    assert response.code == 401
    assert expected == json.loads(response.body)


@pytest.mark.gen_test
async def test_bad_api_key(http_client, create_url):
    # given
    expected = {'error': 'No authorization token.'}

    url = create_url('/log', api_key='123')

    # when
    response = await http_client.fetch(url, raise_error=False)

    # then
    assert response.code == 401
    assert expected == json.loads(response.body)


@pytest.mark.parametrize('password,submitted_password,expected_status', [
    ('password', 'password', 200),
    ('pass:word', 'pass:word', 200),
    ('pass:word:again', 'pass:word:again', 200),
    (':leading', ':leading', 200),
    ('trailing:', 'trailing:', 200),
    (':', ':', 200),
    ('@\'"#%%&/():\\', '@\'"#%%&/():\\', 200),
    ('p\u00e6ssw\u00f8rd:\u00e5', 'p\u00e6ssw\u00f8rd:\u00e5', 200),
    ('pass:word', 'pass', 401),
    ('pass:word', 'pass:wrong', 401),
])
@pytest.mark.gen_test
async def test_basic_auth_password(http_client, create_url, app_config, password, submitted_password, expected_status):
    """Basic authentication preserves colons in passwords and rejects mismatches."""
    app_config('WEB_USERNAME', 'alice')
    app_config('WEB_PASSWORD', password)
    app_config('showList', [])
    url = create_url('/series', api_key=None)

    response = await http_client.fetch(
        url, auth_username='alice', auth_password=submitted_password, raise_error=False
    )

    assert response.code == expected_status
    if expected_status == 200:
        assert json.loads(response.body) == []
    else:
        assert json.loads(response.body) == {'error': 'Invalid user/pass.'}
