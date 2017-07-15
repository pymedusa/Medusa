# coding=utf-8
"""Tests for medusa/process_tv.py."""
import os

from medusa import app
from medusa.process_tv import ProcessResult

import pytest


class ProcessResultTest(ProcessResult):
    """A test `ProcessResult` object that does not check already processed files."""

    def __init__(self, path):
        """Initialize the object."""
        super(ProcessResultTest, self).__init__(self, path)

    def already_postprocessed(self, video_file):
        """Override method."""
        return False


@pytest.mark.parametrize('p', [
    {
        'rar_file': ['test.rar'],
        'extracted_files': ['test.txt'],
        'output': u"Extracted content: [u'test.txt']",
        'missed_files_msg': u''
    },
    {
        'rar_file': ['invalid.rar'],
        'extracted_files': [],
        'output': u'Not a RAR file',
        'missed_files_msg': u'invalid.rar: Unpacking failed: Unpacking failed'
    },
    {
        'rar_file': ['passworded.rar'],
        'extracted_files': [],
        'output': u'wrong password',
        'missed_files_msg': u'passworded.rar: Unpacking failed: Unpacking failed'
    },
])
def test_unpack(monkeypatch, p):
    """Run the test."""
    # Given
    path = os.path.join('tests', 'rar')
    monkeypatch.setattr(ProcessResultTest, 'directory', path)
    monkeypatch.setattr(app, 'UNPACK', True)
    sut = ProcessResultTest(path)

    # When
    result = sut.unrar(path, p['rar_file'])
    missed_files_msg = sut.missedfiles[0] if sut.missedfiles else ''

    # Then
    assert p['extracted_files'] == result
    assert p['output'] in sut.output
    assert p['missed_files_msg'] == missed_files_msg
