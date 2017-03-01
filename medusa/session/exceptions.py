# coding=utf-8


# Request police Exceptions.
class PolicedRequestException(Exception):
    """Generic Police Exception."""


class PolicedRequestScoreExceeded(PolicedRequestException):
    """Police Request Score Exception."""


class PolicedRequestDailyExceeded(PolicedRequestException):
    """Police Request Exception for exceeding the reserved daily search limit."""


class PolicedRequestInvalidConfiguration(PolicedRequestException):
    """Invalid or incomplete configuration provided."""
