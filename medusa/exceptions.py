# coding=utf-8


class ApplicationException(Exception):
    """
    Generic Application Exception - should never be thrown, only sub-classed
    """


class AuthException(ApplicationException):
    """
    Authentication information is incorrect
    """


class RefreshError(ApplicationException):
    """Refreshing failed."""


class RemovalError(ApplicationException):
    """Removal failed."""


class UpdateError(ApplicationException):
    """Update failed."""


class EpisodeNotFoundException(ApplicationException):
    """
    The episode wasn't found on the Indexer
    """


class PostProcessingError(ApplicationException):
    """Error while post-processing."""


class FailedProcessingError(PostProcessingError):
    """Error while processing failed item."""


class IntegrityError(ApplicationException):
    """Relational integrity of the database is affected."""


class NoNFOException(ApplicationException):
    """
    No NFO was found
    """


class ShowDirectoryNotFoundException(ApplicationException):
    """
    The show directory was not found
    """


class ShowNotFoundException(ApplicationException):
    """
    The show wasn't found on the Indexer
    """
