# coding=utf-8

from __future__ import unicode_literals

import datetime
import json
import os
import re

from tornroutes import route

from ..core import PageTemplate, WebRoot
from ..home import Home
from .... import app, db, helpers, logger, post_processor, subtitles, ui
from ....common import (
    Overview, Quality, SNATCHED,
)
from ....helper.common import (
    episode_num, try_int,
)
from ....helper.exceptions import (
    CantRefreshShowException,
    CantUpdateShowException,
)
from ....helpers import is_media_file
from ....show.show import Show
from ....tv import Episode


@route('/manage(/?.*)')
class Manage(Home, WebRoot):
    def __init__(self, *args, **kwargs):
        super(Manage, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename='manage.mako')
        return t.render(title='Mass Update', header='Mass Update', topmenu='manage', controller='manage', action='index')

    @staticmethod
    def showEpisodeStatuses(indexer_id, whichStatus):
        status_list = [int(whichStatus)]
        if status_list[0] == SNATCHED:
            status_list = Quality.SNATCHED + Quality.SNATCHED_PROPER + Quality.SNATCHED_BEST

        main_db_con = db.DBConnection()
        cur_show_results = main_db_con.select(
            b'SELECT season, episode, name '
            b'FROM tv_episodes '
            b'WHERE showid = ? AND season != 0 AND status IN ({statuses})'.format(
                statuses=','.join(['?'] * len(status_list))),
            [int(indexer_id)] + status_list
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
                status_list = Quality.SNATCHED + Quality.SNATCHED_PROPER + Quality.SNATCHED_BEST
        else:
            status_list = []

        t = PageTemplate(rh=self, filename='manage_episodeStatuses.mako')

        # if we have no status then this is as far as we need to go
        if not status_list:
            return t.render(
                title='Episode Overview', header='Episode Overview',
                topmenu='manage', show_names=None, whichStatus=whichStatus,
                ep_counts=None, sorted_show_ids=None,
                controller='manage', action='episodeStatuses')

        main_db_con = db.DBConnection()
        status_results = main_db_con.select(
            b'SELECT show_name, tv_shows.indexer_id AS indexer_id '
            b'FROM tv_episodes, tv_shows '
            b'WHERE season != 0 '
            b'AND tv_episodes.showid = tv_shows.indexer_id '
            b'AND tv_episodes.status IN ({statuses}) '
            b'ORDER BY show_name'.format(statuses=','.join(['?'] * len(status_list))),
            status_list
        )

        ep_counts = {}
        show_names = {}
        sorted_show_ids = []
        for cur_status_result in status_results:
            cur_indexer_id = int(cur_status_result[b'indexer_id'])
            if cur_indexer_id not in ep_counts:
                ep_counts[cur_indexer_id] = 1
            else:
                ep_counts[cur_indexer_id] += 1

            show_names[cur_indexer_id] = cur_status_result[b'show_name']
            if cur_indexer_id not in sorted_show_ids:
                sorted_show_ids.append(cur_indexer_id)

        return t.render(
            title='Episode Overview', header='Episode Overview',
            topmenu='manage', whichStatus=whichStatus,
            show_names=show_names, ep_counts=ep_counts, sorted_show_ids=sorted_show_ids,
            controller='manage', action='episodeStatuses')

    def changeEpisodeStatuses(self, oldStatus, newStatus, *args, **kwargs):
        status_list = [int(oldStatus)]
        if status_list[0] == SNATCHED:
            status_list = Quality.SNATCHED + Quality.SNATCHED_PROPER + Quality.SNATCHED_BEST

        to_change = {}

        # make a list of all shows and their associated args
        for arg in kwargs:
            indexer_id, what = arg.split('-')

            # we don't care about unchecked checkboxes
            if kwargs[arg] != 'on':
                continue

            if indexer_id not in to_change:
                to_change[indexer_id] = []

            to_change[indexer_id].append(what)

        main_db_con = db.DBConnection()
        for cur_indexer_id in to_change:

            # get a list of all the eps we want to change if they just said 'all'
            if 'all' in to_change[cur_indexer_id]:
                all_eps_results = main_db_con.select(
                    b'SELECT season, episode '
                    b'FROM tv_episodes '
                    b'WHERE status IN ({statuses}) '
                    b'AND season != 0 '
                    b'AND showid = ?'.format(statuses=','.join(['?'] * len(status_list))),
                    status_list + [cur_indexer_id]
                )

                all_eps = ['{season}x{episode}'.format(season=x[b'season'], episode=x[b'episode']) for x in all_eps_results]
                to_change[cur_indexer_id] = all_eps

            self.setStatus(cur_indexer_id, '|'.join(to_change[cur_indexer_id]), newStatus, direct=True)

        return self.redirect('/manage/episodeStatuses/')

    @staticmethod
    def showSubtitleMissed(indexer_id, whichSubs):
        main_db_con = db.DBConnection()
        cur_show_results = main_db_con.select(
            b'SELECT season, episode, name, subtitles '
            b'FROM tv_episodes '
            b'WHERE showid = ? '
            b'AND season != 0 '
            b'AND (status LIKE \'%4\' OR status LIKE \'%6\') '
            b'AND location != \'\'',
            [int(indexer_id)]
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
            return t.render(whichSubs=whichSubs, title='Missing Subtitles',
                            header='Missing Subtitles', topmenu='manage',
                            show_names=None, ep_counts=None, sorted_show_ids=None,
                            controller='manage', action='subtitleMissed')

        main_db_con = db.DBConnection()
        status_results = main_db_con.select(
            b'SELECT show_name, tv_shows.indexer_id as indexer_id, tv_episodes.subtitles subtitles '
            b'FROM tv_episodes, tv_shows '
            b'WHERE tv_shows.subtitles = 1 '
            b'AND (tv_episodes.status LIKE \'%4\' OR tv_episodes.status LIKE \'%6\') '
            b'AND tv_episodes.season != 0 '
            b'AND tv_episodes.location != \'\' '
            b'AND tv_episodes.showid = tv_shows.indexer_id '
            b'ORDER BY show_name'
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

            cur_indexer_id = int(cur_status_result[b'indexer_id'])
            if cur_indexer_id not in ep_counts:
                ep_counts[cur_indexer_id] = 1
            else:
                ep_counts[cur_indexer_id] += 1

            show_names[cur_indexer_id] = cur_status_result[b'show_name']
            if cur_indexer_id not in sorted_show_ids:
                sorted_show_ids.append(cur_indexer_id)

        return t.render(whichSubs=whichSubs, show_names=show_names, ep_counts=ep_counts, sorted_show_ids=sorted_show_ids,
                        title='Missing Subtitles', header='Missing Subtitles', topmenu='manage',
                        controller='manage', action='subtitleMissed')

    def downloadSubtitleMissed(self, *args, **kwargs):
        to_download = {}

        # make a list of all shows and their associated args
        for arg in kwargs:
            indexer_id, what = arg.split('-')

            # we don't care about unchecked checkboxes
            if kwargs[arg] != 'on':
                continue

            if indexer_id not in to_download:
                to_download[indexer_id] = []

            to_download[indexer_id].append(what)

        for cur_indexer_id in to_download:
            # get a list of all the eps we want to download subtitles if they just said 'all'
            if 'all' in to_download[cur_indexer_id]:
                main_db_con = db.DBConnection()
                all_eps_results = main_db_con.select(
                    b'SELECT season, episode '
                    b'FROM tv_episodes '
                    b'WHERE (status LIKE \'%4\' OR status LIKE \'%6\') '
                    b'AND season != 0 '
                    b'AND showid = ? '
                    b'AND location != \'\'',
                    [cur_indexer_id]
                )
                to_download[cur_indexer_id] = [str(x[b'season']) + 'x' + str(x[b'episode']) for x in all_eps_results]

            for epResult in to_download[cur_indexer_id]:
                season, episode = epResult.split('x')

                show = Show.find(app.showList, int(cur_indexer_id))
                show.get_episode(season, episode).download_subtitles()

        return self.redirect('/manage/subtitleMissed/')

    def subtitleMissedPP(self):
        t = PageTemplate(rh=self, filename='manage_subtitleMissedPP.mako')
        app.RELEASES_IN_PP = []
        for root, _, files in os.walk(app.TV_DOWNLOAD_DIR, topdown=False):
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

                ep_status = Quality.split_composite_status(tv_episode.status).status
                if ep_status in Quality.SNATCHED + Quality.SNATCHED_PROPER + Quality.SNATCHED_BEST:
                    status = 'snatched'
                elif ep_status in Quality.DOWNLOADED:
                    status = 'downloaded'
                else:
                    continue

                if not tv_episode.show.subtitles:
                    continue

                related_files = post_processor.PostProcessor(video_path).list_associated_files(video_path, base_name_only=True, subfolders=False)
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

                app.RELEASES_IN_PP.append({'release': video_path, 'show': tv_episode.show.indexerid, 'show_name': tv_episode.show.name,
                                           'season': tv_episode.season, 'episode': tv_episode.episode, 'status': status,
                                           'age': age_value, 'age_unit': age_unit, 'age_raw': video_age})
        app.RELEASES_IN_PP = sorted(app.RELEASES_IN_PP, key=lambda k: k['age_raw'], reverse=True)

        return t.render(releases_in_pp=app.RELEASES_IN_PP, title='Missing Subtitles in Post-Process folder',
                        header='Missing Subtitles in Post Process folder', topmenu='manage',
                        controller='manage', action='subtitleMissedPP')

    def backlogShow(self, indexer_id):
        show_obj = Show.find(app.showList, int(indexer_id))

        if show_obj:
            app.backlog_search_scheduler.action.search_backlog([show_obj])

        return self.redirect('/manage/backlogOverview/')

    def backlogOverview(self):
        t = PageTemplate(rh=self, filename='manage_backlogOverview.mako')

        show_counts = {}
        show_cats = {}
        show_sql_results = {}

        main_db_con = db.DBConnection()
        for cur_show in app.showList:

            ep_counts = {
                Overview.WANTED: 0,
                Overview.QUAL: 0,
                Overview.GOOD: 0,
            }
            ep_cats = {}

            sql_results = main_db_con.select(
                """
                SELECT status, season, episode, name, airdate, manually_searched
                FROM tv_episodes
                WHERE tv_episodes.season IS NOT NULL AND
                      tv_episodes.showid IN (SELECT tv_shows.indexer_id
                                             FROM tv_shows
                                             WHERE tv_shows.indexer_id = ? AND
                                                   paused = 0)
                ORDER BY tv_episodes.season DESC, tv_episodes.episode DESC
                """,
                [cur_show.indexerid]
            )

            for cur_result in sql_results:
                cur_ep_cat = cur_show.get_overview(cur_result[b'status'], backlog_mode=True,
                                                   manually_searched=cur_result[b'manually_searched'])
                if cur_ep_cat:
                    ep_cats[u'{ep}'.format(ep=episode_num(cur_result[b'season'], cur_result[b'episode']))] = cur_ep_cat
                    ep_counts[cur_ep_cat] += 1

            show_counts[cur_show.indexerid] = ep_counts
            show_cats[cur_show.indexerid] = ep_cats
            show_sql_results[cur_show.indexerid] = sql_results

        return t.render(
            showCounts=show_counts, showCats=show_cats,
            showSQLResults=show_sql_results, controller='manage',
            action='backlogOverview', title='Backlog Overview',
            header='Backlog Overview', topmenu='manage')

    def massEdit(self, toEdit=None):
        t = PageTemplate(rh=self, filename='manage_massEdit.mako')

        if not toEdit:
            return self.redirect('/manage/')

        show_ids = toEdit.split('|')
        show_list = []
        show_names = []
        for cur_id in show_ids:
            cur_id = int(cur_id)
            show_obj = Show.find(app.showList, cur_id)
            if show_obj:
                show_list.append(show_obj)
                show_names.append(show_obj.name)

        flatten_folders_all_same = True
        last_flatten_folders = None

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

            if flatten_folders_all_same:
                if last_flatten_folders not in (None, cur_show.flatten_folders):
                    flatten_folders_all_same = False
                else:
                    last_flatten_folders = cur_show.flatten_folders

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

        default_ep_status_value = last_default_ep_status if default_ep_status_all_same else None
        paused_value = last_paused if paused_all_same else None
        anime_value = last_anime if anime_all_same else None
        flatten_folders_value = last_flatten_folders if flatten_folders_all_same else None
        quality_value = last_quality if quality_all_same else None
        subtitles_value = last_subtitles if subtitles_all_same else None
        scene_value = last_scene if scene_all_same else None
        sports_value = last_sports if sports_all_same else None
        air_by_date_value = last_air_by_date if air_by_date_all_same else None
        root_dir_list = root_dir_list

        return t.render(showList=toEdit, showNames=show_names, default_ep_status_value=default_ep_status_value,
                        paused_value=paused_value, anime_value=anime_value, flatten_folders_value=flatten_folders_value,
                        quality_value=quality_value, subtitles_value=subtitles_value, scene_value=scene_value, sports_value=sports_value,
                        air_by_date_value=air_by_date_value, root_dir_list=root_dir_list, title='Mass Edit', header='Mass Edit', topmenu='manage')

    def massEditSubmit(self, paused=None, default_ep_status=None,
                       anime=None, sports=None, scene=None, flatten_folders=None, quality_preset=None,
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

        show_ids = toEdit.split('|')
        errors = []
        for cur_show in show_ids:
            cur_errors = []
            show_obj = Show.find(app.showList, int(cur_show))
            if not show_obj:
                continue

            cur_root_dir = os.path.dirname(show_obj._location)  # pylint: disable=protected-access
            cur_show_dir = os.path.basename(show_obj._location)  # pylint: disable=protected-access
            if cur_root_dir in dir_map and cur_root_dir != dir_map[cur_root_dir]:
                new_show_dir = os.path.join(dir_map[cur_root_dir], cur_show_dir)
                logger.log(u'For show {show.name} changing dir from {show.location} to {location}'.format
                           (show=show_obj, location=new_show_dir))  # pylint: disable=protected-access
            else:
                new_show_dir = show_obj._location  # pylint: disable=protected-access

            if paused == 'keep':
                new_paused = show_obj.paused
            else:
                new_paused = True if paused == 'enable' else False
            new_paused = 'on' if new_paused else 'off'

            if default_ep_status == 'keep':
                new_default_ep_status = show_obj.default_ep_status
            else:
                new_default_ep_status = default_ep_status

            if anime == 'keep':
                new_anime = show_obj.anime
            else:
                new_anime = True if anime == 'enable' else False
            new_anime = 'on' if new_anime else 'off'

            if sports == 'keep':
                new_sports = show_obj.sports
            else:
                new_sports = True if sports == 'enable' else False
            new_sports = 'on' if new_sports else 'off'

            if scene == 'keep':
                new_scene = show_obj.is_scene
            else:
                new_scene = True if scene == 'enable' else False
            new_scene = 'on' if new_scene else 'off'

            if air_by_date == 'keep':
                new_air_by_date = show_obj.air_by_date
            else:
                new_air_by_date = True if air_by_date == 'enable' else False
            new_air_by_date = 'on' if new_air_by_date else 'off'

            if flatten_folders == 'keep':
                new_flatten_folders = show_obj.flatten_folders
            else:
                new_flatten_folders = True if flatten_folders == 'enable' else False
            new_flatten_folders = 'on' if new_flatten_folders else 'off'

            if subtitles == 'keep':
                new_subtitles = show_obj.subtitles
            else:
                new_subtitles = True if subtitles == 'enable' else False

            new_subtitles = 'on' if new_subtitles else 'off'

            if quality_preset == 'keep':
                allowed_qualities, preferred_qualities = show_obj.current_qualities
            elif try_int(quality_preset, None):
                preferred_qualities = []

            exceptions_list = []

            cur_errors += self.editShow(cur_show, new_show_dir, allowed_qualities,
                                        preferred_qualities, exceptions_list,
                                        defaultEpStatus=new_default_ep_status,
                                        flatten_folders=new_flatten_folders,
                                        paused=new_paused, sports=new_sports,
                                        subtitles=new_subtitles, anime=new_anime,
                                        scene=new_scene, air_by_date=new_air_by_date,
                                        directCall=True)

            if cur_errors:
                logger.log(u'Errors: {errors}'.format(errors=cur_errors), logger.ERROR)
                errors.append(
                    '<b>{show}:</b>\n<ul>{errors}</ul>'.format(
                        show=show_obj.name,
                        errors=' '.join(['<li>{error}</li>'.format(error=error)
                                         for error in cur_errors])
                    )
                )
        if errors:
            ui.notifications.error(
                '{num} error{s} while saving changes:'.format(
                    num=len(errors),
                    s='s' if len(errors) > 1 else ''),
                ' '.join(errors)
            )

        return self.redirect('/manage/')

    def massUpdate(self, toUpdate=None, toRefresh=None, toRename=None, toDelete=None, toRemove=None, toMetadata=None,
                   toSubtitle=None):
        to_update = toUpdate.split('|') if toUpdate else []
        to_refresh = toRefresh.split('|') if toRefresh else []
        to_rename = toRename.split('|') if toRename else []
        to_subtitle = toSubtitle.split('|') if toSubtitle else []
        to_delete = toDelete.split('|') if toDelete else []
        to_remove = toRemove.split('|') if toRemove else []
        to_metadata = toMetadata.split('|') if toMetadata else []

        errors = []
        refreshes = []
        updates = []
        renames = []
        subtitles = []

        for cur_show_id in set(to_update + to_refresh + to_rename + to_subtitle + to_delete + to_remove + to_metadata):
            show_obj = Show.find(app.showList, int(cur_show_id)) if cur_show_id else None

            if not show_obj:
                continue

            if cur_show_id in to_delete + to_remove:
                app.show_queue_scheduler.action.removeShow(show_obj, cur_show_id in to_delete)
                continue  # don't do anything else if it's being deleted or removed

            if cur_show_id in to_update:
                try:
                    app.show_queue_scheduler.action.updateShow(show_obj)
                    updates.append(show_obj.name)
                except CantUpdateShowException as msg:
                    errors.append('Unable to update show: {error}'.format(error=msg))

            elif cur_show_id in to_refresh:  # don't bother refreshing shows that were updated
                try:
                    app.show_queue_scheduler.action.refreshShow(show_obj)
                    refreshes.append(show_obj.name)
                except CantRefreshShowException as msg:
                    errors.append('Unable to refresh show {show.name}: {error}'.format
                                  (show=show_obj, error=msg))

            if cur_show_id in to_rename:
                app.show_queue_scheduler.action.renameShowEpisodes(show_obj)
                renames.append(show_obj.name)

            if cur_show_id in to_subtitle:
                app.show_queue_scheduler.action.download_subtitles(show_obj)
                subtitles.append(show_obj.name)

        if errors:
            ui.notifications.error('Errors encountered',
                                   '<br />\n'.join(errors))

        def message_detail(title, items):
            """
            Create an unordered list of items with a title.
            :return: The message if items else ''
            """
            return '' if not items else """
                <br />
                <b>{title}</b>
                <br />
                <ul>
                  {list}
                </ul>
                """.format(title=title,
                           list='\n'.join(['  <li>{item}</li>'.format(item=cur_item)
                                           for cur_item in items]))

        message = ''
        message += message_detail('Updates', updates)
        message += message_detail('Refreshes', refreshes)
        message += message_detail('Renames', renames)
        message += message_detail('Subtitles', subtitles)

        if message:
            ui.notifications.message('The following actions were queued:', message)

        return self.redirect('/manage/')

    def manageTorrents(self):
        t = PageTemplate(rh=self, filename='manage_torrents.mako')
        info_download_station = ''

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
                info_download_station = """
                <p>
                    To have a better experience please set the Download Station alias as <code>download</code>, you can check
                    this setting in the Synology DSM <b>Control Panel</b> > <b>Application Portal</b>.  Make sure you allow
                    DSM to be embedded with iFrames too in <b>Control Panel</b> > <b>DSM Settings</b> > <b>Security</b>.
                </p>
                <br />
                <p>
                    There is more information about this available <a href="https://github.com/midgetspy/Sick-Beard/pull/338">here</a>.
                </p>
                <br />
                """

        if not app.TORRENT_PASSWORD == '' and not app.TORRENT_USERNAME == '':
            webui_url = re.sub('://', '://{username}:{password}@'.format(username=app.TORRENT_USERNAME,
                                                                         password=app.TORRENT_PASSWORD), webui_url)

        return t.render(
            webui_url=webui_url, info_download_station=info_download_station,
            title='Manage Torrents', header='Manage Torrents', topmenu='manage')

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
                        title='Failed Downloads', header='Failed Downloads',
                        topmenu='manage', controller='manage',
                        action='failedDownloads')
