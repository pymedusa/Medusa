# coding=utf-8

from __future__ import unicode_literals

from six import text_type


def ex(e):
    """
    :param e: The exception to convert into a unicode string
    :return: A unicode string from the exception text if it exists
    """
    message = ''
    if not e or not e.args:
        return message

    for arg in e.args:
        if arg is not None:
            if isinstance(arg, text_type):
                fixed_arg = arg
            else:
                try:
                    fixed_arg = 'Error: {0!r}'.format(arg)
                except Exception:
                    fixed_arg = None

            if fixed_arg:
                if not message:
                    message = fixed_arg
                else:
                    try:
                        message = '{0}: {1}'.format(message, fixed_arg)
                    except UnicodeDecodeError:
                        message = '{0}: {1}'.format(
                            text_type(message, errors='replace'),
                            text_type(fixed_arg, errors='replace'))

    return message


class ApplicationException(Exception):
    """
    Generic Application Exception - should never be thrown, only sub-classed
    """


class AuthException(ApplicationException):
    """
    Authentication information is incorrect
    """


class CantRefreshShowException(ApplicationException):
    """
    The show can't be refreshed right now
    """


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


class AnidbAdbaConnectionException(Exception):
    """
    Connection exceptions raised while trying to communicate with the Anidb UDP api.

    More info on the api: https://wiki.anidb.net/w/API.
    """
