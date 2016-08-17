from requests.exceptions import (ConnectionError, Timeout, TooManyRedirects)


class TraktException(Exception):
    """A Generic Trakt Exception"""


class AuthException(TraktException):
    """A Generic Trakt Authentication Exception"""


class ServerBusy(TraktException):
    """A Generic Trakt Server Busy Exception"""


class MissingTokenException(TraktException):
    """A Generic Trakt Missing Token Exception"""


class TokenExpiredException(TraktException):
    """A 410 the token has expired Exception"""


class TraktIOError(TraktException, IOError):
    """A Generic Trakt IOError Exception"""


class TraktConnectionException(TraktException, ConnectionError):
    """A Generic Trakt Connection Exception"""


class TimeoutException(TraktIOError, Timeout):
    """A Generic Trakt Timeout Exception"""


class UnavailableException(TraktException):
    """
    A Generic Trakt Unavailable Exception,
    possibly raised when Trakt is reachable but is showing an unavailable response code.
    Possibly raised on in 500 series response codes
    """


class ResourceUnavailable(TraktException):
    """A Trakt Exception for when a requested resources does not exist, possibly raised on 404"""


class TraktTooManyRedirects(TraktException, TooManyRedirects):
    """A Generic Trakt Too Many Redirects Exception"""
