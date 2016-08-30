# coding=utf-8
"""Tests for sickbeard.helpers.py."""

import sickbeard.helpers as sut


def test_ensure_list__single_value():
    # Given
    value = 0

    # When
    actual = sut.ensure_list(value)

    # Then
    assert [0] == actual


def test_ensure_list__multi_values():
    # Given
    value = ['b', 'a', 'c']

    # When
    actual = sut.ensure_list(value)

    # Then
    assert ['a', 'b', 'c'] == actual


def test_ensure_list__none():
    # Given
    value = None

    # When
    actual = sut.ensure_list(value)

    # Then
    assert [] == actual
