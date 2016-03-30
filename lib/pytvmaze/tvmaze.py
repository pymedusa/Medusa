#!/usr/bin/python
# coding=utf-8
from __future__ import unicode_literals

from collections import namedtuple
from datetime import datetime
import logging
import re

import requests
from requests.compat import quote, is_py3

from pytvmaze import endpoints
from pytvmaze.exceptions import *

log = logging.getLogger()
log.addHandler(logging.NullHandler())


__version__ = 1, 4, 8
re_tag = re.compile(r'<.*?>')


def _remove_tags(text):
    return re_tag.sub('', text)


def _valid_encoding(text):
    if text:
        return text if is_py3 else unicode(text).encode('utf-8')


class API(object):
    def __init__(self, session=None):
        self.session = session or requests.Session()
        self.session.headers.setdefault({'user-agent': 'pytvmaze/{}.{}.{}'.format(*__version__)})

    def _query_endpoint(self, url):
        """
        Query TV Maze endpoints
        """
        data = self.session.get(url)
        if not data.ok:
            if data.status_code in [404, 422]:
                return None
        else:
            if data.status_code == 400:
                raise BadRequest(data.request.url)
            else:
                data.raise_for_status()
        results = data.json()
        return results or None

    # Get Show object
    def get_show(self, maze_id=None, tvdb_id=None, tvrage_id=None, imdb_id=None, show_name=None,
                 show_year=None, show_network=None, show_language=None,
                 show_country=None, show_web_channel=None, embed=None):
        """
        Get Show object directly via id or indirectly via name + optional qualifiers

        If only a show_name is given, the show with the highest score using the
        tvmaze algorithm will be returned.
        If you provide extra qualifiers such as network or language they will be
        used for a more specific match, if one exists.
        :param maze_id: Show maze_id
        :param tvdb_id: Show tvdb_id
        :param tvrage_id: Show tvrage_id
        :param imdb_id: Show imdb_id
        :param show_name: Show name to be searched
        :param show_year: Show premiere year
        :param show_network: Show TV Network (like ABC, NBC, etc.)
        :param show_web_channel: Show Web Channel (like Netflix, Amazon, etc.)
        :param show_language: Show language
        :param show_country: Show country
        :param embed: embed parameter to include additional data. Currently 'episodes' and 'cast' are supported
        :return:
        """
        errors = []
        if not (maze_id or tvdb_id or tvrage_id or imdb_id or show_name):
            raise MissingParameters(
                    'Either maze_id, tvdb_id, tvrage_id, imdb_id or show_name are required to get show, none provided,')
        if maze_id:
            try:
                return self.show_main_info(maze_id, embed=embed)
            except IDNotFound as e:
                errors.append(e.value)
        if tvdb_id:
            try:
                return self.show_main_info(self.lookup_tvdb(tvdb_id).id, embed=embed)
            except IDNotFound as e:
                errors.append(e.value)
        if tvrage_id:
            try:
                return self.show_main_info(self.lookup_tvrage(tvrage_id).id, embed=embed)
            except IDNotFound as e:
                errors.append(e.value)
        if imdb_id:
            try:
                return self.show_main_info(self.lookup_imdb(imdb_id).id, embed=embed)
            except IDNotFound as e:
                errors.append(e.value)
        if show_name:
            try:
                show = self._get_show_by_search(show_name, show_year, show_network, show_language, show_country,
                                                show_web_channel, embed=embed)
                return show
            except ShowNotFound as e:
                errors.append(e.value)
        raise ShowNotFound(' ,'.join(errors))

    def _get_show_with_qualifiers(self, show_name, qualifiers):
        shows = self.get_show_list(show_name)
        best_match = -1  # Initialize match value score
        show_match = None

        for show in shows:
            if show.premiered:
                premiered = show.premiered[:-6].lower()
            else:
                premiered = None
            if show.network:
                network = show.network['name'].lower()
            else:
                network = None
            if show.web_channel:
                web_channel = show.web_channel['name'].lower()
            else:
                web_channel = None
            if show.network:
                country = show.network['country']['code'].lower()
            else:
                if show.web_channel:
                    country = show.web_channel['country']['code'].lower()
                else:
                    country = None
            if show.language:
                language = show.language.lower()
            else:
                language = None

            attributes = [premiered, country, network, language, web_channel]
            show_score = len(set(qualifiers) & set(attributes))
            if show_score > best_match:
                best_match = show_score
                show_match = show
        return show_match

    # Search with user-defined qualifiers, used by get_show() method
    def _get_show_by_search(self, show_name, show_year, show_network, show_language, show_country, show_web_channel, embed):
        if show_year:
            show_year = str(show_year)
        qualifiers = list(filter(None, [show_year, show_network, show_language, show_country, show_web_channel]))
        if qualifiers:
            qualifiers = [q.lower() for q in qualifiers if q]
            show = self._get_show_with_qualifiers(show_name, qualifiers)
        else:
            return self.show_single_search(show=show_name, embed=embed)
        if embed:
            return self.show_main_info(maze_id=show.id, embed=embed)
        else:
            return show

    @staticmethod
    def _url_quote(show):
        return quote(show.encode('UTF-8'))

    # Return list of Show objects
    def get_show_list(self, show_name):
        """
        Return list of Show objects from the TVMaze "Show Search" endpoint

        List will be ordered by tvmaze score and should mimic the results you see
        by doing a show search on the website.
        :param show_name: Name of show
        :return: List of Show(s)
        """
        shows = self.show_search(show_name)
        return shows

    # Get list of Person objects
    def get_people(self, name):
        """
        Return list of Person objects from the TVMaze "People Search" endpoint
        :param name: Name of person
        :return: List of Person(s)
        """
        people = self.people_search(name)
        if people:
            return people

    # TV Maze Endpoints
    def show_search(self, show):
        _show = self._url_quote(show)
        url = endpoints.show_search.format(_show)
        q = self._query_endpoint(url)
        if q:
            shows = []
            for result in q:
                show = Show(self, result['show'])
                show.score = result['score']
                shows.append(show)
            return shows
        else:
            raise ShowNotFound('Show {0} not found'.format(show))

    def show_single_search(self, show, embed=None):
        _show = self._url_quote(show)
        if embed:
            url = endpoints.show_single_search.format(_show) + '&embed=' + embed
        else:
            url = endpoints.show_single_search.format(_show)
        q = self._query_endpoint(url)
        if q:
            return Show(self, q)
        else:
            raise ShowNotFound('show name "{0}" not found'.format(show))

    def lookup_tvrage(self, tvrage_id):
        url = endpoints.lookup_tvrage.format(tvrage_id)
        q = self._query_endpoint(url)
        if q:
            return Show(self, q)
        else:
            raise IDNotFound('TVRage id {0} not found'.format(tvrage_id))

    def lookup_tvdb(self, tvdb_id):
        url = endpoints.lookup_tvdb.format(tvdb_id)
        q = self._query_endpoint(url)
        if q:
            return Show(self, q)
        else:
            raise IDNotFound('TVDB ID {0} not found'.format(tvdb_id))

    def lookup_imdb(self, imdb_id):
        url = endpoints.lookup_imdb.format(imdb_id)
        q = self._query_endpoint(url)
        if q:
            return Show(self, q)
        else:
            raise IDNotFound('IMDB ID {0} not found'.format(imdb_id))

    def get_schedule(self, country='US', date=str(datetime.today().date())):
        url = endpoints.get_schedule.format(country, date)
        q = self._query_endpoint(url)
        if q:
            return [Episode(self, episode) for episode in q]
        else:
            raise ScheduleNotFound('Schedule for country {0} at date {1} not found'.format(country, date))

    # ALL known future episodes, several MB large, cached for 24 hours
    def get_full_schedule(self):
        url = endpoints.get_full_schedule
        q = self._query_endpoint(url)
        if q:
            return [Episode(self, episode) for episode in q]
        else:
            raise GeneralError('Something went wrong, www.tvmaze.com may be down')

    def show_main_info(self, maze_id, embed=None):
        if embed:
            url = endpoints.show_main_info.format(maze_id) + '?embed=' + embed
        else:
            url = endpoints.show_main_info.format(maze_id)
        q = self._query_endpoint(url)
        if q:
            return Show(self, q)
        else:
            raise IDNotFound('Maze id {0} not found'.format(maze_id))

    def episode_list(self, maze_id, specials=None):
        if specials:
            url = endpoints.episode_list.format(maze_id) + '&specials=1'
        else:
            url = endpoints.episode_list.format(maze_id)
        q = self._query_endpoint(url)
        if q:
            return [Episode(self, episode) for episode in q]
        else:
            raise IDNotFound('Maze id {0} not found'.format(maze_id))

    def episode_by_number(self, maze_id, season_number, episode_number):
        url = endpoints.episode_by_number.format(maze_id,
                                                 season_number,
                                                 episode_number)
        q = self._query_endpoint(url)
        if q:
            return Episode(self, q)
        else:
            raise EpisodeNotFound(
                    'Couldn\'t find season {0} episode {1} for TVMaze ID {2}'.format(season_number, episode_number,
                                                                                     maze_id))

    def episodes_by_date(self, maze_id, airdate):
        try:
            datetime.strptime(airdate, '%Y-%m-%d')
        except ValueError:
            raise IllegalAirDate('Air date must be string formatted as \'YYYY-MM-DD\'')
        url = endpoints.episodes_by_date.format(maze_id, airdate)
        q = self._query_endpoint(url)
        if q:
            return [Episode(self, episode) for episode in q]
        else:
            raise NoEpisodesForAirdate(
                    'Couldn\'t find an episode airing {0} for TVMaze ID {1}'.format(airdate, maze_id))

    def show_cast(self, maze_id):
        url = endpoints.show_cast.format(maze_id)
        q = self._query_endpoint(url)
        if q:
            return Cast(self, q)
        else:
            raise CastNotFound('Couldn\'nt find show cast for TVMaze ID {0}'.format(maze_id))

    def show_index(self, page=1):
        url = endpoints.show_index.format(page)
        q = self._query_endpoint(url)
        if q:
            return [Show(self, show) for show in q]
        else:
            raise ShowIndexError('Error getting show index, www.tvmaze.com may be down')

    def people_search(self, person):
        person = self._url_quote(person)
        url = endpoints.people_search.format(person)
        q = self._query_endpoint(url)
        if q:
            return [Person(self, person) for person in q]
        else:
            raise PersonNotFound('Couldn\'t find person: {0}'.format(person))

    def person_main_info(self, person_id, embed=None):
        if embed:
            url = endpoints.person_main_info.format(person_id) + '?embed=' + embed
        else:
            url = endpoints.person_main_info.format(person_id)
        q = self._query_endpoint(url)
        if q:
            return Person(self, q)
        else:
            raise PersonNotFound('Couldn\'t find person: {0}'.format(person_id))

    def person_cast_credits(self, person_id, embed=None):
        if embed:
            url = endpoints.person_cast_credits.format(person_id) + '?embed=' + embed
        else:
            url = endpoints.person_cast_credits.format(person_id)
        q = self._query_endpoint(url)
        if q:
            return [CastCredit(self, credit) for credit in q]
        else:
            raise CreditsNotFound('Couldn\'t find cast credits for person ID: {0}'.format(person_id))

    def person_crew_credits(self, person_id, embed=None):
        if embed:
            url = endpoints.person_crew_credits.format(person_id) + '?embed=' + embed
        else:
            url = endpoints.person_crew_credits.format(person_id)
        q = self._query_endpoint(url)
        if q:
            return [CrewCredit(self, credit) for credit in q]
        else:
            raise CreditsNotFound('Couldn\'t find crew credits for person ID: {0}'.format(person_id))

    def show_updates(self, ):
        url = endpoints.show_updates
        q = self._query_endpoint(url)
        if q:
            return Updates(q)
        else:
            raise ShowIndexError('Error getting show updates, www.tvmaze.com may be down')

    def show_akas(self, maze_id):
        url = endpoints.show_akas.format(maze_id)
        q = self._query_endpoint(url)
        if q:
            return [AKA(aka) for aka in q]
        else:
            raise AKASNotFound('Couldn\'t find AKA\'s for TVMaze ID: {0}'.format(maze_id))

    def show_seasons(self, maze_id):
        url = endpoints.show_seasons.format(maze_id)
        q = self._query_endpoint(url)
        if q:
            season_dict = dict()
            for season in q:
                season_dict[season['number']] = Season(self, season)
            return season_dict
        else:
            raise SeasonNotFound('Couldn\'t find Season\'s for TVMaze ID: {0}'.format(maze_id))

    def season_by_id(self, season_id):
        url = endpoints.season_by_id.format(season_id)
        q = self._query_endpoint(url)
        if q:
            return Season(self, q)
        else:
            raise SeasonNotFound('Couldn\'t find Season with ID: {0}'.format(season_id))


class Show(object):
    def __init__(self, tvmaze_api, data):
        self.tvmaze_api = tvmaze_api
        self.status = data.get('status')
        self.rating = data.get('rating')
        self.genres = data.get('genres')
        self.weight = data.get('weight')
        self.updated = data.get('updated')
        self.name = data.get('name')
        self.language = data.get('language')
        self.schedule = data.get('schedule')
        self.url = data.get('url')
        self.image = data.get('image')
        self.externals = data.get('externals')
        self.premiered = data.get('premiered')
        self.summary = _remove_tags(data.get('summary'))
        self.links = data.get('_links')
        self.web_channel = data.get('webChannel')
        self.runtime = data.get('runtime')
        self.type = data.get('type')
        self.id = data.get('id')
        self.maze_id = self.id
        self.network = data.get('network')
        self.episodes = list()
        self.seasons = dict()
        self.cast = None
        self.populate(data)

    def __repr__(self):
        if self.premiered:
            year = str(self.premiered[:4])
        else:
            year = None
        if self.web_channel:
            platform = ',show_web_channel='
            network = self.web_channel.get('name')
        elif self.network:
            platform = ',network='
            network = self.network.get('name')
        else:
            platform = ''
            network = ''

        return _valid_encoding('<Show(maze_id={id},name={name},year={year}{platform}{network})>'.format(
                id=self.maze_id,
                name=self.name,
                year=year,
                platform=platform,
                network=network)
        )

    def __str__(self):
        return _valid_encoding(self.name)

    def __unicode__(self):
        return self.name

    def __iter__(self):
        return iter(self.seasons.values())

    # Python 3 bool evaluation
    def __bool__(self):
        return bool(self.id)

    # Python 2 bool evaluation
    def __nonzero__(self):
        return bool(self.id)

    def __len__(self):
        return len(self.seasons)

    def __getitem__(self, item):
        try:
            return self.seasons[item]
        except KeyError:
            raise SeasonNotFound('Season {0} does not exist for show {1}.'.format(item, self.name))

    def populate(self, data):
        embedded = data.get('_embedded')
        if embedded:
            if embedded.get('episodes'):
                seasons = self.tvmaze_api.show_seasons(self.maze_id)
                for episode in embedded.get('episodes'):
                    self.episodes.append(Episode(self.tvmaze_api, episode))
                for episode in self.episodes:
                    season_num = int(episode.season_number)
                    if season_num not in self.seasons:
                        self.seasons[season_num] = seasons[season_num]
                        self.seasons[season_num].show = self
                    self.seasons[season_num].episodes[episode.episode_number] = episode
            if embedded.get('cast'):
                self.cast = Cast(self.tvmaze_api, embedded.get('cast'))


class Season(object):
    def __init__(self, tvmaze_api, data):
        self.tvmaze_api = tvmaze_api
        self.show = None
        self.episodes = dict()
        self.id = data.get('id')
        self.url = data.get('url')
        self.season_number = data.get('number')
        self.name = data.get('name')
        self.episode_order = data.get('episodeOrder')
        self.premier_date = data.get('premierDate')
        self.end_date = data.get('endDate')
        self.network = data.get('network')
        self.web_channel = data.get('webChannel')
        self.image = data.get('image')
        self.summary = data.get('summary')
        self.links = data.get('_links')

    def __repr__(self):
        return _valid_encoding('<Season(id={id},season_number={number})>'.format(
                id=self.id,
                number=str(self.season_number).zfill(2)
        ))

    def __iter__(self):
        return iter(self.episodes.values())

    def __len__(self):
        return len(self.episodes)

    def __getitem__(self, item):
        try:
            return self.episodes[item]
        except KeyError:
            raise EpisodeNotFound(
                    'Episode {0} does not exist for season {1} of show {2}.'.format(item, self.season_number,
                                                                                    self.show))

    # Python 3 bool evaluation
    def __bool__(self):
        return bool(self.id)

    # Python 2 bool evaluation
    def __nonzero__(self):
        return bool(self.id)


class Episode(object):
    def __init__(self, tvmaze_api, data):
        self.tvmaze_api = tvmaze_api
        self.title = data.get('name')
        self.airdate = data.get('airdate')
        self.url = data.get('url')
        self.season_number = data.get('season')
        self.episode_number = data.get('number')
        self.image = data.get('image')
        self.airstamp = data.get('airstamp')
        self.airtime = data.get('airtime')
        self.runtime = data.get('runtime')
        self.summary = _remove_tags(data.get('summary'))
        self.maze_id = data.get('id')
        # Reference to show for when using get_schedule()
        if data.get('show'):
            self.show = Show(self.tvmaze_api, data.get('show'))
        # Reference to show for when using get_full_schedule()
        if data.get('_embedded'):
            if data['_embedded'].get('show'):
                self.show = Show(tvmaze_api, data['_embedded']['show'])

    def __repr__(self):
        return '<Episode(season={season},episode_number={number})>'.format(
                season=str(self.season_number).zfill(2),
                number=str(self.episode_number).zfill(2)
        )

    def __str__(self):
        season = 'S' + str(self.season_number).zfill(2)
        episode = 'E' + str(self.episode_number).zfill(2)
        return _valid_encoding(season + episode + ' ' + self.title)


class Person(object):
    def __init__(self, tvmaze_api, data):
        self.tvmaze_api = tvmaze_api
        if data.get('person'):
            data = data['person']
        self.links = data.get('_links')
        self.id = data.get('id')
        self.image = data.get('image')
        self.name = data.get('name')
        self.score = data.get('score')
        self.url = data.get('url')
        self.character = None
        self.castcredits = None
        self.crewcredits = None
        self.populate(data)

    def populate(self, data):
        if data.get('_embedded'):
            if data['_embedded'].get('castcredits'):
                self.castcredits = [CastCredit(self.tvmaze_api, credit)
                                    for credit in data['_embedded']['castcredits']]
            elif data['_embedded'].get('crewcredits'):
                self.crewcredits = [CrewCredit(self.tvmaze_api, credit)
                                    for credit in data['_embedded']['crewcredits']]

    def __repr__(self):
        return _valid_encoding('<Person(name={name},maze_id={id})>'.format(
                name=self.name,
                id=self.id
        ))

    def __str__(self):
        return _valid_encoding(self.name)


class Character(object):
    def __init__(self, data):
        self.id = data.get('id')
        self.url = data.get('url')
        self.name = data.get('name')
        self.image = data.get('image')
        self.links = data.get('_links')
        self.person = None

    def __repr__(self):
        return _valid_encoding('<Character(name={name},maze_id={id})>'.format(
                name=self.name,
                id=self.id
        ))

    def __str__(self):
        return _valid_encoding(self.name)


class Cast(object):
    def __init__(self, tvmaze_api, data):
        self.tvmaze_api = tvmaze_api
        self.people = []
        self.characters = []
        self.populate(data)

    def populate(self, data):
        for cast_member in data:
            self.people.append(Person(self.tvmaze_api, cast_member['person']))
            self.characters.append(Character(cast_member['character']))
            self.people[-1].character = self.characters[-1]  # add reference to character
            self.characters[-1].person = self.people[-1]  # add reference to cast member


class CastCredit(object):
    def __init__(self, tvmaze_api, data):
        self.tvmaze_api = tvmaze_api
        self.links = data.get('_links')
        self.character = None
        self.show = None
        self.populate(data)

    def populate(self, data):
        if data.get('_embedded'):
            if data['_embedded'].get('character'):
                self.character = Character(data['_embedded']['character'])
            elif data['_embedded'].get('show'):
                self.show = Show(self.tvmaze_api, data['_embedded']['show'])


class CrewCredit(object):
    def __init__(self, tvmaze_api, data):
        self.tvmaze_api = tvmaze_api
        self.links = data.get('_links')
        self.type = data.get('type')
        self.show = None
        self.populate(data)

    def populate(self, data):
        if data.get('_embedded'):
            if data['_embedded'].get('show'):
                self.show = Show(self.tvmaze_api, data['_embedded']['show'])


class Updates(object):
    def __init__(self, data):
        self.updates = dict()
        self.populate(data)

    def populate(self, data):
        for maze_id, time in data.items():
            self.updates[int(maze_id)] = Update(maze_id, time)

    def __getitem__(self, item):
        try:
            return self.updates[item]
        except KeyError:
            raise UpdateNotFound('No update found for Maze id {}.'.format(item))


class Update(object):
    def __init__(self, maze_id, time):
        self.maze_id = int(maze_id)
        self.seconds_since_epoch = time
        self.timestamp = datetime.fromtimestamp(time)

    def __repr__(self):
        return '<Update(maze_id={maze_id},time={time})>'.format(
                maze_id=self.maze_id,
                time=self.seconds_since_epoch
        )


class AKA(object):
    def __init__(self, data):
        self.country = data.get('country')
        self.name = data.get('name')


def get_show(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).get_show(*args, **kwargs)


def get_show_list(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).get_show_list(*args, **kwargs)


def get_people(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).get_people(*args, **kwargs)


def show_search(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).show_search(*args, **kwargs)


def show_single_search(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).show_single_search(*args, **kwargs)


def lookup_tvrage(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).lookup_tvrage(*args, **kwargs)


def lookup_tvdb(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).lookup_tvdb(*args, **kwargs)


def lookup_imdb(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).lookup_imdb(*args, **kwargs)


def get_schedule(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).get_schedule(*args, **kwargs)


def get_full_schedule(**kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).get_full_schedule()


def show_main_info(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).show_main_info(*args, **kwargs)


def episode_list(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).episode_list(*args, **kwargs)


def episode_by_number(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).episode_by_number(*args, **kwargs)


def episodes_by_date(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).episodes_by_date(*args, **kwargs)


def show_cast(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).show_cast(*args, **kwargs)


def show_index(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).show_index(*args, **kwargs)


def people_search(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).people_search(*args, **kwargs)


def person_main_info(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).person_main_info(*args, **kwargs)


def person_cast_credits(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).person_cast_credits(*args, **kwargs)


def person_crew_credits(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).person_crew_credits(*args, **kwargs)


def show_updates(**kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).show_updates()


def show_akas(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).show_akas(*args, **kwargs)


def show_seasons(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).show_seasons(*args, **kwargs)


def season_by_id(*args, **kwargs):
    session = kwargs.pop('session', None)
    return API(session=session).season_by_id(*args, **kwargs)
