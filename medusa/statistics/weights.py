# coding=utf-8

from __future__ import division


def simple(weight, value):
    """Weight a value using simple weighting."""
    return weight * value


def bayesian(weight, value, threshold, mean):
    """Weight a value using a bayesian estimate."""
    return (weight * value + threshold * mean) / (weight + threshold)
