import sys


class BaseError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        if sys.version_info > (3,):
            return self.value


class ShowNotFound(BaseError):
    pass


class IDNotFound(BaseError):
    pass


class EpisodeNotFound(BaseError):
    pass


class ActorNotFound(BaseError):
    pass


class ShowIndexError(BaseError):
    pass


class UpdateNotFound(BaseError):
    pass


class GeneralError(BaseError):
    pass


class MissingParameters(BaseError):
    pass


class ConnectionError(BaseError):
    pass


class BadRequest(BaseError):
    pass


class BannersNotFound(BaseError):
    pass
