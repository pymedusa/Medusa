# coding=utf-8
"""Statistics module."""
from __future__ import division
from __future__ import unicode_literals


def simple(weight, value):
    """Weight a value using simple weighting."""
    return weight * value


def bayesian(weight, value, threshold, mean):
    """Weight a value using a bayesian estimate."""
    return (weight * value + threshold * mean) / (weight + threshold)
