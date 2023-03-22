# -*- coding: utf-8 -*-
"""Interfaces to all of the Movie objects offered by the Trakt.tv API"""
from collections import namedtuple

from trakt.core import Alias, Comment, Genre, delete, get
from trakt.mixins import IdsMixin
from trakt.people import Person
from trakt.sync import (Scrobbler, add_to_collection, add_to_history,
                        add_to_watchlist, checkin_media, comment,
                        delete_checkin, rate, remove_from_collection,
                        remove_from_history, remove_from_watchlist, search)
from trakt.utils import now, slugify

__author__ = 'Jon Nappi'
__all__ = ['dismiss_recommendation', 'get_recommended_movies', 'genres',
           'trending_movies', 'updated_movies', 'Release', 'Movie',
           'Translation']

Translation = namedtuple('Translation', ['title', 'overview', 'tagline',
                                         'language'])


@delete
def dismiss_recommendation(title):
    """Dismiss the movie matching the specified criteria from showing up in
    recommendations.
    """
    yield 'recommendations/movies/{title}'.format(title=slugify(str(title)))


@get
def get_recommended_movies():
    """Get a list of :class:`Movie`'s recommended based on your watching
    history and your friends. Results are returned with the top recommendation
    first.
    """
    data = yield 'recommendations/movies'
    movies = []
    for movie in data:
        movies.append(Movie(**movie))
    yield movies


@get
def genres():
    """A list of all possible :class:`Movie` Genres"""
    data = yield 'genres/movies'
    yield [Genre(g['name'], g['slug']) for g in data]


@get
def trending_movies():
    """All :class:`Movie`'s being watched right now"""
    data = yield '/movies/trending'
    to_ret = []
    for movie in data:
        watchers = movie.pop('watchers')
        to_ret.append(Movie(watchers=watchers, **movie.pop('movie')))
    yield to_ret


@get
def updated_movies(timestamp=None):
    """Returns all movies updated since a timestamp. The server time is in PST.
    To establish a baseline timestamp, you can use the server/time method. It's
    recommended to store the timestamp so you can be efficient in using this
    method.
    """
    ts = timestamp or now()
    data = yield 'movies/updates/{start_date}'.format(start_date=ts)
    to_ret = []
    for movie in data:
        mov = movie.pop('movie')
        mov.update({'updated_at': movie.pop('updated_at')})
        to_ret.append(Movie(**mov))
    yield to_ret


Release = namedtuple('Release', ['country', 'certification', 'release_date',
                                 'note', 'release_type'])


class Movie(IdsMixin):
    """A Class representing a Movie object"""
    def __init__(self, title, year=None, slug=None, **kwargs):
        super().__init__()
        self.media_type = 'movies'
        self.title = title
        self.year = int(year) if year is not None else year
        if self.year is not None and slug is None:
            self.slug = slugify('-'.join([self.title, str(self.year)]))
        else:
            self.slug = slug or slugify(self.title)

        self.updated_at = self.trailer = self.homepage = self.rating = None
        self.votes = self.language = self.available_translations = None
        self.genres = self.certification = None
        self._comments = self._images = self._aliases = self._people = None
        self._ratings = self._releases = self._translations = None
        self.tmdb_id = self.imdb_id = None  # @deprecated: unused
        self.trakt_id = None  # @deprecated: unused

        if len(kwargs) > 0:
            self._build(kwargs)
        else:
            self._get()

    @staticmethod
    def search(title, year=None):
        """Perform a search for a movie with a title matching *title*

        :param title: The title to search for
        :param year: Optional year to limit results to
        """
        return search(title, search_type='movie', year=year)

    @get
    def _get(self):
        """Handle getting this :class:`Movie`'s data from trakt and building
        our attributes from the returned data
        """
        data = yield self.ext_full
        self._build(data)

    def _build(self, data):
        """Build this :class:`Movie` object with the data in *data*"""
        for key, val in data.items():
            if hasattr(self, '_' + key):
                setattr(self, '_' + key, val)
            else:
                setattr(self, key, val)

    @property
    def ext(self):
        """Base uri to retrieve basic information about this :class:`Movie`"""
        return 'movies/{slug}'.format(slug=self.slug)

    @property
    def ext_full(self):
        """Uri to retrieve all information about this :class:`Movie`"""
        return self.ext + '?extended=full'

    @property
    def images_ext(self):
        """Uri to retrieve additional image information"""
        return self.ext + '?extended=images'

    @property
    @get
    def aliases(self):
        """A list of :class:`Alias` objects representing all of the other
        titles that this :class:`Movie` is known by, and the countries where
        they go by their alternate titles
        """
        if self._aliases is None:
            data = yield self.ext + '/aliases'
            self._aliases = [Alias(**alias) for alias in data]
        yield self._aliases

    @property
    def cast(self):
        """All of the cast members that worked on this :class:`Movie`"""
        return [p for p in self.people if getattr(p, 'character')]

    @property
    @get
    def comments(self):
        """All comments (shouts and reviews) for this :class:`Movie`. Most
        recent comments returned first.
        """
        # TODO (jnappi) Pagination
        from trakt.users import User
        data = yield self.ext + '/comments'
        self._comments = []
        for com in data:
            user = User(**com.get('user'))
            self._comments.append(
                Comment(user=user, **{k: com[k] for k in com if k != 'user'})
            )
        yield self._comments

    @property
    def crew(self):
        """All of the crew members that worked on this :class:`Movie`"""
        return [p for p in self.people if getattr(p, 'job')]

    @property
    @get
    def images(self):
        """All of the artwork associated with this :class:`Movie`"""
        if self._images is None:
            data = yield self.images_ext
            self._images = data.get('images', {})
        yield self._images

    @property
    @get
    def people(self):
        """A :const:`list` of all of the :class:`People` involved in this
        :class:`Movie`, including both cast and crew
        """
        if self._people is None:
            data = yield self.ext + '/people'
            crew = data.get('crew', {})
            cast = []
            for c in data.get('cast', []):
                person = c.pop('person')
                character = c.pop('character')
                cast.append(Person(character=character, **person))

            _crew = []
            for key in crew:
                for department in crew.get(key):  # lists
                    person = department.get('person')
                    person.update({'job': department.get('job')})
                    _crew.append(Person(**person))
            self._people = cast + _crew
        yield self._people

    @property
    @get
    def ratings(self):
        """Ratings (between 0 and 10) and distribution for a movie."""
        if self._ratings is None:
            self._ratings = yield self.ext + '/ratings'
        yield self._ratings

    @property
    @get
    def related(self):
        """The top 10 :class:`Movie`'s related to this :class:`Movie`"""
        data = yield self.ext + '/related'
        movies = []
        for movie in data:
            movies.append(Movie(**movie))
        yield movies

    @property
    @get
    def watching_now(self):
        """A list of all :class:`User`'s watching a movie."""
        from trakt.users import User
        data = yield self.ext + '/watching'
        users = []
        for user in data:
            users.append(User(**user))
        yield users

    def add_to_library(self):
        """Add this :class:`Movie` to your library."""
        return add_to_collection(self)
    add_to_collection = add_to_library

    def add_to_watchlist(self):
        """Add this :class:`Movie` to your watchlist"""
        return add_to_watchlist(self)

    def comment(self, comment_body, spoiler=False, review=False):
        """Add a comment (shout or review) to this :class:`Move` on trakt."""
        return comment(self, comment_body, spoiler, review)

    def dismiss(self):
        """Dismiss this movie from showing up in Movie Recommendations"""
        dismiss_recommendation(title=self.title)

    @get
    def get_releases(self, country_code='us'):
        """Returns all :class:`Release`s for a movie including country,
        certification, and release date.

        :param country_code: The 2 character country code to search from
        :return: a :const:`list` of :class:`Release` objects
        """
        if self._releases is None:
            data = yield self.ext + '/releases/{cc}'.format(cc=country_code)
            self._releases = [Release(**release) for release in data]
        yield self._releases

    @get
    def get_translations(self, country_code='us'):
        """Returns all :class:`Translation`s for a movie, including language
        and translated values for title, tagline and overview.

        :param country_code: The 2 character country code to search from
        :return: a :const:`list` of :class:`Translation` objects
        """
        if self._translations is None:
            data = yield self.ext + '/translations/{cc}'.format(
                cc=country_code
            )
            self._translations = [Translation(**translation)
                                  for translation in data]
        yield self._translations

    def mark_as_seen(self, watched_at=None):
        """Add this :class:`Movie`, watched outside of trakt, to your library.
        """
        return add_to_history(self, watched_at)

    def mark_as_unseen(self):
        """Remove this :class:`Movie`, watched outside of trakt, from your
        library.
        """
        return remove_from_history(self)

    def rate(self, rating):
        """Rate this :class:`Movie` on trakt. Depending on the current users
        settings, this may also send out social updates to facebook, twitter,
        tumblr, and path.
        """
        return rate(self, rating)

    def remove_from_library(self):
        """Remove this :class:`Movie` from your library."""
        return remove_from_collection(self)
    remove_from_collection = remove_from_library

    def remove_from_watchlist(self):
        return remove_from_watchlist(self)

    def scrobble(self, progress, app_version, app_date):
        """Notify trakt that the current user has finished watching a movie.
        This commits this :class:`Movie` to the current users profile. You
        should use movie/watching prior to calling this method.

        :param progress: % progress, integer 0-100. It is recommended to call
            the watching API every 15 minutes, then call the scrobble API near
            the end of the movie to lock it in.
        :param app_version: Version number of the media center, be as specific
            as you can including nightly build number, etc. Used to help debug
            your plugin.
        :param app_date: Build date of the media center. Used to help debug
            your plugin.
        """
        return Scrobbler(self, progress, app_version, app_date)

    def checkin(self, app_version, app_date, message="", sharing=None,
                venue_id="", venue_name="", delete=False):
        """Checkin this :class:`Movie` via the TraktTV API.

        :param app_version:Version number of the media center, be as specific
            as you can including nightly build number, etc. Used to help debug
            your plugin.
        :param app_date: Build date of the media center. Used to help debug
            your plugin.
        :param message: Message used for sharing. If not sent, it will use the
            watching string in the user settings.
        :param sharing: Control sharing to any connected social networks.
        :param venue_id: Foursquare venue ID.
        :param venue_name: Foursquare venue name.
        :param delete: If True, the checkin will be deleted.
        """
        if delete:
            delete_checkin()
        return checkin_media(self, app_version, app_date, message, sharing, venue_id,
                      venue_name)

    def to_json_singular(self):
        return {'movie': dict(title=self.title,
                              year=self.year,
                              **self.ids)}

    def to_json(self):
        return {'movies': [dict(title=self.title,
                                year=self.year,
                                **self.ids)]}

    def __str__(self):
        """String representation of a :class:`Movie`"""
        return '<Movie>: {}'.format(self.title)
    __repr__ = __str__
