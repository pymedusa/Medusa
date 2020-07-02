# coding=utf-8

import json
import os

import pytest


@pytest.fixture
def response_mock(requests_mock):
    def mock(client, method, uri):
        name = '{0}_{1}.json'.format(client.lower(), method)
        resp = os.path.join(os.path.dirname(__file__), 'responses', name)
        with open(resp) as json_file:
            data = json.load(json_file)
            requests_mock.post(uri, json=data)

    return mock
