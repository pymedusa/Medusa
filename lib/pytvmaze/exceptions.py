# coding=utf-8


from requests.compat import is_py3
from requests import RequestException


class BaseError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value if is_py3 else unicode(self.value).encode('utf-8')


class GeneralError(BaseError):
    """General pytvmaze error"""


class ShowIndexError(BaseError):
    """Show Index Error"""


class MissingParameters(GeneralError, TypeError):
    """Missing parameters"""


class TVMazeConnectionError(GeneralError, RequestException):
    """Connection error while accessing TVMaze"""


class BadRequest(TVMazeConnectionError):
    """Bad request"""


class IllegalAirDate(GeneralError, ValueError):
    """Invalid air date"""


class ItemNotFoundError(GeneralError, KeyError):
    """Expected item not found"""


class ShowNotFound(ItemNotFoundError):
    """Show not found"""


class IDNotFound(ItemNotFoundError):
    """ID not found"""


class ScheduleNotFound(ItemNotFoundError):
    """Schedule not found"""


class EpisodeNotFound(ItemNotFoundError):
    """Episode not found"""


class NoEpisodesForAirdate(EpisodeNotFound):
    """No episode found for date"""


class CastNotFound(ItemNotFoundError):
    """Cast not found"""


class PersonNotFound(ItemNotFoundError):
    """Person not found"""


class CreditsNotFound(ItemNotFoundError):
    """Credits not found"""


class UpdateNotFound(ItemNotFoundError):
    """Update not found"""


class AKASNotFound(ItemNotFoundError):
    """AKAs not found"""


class SeasonNotFound(ItemNotFoundError):
    """Season not found"""
