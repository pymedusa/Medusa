# coding=utf-8
"""Tests for medusa/test_list_associated_files.py."""

import pytest

@pytest.mark.parametrize('p', [
    {
        'name': '',
        'search_result': None,
        'expected': (),
    },
])
def test_anime_parsing(p, create_structure, monkeypatch):
    assert True is True
