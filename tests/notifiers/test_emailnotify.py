# coding=utf-8
"""Tests for medusa.notifiers.emailnotify module."""

from __future__ import unicode_literals

from medusa.notifiers.emailnotify import Notifier

import pytest

from six import text_type


@pytest.mark.parametrize('p', [
    {  # p0 - Fail and fallback to legacy parsing
        'ep_name': 'Archer - 9x02 -x Danger Island - Disheartening Situation - 1080p WEB-DL',
        'expected': {
            'show': 'Archer',
            'episode': '9x02 -x Danger Island - Disheartening Situation - 1080p WEB-DL'
        }
    },
    {  # p1 - [%SN - %Sx%0E - %EN - %QN] - hypen in episode name
        'ep_name': 'Archer - 9x02 - Danger Island - Disheartening Situation - 1080p WEB-DL',
        'expected': {
            'show': 'Archer',
            'ep_id': '9x02',
            'episode': 'Danger Island - Disheartening Situation - 1080p WEB-DL'
        }
    },
    {  # p2 - [%SN - %Sx%0E - %EN - %QN]
        'ep_name': 'Jersey Shore Family Vacation - 1x06 - Meatball Down - 1080p WEB-DL',
        'expected': {
            'show': 'Jersey Shore Family Vacation',
            'ep_id': '1x06',
            'episode': 'Meatball Down - 1080p WEB-DL'
        }
    },
    {  # p3 - [%SN - %Sx%0E - %EN - %QN] - empty episode name
        'ep_name': 'Jersey Shore Family Vacation - 1x06 -  - 1080p WEB-DL',
        'expected': {
            'show': 'Jersey Shore Family Vacation',
            'ep_id': '1x06',
            'episode': ' - 1080p WEB-DL'
        }
    },
    {  # p4 - [%SN - %Sx%0E - %EN - %QN] - with additions
        'ep_name': 'Jersey Shore Family Vacation - 1x06 - Meatball Down - 1080p WEB-DL with {seeders} seeders and {leechers} leechers from {provider}',
        'expected': {
            'show': 'Jersey Shore Family Vacation',
            'ep_id': '1x06',
            'episode': 'Meatball Down - 1080p WEB-DL with {seeders} seeders and {leechers} leechers from {provider}'
        }
    },
    {  # p5 - [%SN - %Sx%0E - %AB - %EN - %QN] - hypen in episode name
        'ep_name': 'Archer - 9x02 - 092 - Danger Island - Disheartening Situation - 1080p WEB-DL',
        'expected': {
            'show': 'Archer',
            'ep_id': '9x02 - 092',
            'episode': 'Danger Island - Disheartening Situation - 1080p WEB-DL'
        }
    },
    {  # p6 - [%SN - %Sx%0E - %AB - %EN - %QN]
        'ep_name': 'Jersey Shore Family Vacation - 1x06 - 006 - Meatball Down - 1080p WEB-DL',
        'expected': {
            'show': 'Jersey Shore Family Vacation',
            'ep_id': '1x06 - 006',
            'episode': 'Meatball Down - 1080p WEB-DL'
        }
    },
    {  # p7 - [%SN - %Sx%0E - %AB - %EN - %QN] - empty episode name
        'ep_name': 'Jersey Shore Family Vacation - 1x06 - 006 -  - 1080p WEB-DL',
        'expected': {
            'show': 'Jersey Shore Family Vacation',
            'ep_id': '1x06 - 006',
            'episode': ' - 1080p WEB-DL'
        }
    },
    {  # p8 - [%SN - %AB - %EN] - hypen in episode name
        'ep_name': 'Archer - 092 - Danger Island - Disheartening Situation',
        'expected': {
            'show': 'Archer',
            'ep_id': '092',
            'episode': 'Danger Island - Disheartening Situation'
        }
    },
    {  # p9 - [%SN - %AB - %EN]
        'ep_name': 'Jersey Shore Family Vacation - 006 - Meatball Down',
        'expected': {
            'show': 'Jersey Shore Family Vacation',
            'ep_id': '006',
            'episode': 'Meatball Down'
        }
    },
    {  # p10 - [%SN - %AB - %EN] - empty episode name
        'ep_name': 'Jersey Shore Family Vacation - 006 - ',
        'expected': {
            'show': 'Jersey Shore Family Vacation',
            'ep_id': '006',
            'episode': ''
        }
    },
    {  # p11 - [%SN - %AD - %EN] - hypen in episode name
        'ep_name': 'Archer - 2017 08 12 - Danger Island - Disheartening Situation',
        'expected': {
            'show': 'Archer',
            'ep_id': '2017 08 12',
            'episode': 'Danger Island - Disheartening Situation'
        }
    },
    {  # p12 - [%SN - %AD - %EN]
        'ep_name': 'Jersey Shore Family Vacation - 2018 04 20 - Meatball Down',
        'expected': {
            'show': 'Jersey Shore Family Vacation',
            'ep_id': '2018 04 20',
            'episode': 'Meatball Down'
        }
    },
    {  # p13 - [%SN - %AD - %EN] - empty episode name
        'ep_name': 'Jersey Shore Family Vacation - 2018 04 20 - ',
        'expected': {
            'show': 'Jersey Shore Family Vacation',
            'ep_id': '2018 04 20',
            'episode': ''
        }
    },
    {  # p14 - [%SN - S%0SE%0E - %EN]
        'ep_name': 'Jersey Shore Family Vacation - S01E06 - Meatball Down',
        'expected': {
            'show': 'Jersey Shore Family Vacation',
            'ep_id': 'S01E06',
            'episode': 'Meatball Down'
        }
    },
    {  # p15 - [%SN - S%0SE%0E - %EN] - with absolute number
        'ep_name': 'Jersey Shore Family Vacation - S01E06 - 006 - Meatball Down',
        'expected': {
            'show': 'Jersey Shore Family Vacation',
            'ep_id': 'S01E06 - 006',
            'episode': 'Meatball Down'
        }
    },
    {  # p16 - [%SN - S%0SE%0E - %EN] - with absolute number and hypen in show name
        'ep_name': 'Jersey Shore - Family Vacation - S01E06 - 006 - Meatball Down',
        'expected': {
            'show': 'Jersey Shore - Family Vacation',
            'ep_id': 'S01E06 - 006',
            'episode': 'Meatball Down'
        }
    },
])
def test__parse_name(p):
    # Given
    ep_name = p['ep_name']
    expected = p['expected']

    # When
    actual = Notifier._parse_name(ep_name)

    # Then
    assert actual == expected


@pytest.mark.parametrize('p', [
    {  # p0 - not show-specific
        'show': None,
        'EMAIL_LIST': [
            'admin@pymedusa.com',
            'sameuser@pymedusa.com',
            'sameuser@pymedusa.com',
        ],
        'mocks': [],
        'expected': {
            'admin@pymedusa.com',
            'sameuser@pymedusa.com',
        }
    },
    {  # p1 - show-specific, no emails legacy
        'show': 'Show Name',
        'EMAIL_LIST': [
            'admin@pymedusa.com',
            'sameuser@pymedusa.com',
        ],
        'mocks': [
            ('medusa.db.DBConnection.select', [{
                'notify_list': None
            }])
        ],
        'expected': {
            'admin@pymedusa.com',
            'sameuser@pymedusa.com'
        }
    },
    {  # p2 - show-specific, no emails
        'show': 'Show Name',
        'EMAIL_LIST': [
            'admin@pymedusa.com',
            'sameuser@pymedusa.com',
        ],
        'mocks': [
            ('medusa.db.DBConnection.select', [{
                'notify_list': '{}'
            }])
        ],
        'expected': {
            'admin@pymedusa.com',
            'sameuser@pymedusa.com',
        }
    },
    {  # p3 - show-specific, new style
        'show': 'Show Name',
        'EMAIL_LIST': [
            'admin@pymedusa.com',
            'sameuser@pymedusa.com',
        ],
        'mocks': [
            ('medusa.db.DBConnection.select', [{
                'notify_list': '{"emails": "sameuser@pymedusa.com,user1@pymedusa.com"}'
            }])
        ],
        'expected': {
            'admin@pymedusa.com',
            'sameuser@pymedusa.com',
            'user1@pymedusa.com'
        }
    }
])
def test__generate_recipients(p, app_config, monkeypatch_function_return):
    # Given
    show = p['show']
    expected = p['expected']

    app_config('EMAIL_LIST', p['EMAIL_LIST'])
    if show:
        monkeypatch_function_return(p['mocks'])

    # When
    actual = Notifier._generate_recipients(show)

    # Then
    assert actual == expected
