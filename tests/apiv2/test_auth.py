# coding=utf-8
"""Test /authentication route and authentication checks."""
from __future__ import unicode_literals

import json

import pytest


@pytest.mark.gen_test
def test_no_api_key(http_client, create_url):
    # given
    expected = {'error': 'No authorization token.'}

    url = create_url('/log', api_key=None)

    # when
    response = yield http_client.fetch(url, raise_error=False)

    # then
    assert response.code == 401
    assert expected == json.loads(response.body)


@pytest.mark.gen_test
def test_bad_api_key(http_client, create_url):
    # given
    expected = {'error': 'No authorization token.'}

    url = create_url('/log', api_key='123')

    # when
    response = yield http_client.fetch(url, raise_error=False)

    # then
    assert response.code == 401
    assert expected == json.loads(response.body)
