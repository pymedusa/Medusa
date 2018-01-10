# coding=utf-8

"""Base class for indexer api's."""

import getpass
import logging
import os
import tempfile
import time
import warnings
from itertools import chain
from operator import itemgetter

from medusa.indexers.indexer_exceptions import (
    IndexerAttributeNotFound,
    IndexerEpisodeNotFound,
    IndexerSeasonNotFound,
    IndexerSeasonUpdatesNotSupported,
    IndexerShowNotFound,
)
from medusa.indexers.indexer_ui import BaseUI, ConsoleUI
from medusa.logger.adapters.style import BraceAdapter

import requests

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


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
            raise ValueError('Invalid value for Cache {0!r} (type was {1})'.format(cache, type(cache)))

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
                raise ValueError('Invalid language {0}, options are: {1}'.format(
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

    def _get_show_data(self, sid, language):
        """Return dummy _get_show_data method."""
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
            log.debug('Series result returned zero')
            IndexerShowNotFound('Show search returned zero results (cannot find show on Indexer)')

        if not isinstance(all_series, list):
            all_series = [all_series]

        if self.config['custom_ui'] is not None:
            log.debug('Using custom UI {0!r}', self.config['custom_ui'])
            custom_ui = self.config['custom_ui']
            ui = custom_ui(config=self.config)
        else:
            if not self.config['interactive']:
                log.debug('Auto-selecting first search result using BaseUI')
                ui = BaseUI(config=self.config)
            else:
                log.debug('Interactively selecting show using ConsoleUI')
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

    def _save_images(self, series_id, images):
        """
        Save the highest rated images for the show.

        :param series_id: The series ID
        :param images: A nested mapping of image info
            images[type][res][id] = image_info_mapping
                type: image type such as `banner`, `poster`, etc
                res: resolution such as `1024x768`, `original`, etc
                id: the image id
        """
        def calculate_pixels(resolution):
            w_x_h = resolution.split('x')
            return int(w_x_h[0]) * int(w_x_h[1])


        def penalize_images(images):
            """Penalize images that have a rating count of less then 5 and images that are not withing the highest
            category of resolution, if there are multiple."""
            images = list(images)  # We don't need to the generator.
            banner_types = set([image['bannertype2'] for image in images])

            # Try to sort the banner types based on quality (might not be needed)
            banner_types = sorted(banner_types, key=calculate_pixels)

            for image in images:
                if image['ratingcount'] is not None and int(image['ratingcount']) < 5:
                    image['rating'] -= 1

                if len(banner_types) > 1:
                    # If the image is not of the highest quality resolution available subtract rating by 1.
                    if banner_types.index(image['bannertype2']) < len(banner_types) - 1:
                        image['rating'] -= 1

            return images

        # Get desired image types from images
        image_types = 'banner', 'fanart', 'poster'

        # Iterate through desired image types
        for img_type in image_types:
            try:
                image_type = images[img_type]
            except KeyError:
                log.debug(
                    u'No {image}s found for {series}', {
                        'image': img_type,
                        'series': series_id,
                    }
                )
                continue

            # Flatten image_type[res][id].values() into list of values
            merged_images = chain.from_iterable(
                resolution.values()
                for resolution in image_type.values()
            )

            # Penalize the images
            merged_images = penalize_images(merged_images)

            # Sort by rating
            images_by_rating = sorted(
                merged_images,
                key=itemgetter('rating'),
                reverse=True,
            )
            log.debug(
                u'Found {x} {image}s for {series}: {results}', {
                    'x': len(images_by_rating),
                    'image': img_type,
                    'series': series_id,
                    'results': u''.join(
                        u'\n\t{rating}: {url}'.format(
                            rating=img['rating'],
                            url=img['_bannerpath'],
                        )
                        for img in images_by_rating
                    )
                }
            )

            if not images_by_rating:
                continue

            # Get the highest rated image
            highest_rated = images_by_rating[0]
            img_url = highest_rated['_bannerpath']
            log.debug(
                u'Selecting highest rated {image} (rating={img[rating]}):'
                u' {img[_bannerpath]}', {
                    'image': img_type,
                    'img': highest_rated,
                }
            )
            log.debug(
                u'{image} details: {img}', {
                    'image': img_type.capitalize(),
                    'img': highest_rated,
                }
            )

            # Save the image
            self._set_show_data(series_id, img_type, img_url)

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
        """Retrieve a list with updated shows.

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
        return '<Show {0} (containing {1} seasons)>'.format(
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
            raise IndexerSeasonNotFound('Could not find season {0!r}'.format(key))
        else:
            # If it's not numeric, it must be an attribute name, which
            # doesn't exist, so attribute error.
            raise IndexerAttributeNotFound('Cannot find attribute {0!r}'.format(key))

    def aired_on(self, date):
        """Search and return a list of episodes with the airdates."""
        ret = self.search(str(date), 'firstaired')
        if len(ret) == 0:
            raise IndexerEpisodeNotFound('Could not find any episodes that aired on {0}'.format(date))
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
        return '<Season instance (containing {0} episodes)>'.format(
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
            raise IndexerEpisodeNotFound('Could not find episode {0!r}'.format(episode_number))
        else:
            return dict.__getitem__(self, episode_number)

    def search(self, term=None, key=None):
        """Search all episodes in season, returns a list of matching Episode instances.

        >>> indexer_api = Tvdb()
        >>> indexer_api['scrubs'][1].search('first day')
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

    def __init__(self, season=None):
        """Initialize class with season attribute that points to the parent season."""
        self.season = season

    def __repr__(self):
        """Representation of an episode object."""
        seasno = int(self.get(u'seasonnumber', 0))
        epno = int(self.get(u'episodenumber', 0))
        epname = self.get(u'episodename')
        if epname:
            return '<Episode {0:0>2}x{1:0>2} - {2}>'.format(seasno, epno, epname)
        else:
            return '<Episode {0:0>2}x{1:0>2}>'.format(seasno, epno)

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
            raise IndexerAttributeNotFound('Cannot find attribute {0!r}'.format(key))

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
        return '<Actor {0!r}>'.format(self.get('name'))
