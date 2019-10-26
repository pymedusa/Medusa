# coding=utf-8
"""Statistics module."""

from __future__ import division
from __future__ import unicode_literals

from math import sqrt


def mean(it):
    """Calculate the mean."""
    return sum(it) / len(it)


def differences(it, population_mean):
    """Calculate differences for a population."""
    return (x - population_mean for x in it)


def squares(it):
    """Calculate the squares for a population."""
    return (x**2 for x in it)


def variance(it, dof=None):
    """Calculate the variance of a population."""
    if dof is None:
        dof = len(it) - 1

    if dof <= 0:
        raise ValueError('Degrees of freedom must be greater than 0')
    sample_mean = mean(it)
    sample_differences = differences(it, sample_mean)
    differences_squared = squares(sample_differences)
    sum_of_differences_squared = sum(differences_squared)
    return sum_of_differences_squared / dof


def standard_deviation(it, population=False):
    """Calculate the standard deviation of a sample."""
    num_items = len(it)
    degrees_of_freedom = num_items if population else num_items - 1
    sample_variance = variance(it, degrees_of_freedom)
    return sqrt(sample_variance)


def population_standard_deviation(it):
    """Calculate the standard deviation of a population."""
    return standard_deviation(it, population=True)
