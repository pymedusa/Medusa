# coding=utf-8

from __future__ import unicode_literals

import datetime
import json
import os
import re
from builtins import str

from medusa import (
    app,
    db,
    helpers,
    image_cache,
    logger,
    network_timezones,
    sbdatetime,
    subtitles,
    ui,
)
from medusa.common import (
    DOWNLOADED,
    Overview,
    SNATCHED,
    SNATCHED_BEST,
    SNATCHED_PROPER,
)
from medusa.helper.common import (
    episode_num,
    try_int,
)
from medusa.helper.exceptions import (
    CantRefreshShowException,
    CantUpdateShowException,
)
from medusa.helpers import is_media_file
from medusa.indexers.utils import indexer_id_to_name, indexer_name_to_id
from medusa.network_timezones import app_timezone
from medusa.post_processor import PostProcessor
from medusa.server.web.core import PageTemplate, WebRoot
from medusa.server.web.home import Home
from medusa.show.show import Show
from medusa.tv import Episode, Series
from medusa.tv.series import SeriesIdentifier

from tornroutes import route


@route('/manage(/?.*)')
class Manage(Home, WebRoot):
    def __init__(self, *args, **kwargs):
        super(Manage, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename='manage.mako')
        return t.render(controller='manage', action='index')

    @staticmethod
    def showEpisodeStatuses(indexername, seriesid, whichStatus):
        status_list = [int(whichStatus)]
        if status_list[0] == SNATCHED:
            status_list = [SNATCHED, SNATCHED_PROPER, SNATCHED_BEST]

        main_db_con = db.DBConnection()
        cur_show_results = main_db_con.select(
            b'SELECT season, episode, name '
            b'FROM tv_episodes '
            b'WHERE indexer = ? AND showid = ? '
            b'AND season != 0 AND status IN ({statuses})'.format(
                statuses=','.join(['?'] * len(status_list))),
            [int(indexer_name_to_id(indexername)), int(seriesid)] + status_list
        )

        result = {}
        for cur_result in cur_show_results:
            cur_season = int(cur_result[b'season'])
            cur_episode = int(cur_result[b'episode'])

            if cur_season not in result:
                result[cur_season] = {}

            result[cur_season][cur_episode] = cur_result[b'name']

        return json.dumps(result)

    def episodeStatuses(self, whichStatus=None):
        if whichStatus:
            status_list = [int(whichStatus)]
            if status_list[0] == SNATCHED:
                status_list = [SNATCHED, SNATCHED_PROPER, SNATCHED_BEST]
        else:
            status_list = []

        t = PageTemplate(rh=self, filename='manage_episodeStatuses.mako')

        # if we have no status then this is as far as we need to go
        if not status_list:
            return t.render(
                show_names=None, whichStatus=whichStatus,
                ep_counts=None, sorted_show_ids=None,
                controller='manage', action='episodeStatuses')

        main_db_con = db.DBConnection()
        status_results = main_db_con.select(
            b'SELECT show_name, tv_shows.indexer, tv_shows.show_id, tv_shows.indexer_id AS indexer_id '
            b'FROM tv_episodes, tv_shows '
            b'WHERE season != 0 '
            b'AND tv_episodes.showid = tv_shows.indexer_id '
            b'AND tv_episodes.indexer = tv_shows.indexer '
            b'AND tv_episodes.status IN ({statuses}) '
            b'ORDER BY show_name'.format(statuses=','.join(['?'] * len(status_list))),
            status_list
        )

        ep_counts = {}
        show_names = {}
        sorted_show_ids = []

        for cur_status_result in status_results:
            cur_indexer = int(cur_status_result[b'indexer'])
            cur_series_id = int(cur_status_result[b'indexer_id'])
            if (cur_indexer, cur_series_id) not in ep_counts:
                ep_counts[(cur_indexer, cur_series_id)] = 1
            else:
                ep_counts[(cur_indexer, cur_series_id)] += 1

            show_names[(cur_indexer, cur_series_id)] = cur_status_result[b'show_name']
            if (cur_indexer, cur_series_id) not in sorted_show_ids:
                sorted_show_ids.append((cur_indexer, cur_series_id))

        return t.render(
            title='Episode Overview', header='Episode Overview',
            whichStatus=whichStatus,
            show_names=show_names, ep_counts=ep_counts, sorted_show_ids=sorted_show_ids,
            controller='manage', action='episodeStatuses')

    def changeEpisodeStatuses(self, oldStatus, newStatus, *args, **kwargs):
        status_list = [int(oldStatus)]
        if status_list[0] == SNATCHED:
            status_list = [SNATCHED, SNATCHED_PROPER, SNATCHED_BEST]

        to_change = {}

        # make a list of all shows and their associated args
        for arg in kwargs:
            indexer_id, series_id, what = arg.split('-')

            # we don't care about unchecked checkboxes
            if kwargs[arg] != 'on':
                continue

            if (indexer_id, series_id) not in to_change:
                to_change[(indexer_id, series_id)] = []

            to_change[(indexer_id, series_id)].append(what)

        main_db_con = db.DBConnection()
        for cur_indexer_id, cur_series_id in to_change:

            # get a list of all the eps we want to change if they just said 'all'
            if 'all' in to_change[(cur_indexer_id, cur_series_id)]:
                all_eps_results = main_db_con.select(
                    b'SELECT season, episode '
                    b'FROM tv_episodes '
                    b'WHERE status IN ({statuses}) '
                    b'AND season != 0 '
                    b'AND indexer = ? '
                    b'AND showid = ?'.format(statuses=','.join(['?'] * len(status_list))),
                    status_list + [cur_indexer_id, cur_series_id]
                )

                all_eps = ['{season}x{episode}'.format(season=x[b'season'], episode=x[b'episode']) for x in all_eps_results]
                to_change[cur_indexer_id, cur_series_id] = all_eps

            self.setStatus(indexer_id_to_name(int(cur_indexer_id)), cur_series_id, '|'.join(to_change[(cur_indexer_id, cur_series_id)]), newStatus, direct=True)

        return self.redirect('/manage/episodeStatuses/')

    @staticmethod
    def showSubtitleMissed(indexer, seriesid, whichSubs):
        main_db_con = db.DBConnection()
        cur_show_results = main_db_con.select(
            b'SELECT season, episode, name, subtitles '
            b'FROM tv_episodes '
            b'WHERE indexer = ? '
            b'AND showid = ? '
            b'AND season != 0 '
            b'AND status = ? '
            b"AND location != ''",
            [int(indexer), int(seriesid), DOWNLOADED]
        )

        result = {}
        for cur_result in cur_show_results:
            if whichSubs == 'all':
                if not frozenset(subtitles.wanted_languages()).difference(cur_result[b'subtitles'].split(',')):
                    continue
            elif whichSubs in cur_result[b'subtitles']:
                continue

            cur_season = int(cur_result[b'season'])
            cur_episode = int(cur_result[b'episode'])

            if cur_season not in result:
                result[cur_season] = {}

            if cur_episode not in result[cur_season]:
                result[cur_season][cur_episode] = {}

            result[cur_season][cur_episode]['name'] = cur_result[b'name']
            result[cur_season][cur_episode]['subtitles'] = cur_result[b'subtitles']

        return json.dumps(result)

    def subtitleMissed(self, whichSubs=None):
        t = PageTemplate(rh=self, filename='manage_subtitleMissed.mako')

        if not whichSubs:
            return t.render(whichSubs=whichSubs,
                            show_names=None, ep_counts=None, sorted_show_ids=None,
                            controller='manage', action='subtitleMissed')

        main_db_con = db.DBConnection()
        status_results = main_db_con.select(
            b'SELECT show_name, tv_shows.show_id, tv_shows.indexer, '
            b'tv_shows.indexer_id as indexer_id, tv_episodes.subtitles subtitles '
            b'FROM tv_episodes, tv_shows '
            b'WHERE tv_shows.subtitles = 1 '
            b'AND tv_episodes.status = ? '
            b'AND tv_episodes.season != 0 '
            b"AND tv_episodes.location != '' "
            b'AND tv_episodes.showid = tv_shows.indexer_id '
            b'AND tv_episodes.indexer = tv_shows.indexer '
            b'ORDER BY show_name',
            [DOWNLOADED]
        )

        ep_counts = {}
        show_names = {}
        sorted_show_ids = []
        for cur_status_result in status_results:
            if whichSubs == 'all':
                if not frozenset(subtitles.wanted_languages()).difference(cur_status_result[b'subtitles'].split(',')):
                    continue
            elif whichSubs in cur_status_result[b'subtitles']:
                continue

            # FIXME: This will cause multi-indexer results where series_id overlaps for different indexers.
            # Fix by using tv_shows.show_id in stead.

            cur_indexer_id = int(cur_status_result[b'indexer'])
            cur_series_id = int(cur_status_result[b'indexer_id'])
            if (cur_indexer_id, cur_series_id) not in ep_counts:
                ep_counts[(cur_indexer_id, cur_series_id)] = 1
            else:
                ep_counts[(cur_indexer_id, cur_series_id)] += 1

            show_names[(cur_indexer_id, cur_series_id)] = cur_status_result[b'show_name']
            if (cur_indexer_id, cur_series_id) not in sorted_show_ids:
                sorted_show_ids.append((cur_indexer_id, cur_series_id))

        return t.render(whichSubs=whichSubs, show_names=show_names, ep_counts=ep_counts, sorted_show_ids=sorted_show_ids,
                        title='Missing Subtitles', header='Missing Subtitles',
                        controller='manage', action='subtitleMissed')

    def downloadSubtitleMissed(self, *args, **kwargs):
        to_download = {}

        # make a list of all shows and their associated args
        for arg in kwargs:
            indexer_id, series_id, what = arg.split('-')

            # we don't care about unchecked checkboxes
            if kwargs[arg] != 'on':
                continue

            if (indexer_id, series_id) not in to_download:
                to_download[(indexer_id, series_id)] = []

            to_download[(indexer_id, series_id)].append(what)

        for cur_indexer_id, cur_series_id in to_download:
            # get a list of all the eps we want to download subtitles if they just said 'all'
            if 'all' in to_download[(cur_indexer_id, cur_series_id)]:
                main_db_con = db.DBConnection()
                all_eps_results = main_db_con.select(
                    b'SELECT season, episode '
                    b'FROM tv_episodes '
                    b'WHERE status = ? '
                    b'AND season != 0 '
                    b'AND indexer = ? '
                    b'AND showid = ? '
                    b"AND location != ''",
                    [DOWNLOADED, cur_indexer_id, cur_series_id]
                )
                to_download[(cur_indexer_id, cur_series_id)] = [str(x[b'season']) + 'x' + str(x[b'episode']) for x in all_eps_results]

            for epResult in to_download[(cur_indexer_id, cur_series_id)]:
                season, episode = epResult.split('x')

                series_obj = Show.find_by_id(app.showList, cur_indexer_id, cur_series_id)
                series_obj.get_episode(season, episode).download_subtitles()

        return self.redirect('/manage/subtitleMissed/')

    def subtitleMissedPP(self):
        t = PageTemplate(rh=self, filename='manage_subtitleMissedPP.mako')
        app.RELEASES_IN_PP = []
        for root, _, files in os.walk(app.TV_DOWNLOAD_DIR, topdown=False):
            # Skip folders that are being used for unpacking
            if u'_UNPACK' in root.upper():
                continue
            for filename in sorted(files):
                if not is_media_file(filename):
                    continue

                video_path = os.path.join(root, filename)
                video_date = datetime.datetime.fromtimestamp(os.stat(video_path).st_ctime)
                video_age = datetime.datetime.today() - video_date

                tv_episode = Episode.from_filepath(video_path)

                if not tv_episode:
                    logger.log(u"Filename '{0}' cannot be parsed to an episode".format(filename), logger.DEBUG)
                    continue

                ep_status = tv_episode.status
                if ep_status in (SNATCHED, SNATCHED_PROPER, SNATCHED_BEST):
                    status = 'snatched'
                elif ep_status in DOWNLOADED:
                    status = 'downloaded'
                else:
                    continue

                if not tv_episode.series.subtitles:
                    continue

                related_files = PostProcessor(video_path).list_associated_files(video_path, subtitles_only=True)
                if related_files:
                    continue

                age_hours = divmod(video_age.seconds, 3600)[0]
                age_minutes = divmod(video_age.seconds, 60)[0]
                if video_age.days > 0:
                    age_unit = 'd'
                    age_value = video_age.days
                elif age_hours > 0:
                    age_unit = 'h'
                    age_value = age_hours
                else:
                    age_unit = 'm'
                    age_value = age_minutes

                app.RELEASES_IN_PP.append({'release': video_path, 'seriesid': tv_episode.series.indexerid,
                                           'show_name': tv_episode.series.name, 'season': tv_episode.season,
                                           'episode': tv_episode.episode, 'status': status, 'age': age_value,
                                           'age_unit': age_unit, 'date': video_date,
                                           'indexername': tv_episode.series.indexer_name})

        return t.render(releases_in_pp=app.RELEASES_IN_PP,
                        controller='manage', action='subtitleMissedPP')

    def backlogShow(self, indexername, seriesid):
        indexer_id = indexer_name_to_id(indexername)
        series_obj = Show.find_by_id(app.showList, indexer_id, seriesid)

        if series_obj:
            app.backlog_search_scheduler.action.search_backlog([series_obj])

        return self.redirect('/manage/backlogOverview/')

    def backlogOverview(self):
        t = PageTemplate(rh=self, filename='manage_backlogOverview.mako')

        show_counts = {}
        show_cats = {}
        show_sql_results = {}

        backlog_periods = {
            'all': None,
            'one_day': datetime.timedelta(days=1),
            'three_days': datetime.timedelta(days=3),
            'one_week': datetime.timedelta(days=7),
            'one_month': datetime.timedelta(days=30),
        }
        backlog_period = backlog_periods.get(app.BACKLOG_PERIOD)

        backlog_status = {
            'all': [Overview.QUAL, Overview.WANTED],
            'quality': [Overview.QUAL],
            'wanted': [Overview.WANTED]
        }
        selected_backlog_status = backlog_status.get(app.BACKLOG_STATUS)

        main_db_con = db.DBConnection()
        for cur_show in app.showList:

            if cur_show.paused:
                continue

            ep_counts = {
                Overview.WANTED: 0,
                Overview.QUAL: 0,
            }
            ep_cats = {}

            sql_results = main_db_con.select(
                b"""
                SELECT e.status, e.quality, e.season,
                e.episode, e.name, e.airdate, e.manually_searched
                FROM tv_episodes as e
                WHERE e.season IS NOT NULL AND
                      e.indexer = ? AND e.showid = ?
                ORDER BY e.season DESC, e.episode DESC
                """,
                [cur_show.indexer, cur_show.series_id]
            )
            filtered_episodes = []
            backlogged_episodes = [dict(row) for row in sql_results]
            for cur_result in backlogged_episodes:
                cur_ep_cat = cur_show.get_overview(cur_result[b'status'], cur_result[b'quality'], backlog_mode=True,
                                                   manually_searched=cur_result[b'manually_searched'])
                if cur_ep_cat:
                    if cur_ep_cat in selected_backlog_status and cur_result[b'airdate'] != 1:
                        air_date = datetime.datetime.fromordinal(cur_result[b'airdate'])
                        if air_date.year >= 1970 or cur_show.network:
                            air_date = sbdatetime.sbdatetime.convert_to_setting(
                                network_timezones.parse_date_time(cur_result[b'airdate'],
                                                                  cur_show.airs,
                                                                  cur_show.network))
                            if backlog_period and air_date < datetime.datetime.now(app_timezone) - backlog_period:
                                continue
                        else:
                            air_date = None
                        episode_string = u'{ep}'.format(ep=(episode_num(cur_result[b'season'],
                                                                        cur_result[b'episode']) or
                                                            episode_num(cur_result[b'season'],
                                                                        cur_result[b'episode'],
                                                                        numbering='absolute')))
                        ep_cats[episode_string] = cur_ep_cat
                        ep_counts[cur_ep_cat] += 1
                        cur_result[b'airdate'] = air_date
                        cur_result[b'episode_string'] = episode_string
                        filtered_episodes.append(cur_result)

            show_counts[(cur_show.indexer, cur_show.series_id)] = ep_counts
            show_cats[(cur_show.indexer, cur_show.series_id)] = ep_cats
            show_sql_results[(cur_show.indexer, cur_show.series_id)] = filtered_episodes

        return t.render(
            showCounts=show_counts, showCats=show_cats,
            showSQLResults=show_sql_results, controller='manage',
            action='backlogOverview')

    def massEdit(self, toEdit=None):
        t = PageTemplate(rh=self, filename='manage_massEdit.mako')

        if not toEdit:
            return self.redirect('/manage/')

        series_slugs = toEdit.split('|')
        show_list = []
        show_names = []
        for slug in series_slugs:
            identifier = SeriesIdentifier.from_slug(slug)
            series_obj = Series.find_by_identifier(identifier)

            if series_obj:
                show_list.append(series_obj)
                show_names.append(series_obj.name)

        season_folders_all_same = True
        last_season_folders = None

        paused_all_same = True
        last_paused = None

        default_ep_status_all_same = True
        last_default_ep_status = None

        anime_all_same = True
        last_anime = None

        sports_all_same = True
        last_sports = None

        quality_all_same = True
        last_quality = None

        subtitles_all_same = True
        last_subtitles = None

        scene_all_same = True
        last_scene = None

        air_by_date_all_same = True
        last_air_by_date = None

        dvd_order_all_same = True
        last_dvd_order = None

        root_dir_list = []

        for cur_show in show_list:

            cur_root_dir = os.path.dirname(cur_show._location)  # pylint: disable=protected-access
            if cur_root_dir not in root_dir_list:
                root_dir_list.append(cur_root_dir)

            # if we know they're not all the same then no point even bothering
            if paused_all_same:
                # if we had a value already and this value is different then they're not all the same
                if last_paused not in (None, cur_show.paused):
                    paused_all_same = False
                else:
                    last_paused = cur_show.paused

            if default_ep_status_all_same:
                if last_default_ep_status not in (None, cur_show.default_ep_status):
                    default_ep_status_all_same = False
                else:
                    last_default_ep_status = cur_show.default_ep_status

            if anime_all_same:
                # if we had a value already and this value is different then they're not all the same
                if last_anime not in (None, cur_show.is_anime):
                    anime_all_same = False
                else:
                    last_anime = cur_show.anime

            if season_folders_all_same:
                if last_season_folders not in (None, cur_show.season_folders):
                    season_folders_all_same = False
                else:
                    last_season_folders = cur_show.season_folders

            if quality_all_same:
                if last_quality not in (None, cur_show.quality):
                    quality_all_same = False
                else:
                    last_quality = cur_show.quality

            if subtitles_all_same:
                if last_subtitles not in (None, cur_show.subtitles):
                    subtitles_all_same = False
                else:
                    last_subtitles = cur_show.subtitles

            if scene_all_same:
                if last_scene not in (None, cur_show.scene):
                    scene_all_same = False
                else:
                    last_scene = cur_show.scene

            if sports_all_same:
                if last_sports not in (None, cur_show.sports):
                    sports_all_same = False
                else:
                    last_sports = cur_show.sports

            if air_by_date_all_same:
                if last_air_by_date not in (None, cur_show.air_by_date):
                    air_by_date_all_same = False
                else:
                    last_air_by_date = cur_show.air_by_date

            if dvd_order_all_same:
                if last_dvd_order not in (None, cur_show.dvd_order):
                    dvd_order_all_same = False
                else:
                    last_dvd_order = cur_show.dvd_order

        default_ep_status_value = last_default_ep_status if default_ep_status_all_same else None
        paused_value = last_paused if paused_all_same else None
        anime_value = last_anime if anime_all_same else None
        season_folders_value = last_season_folders if season_folders_all_same else None
        quality_value = last_quality if quality_all_same else None
        subtitles_value = last_subtitles if subtitles_all_same else None
        scene_value = last_scene if scene_all_same else None
        sports_value = last_sports if sports_all_same else None
        air_by_date_value = last_air_by_date if air_by_date_all_same else None
        dvd_order_value = last_dvd_order if dvd_order_all_same else None
        root_dir_list = root_dir_list

        return t.render(showList=toEdit, showNames=show_names, default_ep_status_value=default_ep_status_value, dvd_order_value=dvd_order_value,
                        paused_value=paused_value, anime_value=anime_value, season_folders_value=season_folders_value,
                        quality_value=quality_value, subtitles_value=subtitles_value, scene_value=scene_value, sports_value=sports_value,
                        air_by_date_value=air_by_date_value, root_dir_list=root_dir_list)

    def massEditSubmit(self, paused=None, default_ep_status=None, dvd_order=None,
                       anime=None, sports=None, scene=None, season_folders=None, quality_preset=None,
                       subtitles=None, air_by_date=None, allowed_qualities=None, preferred_qualities=None, toEdit=None, *args,
                       **kwargs):
        allowed_qualities = allowed_qualities or []
        preferred_qualities = preferred_qualities or []

        dir_map = {}
        for cur_arg in kwargs:
            if not cur_arg.startswith('orig_root_dir_'):
                continue
            which_index = cur_arg.replace('orig_root_dir_', '')
            end_dir = kwargs['new_root_dir_{index}'.format(index=which_index)]
            dir_map[kwargs[cur_arg]] = end_dir

        series_slugs = toEdit.split('|') if toEdit else []
        errors = 0
        for series_slug in series_slugs:
            identifier = SeriesIdentifier.from_slug(series_slug)
            series_obj = Series.find_by_identifier(identifier)

            if not series_obj:
                continue

            cur_root_dir = os.path.dirname(series_obj._location)
            cur_show_dir = os.path.basename(series_obj._location)
            if cur_root_dir in dir_map and cur_root_dir != dir_map[cur_root_dir]:
                new_show_dir = os.path.join(dir_map[cur_root_dir], cur_show_dir)
                logger.log(u'For show {show.name} changing dir from {show._location} to {location}'.format
                           (show=series_obj, location=new_show_dir))
            else:
                new_show_dir = series_obj._location

            if paused == 'keep':
                new_paused = series_obj.paused
            else:
                new_paused = True if paused == 'enable' else False
            new_paused = 'on' if new_paused else 'off'

            if default_ep_status == 'keep':
                new_default_ep_status = series_obj.default_ep_status
            else:
                new_default_ep_status = default_ep_status

            if anime == 'keep':
                new_anime = series_obj.anime
            else:
                new_anime = True if anime == 'enable' else False
            new_anime = 'on' if new_anime else 'off'

            if sports == 'keep':
                new_sports = series_obj.sports
            else:
                new_sports = True if sports == 'enable' else False
            new_sports = 'on' if new_sports else 'off'

            if scene == 'keep':
                new_scene = series_obj.is_scene
            else:
                new_scene = True if scene == 'enable' else False
            new_scene = 'on' if new_scene else 'off'

            if air_by_date == 'keep':
                new_air_by_date = series_obj.air_by_date
            else:
                new_air_by_date = True if air_by_date == 'enable' else False
            new_air_by_date = 'on' if new_air_by_date else 'off'

            if dvd_order == 'keep':
                new_dvd_order = series_obj.dvd_order
            else:
                new_dvd_order = True if dvd_order == 'enable' else False
            new_dvd_order = 'on' if new_dvd_order else 'off'

            if season_folders == 'keep':
                new_season_folders = series_obj.season_folders
            else:
                new_season_folders = True if season_folders == 'enable' else False
            new_season_folders = 'on' if new_season_folders else 'off'

            if subtitles == 'keep':
                new_subtitles = series_obj.subtitles
            else:
                new_subtitles = True if subtitles == 'enable' else False

            new_subtitles = 'on' if new_subtitles else 'off'

            if quality_preset == 'keep':
                allowed_qualities, preferred_qualities = series_obj.current_qualities
            elif try_int(quality_preset, None):
                preferred_qualities = []

            exceptions_list = []

            errors += self.editShow(identifier.indexer.slug, identifier.id, new_show_dir, allowed_qualities,
                                    preferred_qualities, exceptions_list,
                                    defaultEpStatus=new_default_ep_status,
                                    season_folders=new_season_folders,
                                    paused=new_paused, sports=new_sports, dvd_order=new_dvd_order,
                                    subtitles=new_subtitles, anime=new_anime,
                                    scene=new_scene, air_by_date=new_air_by_date,
                                    directCall=True)

        if errors:
            ui.notifications.error('Errors', '{num} error{s} while saving changes. Please check logs'.format
                                   (num=errors, s='s' if errors > 1 else ''))

        return self.redirect('/manage/')

    def massUpdate(self, toUpdate=None, toRefresh=None, toRename=None, toDelete=None, toRemove=None, toMetadata=None,
                   toSubtitle=None, toImageUpdate=None):
        to_update = toUpdate.split('|') if toUpdate else []
        to_refresh = toRefresh.split('|') if toRefresh else []
        to_rename = toRename.split('|') if toRename else []
        to_subtitle = toSubtitle.split('|') if toSubtitle else []
        to_delete = toDelete.split('|') if toDelete else []
        to_remove = toRemove.split('|') if toRemove else []
        to_metadata = toMetadata.split('|') if toMetadata else []
        to_image_update = toImageUpdate.split('|') if toImageUpdate else []

        errors = []
        refreshes = []
        updates = []
        renames = []
        subtitles = []
        image_update = []

        for slug in set(to_update + to_refresh + to_rename + to_subtitle + to_delete + to_remove + to_metadata + to_image_update):
            identifier = SeriesIdentifier.from_slug(slug)
            series_obj = Series.find_by_identifier(identifier)

            if not series_obj:
                continue

            if slug in to_delete + to_remove:
                app.show_queue_scheduler.action.removeShow(series_obj, slug in to_delete)
                continue  # don't do anything else if it's being deleted or removed

            if slug in to_update:
                try:
                    app.show_queue_scheduler.action.updateShow(series_obj)
                    updates.append(series_obj.name)
                except CantUpdateShowException as msg:
                    errors.append('Unable to update show: {error}'.format(error=msg))

            elif slug in to_refresh:  # don't bother refreshing shows that were updated
                try:
                    app.show_queue_scheduler.action.refreshShow(series_obj)
                    refreshes.append(series_obj.name)
                except CantRefreshShowException as msg:
                    errors.append('Unable to refresh show {show.name}: {error}'.format
                                  (show=series_obj, error=msg))

            if slug in to_rename:
                app.show_queue_scheduler.action.renameShowEpisodes(series_obj)
                renames.append(series_obj.name)

            if slug in to_subtitle:
                app.show_queue_scheduler.action.download_subtitles(series_obj)
                subtitles.append(series_obj.name)

            if slug in to_image_update:
                image_cache.replace_images(series_obj)

        if errors:
            ui.notifications.error('Errors encountered',
                                   '<br />\n'.join(errors))

        message = ''
        if updates:
            message += '\nUpdates: {0}'.format(len(updates))
        if refreshes:
            message += '\nRefreshes: {0}'.format(len(refreshes))
        if renames:
            message += '\nRenames: {0}'.format(len(renames))
        if subtitles:
            message += '\nSubtitles: {0}'.format(len(subtitles))
        if image_update:
            message += '\nImage updates: {0}'.format(len(image_update))

        if message:
            ui.notifications.message('Queued actions:', message)

        return self.redirect('/manage/')

    def manageTorrents(self):
        if re.search('localhost', app.TORRENT_HOST):

            if app.LOCALHOST_IP == '':
                webui_url = re.sub('localhost', helpers.get_lan_ip(), app.TORRENT_HOST)
            else:
                webui_url = re.sub('localhost', app.LOCALHOST_IP, app.TORRENT_HOST)
        else:
            webui_url = app.TORRENT_HOST

        if app.TORRENT_METHOD == 'utorrent':
            webui_url = '/'.join(s.strip('/') for s in (webui_url, 'gui/'))
        if app.TORRENT_METHOD == 'download_station':
            if helpers.check_url('{url}download/'.format(url=webui_url)):
                webui_url += 'download/'
            else:
                webui_url = 'https://github.com/pymedusa/Medusa/wiki/Download-Station'

        return self.redirect(webui_url)

    def failedDownloads(self, limit=100, toRemove=None):
        failed_db_con = db.DBConnection('failed.db')

        if int(limit):
            sql_results = failed_db_con.select(
                b'SELECT * '
                b'FROM failed '
                b'LIMIT ?',
                [limit]
            )
        else:
            sql_results = failed_db_con.select(
                b'SELECT * '
                b'FROM failed'
            )
        sql_results = sql_results[::-1]

        to_remove = toRemove.split('|') if toRemove is not None else []
        for release in to_remove:
            failed_db_con.action(
                b'DELETE FROM failed '
                b'WHERE failed.release = ?',
                [release]
            )

        if to_remove:
            return self.redirect('/manage/failedDownloads/')

        t = PageTemplate(rh=self, filename='manage_failedDownloads.mako')

        return t.render(limit=limit, failedResults=sql_results,
                        controller='manage',
                        action='failedDownloads')
