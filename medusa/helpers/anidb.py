"""Helper for anidb communications."""
from __future__ import unicode_literals

import logging
from os.path import join

import adba
from adba.aniDBerrors import AniDBCommandTimeoutError

from medusa import app
from medusa.cache import anidb_cache
from medusa.helper.exceptions import AnidbAdbaConnectionException
from medusa.logger.adapters.style import BraceAdapter

import six

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
        try:
            app.ADBA_CONNECTION = adba.Connection(keepAlive=True)
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


def create_key(namespace, fn, **kw):
    def generate_key(*args, **kw):
        show_key = namespace + '|' + args[0]
        if six.PY2:
            return show_key.encode('utf-8')
        return show_key
    return generate_key


@anidb_cache.cache_on_arguments(namespace='anidb', function_key_generator=create_key)
def get_release_groups_for_anime(series_name):
    """Get release groups for an anidb anime."""
    groups = []
    if set_up_anidb_connection():
        try:
            anime = adba.Anime(app.ADBA_CONNECTION, name=series_name, cache_path=join(app.CACHE_DIR, 'adba'))
            groups = anime.get_groups()
        except Exception as error:
            log.warning(u'Unable to retrieve Fansub Groups from AniDB. Error: {error!r}', {'error': error})
            raise AnidbAdbaConnectionException(error)

    return groups


@anidb_cache.cache_on_arguments()
def get_short_group_name(release_group):
    short_group_list = []

    try:
        group = app.ADBA_CONNECTION.group(gname=release_group)
    except AniDBCommandTimeoutError:
        log.debug('Timeout while loading group from AniDB. Trying next group')
    except Exception:
        log.debug('Failed while loading group from AniDB. Trying next group')
    else:
        for line in group.datalines:
            if line['shortname']:
                short_group_list.append(line['shortname'])
            else:
                if release_group not in short_group_list:
                    short_group_list.append(release_group)

    return short_group_list


def short_group_names(groups):
    """Find AniDB short group names for release groups.

    :param groups: list of groups to find short group names for
    :return: list of shortened group names
    """
    short_group_list = []
    if set_up_anidb_connection():
        for group_name in groups:
            # Try to get a short group name, or return the group name provided.
            short_group_list += get_short_group_name(group_name) or [group_name]
    else:
        short_group_list = groups
    return short_group_list
