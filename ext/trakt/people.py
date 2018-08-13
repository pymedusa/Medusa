# -*- coding: utf-8 -*-
"""Interfaces to all of the People objects offered by the Trakt.tv API"""
from trakt.core import get
from trakt.sync import search
from trakt.utils import slugify, extract_ids

__author__ = 'Jon Nappi'
__all__ = ['Person', 'ActingCredit', 'CrewCredit', 'Credits', 'MovieCredits',
           'TVCredits']


class Person(object):
    """A Class representing a trakt.tv Person such as an Actor or Director"""
    def __init__(self, name, slug=None, **kwargs):
        super(Person, self).__init__()
        self.name = name
        self.biography = self.birthplace = self.tmdb_id = self.birthday = None
        self.job = self.character = self._images = self._movie_credits = None
        self._tv_credits = None
        self.slug = slug or slugify(self.name)

        if len(kwargs) > 0:
            self._build(kwargs)
        else:
            self._get()

    @classmethod
    def search(cls, name, year=None):
        """Perform a search for an episode with a title matching *title*

        :param name: The name of the person to search for
        :param year: Optional year to limit results to
        """
        return search(name, search_type='person', year=year)

    @property
    def ext(self):
        return 'people/{id}'.format(id=self.slug)

    @property
    def ext_full(self):
        return self.ext + '?extended=full'

    @property
    def images_ext(self):
        return self.ext + '?extended=images'

    @property
    def ext_movie_credits(self):
        return self.ext + '/movies'

    @property
    def ext_tv_credits(self):
        return self.ext + '/shows'

    @get
    def _get(self):
        data = yield self.ext_full
        self._build(data)

    def _build(self, data):
        extract_ids(data)
        for key, val in data.items():
            try:
                setattr(self, key, val)
            except AttributeError as ae:
                if not hasattr(self, '_' + key):
                    raise ae

    @property
    @get
    def images(self):
        """All of the artwork associated with this :class:`Person`"""
        if self._images is None:
            data = yield self.images_ext
            self._images = data.get('images', {})
        yield self._images

    @property
    @get
    def movie_credits(self):
        """Return a collection of movie credits that this :class:`Person` was a
        cast or crew member on
        """
        if self._movie_credits is None:
            data = yield self.ext_movie_credits
            self._movie_credits = MovieCredits(**data)
        yield self._movie_credits

    @property
    @get
    def tv_credits(self):
        """Return a collection of TV Show credits that this :class:`Person` was
        a cast or crew memeber on
        """
        if self._tv_credits is None:
            data = yield self.ext_tv_credits
            self._tv_credits = TVCredits(**data)
        yield self._tv_credits

    def __str__(self):
        """String representation of a :class:`Person`"""
        return '<Person>: {0}'.format(self.name)
    __repr__ = __str__


class ActingCredit(object):
    """An individual credit for a :class:`Person` who played a character in a
    Movie or TV Show
    """
    def __init__(self, character, media):
        self.character = character
        self.media = media

    def __str__(self):
        return '<{cls}> {character} - {title}'.format(
            cls=self.__class__.__name__,
            character=self.character,
            title=self.media.title
        )

    __repr__ = __str__


class CrewCredit(object):
    """An individual crew credit for a :class:`Person` who had an off-screen
    job on a Movie or a TV Show
    """
    def __init__(self, job, media):
        self.job = job
        self.media = media

    def __str__(self):
        return '<{cls}> {job} - {title}'.format(
            cls=self.__class__.__name__,
            job=self.job,
            title=self.media.title
        )

    __repr__ = __str__


class Credits(object):
    """A base type representing a :class:`Person`'s credits for Movies or TV
    Shows
    """
    MEDIA_KEY = None

    def __init__(self, **kwargs):
        self.cast = []
        self.crew = {}
        self._build(**kwargs)

    def _extract_media(self, media):
        """Extract the nested media object from an individual Credit resource.

        The *MEDIA_KEY* class attribute must be set by all implementing
        subclasses.
        """
        raise NotImplementedError

    def _build_cast(self, *cast):
        """From the provided JSON array of roles a :class:`Person` has
        portrayed, build a detailed list of Acting Credits.
        """
        for role in cast:
            character = role.get('character')
            media = self._extract_media(role)
            self.cast.append(
                ActingCredit(character=character, media=media)
            )

    def _build_crew(self, **crew):
        """From the provided JSON dict of departments and crew credits, build
        a dict of Crew Credits
        """
        for department, jobs in crew.items():
            self.crew[department] = [
                CrewCredit(job=j.get('job'),
                           media=self._extract_media(j))
                for j in jobs
            ]

    def _build(self, **kwargs):
        self._build_cast(*kwargs.get('cast', []))
        self._build_crew(**kwargs.get('crew', {}))


class MovieCredits(Credits):
    """A collection of cast and crew credits for a Movie"""
    MEDIA_KEY = 'movie'

    def _extract_media(self, media):
        from trakt.movies import Movie
        data = media.get(self.MEDIA_KEY)
        return Movie(**data)


class TVCredits(Credits):
    """A collection of cast and crew credits for a TV Show"""
    MEDIA_KEY = 'show'

    def _extract_media(self, media):
        from trakt.tv import TVShow
        data = media.get(self.MEDIA_KEY)
        return TVShow(**data)
