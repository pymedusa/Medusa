"""Helper for anidb communications."""

import adba
import logging
from medusa import app
from medusa.cache import anidb_cache
from medusa.logger.adapters.style import BraceAdapter
from medusa.helper.exceptions import AnidbAdbaConnectionException

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


def set_up_anidb_connection():
    """Connect to anidb."""
    if not app.USE_ANIDB:
        log.debug(u'Usage of anidb disabled. Skipping')
        return False

    if not app.ANIDB_USERNAME and not app.ANIDB_PASSWORD:
        log.debug(u'anidb username and/or password are not set.'
                  u' Aborting anidb lookup.')
        return False

    if not app.ADBA_CONNECTION:
        def anidb_logger(msg):
            return log.debug(u'anidb: {0}', msg)

        try:
            app.ADBA_CONNECTION = adba.Connection(keepAlive=True, log=anidb_logger)
        except Exception as error:
            log.warning(u'anidb exception msg: {0!r}', error)
            return False

    try:
        if not app.ADBA_CONNECTION.authed():
            app.ADBA_CONNECTION.auth(app.ANIDB_USERNAME, app.ANIDB_PASSWORD)
        else:
            return True
    except Exception as error:
        log.warning(u'anidb exception msg: {0!r}', error)
        return False

    return app.ADBA_CONNECTION.authed()


@anidb_cache.cache_on_arguments()
def get_release_groups_for_anime(series_name):
    """Get release groups for an anidb anime."""
    groups = []
    if set_up_anidb_connection():
        try:
            anime = adba.Anime(app.ADBA_CONNECTION, name=series_name)
            groups = anime.get_groups()
        except Exception as error:
            log.warning(u'Unable to retrieve Fansub Groups from AniDB. Error: {error}', {'error': error.message})
            raise AnidbAdbaConnectionException(error)

    return groups
