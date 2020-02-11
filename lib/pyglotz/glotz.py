#!/usr/bin/python
from __future__ import unicode_literals

import re
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from requests import compat
from pyglotz import endpoints
from pyglotz.exceptions import *


class Show(object):
    def __init__(self, data):
        self.id = data.get('Series').get('id')
        # actors = str.split(data.get('Series').get('Actors'),'|')[1:-1]
        self.actors = data.get('Series').get('Actors')
        self.airs_day_of_week = data.get('Series').get('Airs_DayOfWeek')
        self.airs_time = data.get('Series').get('Airs_Time')
        self.content_rating = data.get('Series').get('ContentRating')
        self.first_aired = data.get('Series').get('FirstAired')
        self.genre = data.get('Series').get('Genre')
        self.imdb_id = data.get('Series').get('IMDB_ID')
        self.language = data.get('Series').get('Language')
        self.network = data.get('Series').get('Network')
        self.network_id = data.get('Series').get('NetworkID')
        self.overview = data.get('Series').get('Overview')
        self.rating = data.get('Series').get('Rating')
        self.rating_count = data.get('Series').get('RatingCount')
        self.runtime = data.get('Series').get('Runtime')
        self.series_id = data.get('Series').get('SeriesID')
        self.series_name = data.get('Series').get('SeriesName')
        self.status = data.get('Series').get('Status')
        self.added = data.get('Series').get('added')
        self.added_by = data.get('Series').get('addedBy')
        self.banner = data.get('Series').get('banner')
        self.fan_art = data.get('Series').get('fanart')
        self.last_updated = data.get('Series').get('lastupdated')
        self.poster = data.get('Series').get('poster')
        self.zap2it_id = data.get('Series').get('zap2it_id')
        self.slug = data.get('Series').get('slug')
        self.tvrage_id = data.get('Series').get('tvrage_id')
        self.year = data.get('Series').get('year')
        self.episodes = list()
        if data.get('Episode'):
            for ep in data.get('Episode'):
                self.episodes.append(Episode(ep))
        self.aliases = list()

    def __repr__(self):
        if self.year:
            year = str(self.year)
        elif self.first_aired:
            year = str(self.first_aired[:4])
        else:
            year = None

        return _valid_encoding('<Show(id={id},name={name},year={year})>'.format(
            id=self.id,
            name=self.series_name,
            year=year)
        )

    def __str__(self):
        return _valid_encoding(self.series_name)

    def __unicode__(self):
        return self.series_name

    # Python 3 bool evaluation
    def __bool__(self):
        return bool(self.id)

    def __getitem__(self, item):
        try:
            return self.episodes[item]
        except KeyError:
            raise EpisodeNotFound('Episode {0} does not exist for show {1}.'.format(item, self.series_name))


class Episode(object):
    def __init__(self, data):
        self.id = data.get('id')
        self.imdb_id = data.get('IMDB_ID')
        self.combined_episodenumber = data.get('Combined_episodenumber')
        self.combined_season = data.get('Combined_season')
        self.cvd_chapter = data.get('DVD_chapter')
        self.dvd_discid = data.get('DVD_discid')
        self.dvd_episodenumber = data.get('DVD_episodenumber')
        self.dvd_season = data.get('DVD_season')
        self.director = data.get('Director')
        self.ep_img_flag = data.get('EpImgFlag')
        self.episode_name = data.get('EpisodeName')
        self.episode_number = data.get('EpisodeNumber')
        self.first_aired = data.get('FirstAired')
        self.guest_stars = data.get('GuestStars')
        self.language = data.get('Language')
        self.overview = data.get('Overview')
        self.production_code = data.get('ProductionCode')
        self.rating = data.get('Rating')
        self.rating_count = data.get('RatingCount')
        self.season_number = data.get('SeasonNumber')
        self.writer = data.get('Writer')
        self.absolute_number = data.get('absolute_number')
        if self.absolute_number == '':
            self.absolute_number = None
        self.filename = data.get('filename')
        self.last_updated = data.get('lastupdated')
        self.season_id = data.get('seasonid')
        self.series_id = data.get('seriesid')
        self.thumb_added = data.get('thumb_added')
        self.thumb_height = data.get('thumb_height')
        self.thumb_width = data.get('thumb_width')

    def __repr__(self):
        return '<Episode(season={season},episode_number={number})>'.format(
            season=str(self.season_number).zfill(2),
            number=str(self.episode_number).zfill(2)
        )

    def __str__(self):
        season = 'S' + str(self.season_number).zfill(2)
        episode = 'E' + str(self.episode_number).zfill(2)
        return _valid_encoding(season + episode + ' ' + self.episode_name)

    def is_special(self):
        if self.season_number == '0':
            return True
        return False


def _valid_encoding(text):
    if not text:
        return
    return text


def _url_quote(show):
    return requests.compat.quote(show.encode('UTF-8'))


def _remove_tags(text):
    if not text:
        return None
    return re.sub(r'<.*?>', '', text)


class Actor(object):
    def __init__(self, data):
        self.id = data.get('id')
        self.name = data.get('Name')
        self.image = data.get('Image')
        self.role = data.get('Role')
        self.sort_order = data.get('SortOrder')

    def __repr__(self):
        return _valid_encoding('<Character(name={name},id={id})>'.format(
            name=self.name,
            id=self.id
        ))

    def __str__(self):
        return _valid_encoding(self.name)

    def __unicode__(self):
        return self.name


class Banner(object):
    def __init__(self, data):
        self.id = data.get('id')
        self.banner_path = data.get('BannerPath')
        self.banner_type = data.get('BannerType')
        self.banner_type2 = data.get('BannerType2')
        self.colors = data.get('Colors')
        self.series_name = data.get('SeriesName')
        self.thumbnail_path = data.get('ThumbnailPath')
        self.vignette_path = data.get('VignettePath')
        self.language = data.get('Language')
        self.season = data.get('Season')
        self.rating = data.get('Rating')
        self.rating_count = data.get('RatingCount')

    def __repr__(self):
        return _valid_encoding('<Character(banner_type={banner_type},id={id})>'.format(
            banner_type=self.banner_type,
            id=self.id
        ))

    def __str__(self):
        return _valid_encoding(self.id)

    def __unicode__(self):
        return self.id


class Glotz(object):
    """
    This is the main class of the module enabling interaction with the Glotz API

    Attributes:
        api_key (str): Glotz api key.  Find your key at https://www.glotz.info/profile

    """

    def __init__(self, api_key=None, session=None):
        self.api_key = api_key
        self.session = session or requests.Session()
        self.session.headers.setdefault('user-agent', 'glotz_api/{}.{}.{}'.format(1, 0, 0))

    # Query Glotz endpoints
    def _endpoint_get(self, url):
        retries = Retry(total=5,
                        backoff_factor=0.1,
                        status_forcelist=[429])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        try:
            r = self.session.get(url)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(repr(e))

        if r.status_code in [404, 422]:
            return None

        if r.status_code == 400:
            raise BadRequest('Bad Request for url {}'.format(url))

        results = r.json()
        return results

    # Get Show object
    def get_show(self, tvdb_id=None, language=None):
        """
        Get Show object directly via id

        Args:
            tvdb_id:    Show tvdb_id
            language:   Show information language
        """
        errors = []
        if not tvdb_id:
            raise MissingParameters(
                'tvdb_id required to get show, none provided,')
        if tvdb_id:
            if not language:
                language = 'de'
            try:
                return self.lookup_tvdb(tvdb_id, language)
            except IDNotFound as e:
                errors.append(e.value)

    # Return list of Show objects
    def get_show_list(self, show_name, language=None):
        """
        Return list of Show objects from the Glotz "Show Search" endpoint

        :param show_name: Name of show
        :param language: Language of the show
        :return: List of Show(s)
        """
        if not language:
            language = 'de'
        shows = self.show_search(show_name, language)
        return shows

    def show_search(self, show, language=None):
        _show = _url_quote(show)
        if not language:
            language = 'de'
        url = endpoints.show_search.format(_show, language)
        q = self._endpoint_get(url)
        if q:
            shows = []
            for result in q.get('Data').get('Series'):
                show = Show({'Series': result})
                shows.append(show)
            return shows
        else:
            raise ShowNotFound('Show {0} not found'.format(show))

    def episode_by_id(self, episode_id, language=None):
        if not language:
            language = 'de'
        url = endpoints.episode_by_id.format(self.api_key, episode_id, language)
        q = self._endpoint_get(url)
        if q:
            return Episode(q)
        else:
            raise EpisodeNotFound('Couldn\'t find Episode with ID {0}'.format(episode_id))

    def lookup_tvdb(self, tvdb_id, language=None):
        if not language:
            language = 'de'
        url = endpoints.lookup_tvdb.format(self.api_key, tvdb_id, language)
        q = self._endpoint_get(url)
        if q:
            element = q.get('Data')
            if element:
                if element.get('Series').get('id') != '0':
                    return Show(element)
            else:
                raise IDNotFound('TVDB ID {0} not found'.format(tvdb_id))
        else:
            raise IDNotFound('TVDB ID {0} not found'.format(tvdb_id))

    # Get all aliases of a show
    def get_show_aliases(self, tvdb_id):
        url = endpoints.show_aliases.format(tvdb_id)
        q = self._endpoint_get(url)
        if q:
            if str(tvdb_id) in q:
                embedded = q[str(tvdb_id)]
                if embedded:
                    aliases = list()
                    for alias in embedded:
                        aliases.append(alias)
                    return aliases
        else:
            return '[]'

    # Get all actors of a show
    def get_actors_list(self, tvdb_id):
        url = endpoints.show_actors.format(self.api_key, tvdb_id)
        q = self._endpoint_get(url)
        if q and q.get('Actors') != '':
            actors = []
            for result in q.get('Actors').get('Actor'):
                actor = Actor(result)
                actors.append(actor)
            return actors
        else:
            raise ActorNotFound('Actors for show {0} not found'.format(tvdb_id))

    def get_banners(self, tvdb_id):
        url = endpoints.show_banners.format(self.api_key, tvdb_id)
        q = self._endpoint_get(url)
        if q and q.get('Banners') != '':
            banners = []
            for result in q.get('Banners').get('Banner'):
                banner = Banner(result)
                banners.append(banner)
            return banners
        else:
            raise BannersNotFound('Banners for show {0} not found'.format(tvdb_id))

    def get_show_updates(self, timestamp):
        url = endpoints.show_updates.format(self.api_key, timestamp)
        q = self._endpoint_get(url)
        if q and q.get('shows'):
            return q.get('shows')
        else:
            raise ShowIndexError('Error getting show updates, www.glotz.info may be down')
