# coding=utf-8

"""Exceptions raised by Medusa providers."""


class ProviderError(Exception):
    """A generic provider exception occurred."""


class AuthenticationError(ProviderError):
    """Provider authentication failed."""


class ParsingError(ProviderError):
    """Provider parsing failed."""
