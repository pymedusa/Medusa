# coding=utf-8
"""Test /show route."""
import json

import pytest


@pytest.mark.gen_test
def test_show_get_no_shows(http_client, create_url, auth_headers):
    # given
    url = create_url('/show')

    # when
    response = yield http_client.fetch(url, **auth_headers)
    actual = json.loads(response.body)

    # then
    assert response.code == 200
    assert '1' == response.headers['X-Pagination-Page']
    assert '20' == response.headers['X-Pagination-Limit']
    assert '0' == response.headers['X-Pagination-Count']
    assert [] == actual
