"""Module with Trakt helper methods."""

import logging
from json.decoder import JSONDecodeError

from medusa.helpers import get_title_without_year
from medusa.indexers.imdb.api import ImdbIdentifier
from medusa.logger.adapters.style import BraceAdapter

from requests.exceptions import RequestException

from trakt import calendar, tv, users
from trakt.errors import TraktException


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


def get_trakt_user():
    """Get PyTrakt user object."""
    try:
        user = users.get_user_settings()
        username = user['user']['username']
        return users.User(username)
    except (TraktException, RequestException, JSONDecodeError) as error:
        log.warning('Unable to get trakt user, error: {error}', {'error': error})
        raise


def get_trakt_show_collection(trakt_list, limit=None):
    """
    Flesh out the different list_types into pyTrakt method calls.

    Call the relevant method, with paramaters if required.
    Return Array of TvShows.
    :param trakt_list: String description of the trakt list to return.
    :returns: Array of PyTrakt TvShow objects.
    """
    try:
        if trakt_list == 'trending':
            return tv.trending_shows(limit=limit, extended='full,images')
        elif trakt_list == 'popular':
            return tv.popular_shows(limit=limit, extended='full,images')
        elif trakt_list == 'anticipated':
            return tv.anticipated_shows(limit=limit, extended='full,images')
        elif trakt_list == 'collected':
            return tv.collected_shows(limit=limit, extended='full,images')
        elif trakt_list == 'watched':
            return tv.watched_shows(limit=limit, extended='full,images')
        elif trakt_list == 'played':
            return tv.played_shows(limit=limit, extended='full,images')
        elif trakt_list == 'recommended':
            return tv.recommended_shows(extended='full,images')
        elif trakt_list == 'newshow':
            calendar_items = calendar.PremiereCalendar(days=30, extended='full,images')
            return [tv_episode.show_data for tv_episode in calendar_items]
        elif trakt_list == 'newseason':
            calendar_items = calendar.SeasonCalendar(days=15, extended='full,images')
            return [tv_episode.show_data for tv_episode in calendar_items]

        return tv.anticipated_shows(limit=limit, extended='full,images')
    except (TraktException, RequestException, JSONDecodeError) as error:
        log.warning('Unable to get trakt list {trakt_list}: {error!r}', {'trakt_list': trakt_list, 'error': error})


def create_show_structure(show_obj):
    """Prepare a trakt standard media object. With the show identifier."""
    show = {
        'title': get_title_without_year(show_obj.name, show_obj.start_year),
        'year': show_obj.start_year,
        'ids': {}
    }
    for valid_trakt_id in ['tvdb_id', 'trakt_id', 'tmdb_id', 'imdb_id']:
        external = show_obj.externals.get(valid_trakt_id)
        if external:
            if valid_trakt_id == 'imdb_id':
                external = ImdbIdentifier(external).imdb_id
            show['ids'][valid_trakt_id[:-3]] = external
    return show


def create_episode_structure(show_obj, episodes):
    """Prepare a trakt standard media object. With the show and episode identifiers."""
    if not isinstance(episodes, list):
        episodes = [episodes]

    show = create_show_structure(show_obj)

    # Add episodes to the media_object.
    show['seasons'] = []

    for ep_obj in episodes:
        if ep_obj.season not in show['seasons']:
            show['seasons'].append({
                'number': ep_obj.season,
                'episodes': []
            })

        season = [s for s in show['seasons'] if s['number'] == ep_obj.season][0]
        season['episodes'].append({'number': ep_obj.episode})

    return show
