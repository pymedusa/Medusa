# coding=utf-8

from __future__ import unicode_literals

import datetime
import json
import os
import re

from requests.compat import unquote_plus
from simpleanidb import REQUEST_HOT
from six import iteritems
from tornroutes import route
from traktor import TraktApi
from .handler import Home
from ..core import PageTemplate
from .... import app, classes, config, db, helpers, logger, ui
from ....black_and_white_list import short_group_names
from ....common import Quality
from ....helper.common import sanitize_filename, try_int
from ....helpers import get_showname_from_indexer
from ....indexers.indexer_api import indexerApi
from ....indexers.indexer_config import INDEXER_TVDBV2
from ....indexers.indexer_exceptions import IndexerException, IndexerUnavailable
from ....show.recommendations.anidb import AnidbPopular
from ....show.recommendations.imdb import ImdbPopular
from ....show.recommendations.trakt import TraktPopular
from ....show.show import Show


@route('/addShows(/?.*)')
class HomeAddShows(Home):
    def __init__(self, *args, **kwargs):
        super(HomeAddShows, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename='addShows.mako')
        return t.render(title='Add Shows', header='Add Shows', topmenu='home', controller='addShows', action='index')

    @staticmethod
    def getIndexerLanguages():
        result = indexerApi().config['valid_languages']

        return json.dumps({'results': result})

    @staticmethod
    def sanitizeFileName(name):
        return sanitize_filename(name)

    @staticmethod
    def searchIndexersForShowName(search_term, lang=None, indexer=None):
        if not lang or lang == 'null':
            lang = app.INDEXER_DEFAULT_LANGUAGE

        search_term = search_term.encode('utf-8')

        search_terms = [search_term]

        # If search term ends with what looks like a year, enclose it in ()
        matches = re.match(r'^(.+ |)([12][0-9]{3})$', search_term)
        if matches:
            search_terms.append('%s(%s)' % (matches.group(1), matches.group(2)))

        for searchTerm in search_terms:
            # If search term begins with an article, let's also search for it without
            matches = re.match(r'^(?:a|an|the) (.+)$', searchTerm, re.I)
            if matches:
                search_terms.append(matches.group(1))

        results = {}
        final_results = []

        # Query Indexers for each search term and build the list of results
        for indexer in indexerApi().indexers if not int(indexer) else [int(indexer)]:
            l_indexer_api_parms = indexerApi(indexer).api_params.copy()
            l_indexer_api_parms['language'] = lang
            l_indexer_api_parms['custom_ui'] = classes.AllShowsListUI
            try:
                t = indexerApi(indexer).indexer(**l_indexer_api_parms)
            except IndexerUnavailable as msg:
                logger.log(u'Could not initialize Indexer {indexer}: {error}'.
                           format(indexer=indexerApi(indexer).name, error=msg))
                continue

            logger.log(u'Searching for Show with searchterm(s): %s on Indexer: %s' % (
                search_terms, indexerApi(indexer).name), logger.DEBUG)
            for searchTerm in search_terms:
                try:
                    indexer_results = t[searchTerm]
                    # add search results
                    results.setdefault(indexer, []).extend(indexer_results)
                except IndexerException as msg:
                    logger.log(u'Error searching for show: {error}'.format(error=msg))

        for i, shows in iteritems(results):
            final_results.extend({(indexerApi(i).name, i, indexerApi(i).config['show_url'], int(show['id']),
                                   show['seriesname'].encode('utf-8'), show['firstaired']) for show in shows})

        lang_id = indexerApi().config['langabbv_to_id'][lang]
        return json.dumps({'results': final_results, 'langid': lang_id})

    def massAddTable(self, rootDir=None):
        t = PageTemplate(rh=self, filename='home_massAddTable.mako')

        if not rootDir:
            return 'No folders selected.'
        elif not isinstance(rootDir, list):
            root_dirs = [rootDir]
        else:
            root_dirs = rootDir

        root_dirs = [unquote_plus(x) for x in root_dirs]

        if app.ROOT_DIRS:
            default_index = int(app.ROOT_DIRS.split('|')[0])
        else:
            default_index = 0

        if len(root_dirs) > default_index:
            tmp = root_dirs[default_index]
            if tmp in root_dirs:
                root_dirs.remove(tmp)
                root_dirs = [tmp] + root_dirs

        dir_list = []

        main_db_con = db.DBConnection()
        for root_dir in root_dirs:
            try:
                file_list = os.listdir(root_dir)
            except Exception as error:
                logger.log('Unable to listdir {path}: {e!r}'.format(path=root_dir, e=error))
                continue

            for cur_file in file_list:

                try:
                    cur_path = os.path.normpath(os.path.join(root_dir, cur_file))
                    if not os.path.isdir(cur_path):
                        continue
                except Exception as error:
                    logger.log('Unable to get current path {path} and {file}: {e!r}'.format(path=root_dir, file=cur_file, e=error))
                    continue

                cur_dir = {
                    'dir': cur_path,
                    'display_dir': '<b>{dir}{sep}</b>{base}'.format(
                        dir=os.path.dirname(cur_path), sep=os.sep, base=os.path.basename(cur_path)),
                }

                # see if the folder is in KODI already
                dir_results = main_db_con.select(
                    b'SELECT indexer_id '
                    b'FROM tv_shows '
                    b'WHERE location = ? LIMIT 1',
                    [cur_path]
                )

                cur_dir['added_already'] = bool(dir_results)

                dir_list.append(cur_dir)

                indexer_id = show_name = indexer = None
                for cur_provider in app.metadata_provider_dict.values():
                    if not (indexer_id and show_name):
                        (indexer_id, show_name, indexer) = cur_provider.retrieveShowMetadata(cur_path)

                        # default to TVDB if indexer was not detected
                        if show_name and not (indexer or indexer_id):
                            (_, idxr, i) = helpers.search_indexer_for_show_id(show_name, indexer, indexer_id)

                            # set indexer and indexer_id from found info
                            if not indexer and idxr:
                                indexer = idxr

                            if not indexer_id and i:
                                indexer_id = i

                cur_dir['existing_info'] = (indexer_id, show_name, indexer)

                if indexer_id and Show.find(app.showList, indexer_id):
                    cur_dir['added_already'] = True
        return t.render(dirList=dir_list)

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
            title='New Show', header='New Show', topmenu='home',
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
        except Exception as e:
            # print traceback.format_exc()
            recommended_shows = None

        return t.render(title="Popular Shows", header="Popular Shows",
                        recommended_shows=recommended_shows, exception=e, groups=[],
                        topmenu="home", enable_anime_options=True, blacklist=[], whitelist=[],
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
                        topmenu="home", enable_anime_options=True, blacklist=[], whitelist=[],
                        controller="addShows", action="recommendedShows", realpage="popularAnime")

    def addShowToBlacklist(self, indexer_id):
        # URL parameters
        data = {'shows': [{'ids': {'tvdb': indexer_id}}]}

        trakt_settings = {'trakt_api_secret': app.TRAKT_API_SECRET,
                          'trakt_api_key': app.TRAKT_API_KEY,
                          'trakt_access_token': app.TRAKT_ACCESS_TOKEN,
                          'trakt_refresh_token': app.TRAKT_REFRESH_TOKEN}

        show_name = get_showname_from_indexer(1, indexer_id)
        try:
            trakt_api = TraktApi(timeout=app.TRAKT_TIMEOUT, ssl_verify=app.SSL_VERIFY, **trakt_settings)
            trakt_api.request('users/{0}/lists/{1}/items'.format
                              (app.TRAKT_USERNAME, app.TRAKT_BLACKLIST_NAME), data, method='POST')
            ui.notifications.message('Success!',
                                     "Added show '{0}' to blacklist".format(show_name))
        except Exception as e:
            ui.notifications.error('Error!',
                                   "Unable to add show '{0}' to blacklist. Check logs.".format(show_name))
            logger.log("Error while adding show '{0}' to trakt blacklist: {1}".format
                       (show_name, e), logger.WARNING)

    def existingShows(self):
        """
        Prints out the page to add existing shows from a root dir
        """
        t = PageTemplate(rh=self, filename='addShows_addExistingShow.mako')
        return t.render(enable_anime_options=False, title='Existing Show',
                        header='Existing Show', topmenu='home',
                        controller='addShows', action='addExistingShow')

    def addShowByID(self, indexer_id, show_name=None, indexer="TVDB", which_series=None,
                    indexer_lang=None, root_dir=None, default_status=None,
                    quality_preset=None, any_qualities=None, best_qualities=None,
                    flatten_folders=None, subtitles=None, full_show_path=None,
                    other_shows=None, skip_show=None, provided_indexer=None,
                    anime=None, scene=None, blacklist=None, whitelist=None,
                    default_status_after=None, default_flatten_folders=None,
                    configure_show_options=False):
        """
        Add's a new show with provided show options by indexer_id.
        Currently only TVDB and IMDB id's supported.
        """
        if indexer != 'TVDB':
            tvdb_id = helpers.get_tvdb_from_id(indexer_id, indexer.upper())
            if not tvdb_id:
                logger.log(u'Unable to to find tvdb ID to add %s' % show_name)
                ui.notifications.error(
                    'Unable to add %s' % show_name,
                    'Could not add %s.  We were unable to locate the tvdb id at this time.' % show_name
                )
                return

            indexer_id = try_int(tvdb_id, None)

        if Show.find(app.showList, int(indexer_id)):
            return

        # Sanitize the paramater allowed_qualities and preferred_qualities. As these would normally be passed as lists
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
            flatten_folders = config.checkbox_to_value(flatten_folders)
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
            flatten_folders = app.FLATTEN_FOLDERS_DEFAULT
            subtitles = app.SUBTITLES_DEFAULT
            anime = app.ANIME_DEFAULT
            scene = app.SCENE_DEFAULT
            default_status_after = app.STATUS_DEFAULT_AFTER

            if app.ROOT_DIRS:
                root_dirs = app.ROOT_DIRS.split('|')
                location = root_dirs[int(root_dirs[0]) + 1]
            else:
                location = None

        if not location:
            logger.log(u'There was an error creating the show, '
                       u'no root directory setting found', logger.WARNING)
            return 'No root directories setup, please go back and add one.'

        show_name = get_showname_from_indexer(1, indexer_id)
        show_dir = None

        # add the show
        app.show_queue_scheduler.action.addShow(INDEXER_TVDBV2, int(indexer_id), show_dir, int(default_status), quality,
                                                flatten_folders, indexer_lang, subtitles, anime, scene, None, blacklist,
                                                whitelist, int(default_status_after), root_dir=location)

        ui.notifications.message('Show added', 'Adding the specified show {0}'.format(show_name))

        # done adding show
        return self.redirect('/home/')

    def addNewShow(self, whichSeries=None, indexerLang=None, rootDir=None, defaultStatus=None,
                   quality_preset=None, allowed_qualities=None, preferred_qualities=None, flatten_folders=None, subtitles=None,
                   fullShowPath=None, other_shows=None, skipShow=None, providedIndexer=None, anime=None,
                   scene=None, blacklist=None, whitelist=None, defaultStatusAfter=None):
        """
        Receive tvdb id, dir, and other options and create a show from them. If extra show dirs are
        provided then it forwards back to newShow, if not it goes to /home.
        """
        provided_indexer = providedIndexer

        indexer_lang = app.INDEXER_DEFAULT_LANGUAGE if not indexerLang else indexerLang

        # grab our list of other dirs if given
        if not other_shows:
            other_shows = []
        elif not isinstance(other_shows, list):
            other_shows = [other_shows]

        def finishAddShow():
            # if there are no extra shows then go home
            if not other_shows:
                return self.redirect('/home/')

            # peel off the next one
            next_show_dir = other_shows[0]
            rest_of_show_dirs = other_shows[1:]

            # go to add the next show
            return self.newShow(next_show_dir, rest_of_show_dirs)

        # if we're skipping then behave accordingly
        if skipShow:
            return finishAddShow()

        # sanity check on our inputs
        if (not rootDir and not fullShowPath) or not whichSeries:
            return 'Missing params, no Indexer ID or folder:{series!r} and {root!r}/{path!r}'.format(
                series=whichSeries, root=rootDir, path=fullShowPath)

        # figure out what show we're adding and where
        series_pieces = whichSeries.split('|')
        if (whichSeries and rootDir) or (whichSeries and fullShowPath and len(series_pieces) > 1):
            if len(series_pieces) < 6:
                logger.log(u'Unable to add show due to show selection. Not enough arguments: %s' % (repr(series_pieces)),
                           logger.ERROR)
                ui.notifications.error('Unknown error. Unable to add show due to problem with show selection.')
                return self.redirect('/addShows/existingShows/')

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
            return self.redirect('/addShows/existingShows/')

        # don't create show dir if config says not to
        if app.ADD_SHOWS_WO_DIR:
            logger.log(u'Skipping initial creation of {path} due to config.ini setting'.format
                       (path=show_dir))
        else:
            dir_exists = helpers.make_dir(show_dir)
            if not dir_exists:
                logger.log(u'Unable to create the folder {path}, can\'t add the show'.format
                           (path=show_dir), logger.ERROR)
                ui.notifications.error('Unable to add show',
                                       'Unable to create the folder {path}, can\'t add the show'.format(path=show_dir))
                # Don't redirect to default page because user wants to see the new show
                return self.redirect('/home/')
            else:
                helpers.chmod_as_parent(show_dir)

        # prepare the inputs for passing along
        scene = config.checkbox_to_value(scene)
        anime = config.checkbox_to_value(anime)
        flatten_folders = config.checkbox_to_value(flatten_folders)
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
                                                flatten_folders, indexer_lang, subtitles, anime,
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
            if '|' in cur_dir:
                split_vals = cur_dir.split('|')
                if len(split_vals) < 3:
                    dirs_only.append(cur_dir)
            if '|' not in cur_dir:
                dirs_only.append(cur_dir)
            else:
                indexer, show_dir, indexer_id, show_name = self.split_extra_show(cur_dir)
                if indexer and show_dir and not indexer_id:
                    dirs_only.append(cur_dir)

                if not show_dir or not indexer_id or not show_name:
                    continue

                indexer_id_given.append((int(indexer), show_dir, int(indexer_id), show_name))

        # if they want me to prompt for settings then I will just carry on to the newShow page
        if prompt_for_settings and shows_to_add:
            return self.newShow(shows_to_add[0], shows_to_add[1:])

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
                    flatten_folders=app.FLATTEN_FOLDERS_DEFAULT,
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
            return self.redirect('/home/')

        # for the remaining shows we need to prompt for each one, so forward this on to the newShow page
        return self.newShow(dirs_only[0], dirs_only[1:])
