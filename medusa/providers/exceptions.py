# coding=utf-8

"""Exceptions raised by Medusa providers."""
from __future__ import unicode_literals


class ProviderError(Exception):
    """A generic provider exception occurred."""


class AuthenticationError(ProviderError):
    """Provider authentication failed."""


class ParsingError(ProviderError):
    """Provider parsing failed."""
