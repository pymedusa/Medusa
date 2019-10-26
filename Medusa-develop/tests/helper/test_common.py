# coding=utf-8
"""Tests for medusa.helper.common module."""

from __future__ import unicode_literals

import medusa.helper.common as sut

import pytest

from six import iteritems


@pytest.mark.parametrize('p', [
    {  # p0 - bytes test cases
        None: None,
        b'': None,
        b'123': None,
        b'12.3': None,
        b'-123': None,
        b'-12.3': None,
        b'300': 'Multiple Choices',
        0: None,
        123: None,
        12.3: None,
        -123: None,
        -12.3: None,
        300: 'Multiple Choices',
        451: '(Redirect, Unavailable For Legal Reasons)',
        497: 'HTTP to HTTPS',
        499: '(Client Closed Request, Token required)',
        600: None,
    },
    {  # p1 - unicode test cases
        '': None,
        '123': None,
        '12.3': None,
        '-123': None,
        '-12.3': None,
        '300': 'Multiple Choices',
    }
])
def test_http_code_description(p):
    for (http_code, result) in iteritems(p):
        assert sut.http_code_description(http_code) == result


@pytest.mark.parametrize('p', [
    {  # p0 - special test cases
        None: False,
        42: False,
        b'': False,
    },
    {  # p1 - unicode test cases
        '': False,
        'filename': False,
        '.syncthingfilename': True,
        '.syncthing.filename': True,
        '.syncthing-filename': True,
        '.!sync': True,
        'file.!sync': True,
        'file.!sync.ext': False,
        '.lftp-pget-status': True,
        'file.lftp-pget-status': True,
        'file.lftp-pget-status.ext': False,
        '.part': True,
        'file.part': True,
        'file.part.ext': False,
    }
])
def test_is_sync_file(p, app_config):
    app_config('SYNC_FILES', ['!sync', 'lftp-pget-status', 'part'])

    for (filename, result) in iteritems(p):
        assert sut.is_sync_file(filename) == result


@pytest.mark.parametrize('p', [
    {  # p0 - special test cases
        None: False,
        42: False,
    },
    {  # p1 - unicode test cases
        '': False,
        'filename': False,
        '.nzb': True,
        'file.nzb': True,
        'file.nzb.part': False,
        '.torrent': True,
        'file.torrent': True,
        'file.torrent.part': False,
    }
])
def test_is_torrent_or_nzb_file(p):
    for (filename, result) in iteritems(p):
        assert sut.is_torrent_or_nzb_file(filename) == result


@pytest.mark.parametrize('p', [
    {  # p0 - bytes test cases
        b'': '0.00 B',
        b'1024': '1.00 KB',
        b'1024.5': '1.00 KB',
    },
    {  # p1 - unicode test cases
        None: '0.00 B',
        '': '0.00 B',
        '1024': '1.00 KB',
        '1024.5': '1.00 KB',
        -42.5: '0.00 B',
        -42: '0.00 B',
        0: '0.00 B',
        25: '25.00 B',
        25.5: '25.50 B',
        2 ** 10: '1.00 KB',
        50 * 2 ** 10 + 25: '50.02 KB',
        2 ** 20: '1.00 MB',
        100 * 2 ** 20 + 50 * 2 ** 10 + 25: '100.05 MB',
        2 ** 30: '1.00 GB',
        200 * 2 ** 30 + 100 * 2 ** 20 + 50 * 2 ** 10 + 25: '200.10 GB',
        2 ** 40: '1.00 TB',
        400 * 2 ** 40 + 200 * 2 ** 30 + 100 * 2 ** 20 + 50 * 2 ** 10 + 25: '400.20 TB',
        2 ** 50: '1.00 PB',
        800 * 2 ** 50 + 400 * 2 ** 40 + 200 * 2 ** 30 + 100 * 2 ** 20 + 50 * 2 ** 10 + 25: '800.39 PB',
        2 ** 60: 2 ** 60,
    }
])
def test_pretty_file_size(p):
    for (size, result) in iteritems(p):
        assert sut.pretty_file_size(size) == result


@pytest.mark.parametrize('p', [
    {  # p0 - special test cases
        None: None,
        42: 42,
    },
    {  # p1 - unicode test cases
        '': '',
        '.': '.',
        'filename': 'filename',
        '.bashrc': '.bashrc',
        '.nzb': '.nzb',
        'file.nzb': 'file',
        'file.name.nzb': 'file.name',
        '.torrent': '.torrent',
        'file.torrent': 'file',
        'file.name.torrent': 'file.name',
        '.avi': '.avi',
        'file.avi': 'file',
        'file.name.avi': 'file.name',
    }
])
def test_remove_extension(p):
    for (extension, result) in iteritems(p):
        assert sut.remove_extension(extension) == result


@pytest.mark.parametrize('p', [
    {  # p0 - special test cases
        (None, None): None,
        (None, b''): None,
        (42, None): 42,
        (42, b''): 42,
        (b'', None): b'',
        (b'', b''): b'',
        (b'.', None): b'.',
        (b'.', b''): b'.',
    },
    {  # p1 - unicode test cases
        (None, ''): None,
        (42, ''): 42,
        ('', ''): b'',
        ('', None): '',
        ('', b''): '',
        ('', ''): '',
        ('.', ''): b'.',
        ('.', 'avi'): b'.',
        ('.', None): '.',
        ('.', b''): '.',
        ('.', ''): '.',
        ('.', b'avi'): '.',
        ('.', 'avi'): '.',
        ('filename', ''): b'filename',
        ('filename', 'avi'): b'filename',
        ('filename', None): 'filename',
        ('filename', b''): 'filename',
        ('filename', ''): 'filename',
        ('filename', b'avi'): 'filename',
        ('filename', 'avi'): 'filename',
        ('.bashrc', ''): b'.bashrc',
        ('.bashrc', 'avi'): b'.bashrc',
        ('.bashrc', None): '.bashrc',
        ('.bashrc', b''): '.bashrc',
        ('.bashrc', ''): '.bashrc',
        ('.bashrc', 'avi'): '.bashrc',
        ('file.mkv', ''): b'file.',
        ('file.mkv', 'avi'): b'file.avi',
        ('file.mkv', None): 'file.None',
        ('file.mkv', ''): 'file.',
        ('file.mkv', 'avi'): 'file.avi',
        ('file.name.mkv', ''): b'file.name.',
        ('file.name.mkv', 'avi'): b'file.name.avi',
        ('file.name.mkv', None): 'file.name.None',
        ('file.name.mkv', ''): 'file.name.',
        ('file.name.mkv', ''): 'file.name.',
        ('file.name.mkv', 'avi'): 'file.name.avi',
    }
])
def test_replace_extension(p):
    for ((filename, extension), result) in iteritems(p):
        assert sut.replace_extension(filename, extension) == result


@pytest.mark.parametrize('value,expected', [
    # special test cases
    (None, ''),
    (42, ''),
    (b'', ''),

    # unicode test cases
    ('', ''),
    ('filename', 'filename'),
    ('fi\\le/na*me', 'fi-le-na-me'),
    ('fi:le"na<me', 'filename'),
    ('fi>le|na?me', 'filename'),
    (' . file\u2122name. .', 'filename'),
    (' . file\tname. .', 'filename'),
    (' . file\x00as\x08df\x1fname. .', 'fileasdfname'),
])
def test_sanitize_filename(value, expected):
    # Given

    # When
    actual = sut.sanitize_filename(value)

    # Then
    assert expected == actual


@pytest.mark.parametrize('value,expected', [
    # bytes test cases
    (None, 0),
    (b'', 0),
    (b'123', 123),
    (b'-123', -123),
    (b'12.3', 0),
    (b'-12.3', 0),
    (0, 0),
    (123, 123),
    (-123, -123),
    (12.3, 12),
    (-12.3, -12),

    # unicode test cases
    ('', 0),
    ('123', 123),
    ('-123', -123),
    ('12.3', 0),
    ('-12.3', 0),
])
def test_try_int(value, expected):
    # Given

    # When
    actual = sut.try_int(value)

    # Then
    assert expected == actual


@pytest.mark.parametrize('value,expected', [
    # bytes test cases
    (None, lambda: 'default_value'),
    (b'', lambda: 'default_value'),
    (b'123', 123),
    (b'-123', -123),
    (b'12.3', lambda: 'default_value'),
    (b'-12.3', lambda: 'default_value'),
    (0, 0),
    (123, 123),
    (-123, -123),
    (12.3, 12),
    (-12.3, -12),

    # unicode test cases
    ('', lambda: 'default_value'),
    ('123', 123),
    ('-123', -123),
    ('12.3', lambda: 'default_value'),
    ('-12.3', lambda: 'default_value'),
])
def test_try_int_with_default(value, expected):
    # Given
    default_value = 42

    if callable(expected):
        expected = eval(expected())

    # When
    actual = sut.try_int(value, default_value)

    # Then
    assert expected == actual


def test_convert_size():
    # converts pretty file sizes to integers
    assert sut.convert_size('1 B') == 1
    assert sut.convert_size('1 KB') == 1024
    # can use decimal units (e.g. KB = 1000 bytes instead of 1024)
    assert sut.convert_size('1 kb', use_decimal=True) == 1000

    # returns integer sizes for integers
    assert sut.convert_size(0, -1) == 0
    assert sut.convert_size(100, -1) == 100
    # returns integer sizes for floats too
    assert sut.convert_size(1.312, -1) == 1
    # return integer variant when passed as str
    assert sut.convert_size('1024', -1) == 1024

    # without a default value, failures return None
    assert sut.convert_size('pancakes') is None

    # default value can be anything
    assert sut.convert_size(None, -1) == -1
    assert sut.convert_size('', 3.14) == 3.14
    assert sut.convert_size('elephant', 'frog') == 'frog'

    # negative sizes return 0
    assert sut.convert_size(-1024, -1) == 0
    assert sut.convert_size('-1 GB', -1) == 0

    # can also use `or` for a default value
    assert sut.convert_size(None) or 100 == 100
    # default doesn't have to be integer
    assert sut.convert_size(None) or 1.61803 == 1.61803
    # default doesn't have to be numeric either
    assert sut.convert_size(None) or '100' == '100'
    # can use `or` to provide a default when size evaluates to 0
    assert sut.convert_size('-1 GB') or -1 == -1

    # default units can be kwarg'd
    assert sut.convert_size('1', default_units='GB') == sut.convert_size('1 GB')

    # separator can be kwarg'd
    assert sut.convert_size('1?GB', sep='?') == sut.convert_size('1 GB')

    # can use custom dictionary to support internationalization
    french = ['O', 'KO', 'MO', 'GO', 'TO', 'PO']
    assert sut.convert_size('1 o', units=french) == 1
    assert sut.convert_size('1 go', use_decimal=True, units=french) == 1000000000
    assert sut.convert_size('1 o') is None  # Wrong units so result is None

    # custom units need to be uppercase or they won't match
    oops = ['b', 'kb', 'Mb', 'Gb', 'tB', 'Pb']
    assert sut.convert_size('1 b', units=oops) is None
    assert sut.convert_size('1 B', units=oops) is None
    assert sut.convert_size('1 Mb', units=oops) is None
    assert sut.convert_size('1 MB', units=oops) is None

    # utilize the regex to parse sizes without separator
    assert sut.convert_size('1GB', sep='') == 1073741824
    assert sut.convert_size('1.00GB', sep='') == 1073741824
    assert sut.convert_size('1.01GB', sep='') == 1084479242
    assert sut.convert_size('1B', sep='') == 1

    # no separator and custom units
    french = ['O', 'KO', 'MO', 'GO', 'TO', 'PO']
    assert sut.convert_size('1Go', sep='', units=french) == 1073741824
    assert sut.convert_size('1.00Go', sep='', units=french) == 1073741824
    assert sut.convert_size('1.01Go', sep='', units=french) == 1084479242
    assert sut.convert_size('1o', sep='', units=french) == 1

    # no separator, custom units need to be uppercase or they won't match
    oops = ['b', 'kb', 'Mb', 'Gb', 'tB', 'Pb']
    assert sut.convert_size('1b', sep='', units=oops) is None
    assert sut.convert_size('1B', sep='', units=oops) is None
    assert sut.convert_size('1Mb', sep='', units=oops) is None
    assert sut.convert_size('1MB', sep='', units=oops) is None


def test_episode_num():
    # Standard numbering
    assert sut.episode_num(0, 1) == 'S00E01'  # Seasons start at 0 for specials
    assert sut.episode_num(1, 1) == 'S01E01'

    # Absolute numbering
    assert sut.episode_num(1, numbering='absolute') == '001'
    assert sut.episode_num(0, 1, numbering='absolute') == '001'
    assert sut.episode_num(1, 0, numbering='absolute') == '001'

    # Must have both season and episode for standard numbering
    assert sut.episode_num(0) is None
    assert sut.episode_num(1) is None

    # Episode numbering starts at 1
    assert sut.episode_num(0, 0) is None
    assert sut.episode_num(1, 0) is None

    # Absolute numbering starts at 1
    assert sut.episode_num(0, 0, numbering='absolute') is None

    # Absolute numbering can't have both season and episode
    assert sut.episode_num(1, 1, numbering='absolute') is None
