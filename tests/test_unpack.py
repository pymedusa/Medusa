# coding=utf-8
"""Tests for medusa/process_tv.py."""
import os

from medusa import app
from medusa.process_tv import ProcessResult

import pytest


@pytest.mark.parametrize('p', [
    {
        'rar_file': ['test.rar'],
        'extracted_file': ['test.txt'],
        'error': u'',
        'missed_file_message': u''
    },
    {
        'rar_file': ['invalid.rar'],
        'extracted_file': [],
        'error': u'Not a RAR file',
        'missed_file_message': u'invalid.rar: Unpacking failed: Unpacking failed'
    },
    {
        'rar_file': ['passworded.rar'],
        'extracted_file': [],
        'error': u'wrong password',
        'missed_file_message': u'passworded.rar: Unpacking failed: Unpacking failed'
    },
])
def test_unpack(monkeypatch, p):
    """Run the test."""
    # Given
    path = os.path.join('tests', 'rar')
    monkeypatch.setattr(ProcessResult, 'directory', path)
    monkeypatch.setattr(app, 'UNPACK', True)
    sut = ProcessResult(path)

    # When
    result = sut.unrar(path, p['rar_file'])
    missed_files = sut.missedfiles[0] if sut.missedfiles else ''

    # Then
    assert p['extracted_file'] == result
    assert p['error'] in sut.output
    assert p['missed_file_message'] == missed_files
