# coding=utf-8


from requests.compat import is_py3
from requests import RequestException


class BaseError(Exception):
    def __init__(self, value):
        Exception.__init__()
        self.value = value

    def __str__(self):
        return self.value if is_py3 else unicode(self.value).encode('utf-8')


class GeneralError(BaseError):
    """General simpleanidb error"""


class AnidbConnectionError(GeneralError, RequestException):
    """Connection error while accessing Anidb"""


class BadRequest(AnidbConnectionError):
    """Bad request"""
