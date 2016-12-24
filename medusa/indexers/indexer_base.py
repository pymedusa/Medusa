# coding=utf-8
# Author: p0psicles
#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.
"""Base class for indexer api's."""

import cgi
import getpass
import logging
import os
import re
import tempfile
import time

import warnings
import requests
from six import iteritems
from .indexer_exceptions import (IndexerAttributeNotFound, IndexerEpisodeNotFound, IndexerSeasonNotFound,
                                 IndexerSeasonUpdatesNotSupported, IndexerShowNotFound)

from .indexer_ui import BaseUI, ConsoleUI


def log():
    """Log init."""
    return logging.getLogger('indexer_base')


class BaseIndexer(object):
    """Base class for indexer api's."""

    def __init__(self,
                 interactive=False,
                 select_first=False,
                 debug=False,
                 cache=True,
                 episodes=True,
                 banners=False,
                 actors=False,
                 custom_ui=None,
                 language=None,
                 search_all_languages=False,
                 apikey=None,
                 force_connect=False,
                 use_zip=False,
                 dvdorder=False,
                 proxy=None,
                 session=None,
                 image_type=None):  # pylint: disable=too-many-locals,too-many-arguments
        """Pass these arguments on as args from the subclass."""
        self.shows = ShowContainer()  # Holds all Show classes
        self.corrections = {}  # Holds show-name to show_id mapping

        self.config = {}

        self.config['debug_enabled'] = debug  # show debugging messages

        self.config['custom_ui'] = custom_ui

        self.config['interactive'] = interactive  # prompt for correct series?

        self.config['select_first'] = select_first

        self.config['search_all_languages'] = search_all_languages

        self.config['use_zip'] = use_zip

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

        self.config['episodes_enabled'] = episodes
        self.config['banners_enabled'] = banners
        self.config['image_type'] = image_type
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

    def _get_temp_dir(self):  # pylint: disable=no-self-use
        """Return the [system temp dir]/tvdb_api-u501 (or tvdb_api-myuser)."""
        if hasattr(os, 'getuid'):
            uid = 'u{0}'.format(os.getuid())  # pylint: disable=no-member
        else:
            # For Windows
            try:
                uid = getpass.getuser()
            except ImportError:
                return os.path.join(tempfile.gettempdir(), 'tvdbv2_api')

        return os.path.join(tempfile.gettempdir(), 'tvdbv2_api-{0}'.format(uid))

    def _get_show_data(self, sid, language):  # pylint: disable=too-many-branches,too-many-statements,too-many-locals
        """Dummy _get_show_data method."""
        return None

    def _get_series(self, series):
        """Search themoviedb.org for the series name.

        If a custom_ui UI is configured, it uses this to select the correct
        series. If not, and interactive == True, ConsoleUI is used, if not
        BaseUI is used to select the first result.

        :param series: the query for the series name
        :return: A list of series mapped to a UI (for example: a BaseUi or CustomUI).
        """
        all_series = self.search(series)
        if not all_series:
            log().debug('Series result returned zero')
            IndexerShowNotFound('Show search returned zero results (cannot find show on Indexer)')

        if not isinstance(all_series, list):
            all_series = [all_series]

        if self.config['custom_ui'] is not None:
            log().debug('Using custom UI %s', [repr(self.config['custom_ui'])])
            custom_ui = self.config['custom_ui']
            ui = custom_ui(config=self.config)
        else:
            if not self.config['interactive']:
                log().debug('Auto-selecting first search result using BaseUI')
                ui = BaseUI(config=self.config)
            else:
                log().debug('Interactively selecting show using ConsoleUI')
                ui = ConsoleUI(config=self.config)  # pylint: disable=redefined-variable-type

        return ui.select_series(all_series)

    def _set_show_data(self, sid, key, value):
        """Set self.shows[sid] to a new Show instance, or sets the data."""
        if sid not in self.shows:
            self.shows[sid] = Show()
        self.shows[sid].data[key] = value

    def __repr__(self):
        """Indexer representation, returning representation of all shows indexed."""
        return str(self.shows)

    def _clean_data(self, data):  # pylint: disable=no-self-use
        """Clean up strings.

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

    def _set_item(self, sid, seas, ep, attrib, value):  # pylint: disable=too-many-arguments
        """Create a new episode, creating Show(), Season() and Episode()s as required.

        Called by _get_show_data to populate show.
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

    def _save_images(self, sid, images):
        """Save the highest rated image (banner, poster, fanart) as show data."""
        for image_type in images:
            # get series data / add the base_url to the image urls
            if image_type in ['banner', 'fanart', 'poster']:
                # For each image type, where going to save one image based on the highest rating
                if not len(images[image_type]):
                    continue
                merged_image_list = [y[1] for y in [next(iteritems(v)) for _, v in iteritems(images[image_type])]]
                highest_rated = sorted(merged_image_list, key=lambda k: float(k['rating']), reverse=True)[0]
                self._set_show_data(sid, image_type, highest_rated['_bannerpath'])

    def __getitem__(self, key):
        """Handle tvdbv2_instance['seriesname'] calls. The dict index should be the show id."""
        if isinstance(key, (int, long)):
            # Item is integer, treat as show id
            if key not in self.shows:
                self._get_show_data(key, self.config['language'])
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

    def get_last_updated_series(self, from_time, weeks=1, filter_show_list=None):
        """Retrieve a list with updated shows

        :param from_time: epoch timestamp, with the start date/time
        :param weeks: number of weeks to get updates for.
        :param filter_show_list: Optional list of show objects, to use for filtering the returned list.
        """
        raise IndexerSeasonUpdatesNotSupported("Method get_last_updated_series not implemented by this indexer")

    def get_episodes_for_season(self, show_id, *args, **kwargs):
        self._get_episodes(show_id, *args, **kwargs)
        return self.shows[show_id]


class ShowContainer(dict):
    """Simple dict that holds a series of Show instances."""

    def __init__(self):
        """Init for ShowContainer."""
        dict.__init__(self)
        self._stack = []
        self._lastgc = time.time()

    def __setitem__(self, key, value):
        """Set ShowContainer attribut."""
        self._stack.append(key)

        # keep only the 100th latest results
        if time.time() - self._lastgc > 20:
            for o in self._stack[:-100]:
                del self[o]

            self._stack = self._stack[-100:]

            self._lastgc = time.time()

        super(ShowContainer, self).__setitem__(key, value)


class Show(dict):
    """Hold a dict of seasons, and show data."""

    def __init__(self):
        """Init method of show dict."""
        dict.__init__(self)
        self.data = {}

    def __repr__(self):
        """Represent a Show object."""
        return '<Show %s (containing %s seasons)>' % (
            self.data.get(u'seriesname', 'instance'),
            len(self)
        )

    def __getattr__(self, key):
        """Return Episode or Show-data."""
        if key in self:
            # Key is an episode, return it
            return self[key]

        if key in self.data:
            # Non-numeric request is for show-data
            return self.data[key]

        raise AttributeError

    def __getitem__(self, key):
        """Return Episode or Show-data."""
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

    def aired_on(self, date):
        """Helper menthod for searching and returning a list of episodes with the airdates."""
        ret = self.search(str(date), 'firstaired')
        if len(ret) == 0:
            raise IndexerEpisodeNotFound('Could not find any episodes that aired on %s' % date)
        return ret

    def search(self, term=None, key=None):
        """Search all episodes in show.

        Can search all data, or a specific key (for
        example, episodename).
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
    """Hold all Seasons instances for a show."""

    def __init__(self, show=None):  # pylint: disable=super-init-not-called
        """Show attribute points to the parent show."""
        self.show = show

    def __repr__(self):
        """Representation of a season object."""
        return '<Season instance (containing %s episodes)>' % (
            len(self.keys())
        )

    def __getattr__(self, episode_number):
        """Get an attribute by passing it as episode number."""
        if episode_number in self:
            return self[episode_number]
        raise AttributeError

    def __getitem__(self, episode_number):
        """Get the episode dict by passing it as a dict key."""
        if episode_number not in self:
            raise IndexerEpisodeNotFound('Could not find episode %s' % (repr(episode_number)))
        else:
            return dict.__getitem__(self, episode_number)

    def search(self, term=None, key=None):
        """Search all episodes in season, returns a list of matching Episode instances.

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
    """Hold all episodes instances of a show."""

    def __init__(self, season=None):  # pylint: disable=super-init-not-called
        """The season attribute points to the parent season."""
        self.season = season

    def __repr__(self):
        """Representation of an episode object."""
        seasno = int(self.get(u'seasonnumber', 0))
        epno = int(self.get(u'episodenumber', 0))
        epname = self.get(u'episodename')
        if epname is not None:
            return '<Episode %02dx%02d - %s>' % (seasno, epno, epname)
        else:
            return '<Episode %02dx%02d>' % (seasno, epno)

    def __getattr__(self, key):
        """Get an attribute."""
        if key in self:
            return self[key]
        raise AttributeError

    def __getitem__(self, key):
        """Get an attribute, by passing it as a key."""
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
    """Hold all Actor instances for a show."""

    pass


class Actor(dict):
    """Represent a single actor.

    Should contain:
    id,
    image,
    name,
    role,
    sortorder
    """

    def __repr__(self):
        """Representation of actor name."""
        return '<Actor "%s">' % (self.get('name'))
