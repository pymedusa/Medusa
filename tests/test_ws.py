# coding=utf-8
"""Tests for medusa/ws/*.py."""
from __future__ import unicode_literals

import json

from medusa import ws

import pytest


@pytest.mark.parametrize('p', [
    {  # p0
        'event': 'notification',
        'data': {
            'title': 'Medusa',
            'body': 'Welcome',
            'type': 'notice',
            'hash': 1234
        }
    },
])
def test_message_class(p):
    # Given
    event = p['event']
    data = p['data']
    expected = {
        'event': event,
        'data': data
    }

    # When
    msg = ws.Message(event, data)

    # Then
    assert expected == msg.content
    assert json.dumps(expected) == msg.json()
