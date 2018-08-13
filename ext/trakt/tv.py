# -*- coding: utf-8 -*-
"""Interfaces to all of the TV objects offered by the Trakt.tv API"""
from collections import namedtuple
from datetime import datetime, timedelta
from trakt.core import Airs, Alias, Comment, Genre, delete, get
from trakt.errors import NotFoundException
from trakt.sync import (Scrobbler, rate, comment, add_to_collection,
                        add_to_watchlist, add_to_history, remove_from_history,
                        remove_from_collection, remove_from_watchlist, search)
from trakt.utils import slugify, extract_ids, airs_date, unicode_safe
from trakt.people import Person

__author__ = 'Jon Nappi'
__all__ = ['dismiss_recommendation', 'get_recommended_shows', 'genres',
           'popular_shows', 'trending_shows', 'updated_shows', 'TVShow',
           'TVEpisode', 'TVSeason', 'Translation']


Translation = namedtuple('Translation', ['title', 'overview', 'language'])


@delete
def dismiss_recommendation(title=None):
    """Dismiss the show matching the specified criteria from showing up in
    recommendations.
    """
    yield 'recommendations/shows/{title}'.format(title=title)


@get
def get_recommended_shows():
    """Get a list of :class:`TVShow`'s recommended based on your watching
    history and your friends. Results are returned with the top recommendation
    first.
    """
    data = yield 'recommendations/shows'
    shows = []
    for show in data:
        shows.append(TVShow(**show))
    yield shows


@get
def genres():
    """A list of all possible :class:`TVShow` Genres"""
    data = yield 'genres/shows'
    yield [Genre(g['name'], g['slug']) for g in data]


@get
def popular_shows():
    data = yield 'shows/popular'
    shows = []
    for show in data:
        data = show.get('ids', {})
        extract_ids(data)
        data['year'] = show['year']
        shows.append(TVShow(show['title'], **data))
    yield shows


@get
def trending_shows():
    """All :class:`TVShow`'s being watched right now"""
    data = yield 'shows/trending'
    to_ret = []
    for show in data:
        show_data = show.pop('show')
        ids = show_data.pop('ids')
        extract_ids(ids)
        show_data['watchers'] = show.get('watchers')
        to_ret.append(TVShow(**show_data))
    yield to_ret


@get
def updated_shows(timestamp=None):
    """All :class:`TVShow`'s updated since *timestamp* (PST). To establish a
    baseline timestamp, you can use the server/time method. It's recommended to
    store the timestamp so you can be efficient in using this method.
    """
    y_day = datetime.now() - timedelta(1)
    ts = timestamp or int(y_day.strftime('%s')) * 1000
    data = yield 'shows/updates/{start_date}'.format(start_date=ts)
    yield [TVShow(**d['show']) for d in data]


class TVShow(object):
    """A Class representing a TV Show object"""

    def __init__(self, title='', slug=None, **kwargs):
        super(TVShow, self).__init__()
        self.media_type = 'shows'
        self.top_watchers = self.top_episodes = self.year = self.tvdb = None
        self.imdb = self.genres = self.certification = self.network = None
        self.trakt = self.tmdb = self._aliases = self._comments = None
        self._images = self._people = self._ratings = self._translations = None
        self._seasons = None
        self.title = title
        self.slug = slug or slugify(self.title)
        if len(kwargs) > 0:
            self._build(kwargs)
        else:
            self._get()

    @classmethod
    def search(cls, title, year=None):
        """Perform a search for the specified *title*

        :param title: The title to search for
        """
        return search(title, search_type='show', year=year)

    @get
    def _get(self):
        data = yield self.ext_full
        data['first_aired'] = airs_date(data['first_aired'])
        data['airs'] = Airs(**data['airs'])
        self._build(data)

    def _build(self, data):
        extract_ids(data)
        for key, val in data.items():
            if hasattr(self, '_' + key):
                setattr(self, '_' + key, val)
            else:
                setattr(self, key, val)

    @property
    def ext(self):
        return 'shows/{slug}'.format(slug=self.slug)

    @property
    def ext_full(self):
        return self.ext + '?extended=full'

    @property
    def images_ext(self):
        """Uri to retrieve additional image information"""
        return self.ext + '?extended=images'

    @property
    @get
    def aliases(self):
        """A list of :class:`Alias` objects representing all of the other
        titles that this :class:`TVShow` is known by, and the countries where
        they go by their alternate titles
        """
        if self._aliases is None:
            data = yield (self.ext + '/aliases')
            self._aliases = [Alias(**alias) for alias in data]
        yield self._aliases

    @property
    def cast(self):
        """All of the cast members that worked on this :class:`TVShow`"""
        return [p for p in self.people if getattr(p, 'character')]

    @property
    @get
    def comments(self):
        """All comments (shouts and reviews) for this :class:`TVShow`. Most
        recent comments returned first.
        """
        # TODO (jnappi) Pagination
        from .users import User

        data = yield (self.ext + '/comments')
        self._comments = []
        for com in data:
            user = User(**com.pop('user'))
            self._comments.append(Comment(user=user, **com))
        yield self._comments

    @property
    def crew(self):
        """All of the crew members that worked on this :class:`TVShow`"""
        return [p for p in self.people if getattr(p, 'job')]

    @property
    def ids(self):
        """Accessor to the trakt, imdb, and tmdb ids, as well as the trakt.tv
        slug
        """
        return {'ids': {
            'trakt': self.trakt, 'slug': self.slug, 'imdb': self.imdb,
            'tmdb': self.tmdb, 'tvdb': self.tvdb
        }}

    @property
    @get
    def images(self):
        """All of the artwork associated with this :class:`TVShow`"""
        if self._images is None:
            data = yield self.images_ext
            self._images = data.get('images', {})
        yield self._images

    @property
    @get
    def people(self):
        """A :const:`list` of all of the :class:`People` involved in this
        :class:`TVShow`, including both cast and crew
        """
        if self._people is None:
            data = yield (self.ext + '/people')
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
            self._ratings = yield (self.ext + '/ratings')
        yield self._ratings

    @property
    @get
    def related(self):
        """The top 10 :class:`TVShow`'s related to this :class:`TVShow`"""
        data = yield (self.ext + '/related')
        shows = []
        for show in data:
            shows.append(TVShow(**show))
        yield shows

    @property
    @get
    def seasons(self):
        """A list of :class:`TVSeason` objects representing all of this show's
        seasons
        """
        if self._seasons is None:
            data = yield (self.ext + '/seasons?extended=full')
            self._seasons = []
            for season in data:
                extract_ids(season)
                self._seasons.append(TVSeason(self.title, **season))
        yield self._seasons

    @property
    @get
    def watching_now(self):
        """A list of all :class:`User`'s watching a movie."""
        from .users import User
        data = yield self.ext + '/watching'
        users = []
        for user in data:
            users.append(User(**user))
        yield users

    def add_to_library(self):
        """Add this :class:`TVShow` to your library."""
        add_to_collection(self)

    add_to_collection = add_to_library

    def add_to_watchlist(self):
        """Add this :class:`TVShow` to your watchlist"""
        add_to_watchlist(self)

    def comment(self, comment_body, spoiler=False, review=False):
        """Add a comment (shout or review) to this :class:`Move` on trakt."""
        comment(self, comment_body, spoiler, review)

    def dismiss(self):
        """Dismiss this movie from showing up in Movie Recommendations"""
        dismiss_recommendation(title=self.title)

    @get
    def get_translations(self, country_code='us'):
        """Returns all :class:`Translation`'s for a movie, including language
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
        """Add this :class:`TVShow`, watched outside of trakt, to your library.
        """
        add_to_history(self, watched_at)

    def mark_as_unseen(self):
        """Remove this :class:`TVShow`, watched outside of trakt, from your
        library.
        """
        remove_from_history(self)

    def rate(self, rating):
        """Rate this :class:`TVShow` on trakt. Depending on the current users
        settings, this may also send out social updates to facebook, twitter,
        tumblr, and path.
        """
        rate(self, rating)

    def remove_from_library(self):
        """Remove this :class:`TVShow` from your library."""
        remove_from_collection(self)

    remove_from_collection = remove_from_library

    def remove_from_watchlist(self):
        remove_from_watchlist(self)

    def to_json(self):
        return {'shows': [{
            'title': self.title, 'year': self.year, 'ids': self.ids
        }]}

    def __str__(self):
        """Return a string representation of a :class:`TVShow`"""
        return '<TVShow> {}'.format(unicode_safe(self.title))

    __repr__ = __str__


class TVSeason(object):
    """Container for TV Seasons"""

    def __init__(self, show, season=1, slug=None, **kwargs):
        super(TVSeason, self).__init__()
        self.show = show
        self.season = season
        self.slug = slug or slugify(show)
        self._episodes = self._comments = self._ratings = None
        self.ext = 'shows/{id}/seasons/{season}'.format(id=self.slug,
                                                        season=season)
        if len(kwargs) > 0:
            self._build(kwargs)
        else:
            self._get()

    @get
    def _get(self):
        """Handle getting this :class:`TVSeason`'s data from trakt and building
        our attributes from the returned data
        """
        data = yield self.ext
        self._build(data)

    def _build(self, data):
        """Build this :class:`TVSeason` object with the data in *data*"""
        # only try to build our episodes if we got a list of episodes, not a
        # dict of season data
        if isinstance(data, list):
            self._episodes = [TVEpisode(show=self.show, **ep) for ep in data]
        else:
            for key, val in data.items():
                try:
                    setattr(self, key, val)
                except AttributeError:
                    setattr(self, '_'+key, val)

    @property
    @get
    def comments(self):
        """All comments (shouts and reviews) for this :class:`TVSeason`. Most
        recent comments returned first.
        """
        # TODO (jnappi) Pagination
        from .users import User

        data = yield (self.ext + '/comments')
        self._comments = []
        for com in data:
            user = User(**com.pop('user'))
            comment = Comment(user=user, **com)
            self._comments.append(comment)
        yield self._comments

    @property
    def episodes(self):
        """A list of :class:`TVEpisode` objects representing all of the
        Episodes in this :class:`TVSeason`. Because there is no "Get all
        episodes for a season" endpoint on the trakt api
        """
        if self._episodes is None:
            self._episodes = []
            index = 1
            while True:  # Dangerous? Perhaps, but it works
                try:
                    ep = self._episode_getter(index)
                    self._episodes.append(ep)
                except (NotFoundException, TypeError):
                    break
                index += 1
        return self._episodes

    @get
    def _episode_getter(self, episode):
        """Recursive episode getter generator. Will attempt to get the
        speicifed episode for this season, and if the requested episode wasn't
        found, then we return :const:`None` to indicate to the `episodes`
        property that we've already yielded all valid episodes for this season.

        :param episode: An int corresponding to the number of the episode
            we're trying to retrieve
        """
        episode_extension = '/episodes/{}?extended=full'.format(episode)
        try:
            data = yield (self.ext + episode_extension)
            yield TVEpisode(show=self.show, **data)
        except NotFoundException:
            yield None

    @property
    @get
    def ratings(self):
        """Ratings (between 0 and 10) and distribution for a movie."""
        if self._ratings is None:
            self._ratings = yield (self.ext + '/ratings')
        yield self._ratings

    @property
    @get
    def watching_now(self):
        """A list of all :class:`User`'s watching a movie."""
        from .users import User

        data = yield self.ext + '/watching'
        users = []
        for user in data:
            users.append(User(**user))
        yield users

    def add_to_library(self):
        """Add this :class:`TVSeason` to your library."""
        add_to_collection(self)

    add_to_collection = add_to_library

    def remove_from_library(self):
        """Remove this :class:`TVSeason` from your library."""
        remove_from_collection(self)

    remove_from_collection = remove_from_library

    def to_json(self):
        """Return this :class:`TVSeason` as a Trakt consumable API blob"""
        # I hate that this extra lookup needs to happen here, but I can't see
        # any other way of getting around not having the data on the show...
        show_obj = TVShow(self.slug).to_json()
        show_obj.update({'seasons': [{'number': self.season}]})
        return {'shows': [show_obj]}

    def __str__(self):
        title = ['<TVSeason>:', self.show, 'Season', self.season]
        title = map(str, title)
        return ' '.join(title)

    def __len__(self):
        return len(self._episodes)

    __repr__ = __str__


class TVEpisode(object):
    """Container for TV Episodes"""

    def __init__(self, show, season, number=-1, **kwargs):
        super(TVEpisode, self).__init__()
        self.media_type = 'episodes'
        self.show = show
        self.season = season
        self.number = number
        self.overview = self.title = self.year = self.number_abs = None
        self.first_aired = self.last_updated = None
        self.trakt = self.tmdb = self.tvdb = self.imdb = None
        self.tvrage = self._stats = self._images = self._comments = None
        self._translations = self._ratings = None
        if len(kwargs) > 0:
            self._build(kwargs)
        else:
            self._get()
        self.episode = self.number  # Backwards compatability

    @get
    def _get(self):
        """Handle getting this :class:`TVEpisode`'s data from trakt and
        building our attributes from the returned data
        """
        data = yield self.ext_full
        self._build(data)

    def _build(self, data):
        """Build this :class:`TVEpisode` object with the data in *data*"""
        extract_ids(data)
        for key, val in data.items():
            if hasattr(self, '_' + key):
                setattr(self, '_' + key, val)
            else:
                setattr(self, key, val)

    @property
    @get
    def comments(self):
        """All comments (shouts and reviews) for this :class:`TVEpisode`. Most
        recent comments returned first.
        """
        # TODO (jnappi) Pagination
        from .users import User

        data = yield (self.ext + '/comments')
        self._comments = []
        for com in data:
            user = User(**com.pop('user'))
            self._comments.append(Comment(user=user, **com))
        yield self._comments

    @property
    def ext(self):
        return 'shows/{id}/seasons/{season}/episodes/{episode}'.format(
            id=slugify(self.show), season=self.season, episode=self.number
        )

    @property
    def ext_full(self):
        return self.ext + '?extended=full'

    @property
    def images_ext(self):
        """Uri to retrieve additional image information"""
        return self.ext + '?extended=images'

    @classmethod
    def search(cls, title, year=None):
        """Perform a search for an episode with a title matching *title*

        :param title: The title to search for
        :param year: Optional year to limit results to
        """
        return search(title, search_type='episode', year=year)

    @property
    def ids(self):
        """Accessor to the trakt, imdb, and tmdb ids, as well as the trakt.tv
        slug
        """
        return {'ids': {
            'trakt': self.trakt, 'imdb': self.imdb, 'tmdb': self.tmdb
        }}

    @property
    @get
    def images(self):
        """All of the artwork associated with this :class:`TVEpisode`"""
        if self._images is None:
            data = yield self.images_ext
            self._images = data.get('images', {})
        yield self._images

    @property
    def first_aired_date(self):
        """Python datetime object representation of the first_aired date of
        this :class:`TVEpisode`
        """
        return airs_date(self.first_aired)

    @property
    @get
    def ratings(self):
        """Ratings (between 0 and 10) and distribution for a movie."""
        if self._ratings is None:
            self._ratings = yield (self.ext + '/ratings')
        yield self._ratings

    @property
    @get
    def watching_now(self):
        """A list of all :class:`User`'s watching a movie."""
        from .users import User

        data = yield self.ext + '/watching'
        users = []
        for user in data:
            users.append(User(**user))
        yield users

    def get_description(self):
        """backwards compatible function that returns this :class:`TVEpisode`'s
        overview
        '"""
        return self.overview

    def rate(self, rating):
        """Rate this :class:`TVEpisode` on trakt. Depending on the current users
        settings, this may also send out social updates to facebook, twitter,
        tumblr, and path.
        """
        rate(self, rating)

    def add_to_library(self):
        """Add this :class:`TVEpisode` to your Trakt.tv library"""
        add_to_collection(self)

    add_to_collection = add_to_library

    def add_to_watchlist(self):
        """Add this :class:`TVEpisode` to your watchlist"""
        add_to_watchlist(self)

    def mark_as_seen(self, watched_at=None):
        """Mark this episode as seen"""
        add_to_history(self, watched_at)

    def mark_as_unseen(self):
        """Remove this :class:`TVEpisode` from your list of watched episodes"""
        remove_from_history(self)

    def remove_from_library(self):
        """Remove this :class:`TVEpisode` from your library"""
        remove_from_collection(self)

    remove_from_collection = remove_from_library

    def remove_from_watchlist(self):
        """Remove this :class:`TVEpisode` from your watchlist"""
        remove_from_watchlist(self)

    def comment(self, comment_body, spoiler=False, review=False):
        """Add a comment (shout or review) to this :class:`TVEpisode` on trakt.
        """
        comment(self, comment_body, spoiler, review)

    def scrobble(self, progress, app_version, app_date):
        """Scrobble this :class:`TVEpisode` via the TraktTV Api

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

    def to_json(self):
        """Return this :class:`TVEpisode` as a trakt recognizable JSON object
        """
        return {
            'episodes': [{
                'ids': {
                    'trakt': self.trakt
                }
            }]
        }

    def __str__(self):
        return '<TVEpisode>: {} S{}E{} {}'.format(self.show, self.season,
                                                  self.number,
                                                  unicode_safe(self.title))
    __repr__ = __str__
