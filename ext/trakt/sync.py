# -*- coding: utf-8 -*-
"""This module contains Trakt.tv sync endpoint support functions"""
from collections import defaultdict
from datetime import datetime, timezone

from deprecated import deprecated

from trakt.core import delete, get, post
from trakt.utils import slugify, timestamp

__author__ = 'Jon Nappi'
__all__ = ['Scrobbler', 'comment', 'rate', 'add_to_history', 'get_collection',
           'get_watchlist', 'add_to_watchlist', 'remove_from_history',
           'remove_from_watchlist', 'add_to_collection',
           'remove_from_collection', 'search', 'search_by_id', 'checkin_media',
           'delete_checkin']


@post
def comment(media, comment_body, spoiler=False, review=False):
    """Add a new comment to a :class:`Movie`, :class:`TVShow`, or
        :class:`TVEpisode`. If you add a review,
        it needs to be at least 200 words.

    :param media: The media object to post the comment to
    :param comment_body: The content of comment
    :param spoiler: Boolean flag to indicate whether this comment contains
        spoilers
    :param review: Boolean flag to determine if this comment is a review (>200
        characters. Note, if *comment_body* is longer than 200 characters, the
        review flag will automatically be set to `True`
    """
    if not review and len(comment_body) > 200:
        review = True
    data = dict(comment=comment_body, spoiler=spoiler, review=review)
    data.update(media.to_json_singular())
    result = yield 'comments', data
    yield result


@post
def rate(media, rating, rated_at=None):
    """Add a rating from 1 to 10 to a :class:`Movie`, :class:`TVShow`, or
        :class:`TVEpisode`.

    :param media: The media object to post a rating to
    :param rating: A rating from 1 to 10 for the media item
    :param rated_at: A `datetime.datetime` object indicating the time at which
        this rating was created
    """
    if rated_at is None:
        rated_at = datetime.now(tz=timezone.utc)

    data = dict(rating=rating, rated_at=timestamp(rated_at))
    data.update(media.ids)
    result = yield 'sync/ratings', {media.media_type: [data]}
    yield result


@post
def add_to_history(media, watched_at=None):
    """Add a :class:`Movie`, :class:`TVShow`, or :class:`TVEpisode` to your
        watched history.

    :param media: The media object to add to your history. But also supports passing custom json structures.
    :param watched_at: A `datetime.datetime` object indicating the time at
        which this media item was viewed. Defaults to now.
    """
    """Add a :class:`Movie`, :class:`TVShow`, or :class:`TVEpisode
        to your collection.
    :param media: Supports both the PyTrakt :class:`Movie`,
        :class:`TVShow`, etc. But also supports passing custom json structures.
    """

    if isinstance(media, dict):
        items = media
    else:
        items = {
            media.media_type: [
                dict(ids=media.ids.get("ids", {}), watched_at=watched_at),
            ],
        }

    # Walk over items and convert watched_at to a string.
    # Do not mutate original dict.
    media_object = defaultdict(list)
    now = datetime.now(tz=timezone.utc) if watched_at is None else watched_at
    for media_type, media_items in items.items():
        for item in media_items:
            watched_at = item.get("watched_at") or now
            if not isinstance(watched_at, str):
                watched_at = timestamp(watched_at)
            media_object[media_type].append({
                "ids": item["ids"],
                "watched_at": watched_at,
            })

    result = yield 'sync/history', media_object
    yield result


@post
def add_to_watchlist(media):
    """Add a :class:`Movie`, :class:`TVShow`, or :class:`TVEpisode`
        to your watchlist
    :param media: Supports both the PyTrakt :class:`Movie`,
        :class:`TVShow`, etc. But also supports passing custom json structures.
    """
    from trakt.movies import Movie
    from trakt.tv import TVEpisode, TVSeason, TVShow
    if isinstance(media, (TVEpisode, TVSeason, TVShow, Movie)):
        media_object = media.to_json()
    else:
        media_object = media

    result = yield 'sync/watchlist', media_object
    yield result


@post
def remove_from_history(media):
    """Remove the specified media object from your history

    :param media: Supports both the PyTrakt :class:`Movie`,
        :class:`TVShow`, etc. But also supports passing custom json structures.
    """
    from trakt.movies import Movie
    from trakt.tv import TVEpisode, TVSeason, TVShow
    if isinstance(media, (TVEpisode, TVSeason, TVShow, Movie)):
        media_object = media.to_json()
    else:
        media_object = media

    result = yield 'sync/history/remove', media_object
    yield result


@post
def remove_from_watchlist(media):
    """Remove a :class:`TVShow` from your watchlist.
    :param media: Supports both the PyTrakt :class:`Movie`,
        :class:`TVShow`, etc. But also supports passing custom json structures.
    """
    from trakt.movies import Movie
    from trakt.tv import TVEpisode, TVSeason, TVShow
    if isinstance(media, (TVEpisode, TVSeason, TVShow, Movie)):
        media_object = media.to_json()
    else:
        media_object = media

    result = yield 'sync/watchlist/remove', media_object
    yield result


@post
def add_to_collection(media):
    """Add a :class:`Movie`, :class:`TVShow`, or :class:`TVEpisode
        to your collection.
    :param media: Supports both the PyTrakt :class:`Movie`,
        :class:`TVShow`, etc. But also supports passing custom json structures.
    """
    from trakt.movies import Movie
    from trakt.tv import TVEpisode, TVSeason, TVShow
    if isinstance(media, (TVEpisode, TVSeason, TVShow, Movie)):
        media_object = media.to_json()
    else:
        media_object = media

    result = yield 'sync/collection', media_object
    yield result


@post
def remove_from_collection(media):
    """Remove a :class:`TVShow` from your collection.
    :param media: Supports both the PyTrakt :class:`Movie`,
        :class:`TVShow`, etc. But also supports passing custom json structures.
    """
    from trakt.movies import Movie
    from trakt.tv import TVEpisode, TVSeason, TVShow
    if isinstance(media, (TVEpisode, TVSeason, TVShow, Movie)):
        media_object = media.to_json()
    else:
        media_object = media

    result = yield 'sync/collection/remove', media_object
    yield result


def search(query, search_type='movie', year=None, slugify_query=False):
    """Perform a search query against all of trakt's media types.

    :param query: Your search string
    :param search_type: The type of object you're looking for. Must be one of
        'movie', 'show', 'episode', or 'person'
    :param year: This parameter is ignored as it is no longer a part of the
        official API. It is left here as a valid arg for backwards
        compatibility.
    :param slugify_query: A boolean indicating whether or not the provided
        query should be slugified or not prior to executing the query.
    """
    # the new get_search_results expects a list of types, so handle this
    # conversion to maintain backwards compatibility
    if isinstance(search_type, str):
        search_type = [search_type]
    results = get_search_results(query, search_type, slugify_query)
    return [result.media for result in results]


@get
def get_search_results(query, search_type=None, slugify_query=False):
    """Perform a search query against all of trakt's media types.

    :param query: Your search string
    :param search_type: The types of objects you're looking for. Must be
        specified as a list of strings containing any of 'movie', 'show',
        'episode', or 'person'.
    :param slugify_query: A boolean indicating whether or not the provided
        query should be slugified or not prior to executing the query.
    """
    # if no search type was specified, then search everything
    if search_type is None:
        search_type = ['movie', 'show', 'episode', 'person']

    # If requested, slugify the query prior to running the search
    if slugify_query:
        query = slugify(query)

    uri = 'search/{type}?query={query}'.format(
        query=query, type=','.join(search_type))

    data = yield uri

    # Need to do imports here to prevent circular imports with modules that
    # need to import Scrobblers
    results = []
    for media_item in data:
        result = SearchResult(media_item['type'], media_item['score'])
        if media_item['type'] == 'movie':
            from trakt.movies import Movie
            result.media = Movie(**media_item.pop('movie'))
        elif media_item['type'] == 'show':
            from trakt.tv import TVShow
            result.media = TVShow(**media_item.pop('show'))
        elif media_item['type'] == 'episode':
            from trakt.tv import TVEpisode
            show = media_item.pop('show')
            result.media = TVEpisode(show.get('title', None),
                                     show_id=show['ids'].get('trakt'),
                                     **media_item.pop('episode'))
        elif media_item['type'] == 'person':
            from trakt.people import Person
            result.media = Person(**media_item.pop('person'))
        results.append(result)

    yield results


@get
def search_by_id(query, id_type='imdb', media_type=None, slugify_query=False):
    """Perform a search query by using a Trakt.tv ID or other external ID.

    :param query: Your search string, which should be an ID from your source
    :param id_type: The source of the ID you're looking for. Must be one of
        'trakt', trakt-movie', 'trakt-show', 'trakt-episode', 'trakt-person',
        'imdb', 'tmdb', or 'tvdb'
    :param media_type: The type of media you're looking for. May be one of
        'movie', 'show', 'episode', or 'person', or a comma-separated list of
        any combination of those. Null by default, which will return all types
        of media that match the ID given.
    :param slugify_query: A boolean indicating whether or not the provided
        query should be slugified or not prior to executing the query.
    """
    valids = ('trakt', 'trakt-movie', 'trakt-show', 'trakt-episode',
              'trakt-person', 'imdb', 'tmdb', 'tvdb')
    id_types = {'trakt': 'trakt', 'trakt-movie': 'trakt',
                'trakt-show': 'trakt', 'trakt-episode': 'trakt',
                'trakt-person': 'trakt', 'imdb': 'imdb', 'tmdb': 'tmdb',
                'tvdb': 'tvdb'}
    if id_type not in valids:
        raise ValueError('search_type must be one of {}'.format(valids))
    source = id_types.get(id_type)

    media_types = {'trakt-movie': 'movie', 'trakt-show': 'show',
                   'trakt-episode': 'episode', 'trakt-person': 'person'}

    # If there was no media_type passed in, see if we can guess based off the
    # ID source. None is still an option here, as that will return all possible
    # types for a given source.
    if media_type is None:
        media_type = media_types.get(source, None)

    # If requested, slugify the query prior to running the search
    if slugify_query:
        query = slugify(query)

    # If media_type is still none, don't add it as a parameter to the search
    if media_type is None:
        uri = 'search/{source}/{query}'.format(
            query=query, source=source)
    else:
        uri = 'search/{source}/{query}?type={media_type}'.format(
            query=query, source=source, media_type=media_type)
    data = yield uri

    results = []
    for d in data:
        if 'episode' in d:
            from trakt.tv import TVEpisode
            show = d.pop('show')
            results.append(TVEpisode(show.get('title', None),
                                     show_id=show['ids'].get('trakt'),
                                     **d.pop('episode')))
        elif 'movie' in d:
            from trakt.movies import Movie
            results.append(Movie(**d.pop('movie')))
        elif 'show' in d:
            from trakt.tv import TVShow
            results.append(TVShow(**d.pop('show')))
        elif 'person' in d:
            from trakt.people import Person
            results.append(Person(**d.pop('person')))
    yield results


@get
def get_watchlist(list_type=None, sort=None):
    """
    Returns all items in a user's watchlist filtered by type.
    optionally with a filter for a specific item type.

    The watchlist should not be used as a list
    of what the user is actively watching.

    :param list_type: Optional Filter by a specific type.
        Possible values: movies, shows, seasons or episodes.
    :param sort: Optional sort. Only if the type is also sent.
        Possible values: rank, added, released or title.

    https://trakt.docs.apiary.io/#reference/sync/get-watchlist/get-watchlist
    """
    valid_type = ('movies', 'shows', 'seasons', 'episodes')
    valid_sort = ('rank', 'added', 'released', 'title')

    if list_type and list_type not in valid_type:
        raise ValueError('list_type must be one of {}'.format(valid_type))

    if sort and sort not in valid_sort:
        raise ValueError('sort must be one of {}'.format(valid_sort))

    uri = 'sync/watchlist'
    if list_type:
        uri += '/{}'.format(list_type)

    if list_type and sort:
        uri += '/{}'.format(sort)

    data = yield uri
    results = []
    for d in data:
        if 'episode' in d:
            from trakt.tv import TVEpisode
            show = d.pop('show')
            results.append(TVEpisode(show.get('title', None),
                                     show_id=show.get('trakt', None),
                                     **d['episode']))
        elif 'movie' in d:
            from trakt.movies import Movie
            results.append(Movie(**d.pop('movie')))
        elif 'show' in d:
            from trakt.tv import TVShow
            results.append(TVShow(**d.pop('show')))

    yield results


@deprecated("This method returns watchlist, not watched list. "
            "This will be fixed in PyTrakt 4.x to return watched list")
@get
def get_watched(list_type=None, extended=None):
    """Return all movies or shows a user has watched sorted by most plays.

    :param list_type: Optional Filter by a specific type.
        Possible values: movies, shows, seasons or episodes.
    :param extended: Optional value for requesting extended information.
    """
    valid_type = ('movies', 'shows', 'seasons', 'episodes')

    if list_type and list_type not in valid_type:
        raise ValueError('list_type must be one of {}'.format(valid_type))

    uri = 'sync/watched'
    if list_type:
        uri += '/{}'.format(list_type)

    if list_type == 'shows' and extended:
        uri += '?extended={extended}'.format(extended=extended)

    data = yield uri
    results = []
    for d in data:
        if 'movie' in d:
            from trakt.movies import Movie
            results.append(Movie(**d.pop('movie')))
        elif 'show' in d:
            from trakt.tv import TVShow
            results.append(TVShow(**d.pop('show')))

    yield results


@get
def get_collection(list_type=None, extended=None):
    """
    Get all collected items in a user's collection.

    A collected item indicates availability to watch digitally
    or on physical media.

    :param list_type: Optional Filter by a specific type.
        Possible values: movies or shows.
    :param extended: Optional value for requesting extended information.
    """
    valid_type = ('movies', 'shows')

    if list_type and list_type not in valid_type:
        raise ValueError('list_type must be one of {}'.format(valid_type))

    uri = 'sync/collection'
    if list_type:
        uri += '/{}'.format(list_type)

    if extended:
        uri += '?extended={extended}'.format(extended=extended)

    data = yield uri
    results = []
    for d in data:
        if 'movie' in d:
            from trakt.movies import Movie
            results.append(Movie(**d.pop('movie')))
        elif 'show' in d:
            from trakt.tv import TVShow
            results.append(TVShow(**d.pop('show')))

    yield results


@post
def checkin_media(media, app_version, app_date, message="", sharing=None,
                  venue_id="", venue_name=""):
    """Checkin a media item.
    """
    payload = dict(app_version=app_version, app_date=app_date, sharing=sharing,
                   message=message, venue_id=venue_id, venue_name=venue_name)
    payload.update(media.to_json_singular())
    result = yield "checkin", payload
    yield result


@delete
def delete_checkin():
    yield "checkin"


class Scrobbler:
    """Scrobbling is a seemless and automated way to track what you're watching
        in a media center. This class allows the media center to easily send
        events that correspond to starting, pausing, stopping or finishing
        a movie or episode.
    """

    def __init__(self, media, progress, app_version, app_date):
        """Create a new :class:`Scrobbler` instance

        :param media: The media object you're scrobbling. Must be either a
            :class:`Movie` or :class:`TVEpisode` type
        :param progress: The progress made through *media* at the time of
            creation
        :param app_version: The media center application version
        :param app_date: The date that *app_version* was released
        """
        super().__init__()
        self.progress, self.version = progress, app_version
        self.media, self.date = media, app_date
        if self.progress > 0:
            self.start()

    def start(self, progress=None):
        """Start scrobbling this :class:`Scrobbler`'s *media* object"""
        if progress is not None:
            self.progress = progress
        return self._post('scrobble/start')

    def pause(self, progress=None):
        """Pause the scrobbling of this :class:`Scrobbler`'s *media* object"""
        if progress is not None:
            self.progress = progress
        return self._post('scrobble/pause')

    def stop(self, progress=None):
        """Stop the scrobbling of this :class:`Scrobbler`'s *media* object"""
        if progress is not None:
            self.progress = progress
        return self._post('scrobble/stop')

    def finish(self):
        """Complete the scrobbling this :class:`Scrobbler`'s *media* object"""
        if self.progress < 80.0:
            self.progress = 100.0
        self.stop()

    def update(self, progress):
        """Update the scobbling progress of this :class:`Scrobbler`'s *media*
        object
        """
        self.progress = progress
        return self.start()

    @post
    def _post(self, uri):
        """Handle actually posting the scrobbling data to trakt

        :param uri: The uri to post to
        """
        payload = dict(progress=self.progress, app_version=self.version,
                       date=self.date)
        payload.update(self.media.to_json_singular())
        response = yield uri, payload
        yield response

    def __enter__(self):
        """Context manager support for `with Scrobbler` syntax. Begins
        scrobbling the :class:`Scrobbler`'s *media* object
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support for `with Scrobbler` syntax. Completes
        scrobbling the :class:`Scrobbler`'s *media* object
        """
        self.finish()


class SearchResult:
    """A SearchResult is an individual result item from the trakt.tv search
    API. It wraps a single media entity whose type is indicated by the type
    field.
    """
    def __init__(self, type, score, media=None):
        """Create a new :class:`SearchResult` instance

        :param type: The type of media object contained in this result.
        :param score: The search result relevancy score of this item.
        :param media: The wrapped media item returned by a search.
        """
        self.type = type
        self.score = score
        self.media = media
