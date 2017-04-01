"""Traktor exceptions module."""


class TraktException(Exception):
    """A Generic Trakt Exception."""


class AuthException(TraktException):
    """A Generic Trakt Authentication Exception."""


class MissingTokenException(TraktException):
    """A Generic Trakt Missing Token Exception."""


class TokenExpiredException(TraktException):
    """A 410 the token has expired Exception."""


class UnavailableException(TraktException):
    """A Generic Trakt Unavailable Exception.

    Possibly raised when Trakt is reachable but is showing an unavailable response code.
    Possibly raised on in 500 series response codes
    """


class ResourceUnavailable(TraktException):
    """A Trakt Exception for when a requested resources does not exist, possibly raised on 404."""
