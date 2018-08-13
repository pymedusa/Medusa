# -*- coding: utf-8 -*-
"""Interfaces to all of the Calendar objects offered by the Trakt.tv API"""
from pprint import pformat
from trakt.core import get
from trakt.movies import Movie
from trakt.tv import TVEpisode
from trakt.utils import now, airs_date

__author__ = 'Jon Nappi'
__all__ = ['Calendar', 'PremiereCalendar', 'MyPremiereCalendar',
           'ShowCalendar', 'MyShowCalendar', 'SeasonCalendar',
           'MySeasonCalendar', 'MovieCalendar', 'MyMovieCalendar']


class Calendar(object):
    """Base :class:`Calendar` type serves as a foundation for other Calendar
    types
    """
    url = None

    def __init__(self, date=None, days=7):
        """Create a new :class:`Calendar` object

        :param date: Start date of this :class:`Calendar` in the format Ymd
            (i.e. 2011-04-21). Defaults to today
        :param days: Number of days for this :class:`Calendar`. Defaults to 7
            days
        """
        super(Calendar, self).__init__()
        self.date, self.days, self._calendar = date or now(), days, []
        self._get()

    def __getitem__(self, key):
        """Pass index requests through to the internal _calendar object"""
        return self._calendar.__getitem__(key)

    def __iter__(self):
        """Custom iterator for iterating over the episodes in this Calendar"""
        return iter(self._calendar)

    def __len__(self):
        """Returns the length of the episodes list in this calendar"""
        return len(self._calendar)

    def __str__(self):
        """str representation of this Calendar"""
        return pformat(self._calendar)
    __repr__ = __str__

    @property
    def ext(self):
        """construct the fully formatted url for this Calendar"""
        return '/'.join([self.url, str(self.date), str(self.days)])

    @get
    def _get(self):
        data = yield self.ext
        self._build(data)

    def _build(self, data):
        """Build the calendar"""
        self._calendar = []
        for episode in data:
            show = episode.get('show', {}).get('title')
            season = episode.get('episode', {}).get('season')
            ep = episode.get('episode', {}).get('number')
            e_data = {'airs_at': airs_date(episode.get('first_aired')),
                      'ids': episode.get('episode').get('ids'),
                      'title': episode.get('episode', {}).get('title')}
            self._calendar.append(TVEpisode(show, season, ep, **e_data))
        self._calendar = sorted(self._calendar, key=lambda x: x.airs_at)


class PremiereCalendar(Calendar):
    """All shows premiering during the time period specified."""
    url = 'calendars/all/shows/new'


class MyPremiereCalendar(Calendar):
    """Personalized calendar of all shows premiering during the time period
    specified.
    """
    url = 'calendars/my/shows/new'


class ShowCalendar(Calendar):
    """TraktTV ShowCalendar"""
    url = 'calendars/all/shows'


class MyShowCalendar(Calendar):
    """Personalized TraktTV ShowCalendar"""
    url = 'calendars/my/shows'


class SeasonCalendar(Calendar):
    """TraktTV TV Show Season Premiere"""
    url = 'calendars/all/shows/premieres'


class MySeasonCalendar(Calendar):
    """Personalized TraktTV TV Show Season Premiere"""
    url = 'calendars/my/shows/premieres'


class MovieCalendar(Calendar):
    """TraktTV Movie Calendar. Returns all movies with a release date during
    the time period specified.
    """
    url = 'calendars/all/movies'

    def _build(self, data):
        """Build the calendar of Movies"""
        self._calendar = []
        for movie in data:
            m_data = movie.get('movie', {})
            released = movie.get('released', None)
            self._calendar.append(Movie(released=released, **m_data))

        self._calendar = sorted(self._calendar, key=lambda x: x.released)


class MyMovieCalendar(MovieCalendar):
    """Personalized TraktTV Movie Calendar."""
    url = 'calendars/my/movies'
