from requests.exceptions import (ConnectionError, Timeout, TooManyRedirects)


class TraktException(Exception):
    """A Generic Trakt Exception"""


class TraktAuthException(TraktException):
    """A Generic Trakt Authentication Exception"""


class TraktServerBusy(TraktException):
    """A Generic Trakt Server Busy Exception"""


class TraktMissingTokenException(TraktException):
    """A Generic Trakt Missing Token Exception"""


class TraktIOError(TraktException, IOError):
    """A Generic Trakt IOError Exception"""


class TraktConnectionException(TraktIOError, ConnectionError):
    """A Generic Trakt Connection Exception, inherited from TraktIOError and IOError"""


class TraktTimeoutException(TraktIOError, Timeout):
    """A Generic Trakt Timeout Exception, inherited from TraktIOError and IOError"""


class TraktUnavailableException(TraktException):
    """A Generic Trakt Unavailable Exception,
    possibly raised when Trakt is reachable but is showing an unavailable response code.
    Possibly raised on in 500 series response codes"""


class TraktResourceNotExistException(TraktException):
    """A Generic Trakt Resource Not Exist Exception, possibly raised on 404"""


class TraktTooManyRedirects(TraktException, TooManyRedirects):
    """A Generic Trakt Too Many Redirects Exception"""
