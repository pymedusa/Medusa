# coding=utf-8

from __future__ import unicode_literals

import datetime
import json
import logging

from medusa import app, config, helpers, ui
from medusa.common import Quality
from medusa.helper.common import try_int
from medusa.helpers import get_showname_from_indexer
from medusa.helpers.anidb import short_group_names
from medusa.indexers.config import INDEXER_TVDBV2
from medusa.logger.adapters.style import BraceAdapter
from medusa.server.web.core import PageTemplate
from medusa.server.web.home.handler import Home
from medusa.show.recommendations.anidb import AnidbPopular
from medusa.show.recommendations.imdb import ImdbPopular
from medusa.show.recommendations.trakt import TraktPopular
from medusa.show.show import Show

from requests import RequestException

from simpleanidb import REQUEST_HOT

from six import text_type

from tornroutes import route

from traktor import TraktApi

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


def json_response(result=True, message=None, redirect=None, params=None):
    """
    Make a JSON response.
    :param result: Is this response a success or a failure?
    :param message: Response message
    :param redirect: URL to redirect to
    :param params: Query params to append, as a list of tuple(key, value) items
    """
    return json.dumps({
        'result': bool(result),
        'message': text_type(message or ''),
        'redirect': text_type(redirect or '').strip('/'),
        'params': params or [],
    })


def decode_shows(names):
    """Decode show names to UTF-8."""
    return [
        name.decode('utf-8') if not isinstance(name, text_type) else name
        for name in names
    ]


@route('/addShows(/?.*)')
class HomeAddShows(Home):
    def __init__(self, *args, **kwargs):
        super(HomeAddShows, self).__init__(*args, **kwargs)

    def index(self):
        """
        Render the addShows page.

        [Converted to VueRouter]
        """
        t = PageTemplate(rh=self, filename='index.mako')
        return t.render(controller='addShows', action='index')

    def newShow(self, **query_args):
        """
        Render the newShow page.

        [Converted to VueRouter]
        """
        return PageTemplate(rh=self, filename='index.mako').render()

    def trendingShows(self, traktList=None):
        """
        Display the new show page which collects a tvdb id, folder, and extra options and
        posts them to addNewShow
        """
        trakt_list = traktList if traktList else ''

        trakt_list = trakt_list.lower()

        if trakt_list == 'trending':
            page_title = 'Trakt Trending Shows'
        elif trakt_list == 'popular':
            page_title = 'Trakt Popular Shows'
        elif trakt_list == 'anticipated':
            page_title = 'Trakt Most Anticipated Shows'
        elif trakt_list == 'collected':
            page_title = 'Trakt Most Collected Shows'
        elif trakt_list == 'watched':
            page_title = 'Trakt Most Watched Shows'
        elif trakt_list == 'played':
            page_title = 'Trakt Most Played Shows'
        elif trakt_list == 'recommended':
            page_title = 'Trakt Recommended Shows'
        elif trakt_list == 'newshow':
            page_title = 'Trakt New Shows'
        elif trakt_list == 'newseason':
            page_title = 'Trakt Season Premieres'
        else:
            page_title = 'Trakt Most Anticipated Shows'

        t = PageTemplate(rh=self, filename='addShows_trendingShows.mako')
        return t.render(title=page_title, header=page_title,
                        enable_anime_options=True, blacklist=[], whitelist=[], groups=[],
                        traktList=traktList, controller='addShows', action='trendingShows',
                        realpage='trendingShows')

    def getTrendingShows(self, traktList=None):
        """
        Display the new show page which collects a tvdb id, folder, and extra options and
        posts them to addNewShow
        """
        error = None
        t = PageTemplate(rh=self, filename='addShows_recommended.mako')
        trakt_blacklist = False
        recommended_shows = None
        removed_from_medusa = None

        if traktList is None:
            traktList = ''

        traktList = traktList.lower()

        if traktList == 'trending':
            page_url = 'shows/trending'
        elif traktList == 'popular':
            page_url = 'shows/popular'
        elif traktList == 'anticipated':
            page_url = 'shows/anticipated'
        elif traktList == 'collected':
            page_url = 'shows/collected'
        elif traktList == 'watched':
            page_url = 'shows/watched'
        elif traktList == 'played':
            page_url = 'shows/played'
        elif traktList == 'recommended':
            page_url = 'recommendations/shows'
        elif traktList == 'newshow':
            page_url = 'calendars/all/shows/new/%s/30' % datetime.date.today().strftime('%Y-%m-%d')
        elif traktList == 'newseason':
            page_url = 'calendars/all/shows/premieres/%s/30' % datetime.date.today().strftime('%Y-%m-%d')
        else:
            page_url = 'shows/anticipated'

        try:
            (trakt_blacklist, recommended_shows, removed_from_medusa) = TraktPopular().fetch_popular_shows(page_url=page_url, trakt_list=traktList)
        except Exception as e:
            error = e

        return t.render(trakt_blacklist=trakt_blacklist, recommended_shows=recommended_shows, removed_from_medusa=removed_from_medusa,
                        exception=error, enable_anime_options=False, blacklist=[], whitelist=[], realpage='getTrendingShows')

    def popularShows(self):
        """
        Fetches data from IMDB to show a list of popular shows.
        """
        t = PageTemplate(rh=self, filename='addShows_recommended.mako')
        recommended_shows = None
        error = None

        try:
            recommended_shows = ImdbPopular().fetch_popular_shows()
        except (RequestException, Exception) as e:
            error = e

        return t.render(title='Popular Shows', header='Popular Shows',
                        recommended_shows=recommended_shows, exception=error, groups=[],
                        enable_anime_options=True, blacklist=[], whitelist=[],
                        controller='addShows', action='recommendedShows', realpage='popularShows')

    def popularAnime(self, list_type=REQUEST_HOT):
        """
        Fetches list recommeded shows from anidb.info.
        """
        t = PageTemplate(rh=self, filename='addShows_recommended.mako')
        recommended_shows = None
        error = None

        try:
            recommended_shows = AnidbPopular().fetch_popular_shows(list_type)
        except Exception as e:
            error = e

        return t.render(title='Popular Anime Shows', header='Popular Anime Shows',
                        recommended_shows=recommended_shows, exception=error, groups=[],
                        enable_anime_options=True, blacklist=[], whitelist=[],
                        controller='addShows', action='recommendedShows', realpage='popularAnime')

    def addShowToBlacklist(self, seriesid):
        # URL parameters
        data = {'shows': [{'ids': {'tvdb': seriesid}}]}

        trakt_settings = {'trakt_api_secret': app.TRAKT_API_SECRET,
                          'trakt_api_key': app.TRAKT_API_KEY,
                          'trakt_access_token': app.TRAKT_ACCESS_TOKEN,
                          'trakt_refresh_token': app.TRAKT_REFRESH_TOKEN}

        show_name = get_showname_from_indexer(INDEXER_TVDBV2, seriesid)
        try:
            trakt_api = TraktApi(timeout=app.TRAKT_TIMEOUT, ssl_verify=app.SSL_VERIFY, **trakt_settings)
            trakt_api.request('users/{0}/lists/{1}/items'.format
                              (app.TRAKT_USERNAME, app.TRAKT_BLACKLIST_NAME), data, method='POST')
            ui.notifications.message('Success!',
                                     "Added show '{0}' to blacklist".format(show_name))
        except Exception as e:
            ui.notifications.error('Error!',
                                   "Unable to add show '{0}' to blacklist. Check logs.".format(show_name))
            log.warning("Error while adding show '{name}' to trakt blacklist: {error}",
                        {'name': show_name, 'error': e})

    def existingShows(self):
        """
        Render the add existing shows page.

        [Converted to VueRouter]
        """
        t = PageTemplate(rh=self, filename='index.mako')
        return t.render(controller='addShows', action='addExistingShow')

    def addShowByID(self, indexername=None, seriesid=None, show_name=None, which_series=None,
                    indexer_lang=None, root_dir=None, default_status=None,
                    quality_preset=None, any_qualities=None, best_qualities=None,
                    season_folders=None, subtitles=None, full_show_path=None,
                    other_shows=None, skip_show=None, provided_indexer=None,
                    anime=None, scene=None, blacklist=None, whitelist=None,
                    default_status_after=None, configure_show_options=False):
        """
        Add's a new show with provided show options by indexer_id.
        Currently only TVDB and IMDB id's supported.
        """
        series_id = seriesid
        if indexername != 'tvdb':
            series_id = helpers.get_tvdb_from_id(seriesid, indexername.upper())
            if not series_id:
                log.info('Unable to find tvdb ID to add {name}', {'name': show_name})
                ui.notifications.error(
                    'Unable to add {0}'.format(show_name),
                    'Could not add {0}. We were unable to locate the tvdb id at this time.'.format(show_name)
                )
                return json_response(
                    result=False,
                    message='Unable to find tvdb ID to add {show}'.format(show=show_name)
                )

        if Show.find_by_id(app.showList, INDEXER_TVDBV2, series_id):
            return json_response(
                result=False,
                message='Show already exists'
            )

        # Sanitize the parameter allowed_qualities and preferred_qualities. As these would normally be passed as lists
        if any_qualities:
            any_qualities = any_qualities.split(',')
        else:
            any_qualities = []

        if best_qualities:
            best_qualities = best_qualities.split(',')
        else:
            best_qualities = []

        # If configure_show_options is enabled let's use the provided settings
        configure_show_options = config.checkbox_to_value(configure_show_options)

        if configure_show_options:
            # prepare the inputs for passing along
            scene = config.checkbox_to_value(scene)
            anime = config.checkbox_to_value(anime)
            season_folders = config.checkbox_to_value(season_folders)
            subtitles = config.checkbox_to_value(subtitles)

            if whitelist:
                whitelist = short_group_names(whitelist)
            if blacklist:
                blacklist = short_group_names(blacklist)

            if not any_qualities:
                any_qualities = []

            if not best_qualities or try_int(quality_preset, None):
                best_qualities = []

            if not isinstance(any_qualities, list):
                any_qualities = [any_qualities]

            if not isinstance(best_qualities, list):
                best_qualities = [best_qualities]

            quality = {'allowed': any_qualities, 'preferred': best_qualities}

            location = root_dir

        else:
            default_status = app.STATUS_DEFAULT
            allowed, preferred = Quality.split_quality(int(app.QUALITY_DEFAULT))
            quality = {'allowed': allowed, 'preferred': preferred}
            season_folders = app.SEASON_FOLDERS_DEFAULT
            subtitles = app.SUBTITLES_DEFAULT
            anime = app.ANIME_DEFAULT
            scene = app.SCENE_DEFAULT
            default_status_after = app.STATUS_DEFAULT_AFTER

            if app.ROOT_DIRS:
                root_dirs = app.ROOT_DIRS
                location = root_dirs[int(root_dirs[0]) + 1]
            else:
                location = None

        if not location:
            log.warning('There was an error creating the show, no root directory setting found')
            return json_response(
                result=False,
                message='No root directories set up, please go back and add one.'
            )

        show_name = get_showname_from_indexer(INDEXER_TVDBV2, series_id)
        show_dir = None

        # add the show
        app.show_queue_scheduler.action.addShow(INDEXER_TVDBV2, int(series_id), show_dir, default_status=int(default_status), quality=quality,
                                                season_folders=season_folders, lang=indexer_lang, subtitles=subtitles, anime=anime, scene=scene,
                                                paused=None, blacklist=blacklist, whitelist=whitelist,
                                                default_status_after=int(default_status_after), root_dir=location)

        ui.notifications.message('Show added', 'Adding the specified show {0}'.format(show_name))

        # done adding show
        return json_response(
            message='Adding the specified show {0}'.format(show_name),
            redirect='home'
        )
