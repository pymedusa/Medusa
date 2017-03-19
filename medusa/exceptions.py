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


class CantRemoveShowException(ApplicationException):
    """
    The show can't be removed right now
    """


class CantUpdateShowException(ApplicationException):
    """
    The show can't be updated right now
    """


class EpisodeDeletedException(ApplicationException):
    """
    This episode has been deleted
    """


class EpisodeNotFoundException(ApplicationException):
    """
    The episode wasn't found on the Indexer
    """


class EpisodePostProcessingFailedException(ApplicationException):
    """
    The episode post-processing failed
    """


class FailedPostProcessingFailedException(ApplicationException):
    """
    The failed post-processing failed
    """


class MultipleEpisodesInDatabaseException(ApplicationException):
    """
    Multiple episodes were found in the database! The database must be fixed first
    """


class MultipleShowsInDatabaseException(ApplicationException):
    """
    Multiple shows were found in the database! The database must be fixed first
    """


class MultipleShowObjectsException(ApplicationException):
    """
    Multiple objects for the same show were found! Something is very wrong
    """


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
