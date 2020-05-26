"""Plex or other tvdb fallback sources."""
from __future__ import unicode_literals

import datetime
import functools
import logging
from builtins import object

from medusa import app, ui
from medusa.indexers.exceptions import (
    IndexerEpisodeNotFound, IndexerSeasonNotFound, IndexerShowNotFound,
    IndexerShowNotFoundInLanguage, IndexerUnavailable
)

from tvdbapiv2.auth.tvdb import TVDBAuth

logger = logging.getLogger(__name__)


class PlexFallBackConfig(object):
    """Update the plex fallback config options.

    This will update the plex fallback config options, every time it is updated through the UI.
    If we wouldn't forcibly update this, we'd need to restart Medusa for it to take effect.
    """

    def __init__(self, func, *args, **kwargs):
        """Initialize the PlexFallBackConfig decorator."""
        self.func = func

    def __get__(self, obj, objtype):
        """Support instance methods."""
        return functools.partial(self.__call__, obj)

    def __call__(self, *args, **kwargs):
        """Update the config every time we're accessing the indexerApi."""
        if args[0].indexer_id == 1:
            session = args[0].api_params.get('session')
            if not hasattr(session, 'fallback_config'):
                session.fallback_config = {
                    'plex_fallback_time': datetime.datetime.now(),
                    'api_base_url': 'https://api.thetvdb.com',
                    'fallback_plex_enable': app.FALLBACK_PLEX_ENABLE,
                    'fallback_plex_timeout': app.FALLBACK_PLEX_TIMEOUT,
                    'fallback_plex_notifications': app.FALLBACK_PLEX_NOTIFICATIONS
                }
            else:
                # Try to update some of the values
                session.fallback_config['fallback_plex_enable'] = app.FALLBACK_PLEX_ENABLE
                session.fallback_config['fallback_plex_timeout'] = app.FALLBACK_PLEX_TIMEOUT
                session.fallback_config['fallback_plex_notifications'] = app.FALLBACK_PLEX_NOTIFICATIONS

            # TODO: I'm disabling SSL verify here, as i'm using fiddler to return a 503 and test the fallback.
            # This line should be removed before merging.
            session.verify = False

        return self.func(*args, **kwargs)


class PlexFallback(object):
    """Fallback to plex if tvdb fails to connect.

    Decorator that can be used to catch an exception and fallback to the plex proxy.
    If there are issues with tvdb the plex mirror will also only work for a limited amount of time. That is why we
    revert back to tvdb after an x amount of hours.
    """

    def __init__(self, func):
        """Initialize the PlexFallback decorator."""
        self.func = func

    def __get__(self, obj, objtype):
        """Support instance methods."""
        return functools.partial(self.__call__, obj)

    def __call__(self, *args, **kwargs):
        """Call the decorator just before we're accessing the tvdb apiv2 lib.

        It will try to access TheTvdb's api endpoint, but on exception fall back to plex's.
        """
        session = args[0].config['session']
        fallback_config = session.fallback_config

        if not session.fallback_config['fallback_plex_enable']:
            return self.func(*args, **kwargs)

        def fallback_notification():
            ui.notifications.error(
                'tvdb2.plex.tv fallback',
                'You are currently using the tvdb2.plex.tv fallback, '
                'as TheTVDB source. Moving back to thetvdb.com in {time_left} minutes.'
                .format(
                    time_left=divmod(((fallback_config['plex_fallback_time'] +
                                       datetime.timedelta(hours=fallback_config['fallback_plex_timeout'])) -
                                      datetime.datetime.now()).total_seconds(), 60)[0]
                )
            )

        # Check if we need to revert to tvdb's api, because we exceed the fallback period.
        if fallback_config['api_base_url'] == app.FALLBACK_PLEX_API_URL:
            if (fallback_config['plex_fallback_time'] +
                    datetime.timedelta(hours=fallback_config['fallback_plex_timeout']) < datetime.datetime.now()):
                logger.debug('Disabling Plex fallback as fallback timeout was reached')
                session.api_client.host = 'https://api.thetvdb.com'
                session.auth = TVDBAuth(api_key=app.TVDB_API_KEY)
            else:
                logger.debug('Keeping Plex fallback enabled as fallback timeout not reached')

        try:
            # Run api request
            return self.func(*args, **kwargs)
        # Valid exception, which we don't want to fall back on.
        except (IndexerEpisodeNotFound, IndexerSeasonNotFound, IndexerShowNotFound, IndexerShowNotFoundInLanguage):
            raise
        except IndexerUnavailable as error:
            logger.warning('Could not connect to TheTvdb.com, with reason: %r', error)
        except Exception as error:
            logger.warning('Could not connect to TheTvdb.com, with reason: %r', error)

        # If we got this far, it means we hit an exception, and we want to switch to the plex fallback.
        session.api_client.host = fallback_config['api_base_url'] = app.FALLBACK_PLEX_API_URL
        session.auth = TVDBAuth(api_key=app.TVDB_API_KEY, api_base=app.FALLBACK_PLEX_API_URL)

        fallback_config['plex_fallback_time'] = datetime.datetime.now()

        # Send notification back to user.
        if fallback_config['fallback_plex_notifications']:
            logger.warning('Enabling Plex fallback as TheTvdb.com API is having some connectivity issues')
            fallback_notification()

        # Run api request
        return self.func(*args, **kwargs)
