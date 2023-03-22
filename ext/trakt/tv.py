# -*- coding: utf-8 -*-
"""Interfaces to all of the TV objects offered by the Trakt.tv API"""
from collections import namedtuple
from datetime import datetime, timedelta
from urllib.parse import urlencode

from trakt.core import Airs, Alias, Comment, Genre, delete, get
from trakt.errors import NotFoundException
from trakt.mixins import IdsMixin
from trakt.people import Person
from trakt.sync import (Scrobbler, add_to_collection, add_to_history,
                        add_to_watchlist, checkin_media, comment,
                        delete_checkin, rate, remove_from_collection,
                        remove_from_history, remove_from_watchlist, search)
from trakt.utils import airs_date, slugify

__author__ = 'Jon Nappi'
__all__ = ['dismiss_recommendation', 'get_recommended_shows', 'genres',
           'popular_shows', 'trending_shows', 'updated_shows',
           'recommended_shows', 'played_shows', 'watched_shows',
           'collected_shows', 'anticipated_shows', 'TVShow', 'TVEpisode',
           'TVSeason', 'Translation']


Translation = namedtuple('Translation', ['title', 'overview', 'language'])


@delete
def dismiss_recommendation(title=None):
    """Dismiss the show matching the specified criteria from showing up in
    recommendations.
    """
    yield 'recommendations/shows/{title}'.format(title=title)


@get
def get_recommended_shows(page=1, limit=10):
    """Get a list of :class:`TVShow`'s recommended based on your watching
    history and your friends. Results are returned with the top recommendation
    first.
    """
    data = yield 'recommendations/shows?page={page}&limit={limit}'.format(
        page=page, limit=limit
    )
    yield [TVShow(**show) for show in data]


@get
def genres():
    """A list of all possible :class:`TVShow` Genres"""
    data = yield 'genres/shows'
    yield [Genre(g['name'], g['slug']) for g in data]


@get
def popular_shows(page=1, limit=10, extended=None):
    uri = 'shows/popular?page={page}&limit={limit}'.format(
        page=page, limit=limit
    )
    if extended:
        uri += '&extended={extended}'.format(extended=extended)

    data = yield uri
    yield [TVShow(**show) for show in data]


@get
def trending_shows(page=1, limit=10, extended=None):
    """All :class:`TVShow`'s being watched right now"""
    uri = 'shows/trending?page={page}&limit={limit}'.format(
        page=page, limit=limit
    )
    if extended:
        uri += '&extended={extended}'.format(extended=extended)

    data = yield uri
    yield [TVShow(**show['show']) for show in data]


@get
def updated_shows(timestamp=None, page=1, limit=10, extended=None):
    """All :class:`TVShow`'s updated since *timestamp* (PST). To establish a
    baseline timestamp, you can use the server/time method. It's recommended to
    store the timestamp so you can be efficient in using this method.
    """
    y_day = datetime.now() - timedelta(1)
    ts = timestamp or int(y_day.strftime('%s')) * 1000
    uri = 'shows/updates/{start_date}?page={page}&limit={limit}'.format(
        start_date=ts, page=page, limit=limit
    )
    if extended:
        uri += '&extended={extended}'.format(extended=extended)

    data = yield uri
    yield [TVShow(**show) for show in data]


@get
def recommended_shows(time_period='weekly', page=1, limit=10, extended=None):
    """The most recommended shows in the specified time period,
        defaulting to weekly.
    All stats are relative to the specific time period."""
    valid_time_period = ('daily', 'weekly', 'monthly', 'yearly', 'all')
    if time_period not in valid_time_period:
        raise ValueError('time_period must be one of {}'.format(
            valid_time_period
        ))

    uri = 'shows/recommended/{time_period}?page={page}&limit={limit}'.format(
        time_period=time_period, page=page, limit=limit
    )
    if extended:
        uri += '&extended={extended}'.format(extended=extended)

    data = yield uri
    yield [TVShow(**show['show']) for show in data]


@get
def played_shows(time_period='weekly', page=1, limit=10, extended=None):
    """the most played shows.
    (a single user can watch multiple episodes multiple times)
            shows in the specified time period,
            defaulting to weekly.
            All stats are relative to the specific time period."""
    valid_time_period = ('daily', 'weekly', 'monthly', 'yearly', 'all')
    if time_period not in valid_time_period:
        raise ValueError('time_period must be one of {}'.format(
            valid_time_period
        ))

    uri = 'shows/played/{time_period}?page={page}&limit={limit}'.format(
        time_period=time_period, page=page, limit=limit
    )
    if extended:
        uri += '&extended={extended}'.format(extended=extended)

    data = yield uri
    yield [TVShow(**show['show']) for show in data]


@get
def watched_shows(time_period='weekly', page=1, limit=10, extended=None):
    """Return most watched (unique users) shows in the specified time period.

    Defaulting to weekly.
    All stats are relative to the specific time period."""
    valid_time_period = ('daily', 'weekly', 'monthly', 'yearly', 'all')
    if time_period not in valid_time_period:
        raise ValueError('time_period must be one of {}'.format(
            valid_time_period
        ))

    uri = 'shows/watched/{time_period}?page={page}&limit={limit}'.format(
        time_period=time_period, page=page, limit=limit
    )
    if extended:
        uri += '&extended={extended}'.format(extended=extended)

    data = yield uri
    yield [TVShow(**show['show']) for show in data]


@get
def collected_shows(time_period='weekly', page=1, limit=10, extended=None):
    """Return most collected (unique users) shows in the specified time period.

    Defaulting to weekly.
    All stats are relative to the specific time period."""
    valid_time_period = ('daily', 'weekly', 'monthly', 'yearly', 'all')
    if time_period not in valid_time_period:
        raise ValueError('time_period must be one of {}'.format(
            valid_time_period
        ))

    uri = 'shows/collected/{time_period}?page={page}&limit={limit}'.format(
        time_period=time_period, page=page, limit=limit
    )
    if extended:
        uri += '&extended={extended}'.format(extended=extended)

    data = yield uri
    yield [TVShow(**show['show']) for show in data]


@get
def anticipated_shows(page=1, limit=10, extended=None):
    """
    Return most anticipated shows based on the number of lists
        a show appears on.
    """
    uri = 'shows/anticipated?page={page}&limit={limit}'.format(
        page=page, limit=limit
    )
    if extended:
        uri += '&extended={extended}'.format(extended=extended)
    data = yield uri
    yield [TVShow(**show['show']) for show in data]


class TVShow(IdsMixin):
    """A Class representing a TV Show object."""

    def __init__(self, title='', slug=None, seasons=None, **kwargs):
        super().__init__()
        self.media_type = 'shows'
        self.top_watchers = self.top_episodes = self.year = None
        self.genres = self.certification = self.network = None
        self._aliases = self._comments = None
        self._images = self._people = self._ratings = self._translations = None
        self._last_episode = self._next_episode = None
        self._slug = slug
        self.title = title
        self._seasons = self._build_seasons(seasons) if seasons else None

        if len(kwargs) > 0:
            self._build(kwargs)
        else:
            self._get()

    def _build_seasons(self, seasons_data):
        seasons = []
        show_id = self.trakt
        for season_data in seasons_data:
            number = season_data.pop('number')
            season = TVSeason(show=self.title, season=number, show_id=show_id, **season_data)
            seasons.append(season)
        return seasons

    @property
    def slug(self):
        if self._ids.get('slug', None) is not None:
            return self._ids['slug']

        if self._slug is not None:
            return self._slug

        if self.year is None:
            return slugify(self.title)

        return slugify(self.title + ' ' + str(self.year))

    @staticmethod
    def search(title, year=None):
        """Perform a search for the specified *title*.

        :param title: The title to search for
        :param year: An optional year for the item you're searching for.
        """
        return search(title, search_type='show', year=year)

    @get
    def _get(self):
        data = yield self.ext_full
        data['first_aired'] = airs_date(data['first_aired'])
        data['airs'] = Airs(**data['airs'])
        self._build(data)

    def _build(self, data):
        for key, val in data.items():
            if hasattr(self, '_' + key):
                setattr(self, '_' + key, val)
            else:
                setattr(self, key, val)

    @property
    def ext(self):
        return 'shows/{slug}'.format(slug=self.trakt or self.slug)

    @property
    def ext_full(self):
        return self.ext + '?extended=full'

    @property
    def images_ext(self):
        """Uri to retrieve additional image information."""
        return self.ext + '?extended=images'

    @property
    @get
    def aliases(self):
        """A list of :class:`Alias` objects representing all of the other
        titles that this :class:`TVShow` is known by, and the countries where
        they go by their alternate titles
        """
        if self._aliases is None:
            data = yield self.ext + '/aliases'
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

        data = yield self.ext + '/comments'
        self._comments = []
        for com in data:
            user = User(**com.pop('user'))
            self._comments.append(Comment(user=user, **com))
        yield self._comments

    def _progress(self, progress_type,
                  specials=False, count_specials=False, hidden=False):
        uri = f'{self.ext}/progress/{progress_type}'
        params = {}
        if specials:
            params['specials'] = 'true'
        if count_specials:
            params['count_specials'] = 'true'
        if hidden:
            params['hidden'] = 'true'

        if params:
            uri += '?' + urlencode(params)

        data = yield uri

        yield data

    @property
    @get
    def progress(self):
        """
        collection progress for a show including details on all aired
        seasons and episodes.

        The next_episode will be the next episode the user should collect,
        if there are no upcoming episodes it will be set to null.
        """
        return self._progress('collection')

    @get
    def collection_progress(self, **kwargs):
        """
        collection progress for a show including details on all aired
        seasons and episodes.

        The next_episode will be the next episode the user should collect,
        if there are no upcoming episodes it will be set to null.

        specials: include specials as season 0. Default: false.
        count_specials: count specials in the overall stats. Default: false.
        hidden: include any hidden seasons. Default: false.

        https://trakt.docs.apiary.io/#reference/shows/collection-progress/get-show-collection-progress
        """
        return self._progress('collection', **kwargs)

    @get
    def watched_progress(self, **kwargs):
        """
        watched progress for a show including details on all aired seasons
        and episodes.

        specials: include specials as season 0. Default: false.
        count_specials: count specials in the overall stats. Default: false.
        hidden: include any hidden seasons. Default: false.

        https://trakt.docs.apiary.io/#reference/shows/watched-progress/get-show-collection-progress
        """
        return self._progress('watched', **kwargs)

    @property
    def crew(self):
        """All of the crew members that worked on this :class:`TVShow`"""
        return [p for p in self.people if getattr(p, 'job')]

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
        """The top 10 :class:`TVShow`'s related to this :class:`TVShow`"""
        data = yield self.ext + '/related'
        shows = []
        for show in data:
            shows.append(TVShow(**show))
        yield shows

    @property
    @get
    def seasons(self):
        """A list of :class:`TVSeason` objects representing all of this show's
        seasons which each contain :class:`TVEpisode` elements
        """
        if self._seasons is None:
            data = yield self.ext + '/seasons?extended=episodes'
            self._seasons = []
            for season in data:
                # Prepare episodes
                episodes = []
                for ep in season.pop('episodes', []):
                    episode = TVEpisode(show=self.title,
                                        show_id=self.trakt, **ep)
                    episodes.append(episode)

                number = season.pop('number')
                season = TVSeason(self.title, number, self.slug, **season)
                season._episodes = episodes

                self._seasons.append(season)

        yield self._seasons

    @property
    @get
    def last_episode(self):
        """Returns the most recently aired :class:`TVEpisode`. If no episode
        is found, `None` will be returned.
        """
        if self._last_episode is None:
            data = yield self.ext + '/last_episode?extended=full'
            self._last_episode = data and TVEpisode(show=self.title,
                                                    show_id=self.trakt, **data)
        yield self._last_episode

    @property
    @get
    def next_episode(self):
        """Returns the next scheduled to air :class:`TVEpisode`. If no episode
        is found, `None` will be returned.
        """
        if self._next_episode is None:
            data = yield self.ext + '/next_episode?extended=full'
            self._next_episode = data and TVEpisode(show=self.title,
                                                    show_id=self.trakt, **data)
        yield self._next_episode

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
        return add_to_collection(self)

    add_to_collection = add_to_library

    def add_to_watchlist(self):
        """Add this :class:`TVShow` to your watchlist"""
        return add_to_watchlist(self)

    def comment(self, comment_body, spoiler=False, review=False):
        """Add a comment (shout or review) to this :class:`Move` on trakt."""
        return comment(self, comment_body, spoiler, review)

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
        return add_to_history(self, watched_at)

    def mark_as_unseen(self):
        """Remove this :class:`TVShow`, watched outside of trakt, from your
        library.
        """
        return remove_from_history(self)

    def rate(self, rating):
        """Rate this :class:`TVShow` on trakt. Depending on the current users
        settings, this may also send out social updates to facebook, twitter,
        tumblr, and path.
        """
        return rate(self, rating)

    def remove_from_library(self):
        """Remove this :class:`TVShow` from your library."""
        return remove_from_collection(self)

    remove_from_collection = remove_from_library

    def remove_from_watchlist(self):
        return remove_from_watchlist(self)

    def to_json_singular(self):
        return {'show': {
            'title': self.title, 'year': self.year, 'ids': self.ids
        }}

    def to_json(self):
        return {'shows': [{
            'title': self.title, 'year': self.year, 'ids': self.ids
        }]}

    def __str__(self):
        """Return a string representation of a :class:`TVShow`"""
        return '<TVShow> {}'.format(self.title)

    __repr__ = __str__


class TVSeason(IdsMixin):
    """Container for TV Seasons"""

    def __init__(self, show, season=1, slug=None, episodes=None, show_id=None, **kwargs):
        super().__init__()
        self.show = show
        self.show_id = show_id
        self.season = season
        self.slug = slug or slugify(show)
        self.ext = 'shows/{id}/seasons/{season}'.format(id=self.slug, season=season)
        self._comments = self._ratings = None
        self._episodes = self._build_episodes(episodes) if episodes else None

        if len(kwargs) > 0 or episodes:
            self._build(kwargs)
        else:
            self._get()

    def _build_episodes(self, episodes_data):
        episodes = []
        for episode_data in episodes_data:
            season = episode_data.get('season', self.season)
            episode = TVEpisode(show=self.show, season=season, show_id=self.show_id, **episode_data)
            episodes.append(episode)
        return episodes

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

        data = yield self.ext + '/comments'
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
        specified episode for this season, and if the requested episode wasn't
        found, then we return :const:`None` to indicate to the `episodes`
        property that we've already yielded all valid episodes for this season.

        :param episode: An int corresponding to the number of the episode
            we're trying to retrieve
        """
        episode_extension = '/episodes/{}?extended=full'.format(episode)
        try:
            data = yield self.ext + episode_extension
            yield TVEpisode(show=self.show, **data)
        except NotFoundException:
            yield None

    @property
    @get
    def ratings(self):
        """Ratings (between 0 and 10) and distribution for a movie."""
        if self._ratings is None:
            self._ratings = yield self.ext + '/ratings'
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
        return add_to_collection(self)

    add_to_collection = add_to_library

    def remove_from_library(self):
        """Remove this :class:`TVSeason` from your library."""
        return remove_from_collection(self)

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


class TVEpisode(IdsMixin):
    """Container for TV Episodes"""

    def __init__(self, show, season, number=-1, **kwargs):
        super().__init__()
        self.media_type = 'episodes'
        self.show = show
        self.season = season
        self.number = number
        self.overview = self.title = self.year = self.number_abs = None
        self.first_aired = self.last_updated = None
        self.runtime = None
        self._stats = self._images = self._comments = None
        self._translations = self._ratings = None
        if len(kwargs) > 0:
            self._build(kwargs)
        else:
            self._get()
        self.episode = self.number  # Backwards compatibility

    @get
    def _get(self):
        """Handle getting this :class:`TVEpisode`'s data from trakt and
        building our attributes from the returned data
        """
        data = yield self.ext_full
        self._build(data)

    def _build(self, data):
        """Build this :class:`TVEpisode` object with the data in *data*"""
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

        data = yield self.ext + '/comments'
        self._comments = []
        for com in data:
            user = User(**com.pop('user'))
            self._comments.append(Comment(user=user, **com))
        yield self._comments

    @property
    def ext(self):
        show_id = getattr(self, "show_id", None)
        if not show_id:
            show_id = slugify(self.show)
        return 'shows/{id}/seasons/{season}/episodes/{episode}'.format(
            id=show_id, season=self.season, episode=self.number
        )

    @property
    def ext_full(self):
        return self.ext + '?extended=full'

    @property
    def images_ext(self):
        """Uri to retrieve additional image information"""
        return self.ext + '?extended=images'

    @staticmethod
    def search(title, year=None):
        """Perform a search for an episode with a title matching *title*

        :param title: The title to search for
        :param year: Optional year to limit results to
        """
        return search(title, search_type='episode', year=year)

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
    def first_aired_end_time(self):
        """Python datetime object representing the corresponding end time of
        the first_aired date of this episode
        """
        return self.end_time_from_custom_start(start_date=None)

    def end_time_from_custom_start(self, start_date=None):
        """Calculate a python datetime object representing the calculated end
        time of an episode from the given start_date. ie, start_date +
        runtime.

        :param start_date: a datetime instance indicating the start date of a
        given airing of this episode. Defaults to the first_aired_date of this
        episode.
        """
        if start_date is None:
            start_date = self.first_aired_date

        # create a timedelta instance for the runtime of the episode
        runtime = timedelta(minutes=self.runtime)

        # calculate the end time as the difference between the first_aired_date
        # and the runtime timedelta
        return start_date + runtime

    @property
    @get
    def ratings(self):
        """Ratings (between 0 and 10) and distribution for a movie."""
        if self._ratings is None:
            self._ratings = yield self.ext + '/ratings'
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
        return rate(self, rating)

    def add_to_library(self):
        """Add this :class:`TVEpisode` to your Trakt.tv library"""
        return add_to_collection(self)

    add_to_collection = add_to_library

    def add_to_watchlist(self):
        """Add this :class:`TVEpisode` to your watchlist"""
        return add_to_watchlist(self)

    def mark_as_seen(self, watched_at=None):
        """Mark this episode as seen"""
        return add_to_history(self, watched_at)

    def mark_as_unseen(self):
        """Remove this :class:`TVEpisode` from your list of watched episodes"""
        return remove_from_history(self)

    def remove_from_library(self):
        """Remove this :class:`TVEpisode` from your library"""
        return remove_from_collection(self)

    remove_from_collection = remove_from_library

    def remove_from_watchlist(self):
        """Remove this :class:`TVEpisode` from your watchlist"""
        return remove_from_watchlist(self)

    def comment(self, comment_body, spoiler=False, review=False):
        """Add a comment (shout or review) to this :class:`TVEpisode` on trakt.
        """
        return comment(self, comment_body, spoiler, review)

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

    def checkin(self, app_version, app_date, message="", sharing=None,
                venue_id="", venue_name="", delete=False):
        """Checkin this :class:`TVEpisode` via the TraktTV API

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
        """
        if delete:
            delete_checkin()
        return checkin_media(self, app_version, app_date, message, sharing, venue_id,
                      venue_name)

    def to_json_singular(self):
        """Return this :class:`TVEpisode` as a trakt recognizable JSON object
        """
        return {
            'episode': {
                'ids': {
                    'trakt': self.trakt
                }
            }
        }

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
                                                  self.title)
    __repr__ = __str__
