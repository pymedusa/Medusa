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


import cgi
import getpass
import logging
import os
import re
import tempfile
import time
import warnings
from collections import OrderedDict

from pytvmaze import API
import requests
from .tvmaze_exceptions import (
    tvmaze_attributenotfound, tvmaze_episodenotfound, tvmaze_error,
    tvmaze_seasonnotfound, tvmaze_showincomplete, tvmaze_shownotfound
)
from .tvmaze_ui import BaseUI, ConsoleUI


def log():
    return logging.getLogger('tvdb_api')


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
            raise tvmaze_seasonnotfound('Could not find season %s' % (repr(key)))
        else:
            # If it's not numeric, it must be an attribute name, which
            # doesn't exist, so attribute error.
            raise tvmaze_attributenotfound('Cannot find attribute %s' % (repr(key)))

    def airedOn(self, date):
        ret = self.search(str(date), 'firstaired')
        if len(ret) == 0:
            raise tvmaze_episodenotfound('Could not find any episodes that aired on %s' % date)
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
            raise tvmaze_episodenotfound('Could not find episode %s' % (repr(episode_number)))
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
            raise tvmaze_attributenotfound('Cannot find attribute %s' % (repr(key)))

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


class TVmaze(object):
    """Create easy-to-use interface to name of season/episode name
    >>> t = tvmaze()
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
                 session=None):

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
            self.config['cache_location'] = self._getTempDir()
        elif cache is False:
            self.config['cache_enabled'] = False
        elif isinstance(cache, basestring):
            self.config['cache_enabled'] = True
            self.config['cache_location'] = cache
        else:
            raise ValueError('Invalid value for Cache %r (type was %s)' % (cache, type(cache)))

        self.config['session'] = session if session else requests.Session()

        self.config['banners_enabled'] = banners
        self.config['actors_enabled'] = actors

        if self.config['debug_enabled']:
            warnings.warn('The debug argument to tvmaze_api.__init__ will be removed in the next version. '
                          'To enable debug messages, use the following code before importing: '
                          'import logging; logging.basicConfig(level=logging.DEBUG)')
            logging.basicConfig(level=logging.DEBUG)

        # List of language from http://thetvmaze.com/api/0629B785CE550C8D/languages.xml
        # Hard-coded here as it is realtively static, and saves another HTTP request, as
        # recommended on http://thetvmaze.com/wiki/index.php/API:languages.xml
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

        # Initiate the pytvmaze API
        self.API = API(self.config['session'])

    def _parse_show_data(self, indexer_data, parsing_into_key='series'):  # pylint: disable=no-self-use
        """ These are the fields we'd like to see for a show search"""
        new_dict = OrderedDict()
        name_map = {
            'id': 'id',
            'name': 'seriesname',
            'summary': 'overview',
            'premiered': 'firstaired',
            'image': 'fanart',
            'url': 'show_url',
        }

        for key, value in indexer_data.get('data').__dict__.iteritems():
            try:
                # Try to map the object value using the name_map dict
                if isinstance(value, (unicode, str, int)):
                    new_dict[name_map.get(key) or key] = value
                else:
                    # Try to map more complex structures, and overwrite the default mapping
                    if key == 'schedule':
                        new_dict['airs_time'] = value.get('time')
                        new_dict['airs_dayofweek'] = u', '.join(value.value('days')) if value.get('days') else None
                    if key == 'network':
                        new_dict['network'] = value.get('name')
                        new_dict['code'] = value.get('country', {'code': 'NA'})['code']
                        new_dict['timezone'] = value.get('country', {'timezone': 'NA'})['timezone']
                    if key == 'webChannel':
                        new_dict['webchannel'] = value.get('name')
                    if key == 'image':
                        if value.get('medium'):
                            new_dict['image_medium'] = value.get('medium')
                            new_dict['image_original'] = value.get('original')
                            new_dict['poster'] = value.get('original')
                    if key == 'externals':
                        new_dict['tvrage_id'] = value.get('tvrage')
                        new_dict['tvdb_id'] = value.get('thetvdb')
                        new_dict['imdb_id'] = value.get('imdb')
                    if key == 'genres' and isinstance(value, list):
                        new_dict['genre'] = '|' + '|'.join(value) + '|'
            except Exception:
                continue

        # Fix network for webChannel shows.
        new_dict['network'] = new_dict.get('network') or new_dict.get('webchannel')

        return OrderedDict({parsing_into_key: new_dict})

    def _getTempDir(self):  # pylint: disable=no-self-use
        """Returns the [system temp dir]/tvdb_api-u501 (or
        tvdb_api-myuser)
        """
        if hasattr(os, 'getuid'):
            uid = 'u%d' % (os.getuid())  # pylint: disable=no-member
        else:
            # For Windows
            try:
                uid = getpass.getuser()
            except ImportError:
                return os.path.join(tempfile.gettempdir(), 'tvmaze_api')

        return os.path.join(tempfile.gettempdir(), 'tvdb_api-%s' % (uid))

    def _setItem(self, sid, seas, ep, attrib, value):  # pylint: disable=too-many-arguments
        """Creates a new episode, creating Show(), Season() and
        Episode()s as required. Called by _getShowData to populate show

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

    def _setShowData(self, sid, key, value):
        """Sets self.shows[sid] to a new Show instance, or sets the data
        """
        if sid not in self.shows:
            self.shows[sid] = Show()
        self.shows[sid].data[key] = value

    def _cleanData(self, data):  # pylint: disable=no-self-use
        """Cleans up strings returned by tvrage.com

        Issues corrected:
        - Replaces &amp; with &
        - Trailing whitespace
        """

        if isinstance(data, basestring):
            data = data.replace(u'&amp;', u'&')
            data = data.strip()

            tag_re = re.compile(r'(<!--.*?-->|<[^>]*>)')
            # Remove well-formed tags
            no_tags = tag_re.sub('', data)
            # Clean up anything else by escaping
            data = cgi.escape(no_tags)

        return data

    def _show_search(self, show):
        """
        Uses the pytvmaze API to search for a show
        @param show: The show name that's searched for as a string
        @return: A list of Show objects. Includes the search score.
        """

        results = OrderedDict({'data': self.API.show_search(show)})
        if results:
            return results
        else:
            return OrderedDict({'data': None})

    # Tvdb implementation
    def search(self, series):
        """This searches tvmaze.com for the series name

        :param series: the query for the series name
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"series": [list of shows]}
        """
        series = series.encode('utf-8')
        log().debug('Searching for show %s', [series])

        results = self._show_search(series)

        if not results:
            return

        # Where expecting to a OrderedDict with Show information, let's standardize the returnd dict
        def map_data(indexer_data):
            # These are the fields we'd like to see for a show search
            series_list = []

            name_map = {
                'id': 'id',
                'name': 'seriesname',
                'summary': 'overview',
                'premiered': 'firstaired',
                'genres': 'genre',
                'image': 'fanart',
                'url': 'show_url',
            }

            for series in indexer_data.get('data', []):  # @UnusedVariable, pylint: disable=unused-variable
                new_dict = OrderedDict()
                for key, value in series.__dict__.iteritems():
                    try:
                        # Try to map the object value using the name_map dict
                        if isinstance(value, (unicode, str, int)):
                            new_dict[name_map.get(key) or key] = value
                        else:
                            # Try to map more complex structures, and overwrite the default mapping
                            if key == 'schedule':
                                new_dict['airs_time'] = value.get('time')
                                new_dict['airs_dayofweek'] = u', '.join(value.get('days')) if key.get('days') else None
                            if key == 'network':
                                new_dict['network'] = value.get('name')
                            if key == 'image':
                                if value.get('medium'):
                                    new_dict['image_medium'] = value.get('medium')
                                    new_dict['image_original'] = value.get('original')
                    except Exception:
                        pass
                series_list.append(new_dict)
            return OrderedDict({'series': series_list})

        return map_data(results)['series']

    def _get_show_by_id(self, tvmaze_id=None):  # pylint: disable=unused-argument
        """
        Retrieve tvmaze show information by tvmaze id, or if no tvmaze id provided by passed external id.

        :param tvmaze_id: The shows tvmaze id
        :return: An ordered dict with the show searched for.
        """

        if tvmaze_id:
            log().debug('Getting all show data for %s', [tvmaze_id])
            results = OrderedDict({'data': self.API.get_show(tvmaze_id)})

        if not results:
            return

        return self._parse_show_data(results)

    def _get_episode_list(self, maze_id, specials=False):  # pylint: disable=unused-argument
        """
        Get all the episodes for a show by tvmaze id

        :param maze_id: Series tvmaze id.
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"episode": [list of episodes]}
        """
        # Parse episode data
        log().debug('Getting all episodes of %s', [maze_id])
        results = {'data': self.API.episode_list(maze_id, specials)}

        def map_data(indexer_data):
            # These are the fields we'd like to see for a show search

            episode_list = []
            name_map = {
                'maze_id': 'id',
                'image': 'fanart',
                'epnum': 'absolute_number',
                'title': 'episodename',
                'airdate': 'firstaired',
                'screencap': 'filename',
                'episode_number': 'episodenumber',
                'season_number': 'seasonnumber',
                'summary': 'overview'
            }

            for episode in indexer_data.get('data', []):  # @UnusedVariable, pylint: disable=unused-variable
                new_dict = OrderedDict()
                for key, value in episode.__dict__.iteritems():
                    if isinstance(value, (int, str, unicode)) or value is None:
                        try:
                            new_dict[name_map.get(key) or key] = value
                        except Exception:
                            pass
                episode_list.append(new_dict)
            return episode_list

        return OrderedDict({'episode': map_data(results)})

    def _getSeries(self, series):
        """This searches TVmaze.com for the series name,
        If a custom_ui UI is configured, it uses this to select the correct
        series. If not, and interactive == True, ConsoleUI is used, if not
        BaseUI is used to select the first result.

        :param series: the query for the series name
        :return: A list of series mapped to a UI (for example: a BaseUi or CustomUI).
        """

        allSeries = self.search(series)
        if not allSeries:
            log().debug('Series result returned zero')
            raise tvmaze_shownotfound('Show search returned zero results (cannot find show on TVDB)')

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

    def _parseBanners(self, sid):
        """Parses banners XML, from
        http://thetvdb.com/api/[APIKEY]/series/[SERIES ID]/banners.xml

        Banners are retrieved using t['show name]['_banners'], for example:

        >>> t = Tvdb(banners = True)
        >>> t['scrubs']['_banners'].keys()
        ['fanart', 'poster', 'series', 'season']
        >>> t['scrubs']['_banners']['poster']['680x1000']['35308']['_bannerpath']
        u'http://thetvdb.com/banners/posters/76156-2.jpg'
        >>>

        Any key starting with an underscore has been processed (not the raw
        data from the XML)

        This interface will be improved in future versions.
        """
        log().debug('Getting show banners for %s', [sid])

        try:
            image_original = self.shows[sid]['image_original']
        except Exception:
            log().debug('Could not parse Poster for showid: %s', [sid])
            return False

        # Set the poster (using the original uploaded poster for now, as the medium formated is 210x195
        banners = {u'poster': {u'1014x1500': {u'1': {u'rating': '',
                                                     u'language': u'en',
                                                     u'ratingcount': '',
                                                     u'bannerpath': image_original.split('/')[-1],
                                                     u'bannertype': u'poster',
                                                     u'bannertype2': u'210x195',
                                                     u'_bannerpath': image_original,
                                                     u'id': u'1035106'}}}}

        self._setShowData(sid, '_banners', banners)

    def _parseActors(self, sid):
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
        log().debug('Getting actors for %s', [sid])
        # actorsEt = self._getetsrc(self.config['url_actorsInfo'] % (sid))
        actors = {'data': self.API.show_cast(sid)}

        if not actors:
            log().debug('Actors result returned zero')
            return

        cur_actors = Actors()
        for cur_actor in actors['data'] if isinstance(actors['data'], list) else [actors['data']]:
            curActor = Actor()
            curActor['id'] = cur_actor['person']['id']
            curActor['image'] = cur_actor['person']['image']['original']
            curActor['name'] = cur_actor['person']['name']
            curActor['role'] = cur_actor['character']['name']
            curActor['sortorder'] = 0
            cur_actors.append(curActor)
        self._setShowData(sid, '_actors', cur_actors)

    def _getShowData(self, sid, language, getEpInfo=False):  # pylint: disable=too-many-branches,too-many-statements,too-many-locals
        """Takes a series ID, gets the epInfo URL and parses the TVmaze json response
        into the shows dict in layout:
        shows[series_id][season_number][episode_number]
        """
        if self.config['language'] is None:
            log().debug('Config language is none, using show language')
            if language is None:
                raise tvmaze_error("config['language'] was None, this should not happen")
            # getShowInLanguage = language
        else:
            log().debug('Configured language %s override show language of %s', self.config['language'], language)
            # getShowInLanguage = self.config['language']

        # Parse show information
        seriesInfoEt = self._get_show_by_id(sid)

        if not seriesInfoEt:
            log().debug('Series result returned zero')
            raise tvmaze_error('Series result returned zero')

        # get series data
        for k, v in seriesInfoEt['series'].items():
            if v is not None:
                if k in ['image_medium', 'image_large']:
                    v = self._cleanData(v)
            self._setShowData(sid, k, v)

        # get episode data
        if getEpInfo:
            # Parse banners
            if self.config['banners_enabled']:
                self._parseBanners(sid)

            # Parse actors
            if self.config['actors_enabled']:
                self._parseActors(sid)

            # Parse episode data
            epsEt = self._get_episode_list(sid, specials=False)

            if not epsEt:
                log().debug('Series results incomplete')
                raise tvmaze_showincomplete('Show search returned incomplete results (cannot find complete show on TVmaze)')

            if 'episode' not in epsEt:
                return False

            episodes = epsEt['episode']
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
                            v = self.config['url_artworkPrefix'] % (v)
                        else:
                            v = self._cleanData(v)

                    self._setItem(sid, seas_no, ep_no, k, v)

        return True

    def __getitem__(self, key):
        """Handles tvmaze_instance['seriesname'] calls.
        The dict index should be the show id
        """
        if isinstance(key, (int, long)):
            # Item is integer, treat as show id
            if key not in self.shows:
                self._getShowData(key, self.config['language'], True)
            return self.shows[key]

        key = str(key).lower()
        self.config['searchterm'] = key
        selected_series = self._getSeries(key)
        if isinstance(selected_series, dict):
            selected_series = [selected_series]
        for show in selected_series:
            for k, v in show.items():
                self._setShowData(show['id'], k, v)
        return selected_series

    def __repr__(self):
        return str(self.shows)
