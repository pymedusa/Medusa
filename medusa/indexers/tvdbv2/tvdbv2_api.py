# coding=utf-8
# Author: p0psicles
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import cgi
import getpass
import logging
import os
import re
import tempfile
import time
import warnings
from collections import OrderedDict
import requests

from six import iteritems as six_iteritems, next as six_next
from requests.compat import urljoin
from tvdbapiv2 import (ApiClient, AuthenticationApi, SearchApi, SeriesApi)

from .tvdbv2_ui import BaseUI, ConsoleUI
from ..indexer_exceptions import (IndexerAttributeNotFound, IndexerEpisodeNotFound, IndexerError,
                                  IndexerException, IndexerSeasonNotFound, IndexerShowIncomplete,
                                  IndexerShowNotFound)


def log():
    return logging.getLogger('tvdbv2_api')


class ShowContainer(dict):
    """Simple dict that holds a series of Show instances
    """

    def __init__(self):
        self._stack = []
        self._lastgc = time.time()

    def __setitem__(self, key, value):
        self._stack.append(key)

        # keep only the 100th latest results
        if time.time() - self._lastgc > 20:
            for o in self._stack[:-100]:
                del self[o]

            self._stack = self._stack[-100:]

            self._lastgc = time.time()

        super(ShowContainer, self).__setitem__(key, value)


class Show(dict):
    """Holds a dict of seasons, and show data.
    """

    def __init__(self):
        dict.__init__(self)
        self.data = {}

    def __repr__(self):
        return '<Show %s (containing %s seasons)>' % (
            self.data.get(u'seriesname', 'instance'),
            len(self)
        )

    def __getattr__(self, key):
        if key in self:
            # Key is an episode, return it
            return self[key]

        if key in self.data:
            # Non-numeric request is for show-data
            return self.data[key]

        raise AttributeError

    def __getitem__(self, key):
        if key in self:
            # Key is an episode, return it
            return dict.__getitem__(self, key)

        if key in self.data:
            # Non-numeric request is for show-data
            return dict.__getitem__(self.data, key)

        # Data wasn't found, raise appropriate error
        if isinstance(key, int) or key.isdigit():
            # Episode number x was not found
            raise IndexerSeasonNotFound('Could not find season %s' % (repr(key)))
        else:
            # If it's not numeric, it must be an attribute name, which
            # doesn't exist, so attribute error.
            raise IndexerAttributeNotFound('Cannot find attribute %s' % (repr(key)))

    def airedOn(self, date):
        ret = self.search(str(date), 'firstaired')
        if len(ret) == 0:
            raise IndexerEpisodeNotFound('Could not find any episodes that aired on %s' % date)
        return ret

    def search(self, term=None, key=None):
        """
        Search all episodes in show. Can search all data, or a specific key (for
        example, episodename)

        Always returns an array (can be empty). First index contains the first
        match, and so on.

        Each array index is an Episode() instance, so doing
        search_results[0]['episodename'] will retrieve the episode name of the
        first match.
        """
        results = []
        for cur_season in self.values():
            searchresult = cur_season.search(term=term, key=key)
            if len(searchresult) != 0:
                results.extend(searchresult)

        return results


class Season(dict):
    def __init__(self, show=None):  # pylint: disable=super-init-not-called
        """The show attribute points to the parent show
        """
        self.show = show

    def __repr__(self):
        return '<Season instance (containing %s episodes)>' % (
            len(self.keys())
        )

    def __getattr__(self, episode_number):
        if episode_number in self:
            return self[episode_number]
        raise AttributeError

    def __getitem__(self, episode_number):
        if episode_number not in self:
            raise IndexerEpisodeNotFound('Could not find episode %s' % (repr(episode_number)))
        else:
            return dict.__getitem__(self, episode_number)

    def search(self, term=None, key=None):
        """Search all episodes in season, returns a list of matching Episode
        instances.

        >>> t = Tvdb()
        >>> t['scrubs'][1].search('first day')
        [<Episode 01x01 - My First Day>]
        >>>

        See Show.search documentation for further information on search
        """
        results = []
        for ep in self.values():
            searchresult = ep.search(term=term, key=key)
            if searchresult is not None:
                results.append(
                    searchresult
                )
        return results


class Episode(dict):
    def __init__(self, season=None):  # pylint: disable=super-init-not-called
        """The season attribute points to the parent season
        """
        self.season = season

    def __repr__(self):
        seasno = int(self.get(u'seasonnumber', 0))
        epno = int(self.get(u'episodenumber', 0))
        epname = self.get(u'episodename')
        if epname is not None:
            return '<Episode %02dx%02d - %s>' % (seasno, epno, epname)
        else:
            return '<Episode %02dx%02d>' % (seasno, epno)

    def __getattr__(self, key):
        if key in self:
            return self[key]
        raise AttributeError

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            raise IndexerAttributeNotFound('Cannot find attribute %s' % (repr(key)))

    def search(self, term=None, key=None):
        """Search episode data for term, if it matches, return the Episode (self).
        The key parameter can be used to limit the search to a specific element,
        for example, episodename.

        This primarily for use use by Show.search and Season.search. See
        Show.search for further information on search

        Simple example:

        >>> e = Episode()
        >>> e['episodename'] = "An Example"
        >>> e.search("examp")
        <Episode 00x00 - An Example>
        >>>

        Limiting by key:

        >>> e.search("examp", key = "episodename")
        <Episode 00x00 - An Example>
        >>>
        """
        if term is None:
            raise TypeError('must supply string to search for (contents)')

        term = unicode(term).lower()
        for cur_key, cur_value in self.items():
            cur_key, cur_value = unicode(cur_key).lower(), unicode(cur_value).lower()
            if key is not None and cur_key != key:
                # Do not search this key
                continue
            if cur_value.find(unicode(term).lower()) > -1:
                return self


class Actors(list):
    """Holds all Actor instances for a show
    """
    pass


class Actor(dict):
    """Represents a single actor. Should contain..

    id,
    image,
    name,
    role,
    sortorder
    """

    def __repr__(self):
        return '<Actor "%s">' % (self.get('name'))


class TVDBv2(object):
    """Create easy-to-use interface to name of season/episode name
    >>> t = tvdbv2()
    >>> t['Scrubs'][1][24]['episodename']
    u'My Last Day'
    """

    def __init__(self,  # pylint: disable=too-many-locals,too-many-arguments
                 interactive=False,
                 select_first=False,
                 debug=False,
                 cache=True,
                 banners=False,
                 actors=False,
                 custom_ui=None,
                 language=None,
                 search_all_languages=False,
                 apikey=None,
                 force_connect=False,
                 useZip=False,
                 dvdorder=False,
                 proxy=None,
                 session=None,
                 image_type=None):

        self.shows = ShowContainer()  # Holds all Show classes
        self.corrections = {}  # Holds show-name to show_id mapping

        self.config = {}

        self.config['debug_enabled'] = debug  # show debugging messages

        self.config['custom_ui'] = custom_ui

        self.config['interactive'] = interactive  # prompt for correct series?

        self.config['select_first'] = select_first

        self.config['search_all_languages'] = search_all_languages

        self.config['useZip'] = useZip

        self.config['dvdorder'] = dvdorder

        self.config['proxy'] = proxy

        if cache is True:
            self.config['cache_enabled'] = True
            self.config['cache_location'] = self._get_temp_dir()
        elif cache is False:
            self.config['cache_enabled'] = False
        elif isinstance(cache, basestring):
            self.config['cache_enabled'] = True
            self.config['cache_location'] = cache
        else:
            raise ValueError('Invalid value for Cache %r (type was %s)' % (cache, type(cache)))

        self.config['session'] = session if session else requests.Session()

        self.config['banners_enabled'] = banners
        self.config['image_type'] = None
        self.config['actors_enabled'] = actors

        if self.config['debug_enabled']:
            warnings.warn('The debug argument to tvdbv2_api.__init__ will be removed in the next version. '
                          'To enable debug messages, use the following code before importing: '
                          'import logging; logging.basicConfig(level=logging.DEBUG)')
            logging.basicConfig(level=logging.DEBUG)

        # List of language from http://thetvdbv2.com/api/0629B785CE550C8D/languages.xml
        # Hard-coded here as it is realtively static, and saves another HTTP request, as
        # recommended on http://thetvdbv2.com/wiki/index.php/API:languages.xml
        self.config['valid_languages'] = [
            'da', 'fi', 'nl', 'de', 'it', 'es', 'fr', 'pl', 'hu', 'el', 'tr',
            'ru', 'he', 'ja', 'pt', 'zh', 'cs', 'sl', 'hr', 'ko', 'en', 'sv', 'no'
        ]

        # thetvdb.com should be based around numeric language codes,
        # but to link to a series like http://thetvdb.com/?tab=series&id=79349&lid=16
        # requires the language ID, thus this mapping is required (mainly
        # for usage in tvdb_ui - internally tvdb_api will use the language abbreviations)
        self.config['langabbv_to_id'] = {'el': 20, 'en': 7, 'zh': 27,
                                         'it': 15, 'cs': 28, 'es': 16, 'ru': 22, 'nl': 13, 'pt': 26, 'no': 9,
                                         'tr': 21, 'pl': 18, 'fr': 17, 'hr': 31, 'de': 14, 'da': 10, 'fi': 11,
                                         'hu': 19, 'ja': 25, 'he': 24, 'ko': 32, 'sv': 8, 'sl': 30}

        if language is None:
            self.config['language'] = 'en'
        else:
            if language not in self.config['valid_languages']:
                raise ValueError('Invalid language %s, options are: %s' % (
                    language, self.config['valid_languages']
                ))
            else:
                self.config['language'] = language

        self.config['base_url'] = 'http://thetvdb.com'

        # Configure artwork prefix url
        self.config['artwork_prefix'] = '%(base_url)s/banners/%%s' % self.config
        # Old: self.config['url_artworkPrefix'] = self.config['artwork_prefix']

        # Initiate the tvdb api v2
        api_base_url = 'https://api.thetvdb.com'

        # client_id = 'username'  # (optional! Only required for the /user routes)
        # client_secret = 'pass'  # (optional! Only required for the /user routes)
        apikey = '0629B785CE550C8D'

        authentication_string = {'apikey': apikey, 'username': '', 'userpass': ''}
        unauthenticated_client = ApiClient(api_base_url)
        auth_api = AuthenticationApi(unauthenticated_client)
        access_token = auth_api.login_post(authentication_string)
        auth_client = ApiClient(api_base_url, 'Authorization', 'Bearer ' + access_token.token)
        self.search_api = SearchApi(auth_client)
        self.series_api = SeriesApi(auth_client)

        # An api to indexer series/episode object mapping
        self.series_map = {
            'id': 'id',
            'series_name': 'seriesname',
            'summary': 'overview',
            'first_aired': 'firstaired',
            'banner': 'banner',
            'url': 'show_url',
            'epnum': 'absolute_number',
            'episode_name': 'episodename',
            'aired_episode_number': 'episodenumber',
            'aired_season': 'seasonnumber',
            'dvd_episode_number': 'dvd_episodenumber',
        }

    def _object_to_dict(self, tvdb_response, key_mapping=None, list_separator='|'):
        parsed_response = []

        tvdb_response = getattr(tvdb_response, 'data', tvdb_response)

        if not isinstance(tvdb_response, list):
            tvdb_response = [tvdb_response]

        for parse_object in tvdb_response:
            return_dict = {}
            if parse_object.attribute_map:
                for attribute in parse_object.attribute_map:
                    try:
                        value = getattr(parse_object, attribute, None)
                        if value is None or value == []:
                            continue

                        if isinstance(value, list):
                            if list_separator and all(isinstance(x, (str, unicode)) for x in value):
                                value = list_separator.join(value)
                            else:
                                value = [self._object_to_dict(x, key_mapping) for x in value]

                        if key_mapping and key_mapping.get(attribute):
                            if isinstance(value, dict) and isinstance(key_mapping[attribute], dict):
                                # Let's map the children, i'm only going 1 deep, because usecases that I need it for, I don't need to go any further
                                for k, v in value.iteritems():
                                    if key_mapping.get(attribute)[k]:
                                        return_dict[key_mapping[attribute][k]] = str(v)

                            else:
                                if key_mapping.get(attribute):
                                    return_dict[key_mapping[attribute]] = str(value)
                        else:
                            return_dict[attribute] = str(value)

                    except Exception as e:
                        log().warning('Exception trying to parse attribute: %s, with exception: %r', attribute, e)
                parsed_response.append(return_dict)
            else:
                log().debug('Missing attribute map, cant parse to dict')

        return parsed_response if len(parsed_response) != 1 else parsed_response[0]

    def _get_temp_dir(self):  # pylint: disable=no-self-use
        """Returns the [system temp dir]/tvdb_api-u501 (or
        tvdb_api-myuser)
        """
        if hasattr(os, 'getuid'):
            uid = 'u{0}'.format(os.getuid())  # pylint: disable=no-member
        else:
            # For Windows
            try:
                uid = getpass.getuser()
            except ImportError:
                return os.path.join(tempfile.gettempdir(), 'tvdbv2_api')

        return os.path.join(tempfile.gettempdir(), 'tvdbv2_api-{0}'.format(uid))

    def _set_item(self, sid, seas, ep, attrib, value):  # pylint: disable=too-many-arguments
        """Creates a new episode, creating Show(), Season() and
        Episode()s as required. Called by _get_show_data to populate show

        Since the nice-to-use tvdb[1][24]['name] interface
        makes it impossible to do tvdb[1][24]['name] = "name"
        and still be capable of checking if an episode exists
        so we can raise tvdb_shownotfound, we have a slightly
        less pretty method of setting items.. but since the API
        is supposed to be read-only, this is the best way to
        do it!
        The problem is that calling tvdb[1][24]['episodename'] = "name"
        calls __getitem__ on tvdb[1], there is no way to check if
        tvdb.__dict__ should have a key "1" before we auto-create it
        """
        if sid not in self.shows:
            self.shows[sid] = Show()
        if seas not in self.shows[sid]:
            self.shows[sid][seas] = Season(show=self.shows[sid])
        if ep not in self.shows[sid][seas]:
            self.shows[sid][seas][ep] = Episode(season=self.shows[sid][seas])
        self.shows[sid][seas][ep][attrib] = value

    def _set_show_data(self, sid, key, value):
        """Sets self.shows[sid] to a new Show instance, or sets the data
        """
        if sid not in self.shows:
            self.shows[sid] = Show()
        self.shows[sid].data[key] = value

    def _save_images(self, sid, images):
        """Saves the highest rated image (banner, poster, fanart) as show data.
        """

        for image_type in images:
            # get series data / add the base_url to the image urls
            if image_type in ['banner', 'fanart', 'poster']:
                # For each image type, where going to save one image based on the highest rating
                merged_image_list = [y[1] for y in [six_next(six_iteritems(v))
                                                    for _, v in six_iteritems(images[image_type])]]
                highest_rated = sorted(merged_image_list, key=lambda k: k['rating'], reverse=True)[0]
                self._set_show_data(sid, image_type, highest_rated['_bannerpath'])

    def _clean_data(self, data):  # pylint: disable=no-self-use
        """Cleans up strings returned by tvrage.com

        Issues corrected:
        - Replaces &amp; with &
        - Trailing whitespace
        """

        if isinstance(data, basestring):
            data = data.replace('&amp;', '&')
            data = data.strip()

            tag_re = re.compile(r'(<!--.*?-->|<[^>]*>)')
            # Remove well-formed tags
            no_tags = tag_re.sub('', data)
            # Clean up anything else by escaping
            data = cgi.escape(no_tags)

        return data

    def _show_search(self, show, request_language='en'):
        """
        Uses the pytvdbv2 API to search for a show
        @param show: The show name that's searched for as a string
        @return: A list of Show objects.
        """
        try:
            results = self.search_api.search_series_get(name=show, accept_language=request_language)
        except Exception as e:
            raise IndexerException('Show search failed in getting a result with error: %r', e)

        if results:
            return results
        else:
            return OrderedDict({'data': None})

    # Tvdb implementation
    def search(self, series):
        """This searches tvdbv2.com for the series name

        :param series: the query for the series name
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"series": [list of shows]}
        """
        series = series.encode('utf-8')
        log().debug('Searching for show %s', [series])

        results = self._show_search(series, request_language=self.config['language'])

        if not results:
            return

        mapped_results = self._object_to_dict(results, self.series_map, '|')

        return OrderedDict({'series': mapped_results})['series']

    def _get_show_by_id(self, tvdbv2_id, request_language='en'):  # pylint: disable=unused-argument
        """
        Retrieve tvdbv2 show information by tvdbv2 id, or if no tvdbv2 id provided by passed external id.

        :param tvdbv2_id: The shows tvdbv2 id
        :return: An ordered dict with the show searched for.
        """

        if tvdbv2_id:
            log().debug('Getting all show data for %s', [tvdbv2_id])
            results = self.series_api.series_id_get(tvdbv2_id, accept_language=request_language)

        if not results:
            return

        mapped_results = self._object_to_dict(results, self.series_map, '|')

        return OrderedDict({'series': mapped_results})

    def _get_episode_list(self, tvdb_id, specials=False):  # pylint: disable=unused-argument
        """
        Get all the episodes for a show by tvdbv2 id

        :param tvdb_id: Series tvdbv2 id.
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"episode": [list of episodes]}
        """
        results = []

        # Parse episode data
        log().debug('Getting all episodes of %s', [tvdb_id])

        # get paginated pages
        page = 1
        last = 1
        while page <= last:
            paged_episodes = self.series_api.series_id_episodes_query_get(tvdb_id, page=page, accept_language=self.config['language'])
            results += paged_episodes.data
            last = paged_episodes.links.last
            page += 1

        mapped_episodes = self._object_to_dict(results, self.series_map, '|')

        return OrderedDict({'episode': mapped_episodes})

    def _get_series(self, series):
        """This searches thetvdb.com for the series name,
        If a custom_ui UI is configured, it uses this to select the correct
        series. If not, and interactive == True, ConsoleUI is used, if not
        BaseUI is used to select the first result.

        :param series: the query for the series name
        :return: A list of series mapped to a UI (for example: a BaseUi or CustomUI).
        """

        allSeries = self.search(series)
        if not allSeries:
            log().debug('Series result returned zero')
            IndexerShowNotFound('Show search returned zero results (cannot find show on TVDB)')

        if not isinstance(allSeries, list):
            allSeries = [allSeries]

        if self.config['custom_ui'] is not None:
            log().debug('Using custom UI %s', [repr(self.config['custom_ui'])])
            CustomUI = self.config['custom_ui']
            ui = CustomUI(config=self.config)
        else:
            if not self.config['interactive']:
                log().debug('Auto-selecting first search result using BaseUI')
                ui = BaseUI(config=self.config)
            else:
                log().debug('Interactively selecting show using ConsoleUI')
                ui = ConsoleUI(config=self.config)  # pylint: disable=redefined-variable-type

        return ui.selectSeries(allSeries)

    def _parse_images(self, sid):
        """Parses images XML, from
        http://thetvdb.com/api/[APIKEY]/series/[SERIES ID]/banners.xml

        images are retrieved using t['show name]['_banners'], for example:

        >>> t = Tvdb(images = True)
        >>> t['scrubs']['_banners'].keys()
        ['fanart', 'poster', 'series', 'season']
        >>> t['scrubs']['_banners']['poster']['680x1000']['35308']['_bannerpath']
        u'http://thetvdb.com/banners/posters/76156-2.jpg'
        >>>

        Any key starting with an underscore has been processed (not the raw
        data from the XML)

        This interface will be improved in future versions.
        """
        key_mapping = {'file_name': 'bannerpath', 'language_id': 'language', 'key_type': 'bannertype', 'resolution': 'bannertype2',
                       'ratings_info': {'count': 'ratingcount', 'average': 'rating'}, 'thumbnail': 'thumbnailpath', 'sub_key': 'sub_key', 'id': 'id'}

        search_for_image_type = self.config['image_type']

        log().debug('Getting show banners for %s', sid)
        _images = {}

        # Let's fget the different type of images available for this series

        try:
            series_images_count = self.series_api.series_id_images_get(sid, accept_language=self.config['language'])
        except Exception as e:
            log().debug('Could not get image count for showid: %s, with exception: %r', sid, e)
            return False

        for image_type, image_count in self._object_to_dict(series_images_count).iteritems():
            try:

                if search_for_image_type and search_for_image_type != image_type:
                    continue

                if not image_count:
                    continue

                if image_type not in _images:
                    _images[image_type] = {}

                images = self.series_api.series_id_images_query_get(sid, key_type=image_type)
                for image in images.data:
                    # Store the images for each resolution available
                    if image.resolution not in _images[image_type]:
                        _images[image_type][image.resolution] = {}

                    # _images[image_type][image.resolution][image.id] = image_dict
                    image_attributes = self._object_to_dict(image, key_mapping)
                    bid = image_attributes.pop('id')
                    _images[image_type][image.resolution][bid] = {}

                    for k, v in image_attributes.items():
                        if k is None or v is None:
                            continue

                        k, v = k.lower(), v.lower()
                        _images[image_type][image.resolution][bid][k] = v

                    for k, v in _images[image_type][image.resolution][bid].items():
                        if k.endswith('path'):
                            new_key = '_%s' % (k)
                            log().debug('Adding base url for image: %s', v)
                            new_url = self.config['artwork_prefix'] % (v)
                            _images[image_type][image.resolution][bid][new_key] = new_url

            except Exception as e:
                log().warning('Could not parse Poster for showid: %s, with exception: %r', sid, e)
                return False

        self._save_images(sid, _images)
        self._set_show_data(sid, '_banners', _images)

    def _parse_actors(self, sid):
        """Parsers actors XML, from
        http://thetvdb.com/api/[APIKEY]/series/[SERIES ID]/actors.xml

        Actors are retrieved using t['show name]['_actors'], for example:

        >>> t = Tvdb(actors = True)
        >>> actors = t['scrubs']['_actors']
        >>> type(actors)
        <class 'tvdb_api.Actors'>
        >>> type(actors[0])
        <class 'tvdb_api.Actor'>
        >>> actors[0]
        <Actor "Zach Braff">
        >>> sorted(actors[0].keys())
        ['id', 'image', 'name', 'role', 'sortorder']
        >>> actors[0]['name']
        u'Zach Braff'
        >>> actors[0]['image']
        u'http://thetvdb.com/banners/actors/43640.jpg'

        Any key starting with an underscore has been processed (not the raw
        data from the XML)
        """
        log().debug('Getting actors for %s', sid)

        actors = self.series_api.series_id_actors_get(sid)

        if not actors or not actors.data:
            log().debug('Actors result returned zero')
            return

        cur_actors = Actors()
        for cur_actor in actors.data if isinstance(actors.data, list) else [actors.data]:
            new_actor = Actor()
            new_actor['id'] = cur_actor.id
            new_actor['image'] = cur_actor.image
            new_actor['name'] = cur_actor.name
            new_actor['role'] = cur_actor.role
            new_actor['sortorder'] = 0
            cur_actors.append(new_actor)
        self._set_show_data(sid, '_actors', cur_actors)

    def _get_show_data(self, sid, language, get_ep_info=False):  # pylint: disable=too-many-branches,too-many-statements,too-many-locals
        """Takes a series ID, gets the epInfo URL and parses the TheTVDB json response
        into the shows dict in layout:
        shows[series_id][season_number][episode_number]
        """
        if self.config['language'] is None:
            log().debug('Config language is none, using show language')
            if language is None:
                raise IndexerError("config['language'] was None, this should not happen")
            get_show_in_language = language
        else:
            log().debug(
                'Configured language %s override show language of %s' % (
                    self.config['language'],
                    language
                )
            )
            get_show_in_language = self.config['language']

        # Parse show information
        log().debug('Getting all series data for %s' % (sid))

        # Parse show information
        series_info = self._get_show_by_id(sid, request_language=get_show_in_language)

        if not series_info:
            log().debug('Series result returned zero')
            raise IndexerError('Series result returned zero')

        # get series data / add the base_url to the image urls
        for k, v in series_info['series'].items():
            if v is not None:
                if k in ['banner', 'fanart', 'poster']:
                    v = self.config['artwork_prefix'] % (v)
                else:
                    v = self._clean_data(v)

            self._set_show_data(sid, k, v)

        # get episode data
        if get_ep_info:
            # Parse banners
            if self.config['banners_enabled']:
                self._parse_images(sid)

            # Parse actors
            if self.config['actors_enabled']:
                self._parse_actors(sid)

            # Parse episode data
            episode_data = self._get_episode_list(sid, specials=False)

            if not episode_data:
                log().debug('Series results incomplete')
                raise IndexerShowIncomplete('Show search returned incomplete results (cannot find complete show on TheTVDB)')

            if 'episode' not in episode_data:
                return False

            episodes = episode_data['episode']
            if not isinstance(episodes, list):
                episodes = [episodes]

            for cur_ep in episodes:
                if self.config['dvdorder']:
                    log().debug('Using DVD ordering.')
                    use_dvd = cur_ep['dvd_season'] != None and cur_ep['dvd_episodenumber'] != None
                else:
                    use_dvd = False

                if use_dvd:
                    seasnum, epno = cur_ep.get('dvd_season'), cur_ep.get('dvd_episodenumber')
                else:
                    seasnum, epno = cur_ep.get('seasonnumber'), cur_ep.get('episodenumber')

                if seasnum is None or epno is None:
                    log().warning('An episode has incomplete season/episode number (season: %r, episode: %r)', seasnum, epno)
                    continue  # Skip to next episode

                # float() is because https://github.com/dbr/tvnamer/issues/95 - should probably be fixed in TVDB data
                seas_no = int(float(seasnum))
                ep_no = int(float(epno))

                for k, v in cur_ep.items():
                    k = k.lower()

                    if v is not None:
                        if k == 'filename':
                            v = urljoin(self.config['artwork_prefix'], v)
                        else:
                            v = self._clean_data(v)

                    self._set_item(sid, seas_no, ep_no, k, v)

        return True

    def __getitem__(self, key):
        """Handles tvdbv2_instance['seriesname'] calls.
        The dict index should be the show id
        """
        if isinstance(key, (int, long)):
            # Item is integer, treat as show id
            if key not in self.shows:
                self._get_show_data(key, self.config['language'], True)
            return self.shows[key]

        key = str(key).lower()
        self.config['searchterm'] = key
        selected_series = self._get_series(key)
        if isinstance(selected_series, dict):
            selected_series = [selected_series]

        for show in selected_series:
            for k, v in show.items():
                self._set_show_data(show['id'], k, v)
        return selected_series

    def __repr__(self):
        return str(self.shows)
