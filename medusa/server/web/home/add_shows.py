# coding=utf-8

from __future__ import unicode_literals

import datetime
import json
import logging
import os
import re

from medusa import app, config, helpers, ui
from medusa.common import Quality
from medusa.helper.common import sanitize_filename, try_int
from medusa.helpers import get_showname_from_indexer
from medusa.helpers.anidb import short_group_names
from medusa.indexers.indexer_api import indexerApi
from medusa.indexers.indexer_config import INDEXER_TVDBV2
from medusa.logger.adapters.style import BraceAdapter
from medusa.server.web.core import PageTemplate
from medusa.server.web.home.handler import Home
from medusa.show.recommendations.anidb import AnidbPopular
from medusa.show.recommendations.imdb import ImdbPopular
from medusa.show.recommendations.trakt import TraktPopular
from medusa.show.show import Show

from requests import RequestException
from requests.compat import unquote_plus

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

    def newShow(self, show_to_add=None, other_shows=None, search_string=None):
        """
        Display the new show page which collects a tvdb id, folder, and extra options and
        posts them to addNewShow
        """
        t = PageTemplate(rh=self, filename='addShows_newShow.mako')

        indexer, show_dir, indexer_id, show_name = self.split_extra_show(show_to_add)
        use_provided_info = bool(indexer_id and indexer and show_name)

        # use the given show_dir for the indexer search if available
        if not show_dir:
            if search_string:
                default_show_name = search_string
            else:
                default_show_name = ''

        elif not show_name:
            default_show_name = re.sub(r' \(\d{4}\)', '',
                                       os.path.basename(os.path.normpath(show_dir)))
        else:
            default_show_name = show_name

        # carry a list of other dirs if given
        if not other_shows:
            other_shows = []
        elif not isinstance(other_shows, list):
            other_shows = [other_shows]

        provided_indexer_id = int(indexer_id or 0)
        provided_indexer_name = show_name

        provided_indexer = int(indexer or app.INDEXER_DEFAULT)

        return t.render(
            enable_anime_options=True, use_provided_info=use_provided_info,
            default_show_name=default_show_name, other_shows=other_shows,
            provided_show_dir=show_dir, provided_indexer_id=provided_indexer_id,
            provided_indexer_name=provided_indexer_name, provided_indexer=provided_indexer,
            indexers=indexerApi().indexers, whitelist=[], blacklist=[], groups=[],
            controller='addShows', action='newShow'
        )

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

        t = PageTemplate(rh=self, filename="addShows_trendingShows.mako")
        return t.render(title=page_title, header=page_title,
                        enable_anime_options=True, blacklist=[], whitelist=[], groups=[],
                        traktList=traktList, controller="addShows", action="trendingShows",
                        realpage="trendingShows")

    def getTrendingShows(self, traktList=None):
        """
        Display the new show page which collects a tvdb id, folder, and extra options and
        posts them to addNewShow
        """
        e = None
        t = PageTemplate(rh=self, filename="addShows_recommended.mako")
        if traktList is None:
            traktList = ""

        traktList = traktList.lower()

        if traktList == "trending":
            page_url = "shows/trending"
        elif traktList == "popular":
            page_url = "shows/popular"
        elif traktList == "anticipated":
            page_url = "shows/anticipated"
        elif traktList == "collected":
            page_url = "shows/collected"
        elif traktList == "watched":
            page_url = "shows/watched"
        elif traktList == "played":
            page_url = "shows/played"
        elif traktList == "recommended":
            page_url = "recommendations/shows"
        elif traktList == "newshow":
            page_url = 'calendars/all/shows/new/%s/30' % datetime.date.today().strftime("%Y-%m-%d")
        elif traktList == "newseason":
            page_url = 'calendars/all/shows/premieres/%s/30' % datetime.date.today().strftime("%Y-%m-%d")
        else:
            page_url = "shows/anticipated"

        try:
            (trakt_blacklist, recommended_shows, removed_from_medusa) = TraktPopular().fetch_popular_shows(page_url=page_url, trakt_list=traktList)
        except Exception as e:
            # print traceback.format_exc()
            trakt_blacklist = False
            recommended_shows = None
            removed_from_medusa = None

        return t.render(trakt_blacklist=trakt_blacklist, recommended_shows=recommended_shows, removed_from_medusa=removed_from_medusa,
                        exception=e, enable_anime_options=False, blacklist=[], whitelist=[], realpage="getTrendingShows")

    def popularShows(self):
        """
        Fetches data from IMDB to show a list of popular shows.
        """
        t = PageTemplate(rh=self, filename="addShows_recommended.mako")
        e = None

        try:
            recommended_shows = ImdbPopular().fetch_popular_shows()
        except (RequestException, Exception) as e:
            recommended_shows = None

        return t.render(title="Popular Shows", header="Popular Shows",
                        recommended_shows=recommended_shows, exception=e, groups=[],
                        enable_anime_options=True, blacklist=[], whitelist=[],
                        controller="addShows", action="recommendedShows", realpage="popularShows")

    def popularAnime(self, list_type=REQUEST_HOT):
        """
        Fetches list recommeded shows from anidb.info.
        """
        t = PageTemplate(rh=self, filename="addShows_recommended.mako")
        e = None

        try:
            recommended_shows = AnidbPopular().fetch_popular_shows(list_type)
        except Exception as e:
            # print traceback.format_exc()
            recommended_shows = None

        return t.render(title="Popular Anime Shows", header="Popular Anime Shows",
                        recommended_shows=recommended_shows, exception=e, groups=[],
                        enable_anime_options=True, blacklist=[], whitelist=[],
                        controller="addShows", action="recommendedShows", realpage="popularAnime")

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
        Prints out the page to add existing shows from a root dir
        """
        t = PageTemplate(rh=self, filename='addShows_addExistingShow.mako')
        return t.render(enable_anime_options=True, blacklist=[], whitelist=[], groups=[],
                        controller='addShows', action='addExistingShow')

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
                    'Unable to add %s' % show_name,
                    'Could not add %s.  We were unable to locate the tvdb id at this time.' % show_name
                )
                return json_response(
                    result=False,
                    message='Unable to find tvdb ID to add {0}'.format(show=show_name)
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

            quality = Quality.combine_qualities([int(q) for q in any_qualities], [int(q) for q in best_qualities])

            location = root_dir

        else:
            default_status = app.STATUS_DEFAULT
            quality = app.QUALITY_DEFAULT
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
        app.show_queue_scheduler.action.addShow(INDEXER_TVDBV2, int(series_id), show_dir, int(default_status), quality,
                                                season_folders, indexer_lang, subtitles, anime, scene, None, blacklist,
                                                whitelist, int(default_status_after), root_dir=location)

        ui.notifications.message('Show added', 'Adding the specified show {0}'.format(show_name))

        # done adding show
        return json_response(
            message='Adding the specified show {0}'.format(show_name),
            redirect='home'
        )

    def addNewShow(self, whichSeries=None, indexer_lang=None, rootDir=None, defaultStatus=None, quality_preset=None,
                   allowed_qualities=None, preferred_qualities=None, season_folders=None, subtitles=None,
                   fullShowPath=None, other_shows=None, skipShow=None, providedIndexer=None, anime=None,
                   scene=None, blacklist=None, whitelist=None, defaultStatusAfter=None):
        """
        Receive tvdb id, dir, and other options and create a show from them. If extra show dirs are
        provided then it forwards back to newShow, if not it goes to /home.
        """
        provided_indexer = providedIndexer

        indexer_lang = app.INDEXER_DEFAULT_LANGUAGE if not indexer_lang else indexer_lang

        # grab our list of other dirs if given
        if not other_shows:
            other_shows = []
        elif not isinstance(other_shows, list):
            other_shows = [other_shows]

        def finishAddShow():
            # if there are no extra shows then go home
            if not other_shows:
                return json_response(redirect='/home/')

            # go to add the next show
            return json_response(
                redirect='/addShows/newShow/',
                params=[
                    ('show_to_add' if not i else 'other_shows', cur_dir)
                    for i, cur_dir in enumerate(other_shows)
                ]
            )

        # if we're skipping then behave accordingly
        if skipShow:
            return finishAddShow()

        # sanity check on our inputs
        if (not rootDir and not fullShowPath) or not whichSeries:
            error_msg = 'Missing params, no Indexer ID or folder: {series!r} and {root!r}/{path!r}'.format(
                series=whichSeries, root=rootDir, path=fullShowPath)
            log.error(error_msg)
            return json_response(
                result=False,
                message=error_msg,
                redirect='/home/'
            )

        # figure out what show we're adding and where
        series_pieces = whichSeries.split('|')
        if (whichSeries and rootDir) or (whichSeries and fullShowPath and len(series_pieces) > 1):
            if len(series_pieces) < 6:
                log.error('Unable to add show due to show selection. Not enough arguments: {pieces!r}',
                          {'pieces': series_pieces})
                ui.notifications.error('Unknown error. Unable to add show due to problem with show selection.')
                return json_response(
                    result=False,
                    message='Unable to add show due to show selection. Not enough arguments: {0!r}'.format(series_pieces),
                    redirect='/addShows/existingShows/'
                )

            indexer = int(series_pieces[1])
            indexer_id = int(series_pieces[3])
            show_name = series_pieces[4]
        else:
            # if no indexer was provided use the default indexer set in General settings
            if not provided_indexer:
                provided_indexer = app.INDEXER_DEFAULT

            indexer = int(provided_indexer)
            indexer_id = int(whichSeries)
            show_name = os.path.basename(os.path.normpath(fullShowPath))

        # use the whole path if it's given, or else append the show name to the root dir to get the full show path
        if fullShowPath:
            show_dir = os.path.normpath(fullShowPath)
        else:
            show_dir = os.path.join(rootDir, sanitize_filename(show_name))

        # blanket policy - if the dir exists you should have used 'add existing show' numbnuts
        if os.path.isdir(show_dir) and not fullShowPath:
            ui.notifications.error('Unable to add show', 'Folder {path} exists already'.format(path=show_dir))
            return json_response(
                result=False,
                message='Unable to add show: Folder {path} exists already'.format(path=show_dir),
                redirect='/addShows/existingShows/'
            )

        # don't create show dir if config says not to
        if app.ADD_SHOWS_WO_DIR:
            log.info('Skipping initial creation of {path} due to config.ini setting',
                     {'path': show_dir})
        else:
            dir_exists = helpers.make_dir(show_dir)
            if not dir_exists:
                log.error("Unable to create the folder {path}, can't add the show",
                          {'path': show_dir})
                ui.notifications.error('Unable to add show',
                                       'Unable to create the folder {path}, can\'t add the show'.format(path=show_dir))
                # Don't redirect to default page because user wants to see the new show
                return json_response(
                    result=False,
                    message='Unable to add show: Unable to create the folder {path}'.format(path=show_dir),
                    redirect='/home/'
                )
            else:
                helpers.chmod_as_parent(show_dir)

        # prepare the inputs for passing along
        scene = config.checkbox_to_value(scene)
        anime = config.checkbox_to_value(anime)
        season_folders = config.checkbox_to_value(season_folders)
        subtitles = config.checkbox_to_value(subtitles)

        if whitelist:
            whitelist = short_group_names(whitelist)
        if blacklist:
            blacklist = short_group_names(blacklist)

        if not allowed_qualities:
            allowed_qualities = []
        if not preferred_qualities or try_int(quality_preset, None):
            preferred_qualities = []
        if not isinstance(allowed_qualities, list):
            allowed_qualities = [allowed_qualities]
        if not isinstance(preferred_qualities, list):
            preferred_qualities = [preferred_qualities]
        new_quality = Quality.combine_qualities([int(q) for q in allowed_qualities], [int(q) for q in preferred_qualities])

        # add the show
        app.show_queue_scheduler.action.addShow(indexer, indexer_id, show_dir, int(defaultStatus), new_quality,
                                                season_folders, indexer_lang, subtitles, anime,
                                                scene, None, blacklist, whitelist, int(defaultStatusAfter))
        ui.notifications.message('Show added', 'Adding the specified show into {path}'.format(path=show_dir))

        return finishAddShow()

    @staticmethod
    def split_extra_show(extra_show):
        if not extra_show:
            return None, None, None, None
        split_vals = extra_show.split('|')
        if len(split_vals) < 4:
            indexer = split_vals[0]
            show_dir = split_vals[1]
            return indexer, show_dir, None, None
        indexer = split_vals[0]
        show_dir = split_vals[1]
        indexer_id = split_vals[2]
        show_name = '|'.join(split_vals[3:])

        return indexer, show_dir, indexer_id, show_name

    def addExistingShows(self, shows_to_add=None, promptForSettings=None):
        """
        Receives a dir list and add them. Adds the ones with given TVDB IDs first, then forwards
        along to the newShow page.
        """
        prompt_for_settings = promptForSettings

        # grab a list of other shows to add, if provided
        if not shows_to_add:
            shows_to_add = []
        elif not isinstance(shows_to_add, list):
            shows_to_add = [shows_to_add]

        shows_to_add = [unquote_plus(x) for x in shows_to_add]

        prompt_for_settings = config.checkbox_to_value(prompt_for_settings)

        indexer_id_given = []
        dirs_only = []
        # separate all the ones with Indexer IDs
        for cur_dir in shows_to_add:
            if '|' not in cur_dir:
                # 'series_dir'
                dirs_only.append(cur_dir)
            else:
                indexer, show_dir, indexer_id, show_name = self.split_extra_show(cur_dir)
                if indexer and show_dir and not indexer_id:
                    # 'indexer_id|show_dir' or 'indexer_id|show_dir|show_name'
                    dirs_only.append(cur_dir)
                    continue

                if not (show_dir and indexer_id and show_name):
                    # 'indexer_id'
                    continue

                # 'indexer_id|show_dir|series_id|series_name'
                indexer_id_given.append((int(indexer), show_dir, int(indexer_id), show_name))

        # if they want me to prompt for settings then I will just carry on to the newShow page
        if prompt_for_settings and shows_to_add:
            return json_response(
                redirect='/addShows/newShow/',
                params=[
                    ('show_to_add' if not i else 'other_shows', cur_dir)
                    for i, cur_dir in enumerate(shows_to_add)
                ]
            )

        # if they don't want me to prompt for settings then I can just add all the nfo shows now
        num_added = 0
        for cur_show in indexer_id_given:
            indexer, show_dir, indexer_id, show_name = cur_show

            if indexer is not None and indexer_id is not None:
                # add the show
                app.show_queue_scheduler.action.addShow(
                    indexer, indexer_id, show_dir,
                    default_status=app.STATUS_DEFAULT,
                    quality=app.QUALITY_DEFAULT,
                    season_folders=app.SEASON_FOLDERS_DEFAULT,
                    subtitles=app.SUBTITLES_DEFAULT,
                    anime=app.ANIME_DEFAULT,
                    scene=app.SCENE_DEFAULT,
                    default_status_after=app.STATUS_DEFAULT_AFTER
                )
                num_added += 1

        if num_added:
            ui.notifications.message('Shows Added',
                                     'Automatically added {quantity} from their existing metadata files'.format(quantity=num_added))

        # if we're done then go home
        if not dirs_only:
            return json_response(redirect='/home/')

        # for the remaining shows we need to prompt for each one, so forward this on to the newShow page
        return json_response(
            redirect='/addShows/newShow/',
            params=[
                ('show_to_add' if not i else 'other_shows', cur_dir)
                for i, cur_dir in enumerate(dirs_only)
            ]
        )
