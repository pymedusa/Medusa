# coding=utf-8

from __future__ import unicode_literals

import os
import json
import re
from tornado.routes import route
import sickbeard
from sickbeard import (
    db, helpers, logger,
    subtitles, ui,
)
from sickbeard.common import (
    Overview, Quality, SNATCHED,
)
from sickrage.helper.common import (
    episode_num, try_int,
)
from sickrage.helper.encoding import ek
from sickrage.helper.exceptions import (
    ex,
    CantRefreshShowException,
    CantUpdateShowException,
)
from sickrage.show.Show import Show
from sickbeard.server.web.home import Home
from sickbeard.server.web.core import WebRoot, PageTemplate


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
            'SELECT season, episode, name FROM tv_episodes WHERE showid = ? AND season != 0 AND status IN (' + ','.join(
                ['?'] * len(status_list)) + ')', [int(indexer_id)] + status_list)

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
            'SELECT show_name, tv_shows.indexer_id AS indexer_id FROM tv_episodes, tv_shows WHERE tv_episodes.status IN (' + ','.join(
                ['?'] * len(
                    status_list)) + ') AND season != 0 AND tv_episodes.showid = tv_shows.indexer_id ORDER BY show_name',
            status_list)

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
                    b'SELECT season, episode FROM tv_episodes WHERE status IN (' + ','.join(
                        ['?'] * len(status_list)) + ') AND season != 0 AND showid = ?',
                    status_list + [cur_indexer_id])
                all_eps = [str(x['season']) + 'x' + str(x['episode']) for x in all_eps_results]
                to_change[cur_indexer_id] = all_eps

            self.setStatus(cur_indexer_id, '|'.join(to_change[cur_indexer_id]), newStatus, direct=True)

        return self.redirect('/manage/episodeStatuses/')

    @staticmethod
    def showSubtitleMissed(indexer_id, whichSubs):
        main_db_con = db.DBConnection()
        cur_show_results = main_db_con.select(
            'SELECT season, episode, name, subtitles FROM tv_episodes WHERE showid = ? AND season != 0 AND (status LIKE \'%4\' OR status LIKE \'%6\') and location != \'\'',
            [int(indexer_id)])

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
            'SELECT show_name, tv_shows.indexer_id as indexer_id, tv_episodes.subtitles subtitles ' +
            'FROM tv_episodes, tv_shows ' +
            'WHERE tv_shows.subtitles = 1 AND (tv_episodes.status LIKE \'%4\' OR tv_episodes.status LIKE \'%6\') AND tv_episodes.season != 0 ' +
            'AND tv_episodes.location != \'\' AND tv_episodes.showid = tv_shows.indexer_id ORDER BY show_name')

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
                to_download[cur_indexer_id] = [str(x['season']) + 'x' + str(x['episode']) for x in all_eps_results]

            for epResult in to_download[cur_indexer_id]:
                season, episode = epResult.split('x')

                show = Show.find(sickbeard.showList, int(cur_indexer_id))
                show.getEpisode(season, episode).download_subtitles()

        return self.redirect('/manage/subtitleMissed/')

    def backlogShow(self, indexer_id):
        show_obj = Show.find(sickbeard.showList, int(indexer_id))

        if show_obj:
            sickbeard.backlogSearchScheduler.action.searchBacklog([show_obj])

        return self.redirect('/manage/backlogOverview/')

    def backlogOverview(self):
        t = PageTemplate(rh=self, filename='manage_backlogOverview.mako')

        showCounts = {}
        showCats = {}
        showSQLResults = {}

        main_db_con = db.DBConnection()
        for curShow in sickbeard.showList:

            epCounts = {
                Overview.SKIPPED: 0,
                Overview.WANTED: 0,
                Overview.QUAL: 0,
                Overview.GOOD: 0,
                Overview.UNAIRED: 0,
                Overview.SNATCHED: 0,
                Overview.SNATCHED_PROPER: 0,
                Overview.SNATCHED_BEST: 0
            }
            epCats = {}

            sql_results = main_db_con.select(
                'SELECT status, season, episode, name, airdate FROM tv_episodes WHERE tv_episodes.season IS NOT NULL AND tv_episodes.showid IN (SELECT tv_shows.indexer_id FROM tv_shows WHERE tv_shows.indexer_id = ? AND paused = 0) ORDER BY tv_episodes.season DESC, tv_episodes.episode DESC',
                [curShow.indexerid])

            for curResult in sql_results:
                curEpCat = curShow.getOverview(curResult[b'status'])
                if curEpCat:
                    epCats[u'{ep}'.format(ep=episode_num(curResult[b'season'], curResult[b'episode']))] = curEpCat
                    epCounts[curEpCat] += 1

            showCounts[curShow.indexerid] = epCounts
            showCats[curShow.indexerid] = epCats
            showSQLResults[curShow.indexerid] = sql_results

        return t.render(
            showCounts=showCounts, showCats=showCats,
            showSQLResults=showSQLResults, controller='manage',
            action='backlogOverview', title='Backlog Overview',
            header='Backlog Overview', topmenu='manage')

    def massEdit(self, toEdit=None):
        t = PageTemplate(rh=self, filename='manage_massEdit.mako')

        if not toEdit:
            return self.redirect('/manage/')

        showIDs = toEdit.split('|')
        showList = []
        showNames = []
        for curID in showIDs:
            curID = int(curID)
            showObj = Show.find(sickbeard.showList, curID)
            if showObj:
                showList.append(showObj)
                showNames.append(showObj.name)

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

        for curShow in showList:

            cur_root_dir = ek(os.path.dirname, curShow._location)  # pylint: disable=protected-access
            if cur_root_dir not in root_dir_list:
                root_dir_list.append(cur_root_dir)

            # if we know they're not all the same then no point even bothering
            if paused_all_same:
                # if we had a value already and this value is different then they're not all the same
                if last_paused not in (None, curShow.paused):
                    paused_all_same = False
                else:
                    last_paused = curShow.paused

            if default_ep_status_all_same:
                if last_default_ep_status not in (None, curShow.default_ep_status):
                    default_ep_status_all_same = False
                else:
                    last_default_ep_status = curShow.default_ep_status

            if anime_all_same:
                # if we had a value already and this value is different then they're not all the same
                if last_anime not in (None, curShow.is_anime):
                    anime_all_same = False
                else:
                    last_anime = curShow.anime

            if flatten_folders_all_same:
                if last_flatten_folders not in (None, curShow.flatten_folders):
                    flatten_folders_all_same = False
                else:
                    last_flatten_folders = curShow.flatten_folders

            if quality_all_same:
                if last_quality not in (None, curShow.quality):
                    quality_all_same = False
                else:
                    last_quality = curShow.quality

            if subtitles_all_same:
                if last_subtitles not in (None, curShow.subtitles):
                    subtitles_all_same = False
                else:
                    last_subtitles = curShow.subtitles

            if scene_all_same:
                if last_scene not in (None, curShow.scene):
                    scene_all_same = False
                else:
                    last_scene = curShow.scene

            if sports_all_same:
                if last_sports not in (None, curShow.sports):
                    sports_all_same = False
                else:
                    last_sports = curShow.sports

            if air_by_date_all_same:
                if last_air_by_date not in (None, curShow.air_by_date):
                    air_by_date_all_same = False
                else:
                    last_air_by_date = curShow.air_by_date

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

        return t.render(showList=toEdit, showNames=showNames, default_ep_status_value=default_ep_status_value,
                        paused_value=paused_value, anime_value=anime_value, flatten_folders_value=flatten_folders_value,
                        quality_value=quality_value, subtitles_value=subtitles_value, scene_value=scene_value, sports_value=sports_value,
                        air_by_date_value=air_by_date_value, root_dir_list=root_dir_list, title='Mass Edit', header='Mass Edit', topmenu='manage')

    def massEditSubmit(self, paused=None, default_ep_status=None,
                       anime=None, sports=None, scene=None, flatten_folders=None, quality_preset=None,
                       subtitles=None, air_by_date=None, anyQualities=[], bestQualities=[], toEdit=None, *args,
                       **kwargs):
        dir_map = {}
        for cur_arg in kwargs:
            if not cur_arg.startswith('orig_root_dir_'):
                continue
            which_index = cur_arg.replace('orig_root_dir_', '')
            end_dir = kwargs['new_root_dir_{index}'.format(index=which_index)]
            dir_map[kwargs[cur_arg]] = end_dir

        showIDs = toEdit.split('|')
        errors = []
        for curShow in showIDs:
            curErrors = []
            showObj = Show.find(sickbeard.showList, int(curShow))
            if not showObj:
                continue

            cur_root_dir = ek(os.path.dirname, showObj._location)  # pylint: disable=protected-access
            cur_show_dir = ek(os.path.basename, showObj._location)  # pylint: disable=protected-access
            if cur_root_dir in dir_map and cur_root_dir != dir_map[cur_root_dir]:
                new_show_dir = ek(os.path.join, dir_map[cur_root_dir], cur_show_dir)
                logger.log(u'For show {show.name} changing dir from {show.location} to {location}'.format
                           (show=showObj, location=new_show_dir))  # pylint: disable=protected-access
            else:
                new_show_dir = showObj._location  # pylint: disable=protected-access

            if paused == 'keep':
                new_paused = showObj.paused
            else:
                new_paused = True if paused == 'enable' else False
            new_paused = 'on' if new_paused else 'off'

            if default_ep_status == 'keep':
                new_default_ep_status = showObj.default_ep_status
            else:
                new_default_ep_status = default_ep_status

            if anime == 'keep':
                new_anime = showObj.anime
            else:
                new_anime = True if anime == 'enable' else False
            new_anime = 'on' if new_anime else 'off'

            if sports == 'keep':
                new_sports = showObj.sports
            else:
                new_sports = True if sports == 'enable' else False
            new_sports = 'on' if new_sports else 'off'

            if scene == 'keep':
                new_scene = showObj.is_scene
            else:
                new_scene = True if scene == 'enable' else False
            new_scene = 'on' if new_scene else 'off'

            if air_by_date == 'keep':
                new_air_by_date = showObj.air_by_date
            else:
                new_air_by_date = True if air_by_date == 'enable' else False
            new_air_by_date = 'on' if new_air_by_date else 'off'

            if flatten_folders == 'keep':
                new_flatten_folders = showObj.flatten_folders
            else:
                new_flatten_folders = True if flatten_folders == 'enable' else False
            new_flatten_folders = 'on' if new_flatten_folders else 'off'

            if subtitles == 'keep':
                new_subtitles = showObj.subtitles
            else:
                new_subtitles = True if subtitles == 'enable' else False

            new_subtitles = 'on' if new_subtitles else 'off'

            if quality_preset == 'keep':
                anyQualities, bestQualities = Quality.splitQuality(showObj.quality)
            elif try_int(quality_preset, None):
                bestQualities = []

            exceptions_list = []

            curErrors += self.editShow(curShow, new_show_dir, anyQualities,
                                       bestQualities, exceptions_list,
                                       defaultEpStatus=new_default_ep_status,
                                       flatten_folders=new_flatten_folders,
                                       paused=new_paused, sports=new_sports,
                                       subtitles=new_subtitles, anime=new_anime,
                                       scene=new_scene, air_by_date=new_air_by_date,
                                       directCall=True)

            if curErrors:
                logger.log(u'Errors: {errors}'.format(errors=curErrors), logger.ERROR)
                errors.append(
                    '<b>{show}:</b>\n<ul>{errors}</ul>'.format(
                        show=showObj.name,
                        errors=' '.join(['<li>{error}</li>'.format(error=error)
                                         for error in curErrors])
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
        if toUpdate is not None:
            toUpdate = toUpdate.split('|')
        else:
            toUpdate = []

        if toRefresh is not None:
            toRefresh = toRefresh.split('|')
        else:
            toRefresh = []

        if toRename is not None:
            toRename = toRename.split('|')
        else:
            toRename = []

        if toSubtitle is not None:
            toSubtitle = toSubtitle.split('|')
        else:
            toSubtitle = []

        if toDelete is not None:
            toDelete = toDelete.split('|')
        else:
            toDelete = []

        if toRemove is not None:
            toRemove = toRemove.split('|')
        else:
            toRemove = []

        if toMetadata is not None:
            toMetadata = toMetadata.split('|')
        else:
            toMetadata = []

        errors = []
        refreshes = []
        updates = []
        renames = []
        subtitles = []

        for curShowID in set(toUpdate + toRefresh + toRename + toSubtitle + toDelete + toRemove + toMetadata):

            if curShowID == '':
                continue

            showObj = Show.find(sickbeard.showList, int(curShowID))

            if showObj is None:
                continue

            if curShowID in toDelete:
                sickbeard.showQueueScheduler.action.removeShow(showObj, True)
                # don't do anything else if it's being deleted
                continue

            if curShowID in toRemove:
                sickbeard.showQueueScheduler.action.removeShow(showObj)
                # don't do anything else if it's being remove
                continue

            if curShowID in toUpdate:
                try:
                    sickbeard.showQueueScheduler.action.updateShow(showObj, True)
                    updates.append(showObj.name)
                except CantUpdateShowException as e:
                    errors.append('Unable to update show: {0}'.format(str(e)))

            # don't bother refreshing shows that were updated anyway
            if curShowID in toRefresh and curShowID not in toUpdate:
                try:
                    sickbeard.showQueueScheduler.action.refreshShow(showObj)
                    refreshes.append(showObj.name)
                except CantRefreshShowException as e:
                    errors.append('Unable to refresh show {show.name}: {error}'.format
                                  (show=showObj, error=ex(e)))

            if curShowID in toRename:
                sickbeard.showQueueScheduler.action.renameShowEpisodes(showObj)
                renames.append(showObj.name)

            if curShowID in toSubtitle:
                sickbeard.showQueueScheduler.action.download_subtitles(showObj)
                subtitles.append(showObj.name)

        if errors:
            ui.notifications.error('Errors encountered',
                                   '<br >\n'.join(errors))

        messageDetail = ''

        if updates:
            messageDetail += '<br><b>Updates</b><br><ul><li>'
            messageDetail += '</li><li>'.join(updates)
            messageDetail += '</li></ul>'

        if refreshes:
            messageDetail += '<br><b>Refreshes</b><br><ul><li>'
            messageDetail += '</li><li>'.join(refreshes)
            messageDetail += '</li></ul>'

        if renames:
            messageDetail += '<br><b>Renames</b><br><ul><li>'
            messageDetail += '</li><li>'.join(renames)
            messageDetail += '</li></ul>'

        if subtitles:
            messageDetail += '<br><b>Subtitles</b><br><ul><li>'
            messageDetail += '</li><li>'.join(subtitles)
            messageDetail += '</li></ul>'

        if updates + refreshes + renames + subtitles:
            ui.notifications.message('The following actions were queued:',
                                     messageDetail)

        return self.redirect('/manage/')

    def manageTorrents(self):
        t = PageTemplate(rh=self, filename='manage_torrents.mako')
        info_download_station = ''

        if re.search('localhost', sickbeard.TORRENT_HOST):

            if sickbeard.LOCALHOST_IP == '':
                webui_url = re.sub('localhost', helpers.get_lan_ip(), sickbeard.TORRENT_HOST)
            else:
                webui_url = re.sub('localhost', sickbeard.LOCALHOST_IP, sickbeard.TORRENT_HOST)
        else:
            webui_url = sickbeard.TORRENT_HOST

        if sickbeard.TORRENT_METHOD == 'utorrent':
            webui_url = '/'.join(s.strip('/') for s in (webui_url, 'gui/'))
        if sickbeard.TORRENT_METHOD == 'download_station':
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

        if not sickbeard.TORRENT_PASSWORD == '' and not sickbeard.TORRENT_USERNAME == '':
            webui_url = re.sub('://', '://{username}:{password}@'.format(username=sickbeard.TORRENT_USERNAME,
                                                                         password=sickbeard.TORRENT_PASSWORD), webui_url)

        return t.render(
            webui_url=webui_url, info_download_station=info_download_station,
            title='Manage Torrents', header='Manage Torrents', topmenu='manage')

    def failedDownloads(self, limit=100, toRemove=None):
        failed_db_con = db.DBConnection('failed.db')

        if limit == '0':
            sql_results = failed_db_con.select('SELECT * FROM failed')
        else:
            sql_results = failed_db_con.select('SELECT * FROM failed LIMIT ?', [limit])

        toRemove = toRemove.split('|') if toRemove is not None else []

        for release in toRemove:
            failed_db_con.action('DELETE FROM failed WHERE failed.release = ?', [release])

        if toRemove:
            return self.redirect('/manage/failedDownloads/')

        t = PageTemplate(rh=self, filename='manage_failedDownloads.mako')

        return t.render(limit=limit, failedResults=sql_results,
                        title='Failed Downloads', header='Failed Downloads',
                        topmenu='manage', controller='manage',
                        action='failedDownloads')
