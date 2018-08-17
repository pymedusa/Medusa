# -*- coding: utf-8 -*-
"""This module contains Trakt.tv sync endpoint support functions"""
from datetime import datetime

from trakt.core import get, post
from trakt.utils import slugify, extract_ids, timestamp

__author__ = 'Jon Nappi'
__all__ = ['Scrobbler', 'comment', 'rate', 'add_to_history',
           'add_to_watchlist', 'remove_from_history', 'remove_from_watchlist',
           'add_to_collection', 'remove_from_collection', 'search',
           'search_by_id']


@post
def comment(media, comment_body, spoiler=False, review=False):
    """Add a new comment to a :class:`Movie`, :class:`TVShow`, or
    :class:`TVEpisode`. If you add a review, it needs to
    be at least 200 words

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
    data.update(media.to_json())
    yield 'comments', data


@post
def rate(media, rating, rated_at=None):
    """Add a rating from 1 to 10 to a :class:`Movie`, :class:`TVShow`, or
    :class:`TVEpisode`

    :param media: The media object to post a rating to
    :param rating: A rating from 1 to 10 for the media item
    :param rated_at: A `datetime.datetime` object indicating the time at which
        this rating was created
    """
    if rated_at is None:
        rated_at = datetime.now()

    data = dict(rating=rating, rated_at=timestamp(rated_at))
    data.update(media.ids)
    yield 'sync/ratings', {media.media_type: [data]}


@post
def add_to_history(media, watched_at=None):
    """Add a :class:`Movie`, :class:`TVShow`, or :class:`TVEpisode` to your
    watched history

    :param media: The media object to add to your history
    :param watched_at: A `datetime.datetime` object indicating the time at
        which this media item was viewed
    """
    if watched_at is None:
        watched_at = datetime.now()

    data = dict(watched_at=timestamp(watched_at))
    data.update(media.ids)
    yield 'sync/history', {media.media_type: [data]}


@post
def add_to_watchlist(media):
    """Add a :class:`TVShow` to your watchlist

    :param media: The :class:`TVShow` object to add to your watchlist
    """
    yield 'sync/watchlist', media.to_json()


@post
def remove_from_history(media):
    """Remove the specified media object from your history

    :param media: The media object to remove from your history
    """
    yield 'sync/history/remove', media.to_json()


@post
def remove_from_watchlist(media):
    """Remove a :class:`TVShow` from your watchlist

    :param media: The :clas:`TVShow` to remove from your watchlist
    """
    yield 'sync/watchlist/remove', media.to_json()


@post
def add_to_collection(media):
    """Add a :class:`Movie`, :class:`TVShow`, or :class:`TVEpisode` to your
    collection

    :param media: The media object to collect
    """
    yield 'sync/collection', media.to_json()


@post
def remove_from_collection(media):
    """Remove a media item from your collection

    :param media: The media object to remove from your collection
    """
    yield 'sync/collection/remove', media.to_json()


@get
def search(query, search_type='movie', year=None):
    """Perform a search query against all of trakt's media types

    :param query: Your search string
    :param search_type: The type of object you're looking for. Must be one of
        'movie', 'show', 'episode', or 'person'
    """
    valids = ('movie', 'show', 'episode', 'person')
    if search_type not in valids:
        raise ValueError('search_type must be one of {}'.format(valids))
    uri = 'search?query={query}&type={type}'.format(
        query=slugify(query), type=search_type)

    if year is not None:
        uri += '&year={}'.format(year)

    data = yield uri

    for media_item in data:
        extract_ids(media_item)

    # Need to do imports here to prevent circular imports with modules that
    # need to import Scrobblers
    if search_type == 'movie':
        from trakt.movies import Movie
        yield [Movie(**d.pop('movie')) for d in data]
    elif search_type == 'show':
        from trakt.tv import TVShow
        yield [TVShow(**d.pop('show')) for d in data]
    elif search_type == 'episode':
        from trakt.tv import TVEpisode
        episodes = []
        for episode in data:
            show = episode.pop('show')
            extract_ids(episode['episode'])
            episodes.append(TVEpisode(show.get('title', None),
                                      **episode['episode']))
        yield episodes
    elif search_type == 'person':
        from trakt.people import Person
        yield [Person(**d.pop('person')) for d in data]


@get
def search_by_id(query, id_type='imdb'):
    """Perform a search query by using a Trakt.tv ID or other external ID

    :param query: Your search string
    :param id_type: The type of object you're looking for. Must be one of
        'trakt-movie', 'trakt-show', 'trakt-episode', 'imdb', 'tmdb', 'tvdb' or
        'tvrage'
    """
    valids = ('trakt-movie', 'trakt-show', 'trakt-episode', 'imdb', 'tmdb',
              'tvdb', 'tvrage')
    if id_type not in valids:
        raise ValueError('search_type must be one of {}'.format(valids))
    data = yield 'search?id={query}&id_type={id_type}'.format(
        query=slugify(query), id_type=id_type)

    for media_item in data:
        extract_ids(media_item)

    results = []
    for d in data:
        if 'episode' in d:
            from trakt.tv import TVEpisode
            show = d.pop('show')
            extract_ids(d['episode'])
            results.append(TVEpisode(show['title'], **d['episode']))
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


class Scrobbler(object):
    """Scrobbling is a seemless and automated way to track what you're watching
    in a media center. This class allows the media center to easily send events
    that correspond to starting, pausing, stopping or finishing a movie or
    episode.
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
        super(Scrobbler, self).__init__()
        self.progress, self.version = progress, app_version
        self.media, self.date = media, app_date
        if self.progress > 0:
            self.start()

    def start(self):
        """Start scrobbling this :class:`Scrobbler`'s *media* object"""
        self._post('scrobble/start')

    def pause(self):
        """Pause the scrobbling of this :class:`Scrobbler`'s *media* object"""
        self._post('scrobble/pause')

    def stop(self):
        """Stop the scrobbling of this :class:`Scrobbler`'s *media* object"""
        self._post('scrobble/stop')

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
        self.start()

    @post
    def _post(self, uri):
        """Handle actually posting the scrobbling data to trakt

        :param uri: The uri to post to
        :param args: Any additional data to post to trakt alond with the
            generic scrobbling data
        """
        payload = dict(progress=self.progress, app_version=self.version,
                       date=self.date)
        payload.update(self.media.to_json())
        yield uri, payload

    def __enter__(self):
        """Context manager support for `with Scrobbler` syntax. Begins
        scrobbling the :class:`Scrobller`'s *media* object
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support for `with Scrobbler` syntax. Completes
        scrobbling the :class:`Scrobller`'s *media* object
        """
        self.finish()
