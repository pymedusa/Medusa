# coding=utf-8

from __future__ import unicode_literals

import ast
import datetime
import json
import os
import time
import adba
from libtrakt import TraktAPI
from requests.compat import unquote_plus, quote_plus
from tornado.routes import route
import sickbeard
from sickbeard import (
    clients, config, db, helpers, logger,
    notifiers, sab, search_queue,
    subtitles, ui, show_name_helpers
)
from sickbeard.blackandwhitelist import BlackAndWhiteList, short_group_names
from sickbeard.common import (
    cpu_presets, Overview, Quality, statusStrings,
    UNAIRED, IGNORED, WANTED, FAILED, SKIPPED
)
from sickbeard.manual_search import (
    collectEpisodesFromSearchThread, get_provider_cache_results, getEpisode, update_finished_search_queue_item,
    SEARCH_STATUS_FINISHED, SEARCH_STATUS_SEARCHING, SEARCH_STATUS_QUEUED,
)
from sickbeard.scene_numbering import (
    get_scene_absolute_numbering, get_scene_absolute_numbering_for_show,
    get_scene_numbering, get_scene_numbering_for_show,
    get_xem_absolute_numbering_for_show, get_xem_numbering_for_show,
    set_scene_numbering,
)
from sickbeard.versionChecker import CheckVersion
from sickrage.helper.common import (
    try_int, enabled_providers,
)
from sickrage.helper.encoding import ek
from sickrage.helper.exceptions import (
    ex,
    CantRefreshShowException,
    CantUpdateShowException,
    NoNFOException,
    ShowDirectoryNotFoundException,
)
from sickrage.show.Show import Show
from sickrage.system.Restart import Restart
from sickrage.system.Shutdown import Shutdown
from sickbeard.server.web.core import WebRoot, PageTemplate


@route('/home(/?.*)')
class Home(WebRoot):
    def __init__(self, *args, **kwargs):
        super(Home, self).__init__(*args, **kwargs)

    def _genericMessage(self, subject, message):
        t = PageTemplate(rh=self, filename='genericMessage.mako')
        return t.render(message=message, subject=subject, topmenu='home', title='')

    def index(self):
        t = PageTemplate(rh=self, filename='home.mako')
        if sickbeard.ANIME_SPLIT_HOME:
            shows = []
            anime = []
            for show in sickbeard.showList:
                if show.is_anime:
                    anime.append(show)
                else:
                    shows.append(show)
            showlists = [['Shows', shows], ['Anime', anime]]
        else:
            showlists = [['Shows', sickbeard.showList]]

        stats = self.show_statistics()
        return t.render(title='Home', header='Show List', topmenu='home', showlists=showlists, show_stat=stats[0], max_download_count=stats[1], controller='home', action='index')

    @staticmethod
    def show_statistics():
        main_db_con = db.DBConnection()
        today = str(datetime.date.today().toordinal())

        status_quality = '(' + ','.join([str(x) for x in Quality.SNATCHED + Quality.SNATCHED_PROPER + Quality.SNATCHED_BEST]) + ')'
        status_download = '(' + ','.join([str(x) for x in Quality.DOWNLOADED + Quality.ARCHIVED]) + ')'

        sql_statement = 'SELECT showid, '

        sql_statement += '(SELECT COUNT(*) FROM tv_episodes WHERE showid=tv_eps.showid AND season > 0 AND episode > 0 AND airdate > 1 AND status IN ' + status_quality + ') AS ep_snatched, '
        sql_statement += '(SELECT COUNT(*) FROM tv_episodes WHERE showid=tv_eps.showid AND season > 0 AND episode > 0 AND airdate > 1 AND status IN ' + status_download + ') AS ep_downloaded, '
        sql_statement += '(SELECT COUNT(*) FROM tv_episodes WHERE showid=tv_eps.showid AND season > 0 AND episode > 0 AND airdate > 1 '
        sql_statement += ' AND ((airdate <= ' + today + ' AND (status = ' + str(SKIPPED) + ' OR status = ' + str(WANTED) + ' OR status = ' + str(FAILED) + ')) '
        sql_statement += ' OR (status IN ' + status_quality + ') OR (status IN ' + status_download + '))) AS ep_total, '

        sql_statement += ' (SELECT airdate FROM tv_episodes WHERE showid=tv_eps.showid AND airdate >= ' + today + ' AND (status = ' + str(UNAIRED) + ' OR status = ' + str(WANTED) + ') ORDER BY airdate ASC LIMIT 1) AS ep_airs_next, '
        sql_statement += ' (SELECT airdate FROM tv_episodes WHERE showid=tv_eps.showid AND airdate > 1 AND status <> ' + str(UNAIRED) + ' ORDER BY airdate DESC LIMIT 1) AS ep_airs_prev, '
        sql_statement += ' (SELECT SUM(file_size) FROM tv_episodes WHERE showid=tv_eps.showid) AS show_size'
        sql_statement += ' FROM tv_episodes tv_eps GROUP BY showid'

        sql_result = main_db_con.select(sql_statement)

        show_stat = {}
        max_download_count = 1000
        for cur_result in sql_result:
            show_stat[cur_result[b'showid']] = cur_result
            if cur_result[b'ep_total'] > max_download_count:
                max_download_count = cur_result[b'ep_total']

        max_download_count *= 100

        return show_stat, max_download_count

    def is_alive(self, *args, **kwargs):
        if 'callback' in kwargs and '_' in kwargs:
            callback, _ = kwargs['callback'], kwargs['_']
        else:
            return 'Error: Unsupported Request. Send jsonp request with \'callback\' variable in the query string.'

        # self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')
        self.set_header('Content-Type', 'text/javascript')
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Headers', 'x-requested-with')

        if sickbeard.started:
            return callback + '(' + json.dumps(
                {'msg': str(sickbeard.PID)}) + ');'
        else:
            return callback + '(' + json.dumps({'msg': 'nope'}) + ');'

    @staticmethod
    def haveKODI():
        return sickbeard.USE_KODI and sickbeard.KODI_UPDATE_LIBRARY

    @staticmethod
    def havePLEX():
        return sickbeard.USE_PLEX_SERVER and sickbeard.PLEX_UPDATE_LIBRARY

    @staticmethod
    def haveEMBY():
        return sickbeard.USE_EMBY

    @staticmethod
    def haveTORRENT():
        if sickbeard.USE_TORRENTS and sickbeard.TORRENT_METHOD != 'blackhole' and \
                (sickbeard.ENABLE_HTTPS and sickbeard.TORRENT_HOST[:5] == 'https' or not
                 sickbeard.ENABLE_HTTPS and sickbeard.TORRENT_HOST[:5] == 'http:'):
            return True
        else:
            return False

    @staticmethod
    def testSABnzbd(host=None, username=None, password=None, apikey=None):
        # self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')

        host = config.clean_url(host)

        connection, accesMsg = sab.getSabAccesMethod(host)
        if connection:
            authed, authMsg = sab.testAuthentication(host, username, password, apikey)  # @UnusedVariable
            if authed:
                return 'Success. Connected and authenticated'
            else:
                return 'Authentication failed. SABnzbd expects \'' + accesMsg + '\' as authentication method, \'' + authMsg + '\''
        else:
            return 'Unable to connect to host'

    @staticmethod
    def testTorrent(torrent_method=None, host=None, username=None, password=None):

        host = config.clean_url(host)

        client = clients.get_client_instance(torrent_method)

        _, accesMsg = client(host, username, password).test_authentication()

        return accesMsg

    @staticmethod
    def testFreeMobile(freemobile_id=None, freemobile_apikey=None):

        result, message = notifiers.freemobile_notifier.test_notify(freemobile_id, freemobile_apikey)
        if result:
            return 'SMS sent successfully'
        else:
            return 'Problem sending SMS: ' + message

    @staticmethod
    def testTelegram(telegram_id=None, telegram_apikey=None):

        result, message = notifiers.telegram_notifier.test_notify(telegram_id, telegram_apikey)
        if result:
            return 'Telegram notification succeeded. Check your Telegram clients to make sure it worked'
        else:
            return 'Error sending Telegram notification: ' + message

    @staticmethod
    def testGrowl(host=None, password=None):
        # self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')

        host = config.clean_host(host, default_port=23053)

        result = notifiers.growl_notifier.test_notify(host, password)
        if password is None or password == '':
            pw_append = ''
        else:
            pw_append = ' with password: ' + password

        if result:
            return 'Registered and Tested growl successfully ' + unquote_plus(host) + pw_append
        else:
            return 'Registration and Testing of growl failed ' + unquote_plus(host) + pw_append

    @staticmethod
    def testProwl(prowl_api=None, prowl_priority=0):

        result = notifiers.prowl_notifier.test_notify(prowl_api, prowl_priority)
        if result:
            return 'Test prowl notice sent successfully'
        else:
            return 'Test prowl notice failed'

    @staticmethod
    def testBoxcar2(accesstoken=None):

        result = notifiers.boxcar2_notifier.test_notify(accesstoken)
        if result:
            return 'Boxcar2 notification succeeded. Check your Boxcar2 clients to make sure it worked'
        else:
            return 'Error sending Boxcar2 notification'

    @staticmethod
    def testPushover(userKey=None, apiKey=None):

        result = notifiers.pushover_notifier.test_notify(userKey, apiKey)
        if result:
            return 'Pushover notification succeeded. Check your Pushover clients to make sure it worked'
        else:
            return 'Error sending Pushover notification'

    @staticmethod
    def twitterStep1():
        return notifiers.twitter_notifier._get_authorization()  # pylint: disable=protected-access

    @staticmethod
    def twitterStep2(key):

        result = notifiers.twitter_notifier._get_credentials(key)  # pylint: disable=protected-access
        logger.log(u'result: ' + str(result))
        if result:
            return 'Key verification successful'
        else:
            return 'Unable to verify key'

    @staticmethod
    def testTwitter():

        result = notifiers.twitter_notifier.test_notify()
        if result:
            return 'Tweet successful, check your twitter to make sure it worked'
        else:
            return 'Error sending tweet'

    @staticmethod
    def testKODI(host=None, username=None, password=None):

        host = config.clean_hosts(host)
        finalResult = ''
        for curHost in [x.strip() for x in host.split(',')]:
            curResult = notifiers.kodi_notifier.test_notify(unquote_plus(curHost), username, password)
            if len(curResult.split(':')) > 2 and 'OK' in curResult.split(':')[2]:
                finalResult += 'Test KODI notice sent successfully to ' + unquote_plus(curHost)
            else:
                finalResult += 'Test KODI notice failed to ' + unquote_plus(curHost)
            finalResult += '<br>\n'

        return finalResult

    def testPHT(self, host=None, username=None, password=None):
        self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')

        if None is not password and set('*') == set(password):
            password = sickbeard.PLEX_CLIENT_PASSWORD

        finalResult = ''
        for curHost in [x.strip() for x in host.split(',')]:
            curResult = notifiers.plex_notifier.test_notify_pht(unquote_plus(curHost), username, password)
            if len(curResult.split(':')) > 2 and 'OK' in curResult.split(':')[2]:
                finalResult += 'Successful test notice sent to Plex Home Theater ... ' + unquote_plus(curHost)
            else:
                finalResult += 'Test failed for Plex Home Theater ... ' + unquote_plus(curHost)
            finalResult += '<br>' + '\n'

        ui.notifications.message('Tested Plex Home Theater(s): ', unquote_plus(host.replace(',', ', ')))

        return finalResult

    def testPMS(self, host=None, username=None, password=None, plex_server_token=None):
        self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')

        if password is not None and set('*') == set(password):
            password = sickbeard.PLEX_SERVER_PASSWORD

        finalResult = ''

        curResult = notifiers.plex_notifier.test_notify_pms(unquote_plus(host), username, password, plex_server_token)
        if curResult is None:
            finalResult += 'Successful test of Plex Media Server(s) ... ' + unquote_plus(host.replace(',', ', '))
        elif curResult is False:
            finalResult += 'Test failed, No Plex Media Server host specified'
        else:
            finalResult += 'Test failed for Plex Media Server(s) ... ' + unquote_plus(str(curResult).replace(',', ', '))
        finalResult += '<br>' + '\n'

        ui.notifications.message('Tested Plex Media Server host(s): ', unquote_plus(host.replace(',', ', ')))

        return finalResult

    @staticmethod
    def testLibnotify():

        if notifiers.libnotify_notifier.test_notify():
            return 'Tried sending desktop notification via libnotify'
        else:
            return notifiers.libnotify.diagnose()

    @staticmethod
    def testEMBY(host=None, emby_apikey=None):

        host = config.clean_host(host)
        result = notifiers.emby_notifier.test_notify(unquote_plus(host), emby_apikey)
        if result:
            return 'Test notice sent successfully to ' + unquote_plus(host)
        else:
            return 'Test notice failed to ' + unquote_plus(host)

    @staticmethod
    def testNMJ(host=None, database=None, mount=None):

        host = config.clean_host(host)
        result = notifiers.nmj_notifier.test_notify(unquote_plus(host), database, mount)
        if result:
            return 'Successfully started the scan update'
        else:
            return 'Test failed to start the scan update'

    @staticmethod
    def settingsNMJ(host=None):

        host = config.clean_host(host)
        result = notifiers.nmj_notifier.notify_settings(unquote_plus(host))
        if result:
            return '{"message": "Got settings from %(host)s", "database": "%(database)s", "mount": "%(mount)s"}' % {
                'host': host, 'database': sickbeard.NMJ_DATABASE, 'mount': sickbeard.NMJ_MOUNT}
        else:
            return '{"message": "Failed! Make sure your Popcorn is on and NMJ is running. (see Log & Errors -> Debug for detailed info)", "database": "", "mount": ""}'

    @staticmethod
    def testNMJv2(host=None):

        host = config.clean_host(host)
        result = notifiers.nmjv2_notifier.test_notify(unquote_plus(host))
        if result:
            return 'Test notice sent successfully to ' + unquote_plus(host)
        else:
            return 'Test notice failed to ' + unquote_plus(host)

    @staticmethod
    def settingsNMJv2(host=None, dbloc=None, instance=None):

        host = config.clean_host(host)
        result = notifiers.nmjv2_notifier.notify_settings(unquote_plus(host), dbloc, instance)
        if result:
            return '{"message": "NMJ Database found at: %(host)s", "database": "%(database)s"}' % {'host': host,
                                                                                                   'database': sickbeard.NMJv2_DATABASE}
        else:
            return '{"message": "Unable to find NMJ Database at location: %(dbloc)s. Is the right location selected and PCH running?", "database": ""}' % {
                'dbloc': dbloc}

    @staticmethod
    def getTraktToken(trakt_pin=None):

        trakt_api = TraktAPI(sickbeard.SSL_VERIFY, sickbeard.TRAKT_TIMEOUT)
        response = trakt_api.traktToken(trakt_pin)
        if response:
            return 'Trakt Authorized'
        return 'Trakt Not Authorized!'

    @staticmethod
    def testTrakt(username=None, blacklist_name=None):
        return notifiers.trakt_notifier.test_notify(username, blacklist_name)

    @staticmethod
    def loadShowNotifyLists():

        main_db_con = db.DBConnection()
        rows = main_db_con.select('SELECT show_id, show_name, notify_list FROM tv_shows ORDER BY show_name ASC')

        data = {}
        size = 0
        for r in rows:
            NotifyList = {'emails': '', 'prowlAPIs': ''}
            if r[b'notify_list'] and len(r['notify_list']) > 0:
                # First, handle legacy format (emails only)
                if not r[b'notify_list'][0] == '{':
                    NotifyList['emails'] = r[b'notify_list']
                else:
                    NotifyList = dict(ast.literal_eval(r[b'notify_list']))

            data[r[b'show_id']] = {
                'id': r[b'show_id'],
                'name': r[b'show_name'],
                'list': NotifyList['emails'],
                'prowl_notify_list': NotifyList['prowlAPIs']
            }
            size += 1
        data['_size'] = size
        return json.dumps(data)

    @staticmethod
    def saveShowNotifyList(show=None, emails=None, prowlAPIs=None):

        entries = {'emails': '', 'prowlAPIs': ''}
        main_db_con = db.DBConnection()

        # Get current data
        for subs in main_db_con.select(b'SELECT notify_list FROM tv_shows WHERE show_id = ?', [show]):
            if subs[b'notify_list'] and len(subs[b'notify_list']) > 0:
                # First, handle legacy format (emails only)
                if not subs[b'notify_list'][0] == '{':
                    entries['emails'] = subs[b'notify_list']
                else:
                    entries = dict(ast.literal_eval(subs[b'notify_list']))

        if emails is not None:
            entries['emails'] = emails
            if not main_db_con.action('UPDATE tv_shows SET notify_list = ? WHERE show_id = ?', [str(entries), show]):
                return 'ERROR'

        if prowlAPIs is not None:
            entries['prowlAPIs'] = prowlAPIs
            if not main_db_con.action('UPDATE tv_shows SET notify_list = ? WHERE show_id = ?', [str(entries), show]):
                return 'ERROR'

        return 'OK'

    @staticmethod
    def testEmail(host=None, port=None, smtp_from=None, use_tls=None, user=None, pwd=None, to=None):

        host = config.clean_host(host)
        if notifiers.email_notifier.test_notify(host, port, smtp_from, use_tls, user, pwd, to):
            return 'Test email sent successfully! Check inbox.'
        else:
            return 'ERROR: %s' % notifiers.email_notifier.last_err

    @staticmethod
    def testNMA(nma_api=None, nma_priority=0):

        result = notifiers.nma_notifier.test_notify(nma_api, nma_priority)
        if result:
            return 'Test NMA notice sent successfully'
        else:
            return 'Test NMA notice failed'

    @staticmethod
    def testPushalot(authorizationToken=None):

        result = notifiers.pushalot_notifier.test_notify(authorizationToken)
        if result:
            return 'Pushalot notification succeeded. Check your Pushalot clients to make sure it worked'
        else:
            return 'Error sending Pushalot notification'

    @staticmethod
    def testPushbullet(api=None):

        result = notifiers.pushbullet_notifier.test_notify(api)
        if result:
            return 'Pushbullet notification succeeded. Check your device to make sure it worked'
        else:
            return 'Error sending Pushbullet notification'

    @staticmethod
    def getPushbulletDevices(api=None):
        # self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')

        result = notifiers.pushbullet_notifier.get_devices(api)
        if result:
            return result
        else:
            return 'Error sending Pushbullet notification'

    def status(self):
        tvdirFree = helpers.getDiskSpaceUsage(sickbeard.TV_DOWNLOAD_DIR)
        rootDir = {}
        if sickbeard.ROOT_DIRS:
            backend_pieces = sickbeard.ROOT_DIRS.split('|')
            backend_dirs = backend_pieces[1:]
        else:
            backend_dirs = []

        if len(backend_dirs):
            for subject in backend_dirs:
                rootDir[subject] = helpers.getDiskSpaceUsage(subject)

        t = PageTemplate(rh=self, filename='status.mako')
        return t.render(title='Status', header='Status', topmenu='system',
                        tvdirFree=tvdirFree, rootDir=rootDir,
                        controller='home', action='status')

    def shutdown(self, pid=None):
        if not Shutdown.stop(pid):
            return self.redirect('/' + sickbeard.DEFAULT_PAGE + '/')

        title = 'Shutting down'
        message = 'Medusa is shutting down...'

        return self._genericMessage(title, message)

    def restart(self, pid=None):
        if not Restart.restart(pid):
            return self.redirect('/' + sickbeard.DEFAULT_PAGE + '/')

        t = PageTemplate(rh=self, filename='restart.mako')

        return t.render(title='Home', header='Restarting Medusa', topmenu='system',
                        controller='home', action='restart')

    def updateCheck(self, pid=None):
        if str(pid) != str(sickbeard.PID):
            return self.redirect('/home/')

        sickbeard.versionCheckScheduler.action.check_for_new_version(force=True)
        sickbeard.versionCheckScheduler.action.check_for_new_news(force=True)

        return self.redirect('/' + sickbeard.DEFAULT_PAGE + '/')

    def update(self, pid=None, branch=None):

        if str(pid) != str(sickbeard.PID):
            return self.redirect('/home/')

        checkversion = CheckVersion()
        backup = checkversion.updater and checkversion._runbackup()  # pylint: disable=protected-access

        if backup is True:
            if branch:
                checkversion.updater.branch = branch

            if checkversion.updater.need_update() and checkversion.updater.update():
                # do a hard restart
                sickbeard.events.put(sickbeard.events.SystemEvent.RESTART)

                t = PageTemplate(rh=self, filename='restart.mako')
                return t.render(title='Home', header='Restarting Medusa', topmenu='home',
                                controller='home', action='restart')
            else:
                return self._genericMessage('Update Failed',
                                            'Update wasn\'t successful, not restarting. Check your log for more information.')
        else:
            return self.redirect('/' + sickbeard.DEFAULT_PAGE + '/')

    def branchCheckout(self, branch):
        if sickbeard.BRANCH != branch:
            sickbeard.BRANCH = branch
            ui.notifications.message('Checking out branch: ', branch)
            return self.update(sickbeard.PID, branch)
        else:
            ui.notifications.message('Already on branch: ', branch)
            return self.redirect('/' + sickbeard.DEFAULT_PAGE + '/')

    @staticmethod
    def getDBcompare():

        checkversion = CheckVersion()  # TODO: replace with settings var
        db_status = checkversion.getDBcompare()

        if db_status == 'upgrade':
            logger.log(u'Checkout branch has a new DB version - Upgrade', logger.DEBUG)
            return json.dumps({'status': 'success', 'message': 'upgrade'})
        elif db_status == 'equal':
            logger.log(u'Checkout branch has the same DB version - Equal', logger.DEBUG)
            return json.dumps({'status': 'success', 'message': 'equal'})
        elif db_status == 'downgrade':
            logger.log(u'Checkout branch has an old DB version - Downgrade', logger.DEBUG)
            return json.dumps({'status': 'success', 'message': 'downgrade'})
        else:
            logger.log(u'Checkout branch couldn\'t compare DB version.', logger.ERROR)
            return json.dumps({'status': 'error', 'message': 'General exception'})

    def getSeasonSceneExceptions(self, indexer, indexer_id):
        """Get show name scene exceptions per season

        :param indexer: The shows indexer
        :param indexer_id: The shows indexer_id
        :return: A json with the scene exceptions per season.
        """

        exceptions_list = {}

        exceptions_list['seasonExceptions'] = sickbeard.scene_exceptions.get_all_scene_exceptions(indexer_id)

        xem_numbering_season = {tvdb_season_ep[0]: anidb_season_ep[0]
                                for (tvdb_season_ep, anidb_season_ep)
                                in get_xem_numbering_for_show(indexer_id, indexer).iteritems()}

        exceptions_list['xemNumbering'] = xem_numbering_season
        return json.dumps(exceptions_list)

    def displayShow(self, show=None):
        # TODO: add more comprehensive show validation
        try:
            show = int(show)  # fails if show id ends in a period SickRage/sickrage-issues#65
            showObj = Show.find(sickbeard.showList, show)
        except (ValueError, TypeError):
            return self._genericMessage('Error', 'Invalid show ID: %s' % str(show))

        if showObj is None:
            return self._genericMessage('Error', 'Show not in show list')

        main_db_con = db.DBConnection()
        seasonResults = main_db_con.select(
            'SELECT DISTINCT season FROM tv_episodes WHERE showid = ? AND season IS NOT NULL ORDER BY season DESC',
            [showObj.indexerid]
        )

        min_season = 0 if sickbeard.DISPLAY_SHOW_SPECIALS else 1

        sql_results = main_db_con.select(
            'SELECT * FROM tv_episodes WHERE showid = ? and season >= ? ORDER BY season DESC, episode DESC',
            [showObj.indexerid, min_season]
        )

        t = PageTemplate(rh=self, filename='displayShow.mako')
        submenu = [{'title': 'Edit', 'path': 'home/editShow?show=%d' % showObj.indexerid, 'icon': 'ui-icon ui-icon-pencil'}]

        try:
            showLoc = (showObj.location, True)
        except ShowDirectoryNotFoundException:
            showLoc = (showObj._location, False)  # pylint: disable=protected-access

        show_message = ''

        if sickbeard.showQueueScheduler.action.isBeingAdded(showObj):
            show_message = 'This show is in the process of being downloaded - the info below is incomplete.'

        elif sickbeard.showQueueScheduler.action.isBeingUpdated(showObj):
            show_message = 'The information on this page is in the process of being updated.'

        elif sickbeard.showQueueScheduler.action.isBeingRefreshed(showObj):
            show_message = 'The episodes below are currently being refreshed from disk'

        elif sickbeard.showQueueScheduler.action.isBeingSubtitled(showObj):
            show_message = 'Currently downloading subtitles for this show'

        elif sickbeard.showQueueScheduler.action.isInRefreshQueue(showObj):
            show_message = 'This show is queued to be refreshed.'

        elif sickbeard.showQueueScheduler.action.isInUpdateQueue(showObj):
            show_message = 'This show is queued and awaiting an update.'

        elif sickbeard.showQueueScheduler.action.isInSubtitleQueue(showObj):
            show_message = 'This show is queued and awaiting subtitles download.'

        if not sickbeard.showQueueScheduler.action.isBeingAdded(showObj):
            if not sickbeard.showQueueScheduler.action.isBeingUpdated(showObj):
                if showObj.paused:
                    submenu.append({'title': 'Resume', 'path': 'home/togglePause?show=%d' % showObj.indexerid, 'icon': 'ui-icon ui-icon-play'})
                else:
                    submenu.append({'title': 'Pause', 'path': 'home/togglePause?show=%d' % showObj.indexerid, 'icon': 'ui-icon ui-icon-pause'})

                submenu.append({'title': 'Remove', 'path': 'home/deleteShow?show=%d' % showObj.indexerid, 'class': 'removeshow', 'confirm': True, 'icon': 'ui-icon ui-icon-trash'})
                submenu.append({'title': 'Re-scan files', 'path': 'home/refreshShow?show=%d' % showObj.indexerid, 'icon': 'ui-icon ui-icon-refresh'})
                submenu.append({'title': 'Force Full Update', 'path': 'home/updateShow?show=%d&amp;force=1' % showObj.indexerid, 'icon': 'ui-icon ui-icon-transfer-e-w'})
                submenu.append({'title': 'Update show in KODI', 'path': 'home/updateKODI?show=%d' % showObj.indexerid, 'requires': self.haveKODI(), 'icon': 'menu-icon-kodi'})
                submenu.append({'title': 'Update show in Emby', 'path': 'home/updateEMBY?show=%d' % showObj.indexerid, 'requires': self.haveEMBY(), 'icon': 'menu-icon-emby'})
                submenu.append({'title': 'Preview Rename', 'path': 'home/testRename?show=%d' % showObj.indexerid, 'icon': 'ui-icon ui-icon-tag'})

                if sickbeard.USE_SUBTITLES and not sickbeard.showQueueScheduler.action.isBeingSubtitled(
                        showObj) and showObj.subtitles:
                    submenu.append({'title': 'Download Subtitles', 'path': 'home/subtitleShow?show=%d' % showObj.indexerid, 'icon': 'menu-icon-backlog'})

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

        for curResult in sql_results:
            curEpCat = showObj.getOverview(curResult[b'status'])
            if curEpCat:
                epCats[str(curResult[b'season']) + 'x' + str(curResult[b'episode'])] = curEpCat
                epCounts[curEpCat] += 1

        def titler(x):
            return (helpers.remove_article(x), x)[not x or sickbeard.SORT_ARTICLE]

        if sickbeard.ANIME_SPLIT_HOME:
            shows = []
            anime = []
            for show in sickbeard.showList:
                if show.is_anime:
                    anime.append(show)
                else:
                    shows.append(show)
            sortedShowLists = [['Shows', sorted(shows, lambda x, y: cmp(titler(x.name), titler(y.name)))],
                               ['Anime', sorted(anime, lambda x, y: cmp(titler(x.name), titler(y.name)))]]
        else:
            sortedShowLists = [
                ['Shows', sorted(sickbeard.showList, lambda x, y: cmp(titler(x.name), titler(y.name)))]]

        bwl = None
        if showObj.is_anime:
            bwl = showObj.release_groups

        showObj.exceptions = sickbeard.scene_exceptions.get_scene_exceptions(showObj.indexerid)

        indexerid = int(showObj.indexerid)
        indexer = int(showObj.indexer)

        # Delete any previous occurrances
        for index, recentShow in enumerate(sickbeard.SHOWS_RECENT):
            if recentShow['indexerid'] == indexerid:
                del sickbeard.SHOWS_RECENT[index]

        # Only track 5 most recent shows
        del sickbeard.SHOWS_RECENT[4:]

        # Insert most recent show
        sickbeard.SHOWS_RECENT.insert(0, {
            'indexerid': indexerid,
            'name': showObj.name,
        })

        show_words = show_name_helpers.show_words(showObj)

        return t.render(
            submenu=submenu, showLoc=showLoc, show_message=show_message,
            show=showObj, sql_results=sql_results, seasonResults=seasonResults,
            sortedShowLists=sortedShowLists, bwl=bwl, epCounts=epCounts,
            epCats=epCats, all_scene_exceptions=' | '.join(showObj.exceptions),
            scene_numbering=get_scene_numbering_for_show(indexerid, indexer),
            xem_numbering=get_xem_numbering_for_show(indexerid, indexer),
            scene_absolute_numbering=get_scene_absolute_numbering_for_show(indexerid, indexer),
            xem_absolute_numbering=get_xem_absolute_numbering_for_show(indexerid, indexer),
            title=showObj.name,
            controller='home',
            action='displayShow',
            preferred_words=show_words.preferred_words,
            undesired_words=show_words.undesired_words,
            ignore_words=show_words.ignore_words,
            require_words=show_words.require_words
        )

    def pickManualSearch(self, provider=None, rowid=None, manual_search_type='episode'):
        """
        Tries to Perform the snatch for a manualSelected episode, episodes or season pack.

        @param provider: The provider id, passed as usenet_crawler and not the provider name (Usenet-Crawler)
        @param rowid: The provider's cache table's rowid. (currently the implicit sqlites rowid is used, needs to be replaced in future)

        @return: A json with a {'success': true} or false.
        """

        # Try to retrieve the cached result from the providers cache table.
        # TODO: the implicit sqlite rowid is used, should be replaced with an explicit PK column

        try:
            main_db_con = db.DBConnection('cache.db')
            cached_result = main_db_con.action('SELECT * FROM \'%s\' WHERE rowid = ?' %
                                               provider, [rowid], fetchone=True)
        except Exception as e:
            logger.log('Couldn\'t read cached results. Error: {}'.format(e))
            return self._genericMessage('Error', 'Couldn\'t read cached results. Error: {}'.format(e))

        if not cached_result or not all([cached_result[b'url'],
                                         cached_result[b'quality'],
                                         cached_result[b'name'],
                                         cached_result[b'indexerid'],
                                         cached_result[b'season'],
                                         provider]):
            return self._genericMessage('Error', 'Cached result doesn\'t have all needed info to snatch episode')

        if manual_search_type == 'season':
            try:
                main_db_con = db.DBConnection()
                season_pack_episodes_result = main_db_con.action('SELECT episode FROM tv_episodes WHERE showid = ? and season = ?',
                                                                 [cached_result['indexerid'], cached_result['season']])
            except Exception as e:
                logger.log('Couldn\'t read episodes for season pack result. Error: {}'.format(e))
                return self._genericMessage('Error', 'Couldn\'t read episodes for season pack result. Error: {}'.format(e))

            season_pack_episodes = []
            for item in season_pack_episodes_result:
                season_pack_episodes.append(int(item[b'episode']))

        try:
            show = int(cached_result[b'indexerid'])  # fails if show id ends in a period SickRage/sickrage-issues#65
            show_obj = Show.find(sickbeard.showList, show)
        except (ValueError, TypeError):
            return self._genericMessage('Error', 'Invalid show ID: {0}'.format(show))

        if not show_obj:
            return self._genericMessage('Error', 'Could not find a show with id {0} in the list of shows, did you remove the show?'.format(show))

        # Create a list of episode object(s)
        # if multi-episode: |1|2|
        # if single-episode: |1|
        # TODO:  Handle Season Packs: || (no episode)
        episodes = season_pack_episodes if manual_search_type == 'season' else cached_result[b'episodes'].strip('|').split('|')
        ep_objs = []
        for episode in episodes:
            if episode:
                ep_objs.append(show_obj.getEpisode(int(cached_result[b'season']), int(episode)))

        # Create the queue item
        snatch_queue_item = search_queue.ManualSnatchQueueItem(show_obj, ep_objs, provider, cached_result)

        # Add the queue item to the queue
        sickbeard.manualSnatchScheduler.action.add_item(snatch_queue_item)

        while snatch_queue_item.success is not False:
            if snatch_queue_item.started and snatch_queue_item.success:
                # If the snatch was successfull we'll need to update the original searched segment,
                # with the new status: SNATCHED (2)
                update_finished_search_queue_item(snatch_queue_item)
                return json.dumps({'result': 'success'})
            time.sleep(1)

        return json.dumps({'result': 'failure'})

    def manualSearchCheckCache(self, show, season, episode, manual_search_type, **last_prov_updates):
        """ Periodic check if the searchthread is still running for the selected show/season/ep
        and if there are new results in the cache.db
        """

        REFRESH_RESULTS = 'refresh'

        # To prevent it from keeping searching when no providers have been enabled
        if not enabled_providers('manualsearch'):
            return {'result': SEARCH_STATUS_FINISHED}

        main_db_con = db.DBConnection('cache.db')

        episodesInSearch = collectEpisodesFromSearchThread(show)

        # Check if the requested ep is in a search thread
        searched_item = [search for search in episodesInSearch if (str(search.get('show')) == show and
                                                                   str(search.get('season')) == season and
                                                                   str(search.get('episode')) == episode)]

        # No last_prov_updates available, let's assume we need to refresh until we get some
#         if not last_prov_updates:
#             return {'result': REFRESH_RESULTS}

        sql_episode = '' if manual_search_type == 'season' else episode

        for provider, last_update in last_prov_updates.iteritems():
            table_exists = main_db_con.select('SELECT name FROM sqlite_master WHERE type=\'table\' AND name=?', [provider])
            if not table_exists:
                continue
            # Check if the cache table has a result for this show + season + ep wich has a later timestamp, then last_update
            needs_update = main_db_con.select('SELECT * FROM \'%s\' WHERE episodes LIKE ? AND season = ? AND indexerid = ? \
                                              AND time > ?'
                                              % provider, ['%|' + sql_episode + '|%', season, show, int(last_update)])

            if needs_update:
                return {'result': REFRESH_RESULTS}

        # If the item is queued multiple times (don't know if this is posible), but then check if as soon as a search has finished
        # Move on and show results
        # Return a list of queues the episode has been found in
        search_status = [item.get('searchstatus') for item in searched_item]
        if (not len(searched_item) or
            (last_prov_updates and
             SEARCH_STATUS_QUEUED not in search_status and
             SEARCH_STATUS_SEARCHING not in search_status and
             SEARCH_STATUS_FINISHED in search_status)):
                # If the ep not anymore in the QUEUED or SEARCHING Thread, and it has the status finished, return it as finished
                return {'result': SEARCH_STATUS_FINISHED}

        # Force a refresh when the last_prov_updates is empty due to the tables not existing yet.
        # This can be removed if we make sure the provider cache tables always exist prior to the start of the first search
        if not last_prov_updates and SEARCH_STATUS_FINISHED in search_status:
            return {'result': REFRESH_RESULTS}


        return {'result': searched_item[0]['searchstatus']}

    def snatchSelection(self, show=None, season=None, episode=None, manual_search_type='episode',
                        perform_search=0, down_cur_quality=0, show_all_results=0):
        """ The view with results for the manual selected show/episode """

        INDEXER_TVDB = 1
        # TODO: add more comprehensive show validation
        try:
            show = int(show)  # fails if show id ends in a period SickRage/sickrage-issues#65
            showObj = Show.find(sickbeard.showList, show)
        except (ValueError, TypeError):
            return self._genericMessage('Error', 'Invalid show ID: %s' % str(show))

        if showObj is None:
            return self._genericMessage('Error', 'Show not in show list')

        # Retrieve cache results from providers
        search_show = {'show': show, 'season': season, 'episode': episode, 'manual_search_type': manual_search_type}

        provider_results = get_provider_cache_results(INDEXER_TVDB, perform_search=perform_search,
                                                      show_all_results=show_all_results, **search_show)

        t = PageTemplate(rh=self, filename='snatchSelection.mako')
        submenu = [{'title': 'Edit', 'path': 'home/editShow?show=%d' % showObj.indexerid, 'icon': 'ui-icon ui-icon-pencil'}]

        try:
            showLoc = (showObj.location, True)
        except ShowDirectoryNotFoundException:
            showLoc = (showObj._location, False)  # pylint: disable=protected-access

        show_message = sickbeard.showQueueScheduler.action.getQueueActionMessage(showObj)

        if not sickbeard.showQueueScheduler.action.isBeingAdded(showObj):
            if not sickbeard.showQueueScheduler.action.isBeingUpdated(showObj):
                if showObj.paused:
                    submenu.append({'title': 'Resume', 'path': 'home/togglePause?show=%d' % showObj.indexerid, 'icon': 'ui-icon ui-icon-play'})
                else:
                    submenu.append({'title': 'Pause', 'path': 'home/togglePause?show=%d' % showObj.indexerid, 'icon': 'ui-icon ui-icon-pause'})

                submenu.append({'title': 'Remove', 'path': 'home/deleteShow?show=%d' % showObj.indexerid, 'class': 'removeshow', 'confirm': True, 'icon': 'ui-icon ui-icon-trash'})
                submenu.append({'title': 'Re-scan files', 'path': 'home/refreshShow?show=%d' % showObj.indexerid, 'icon': 'ui-icon ui-icon-refresh'})
                submenu.append({'title': 'Force Full Update', 'path': 'home/updateShow?show=%d&amp;force=1' % showObj.indexerid, 'icon': 'ui-icon ui-icon-transfer-e-w'})
                submenu.append({'title': 'Update show in KODI', 'path': 'home/updateKODI?show=%d' % showObj.indexerid, 'requires': self.haveKODI(), 'icon': 'submenu-icon-kodi'})
                submenu.append({'title': 'Update show in Emby', 'path': 'home/updateEMBY?show=%d' % showObj.indexerid, 'requires': self.haveEMBY(), 'icon': 'ui-icon ui-icon-refresh'})
                submenu.append({'title': 'Preview Rename', 'path': 'home/testRename?show=%d' % showObj.indexerid, 'icon': 'ui-icon ui-icon-tag'})

                if sickbeard.USE_SUBTITLES and not sickbeard.showQueueScheduler.action.isBeingSubtitled(
                        showObj) and showObj.subtitles:
                    submenu.append({'title': 'Download Subtitles', 'path': 'home/subtitleShow?show=%d' % showObj.indexerid, 'icon': 'ui-icon ui-icon-comment'})

        def titler(x):
            return (helpers.remove_article(x), x)[not x or sickbeard.SORT_ARTICLE]

        if sickbeard.ANIME_SPLIT_HOME:
            shows = []
            anime = []
            for show in sickbeard.showList:
                if show.is_anime:
                    anime.append(show)
                else:
                    shows.append(show)
            sortedShowLists = [['Shows', sorted(shows, lambda x, y: cmp(titler(x.name), titler(y.name)))],
                               ['Anime', sorted(anime, lambda x, y: cmp(titler(x.name), titler(y.name)))]]
        else:
            sortedShowLists = [
                ['Shows', sorted(sickbeard.showList, lambda x, y: cmp(titler(x.name), titler(y.name)))]]

        bwl = None
        if showObj.is_anime:
            bwl = showObj.release_groups

        showObj.exceptions = sickbeard.scene_exceptions.get_scene_exceptions(showObj.indexerid)

        indexerid = int(showObj.indexerid)
        indexer = int(showObj.indexer)

        # Delete any previous occurrances
        for index, recentShow in enumerate(sickbeard.SHOWS_RECENT):
            if recentShow['indexerid'] == indexerid:
                del sickbeard.SHOWS_RECENT[index]

        # Only track 5 most recent shows
        del sickbeard.SHOWS_RECENT[4:]

        # Insert most recent show
        sickbeard.SHOWS_RECENT.insert(0, {
            'indexerid': indexerid,
            'name': showObj.name,
        })

        episode_history = []
        try:
            main_db_con = db.DBConnection()
            episode_status_result = main_db_con.action('SELECT date, action, provider, resource FROM history WHERE showid = ? AND \
                                                        season = ? AND episode = ? AND (action LIKE \'%02\' OR action LIKE \'%04\'\
                                                        OR action LIKE \'%09\' OR action LIKE \'%11\' OR action LIKE \'%12\') \
                                                        ORDER BY date DESC', [indexerid, season, episode])
            if episode_status_result:
                for item in episode_status_result:
                    episode_history.append(dict(item))
        except Exception as e:
            logger.log('Couldn\'t read latest episode statust. Error: {}'.format(e))

        show_words = show_name_helpers.show_words(showObj)

        return t.render(
            submenu=submenu, showLoc=showLoc, show_message=show_message,
            show=showObj, provider_results=provider_results, episode=episode,
            sortedShowLists=sortedShowLists, bwl=bwl, season=season, manual_search_type=manual_search_type,
            all_scene_exceptions=showObj.exceptions,
            scene_numbering=get_scene_numbering_for_show(indexerid, indexer),
            xem_numbering=get_xem_numbering_for_show(indexerid, indexer),
            scene_absolute_numbering=get_scene_absolute_numbering_for_show(indexerid, indexer),
            xem_absolute_numbering=get_xem_absolute_numbering_for_show(indexerid, indexer),
            title=showObj.name,
            controller='home',
            action='snatchSelection',
            preferred_words=show_words.preferred_words,
            undesired_words=show_words.undesired_words,
            ignore_words=show_words.ignore_words,
            require_words=show_words.require_words,
            episode_history=episode_history
        )


    @staticmethod
    def plotDetails(show, season, episode):
        main_db_con = db.DBConnection()
        result = main_db_con.selectOne(
            b'SELECT description FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?',
            (int(show), int(season), int(episode)))
        return result[b'description'] if result else 'Episode not found.'

    @staticmethod
    def sceneExceptions(show):
        exceptionsList = sickbeard.scene_exceptions.get_all_scene_exceptions(show)
        if not exceptionsList:
            return 'No scene exceptions'

        out = []
        for season, names in iter(sorted(exceptionsList.iteritems())):
            if season == -1:
                season = '*'
            out.append('S' + str(season) + ': ' + ', '.join(names))
        return '<br>'.join(out)

    def editShow(self, show=None, location=None, anyQualities=[], bestQualities=[],
                 exceptions_list=[], flatten_folders=None, paused=None, directCall=False,
                 air_by_date=None, sports=None, dvdorder=None, indexerLang=None,
                 subtitles=None, rls_ignore_words=None, rls_require_words=None,
                 anime=None, blacklist=None, whitelist=None, scene=None,
                 defaultEpStatus=None, quality_preset=None):

        anidb_failed = False
        if show is None:
            errString = 'Invalid show ID: ' + str(show)
            if directCall:
                return [errString]
            else:
                return self._genericMessage('Error', errString)

        showObj = Show.find(sickbeard.showList, int(show))

        if not showObj:
            errString = 'Unable to find the specified show: ' + str(show)
            if directCall:
                return [errString]
            else:
                return self._genericMessage('Error', errString)

        showObj.exceptions = sickbeard.scene_exceptions.get_scene_exceptions(showObj.indexerid)

        if try_int(quality_preset, None):
            bestQualities = []

        if not location and not anyQualities and not bestQualities and not flatten_folders:
            t = PageTemplate(rh=self, filename='editShow.mako')

            if showObj.is_anime:
                whitelist = showObj.release_groups.whitelist
                blacklist = showObj.release_groups.blacklist

                groups = []
                if helpers.set_up_anidb_connection() and not anidb_failed:
                    try:
                        anime = adba.Anime(sickbeard.ADBA_CONNECTION, name=showObj.name)
                        groups = anime.get_groups()
                    except Exception as e:
                        ui.notifications.error('Unable to retreive Fansub Groups from AniDB.')
                        logger.log(u'Unable to retreive Fansub Groups from AniDB. Error is {0}'.format(str(e)), logger.DEBUG)

            with showObj.lock:
                show = showObj
                scene_exceptions = sickbeard.scene_exceptions.get_scene_exceptions(showObj.indexerid)

            if showObj.is_anime:
                return t.render(show=show, scene_exceptions=scene_exceptions, groups=groups, whitelist=whitelist,
                                blacklist=blacklist, title='Edit Show', header='Edit Show', controller='home', action='editShow')
            else:
                return t.render(show=show, scene_exceptions=scene_exceptions, title='Edit Show', header='Edit Show',
                                controller='home', action='editShow')

        flatten_folders = not config.checkbox_to_value(flatten_folders)  # UI inverts this value
        dvdorder = config.checkbox_to_value(dvdorder)
        paused = config.checkbox_to_value(paused)
        air_by_date = config.checkbox_to_value(air_by_date)
        scene = config.checkbox_to_value(scene)
        sports = config.checkbox_to_value(sports)
        anime = config.checkbox_to_value(anime)
        subtitles = config.checkbox_to_value(subtitles)

        if indexerLang and indexerLang in sickbeard.indexerApi(showObj.indexer).indexer().config['valid_languages']:
            indexer_lang = indexerLang
        else:
            indexer_lang = showObj.lang

        # if we changed the language then kick off an update
        if indexer_lang == showObj.lang:
            do_update = False
        else:
            do_update = True

        if scene == showObj.scene and anime == showObj.anime:
            do_update_scene_numbering = False
        else:
            do_update_scene_numbering = True

        if not isinstance(anyQualities, list):
            anyQualities = [anyQualities]

        if not isinstance(bestQualities, list):
            bestQualities = [bestQualities]

        if not isinstance(exceptions_list, list):
            exceptions_list = [exceptions_list]

        # If directCall from mass_edit_update no scene exceptions handling or blackandwhite list handling
        if directCall:
            do_update_exceptions = False
        else:
            if set(exceptions_list) == set(showObj.exceptions):
                do_update_exceptions = False
            else:
                do_update_exceptions = True

            with showObj.lock:
                if anime:
                    if not showObj.release_groups:
                        showObj.release_groups = BlackAndWhiteList(showObj.indexerid)

                    if whitelist:
                        shortwhitelist = short_group_names(whitelist)
                        showObj.release_groups.set_white_keywords(shortwhitelist)
                    else:
                        showObj.release_groups.set_white_keywords([])

                    if blacklist:
                        shortblacklist = short_group_names(blacklist)
                        showObj.release_groups.set_black_keywords(shortblacklist)
                    else:
                        showObj.release_groups.set_black_keywords([])

        errors = []
        with showObj.lock:
            newQuality = Quality.combineQualities([int(q) for q in anyQualities], [int(q) for q in bestQualities])
            showObj.quality = newQuality

            # reversed for now
            if bool(showObj.flatten_folders) != bool(flatten_folders):
                showObj.flatten_folders = flatten_folders
                try:
                    sickbeard.showQueueScheduler.action.refreshShow(showObj)
                except CantRefreshShowException as e:
                    errors.append('Unable to refresh this show: ' + ex(e))

            showObj.paused = paused
            showObj.scene = scene
            showObj.anime = anime
            showObj.sports = sports
            showObj.subtitles = subtitles
            showObj.air_by_date = air_by_date
            showObj.default_ep_status = int(defaultEpStatus)

            if not directCall:
                showObj.lang = indexer_lang
                showObj.dvdorder = dvdorder
                showObj.rls_ignore_words = rls_ignore_words.strip()
                showObj.rls_require_words = rls_require_words.strip()

            location = location.decode('UTF-8')
            # if we change location clear the db of episodes, change it, write to db, and rescan
            if ek(os.path.normpath, showObj._location) != ek(os.path.normpath, location):  # pylint: disable=protected-access
                logger.log(ek(os.path.normpath, showObj._location) + ' != ' + ek(os.path.normpath, location), logger.DEBUG)  # pylint: disable=protected-access
                if not ek(os.path.isdir, location) and not sickbeard.CREATE_MISSING_SHOW_DIRS:
                    errors.append('New location <tt>%s</tt> does not exist' % location)

                # don't bother if we're going to update anyway
                elif not do_update:
                    # change it
                    try:
                        showObj.location = location
                        try:
                            sickbeard.showQueueScheduler.action.refreshShow(showObj)
                        except CantRefreshShowException as e:
                            errors.append('Unable to refresh this show:' + ex(e))
                            # grab updated info from TVDB
                            # showObj.loadEpisodesFromIndexer()
                            # rescan the episodes in the new folder
                    except NoNFOException:
                        errors.append(
                            'The folder at <tt>%s</tt> doesn\'t contain a tvshow.nfo - copy your files to that folder before you change the directory in Medusa.' % location)

            # save it to the DB
            showObj.saveToDB()

        # force the update
        if do_update:
            try:
                sickbeard.showQueueScheduler.action.updateShow(showObj, True)
                time.sleep(cpu_presets[sickbeard.CPU_PRESET])
            except CantUpdateShowException as e:
                errors.append('Unable to update show: {0}'.format(str(e)))

        if do_update_exceptions:
            try:
                sickbeard.scene_exceptions.update_scene_exceptions(showObj.indexerid, exceptions_list)  # @UndefinedVdexerid)
                time.sleep(cpu_presets[sickbeard.CPU_PRESET])
            except CantUpdateShowException:
                errors.append('Unable to force an update on scene exceptions of the show.')

        if do_update_scene_numbering:
            try:
                sickbeard.scene_numbering.xem_refresh(showObj.indexerid, showObj.indexer)
                time.sleep(cpu_presets[sickbeard.CPU_PRESET])
            except CantUpdateShowException:
                errors.append('Unable to force an update on scene numbering of the show.')

            # Must erase cached results when toggling scene numbering
            self.erase_cache(showObj)

        if directCall:
            return errors

        if len(errors) > 0:
            ui.notifications.error('%d error%s while saving changes:' % (len(errors), '' if len(errors) == 1 else 's'),
                                   '<ul>' + '\n'.join(['<li>%s</li>' % error for error in errors]) + '</ul>')

        return self.redirect('/home/displayShow?show=' + show)

    def erase_cache(self, showObj):

        try:
            main_db_con = db.DBConnection('cache.db')
            for cur_provider in sickbeard.providers.sortedProviderList():
                # Let's check if this provider table already exists
                table_exists = main_db_con.select('SELECT name FROM sqlite_master WHERE type=\'table\' AND name=?', [cur_provider.get_id()])
                if not table_exists:
                    continue
                try:
                    main_db_con.action('DELETE FROM \'%s\' WHERE indexerid = ?' % cur_provider.get_id(), [showObj.indexerid])
                except Exception:
                    logger.log(u'Unable to delete cached results for provider {} for show: {}'.format(cur_provider, showObj.name), logger.DEBUG)

        except Exception:
            logger.log(u'Unable to delete cached results for show: {}'.format(showObj.name), logger.DEBUG)

    def togglePause(self, show=None):
        error, show = Show.pause(show)

        if error is not None:
            return self._genericMessage('Error', error)

        ui.notifications.message('%s has been %s' % (show.name, ('resumed', 'paused')[show.paused]))

        return self.redirect('/home/displayShow?show=%i' % show.indexerid)

    def deleteShow(self, show=None, full=0):
        if show:
            error, show = Show.delete(show, full)

            if error is not None:
                return self._genericMessage('Error', error)

            ui.notifications.message(
                '%s has been %s %s' %
                (
                    show.name,
                    ('deleted', 'trashed')[bool(sickbeard.TRASH_REMOVE_SHOW)],
                    ('(media untouched)', '(with all related media)')[bool(full)]
                )
            )

            time.sleep(cpu_presets[sickbeard.CPU_PRESET])

        # Remove show from 'RECENT SHOWS' in 'Shows' menu
        sickbeard.SHOWS_RECENT = [x for x in sickbeard.SHOWS_RECENT if x['indexerid'] != show.indexerid]

        # Don't redirect to the default page, so the user can confirm that the show was deleted
        return self.redirect('/home/')

    def refreshShow(self, show=None):
        error, show = Show.refresh(show)

        # This is a show validation error
        if error is not None and show is None:
            return self._genericMessage('Error', error)

        # This is a refresh error
        if error is not None:
            ui.notifications.error('Unable to refresh this show.', error)

        time.sleep(cpu_presets[sickbeard.CPU_PRESET])

        return self.redirect('/home/displayShow?show=' + str(show.indexerid))

    def updateShow(self, show=None, force=0):

        if show is None:
            return self._genericMessage('Error', 'Invalid show ID')

        showObj = Show.find(sickbeard.showList, int(show))

        if showObj is None:
            return self._genericMessage('Error', 'Unable to find the specified show')

        # force the update
        try:
            sickbeard.showQueueScheduler.action.updateShow(showObj, bool(force))
        except CantUpdateShowException as e:
            ui.notifications.error('Unable to update this show.', ex(e))

        # just give it some time
        time.sleep(cpu_presets[sickbeard.CPU_PRESET])

        return self.redirect('/home/displayShow?show=' + str(showObj.indexerid))

    def subtitleShow(self, show=None, force=0):

        if show is None:
            return self._genericMessage('Error', 'Invalid show ID')

        showObj = Show.find(sickbeard.showList, int(show))

        if showObj is None:
            return self._genericMessage('Error', 'Unable to find the specified show')

        # search and download subtitles
        sickbeard.showQueueScheduler.action.download_subtitles(showObj, bool(force))

        time.sleep(cpu_presets[sickbeard.CPU_PRESET])

        return self.redirect('/home/displayShow?show=' + str(showObj.indexerid))

    def updateKODI(self, show=None):
        showName = None
        showObj = None

        if show:
            showObj = Show.find(sickbeard.showList, int(show))
            if showObj:
                showName = quote_plus(showObj.name.encode('utf-8'))

        if sickbeard.KODI_UPDATE_ONLYFIRST:
            host = sickbeard.KODI_HOST.split(',')[0].strip()
        else:
            host = sickbeard.KODI_HOST

        if notifiers.kodi_notifier.update_library(showName=showName):
            ui.notifications.message('Library update command sent to KODI host(s): ' + host)
        else:
            ui.notifications.error('Unable to contact one or more KODI host(s): ' + host)

        if showObj:
            return self.redirect('/home/displayShow?show=' + str(showObj.indexerid))
        else:
            return self.redirect('/home/')

    def updatePLEX(self):
        if None is notifiers.plex_notifier.update_library():
            ui.notifications.message(
                'Library update command sent to Plex Media Server host: ' + sickbeard.PLEX_SERVER_HOST)
        else:
            ui.notifications.error('Unable to contact Plex Media Server host: ' + sickbeard.PLEX_SERVER_HOST)
        return self.redirect('/home/')

    def updateEMBY(self, show=None):
        showObj = None

        if show:
            showObj = Show.find(sickbeard.showList, int(show))

        if notifiers.emby_notifier.update_library(showObj):
            ui.notifications.message(
                'Library update command sent to Emby host: ' + sickbeard.EMBY_HOST)
        else:
            ui.notifications.error('Unable to contact Emby host: ' + sickbeard.EMBY_HOST)

        if showObj:
            return self.redirect('/home/displayShow?show=' + str(showObj.indexerid))
        else:
            return self.redirect('/home/')

    def setStatus(self, show=None, eps=None, status=None, direct=False):

        if not all([show, eps, status]):
            errMsg = 'You must specify a show and at least one episode'
            if direct:
                ui.notifications.error('Error', errMsg)
                return json.dumps({'result': 'error'})
            else:
                return self._genericMessage('Error', errMsg)

        # Use .has_key() since it is overridden for statusStrings in common.py
        if status not in statusStrings:
            errMsg = 'Invalid status'
            if direct:
                ui.notifications.error('Error', errMsg)
                return json.dumps({'result': 'error'})
            else:
                return self._genericMessage('Error', errMsg)

        showObj = Show.find(sickbeard.showList, int(show))

        if not showObj:
            errMsg = 'Error', 'Show not in show list'
            if direct:
                ui.notifications.error('Error', errMsg)
                return json.dumps({'result': 'error'})
            else:
                return self._genericMessage('Error', errMsg)

        segments = {}
        trakt_data = []
        if eps:

            sql_l = []
            for curEp in eps.split('|'):

                if not curEp:
                    logger.log(u'curEp was empty when trying to setStatus', logger.DEBUG)

                logger.log(u'Attempting to set status on episode ' + curEp + ' to ' + status, logger.DEBUG)

                epInfo = curEp.split('x')

                if not all(epInfo):
                    logger.log(u'Something went wrong when trying to setStatus, epInfo[0]: %s, epInfo[1]: %s' % (epInfo[0], epInfo[1]), logger.DEBUG)
                    continue

                epObj = showObj.getEpisode(epInfo[0], epInfo[1])

                if not epObj:
                    return self._genericMessage('Error', 'Episode couldn\'t be retrieved')

                if int(status) in [WANTED, FAILED]:
                    # figure out what episodes are wanted so we can backlog them
                    if epObj.season in segments:
                        segments[epObj.season].append(epObj)
                    else:
                        segments[epObj.season] = [epObj]

                with epObj.lock:
                    # don't let them mess up UNAIRED episodes
                    if epObj.status == UNAIRED:
                        logger.log(u'Refusing to change status of ' + curEp + ' because it is UNAIRED', logger.WARNING)
                        continue

                    if int(status) in Quality.DOWNLOADED and epObj.status not in Quality.SNATCHED + \
                            Quality.SNATCHED_PROPER + Quality.SNATCHED_BEST + Quality.DOWNLOADED + [IGNORED] and not ek(os.path.isfile, epObj.location):
                        logger.log(u'Refusing to change status of ' + curEp + ' to DOWNLOADED because it\'s not SNATCHED/DOWNLOADED', logger.WARNING)
                        continue

                    if int(status) == FAILED and epObj.status not in Quality.SNATCHED + Quality.SNATCHED_PROPER + \
                            Quality.SNATCHED_BEST + Quality.DOWNLOADED + Quality.ARCHIVED:
                        logger.log(u'Refusing to change status of ' + curEp + ' to FAILED because it\'s not SNATCHED/DOWNLOADED', logger.WARNING)
                        continue

                    if epObj.status in Quality.DOWNLOADED + Quality.ARCHIVED and int(status) == WANTED:
                        logger.log(u'Removing release_name for episode as you want to set a downloaded episode back to wanted, so obviously you want it replaced')
                        epObj.release_name = ''

                    epObj.status = int(status)

                    # mass add to database
                    sql_l.append(epObj.get_sql())

                    trakt_data.append((epObj.season, epObj.episode))

            data = notifiers.trakt_notifier.trakt_episode_data_generate(trakt_data)

            if sickbeard.USE_TRAKT and sickbeard.TRAKT_SYNC_WATCHLIST:
                if int(status) in [WANTED, FAILED]:
                    logger.log(u'Add episodes, showid: indexerid ' + str(showObj.indexerid) + ', Title ' + str(showObj.name) + ' to Watchlist', logger.DEBUG)
                    upd = 'add'
                elif int(status) in [IGNORED, SKIPPED] + Quality.DOWNLOADED + Quality.ARCHIVED:
                    logger.log(u'Remove episodes, showid: indexerid ' + str(showObj.indexerid) + ', Title ' + str(showObj.name) + ' from Watchlist', logger.DEBUG)
                    upd = 'remove'

                if data:
                    notifiers.trakt_notifier.update_watchlist(showObj, data_episode=data, update=upd)

            if len(sql_l) > 0:
                main_db_con = db.DBConnection()
                main_db_con.mass_action(sql_l)

        if int(status) == WANTED and not showObj.paused:
            msg = 'Backlog was automatically started for the following seasons of <b>' + showObj.name + '</b>:<br>'
            msg += '<ul>'

            for season, segment in segments.iteritems():
                cur_backlog_queue_item = search_queue.BacklogQueueItem(showObj, segment)
                sickbeard.searchQueueScheduler.action.add_item(cur_backlog_queue_item)

                msg += '<li>Season ' + str(season) + '</li>'
                logger.log(u'Sending backlog for ' + showObj.name + ' season ' + str(
                    season) + ' because some eps were set to wanted')

            msg += '</ul>'

            if segments:
                ui.notifications.message('Backlog started', msg)
        elif int(status) == WANTED and showObj.paused:
            logger.log(u'Some episodes were set to wanted, but ' + showObj.name + ' is paused. Not adding to Backlog until show is unpaused')

        if int(status) == FAILED:
            msg = 'Retrying Search was automatically started for the following season of <b>' + showObj.name + '</b>:<br>'
            msg += '<ul>'

            for season, segment in segments.iteritems():
                cur_failed_queue_item = search_queue.FailedQueueItem(showObj, segment)
                sickbeard.searchQueueScheduler.action.add_item(cur_failed_queue_item)

                msg += '<li>Season ' + str(season) + '</li>'
                logger.log(u'Retrying Search for ' + showObj.name + ' season ' + str(
                    season) + ' because some eps were set to failed')

            msg += '</ul>'

            if segments:
                ui.notifications.message('Retry Search started', msg)

        if direct:
            return json.dumps({'result': 'success'})
        else:
            return self.redirect('/home/displayShow?show=' + show)

    def testRename(self, show=None):

        if show is None:
            return self._genericMessage('Error', 'You must specify a show')

        showObj = Show.find(sickbeard.showList, int(show))

        if showObj is None:
            return self._genericMessage('Error', 'Show not in show list')

        try:
            showObj.location  # @UnusedVariable
        except ShowDirectoryNotFoundException:
            return self._genericMessage('Error', 'Can\'t rename episodes when the show dir is missing.')

        ep_obj_list = showObj.getAllEpisodes(has_location=True)
        ep_obj_list = [x for x in ep_obj_list if x.location]
        ep_obj_rename_list = []
        for ep_obj in ep_obj_list:
            has_already = False
            for check in ep_obj.relatedEps + [ep_obj]:
                if check in ep_obj_rename_list:
                    has_already = True
                    break
            if not has_already:
                ep_obj_rename_list.append(ep_obj)

        if ep_obj_rename_list:
            ep_obj_rename_list.reverse()

        t = PageTemplate(rh=self, filename='testRename.mako')
        submenu = [{'title': 'Edit', 'path': 'home/editShow?show=%d' % showObj.indexerid, 'icon': 'ui-icon ui-icon-pencil'}]

        return t.render(submenu=submenu, ep_obj_list=ep_obj_rename_list,
                        show=showObj, title='Preview Rename',
                        header='Preview Rename',
                        controller='home', action='previewRename')

    def doRename(self, show=None, eps=None):
        if show is None or eps is None:
            errMsg = 'You must specify a show and at least one episode'
            return self._genericMessage('Error', errMsg)

        show_obj = Show.find(sickbeard.showList, int(show))

        if show_obj is None:
            errMsg = 'Error', 'Show not in show list'
            return self._genericMessage('Error', errMsg)

        try:
            show_obj.location  # @UnusedVariable
        except ShowDirectoryNotFoundException:
            return self._genericMessage('Error', 'Can\'t rename episodes when the show dir is missing.')

        if eps is None:
            return self.redirect('/home/displayShow?show=' + show)

        main_db_con = db.DBConnection()
        for curEp in eps.split('|'):

            epInfo = curEp.split('x')

            # this is probably the worst possible way to deal with double eps but I've kinda painted myself into a corner here with this stupid database
            ep_result = main_db_con.select(
                'SELECT location FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ? AND 5=5',
                [show, epInfo[0], epInfo[1]])
            if not ep_result:
                logger.log(u'Unable to find an episode for ' + curEp + ', skipping', logger.WARNING)
                continue
            related_eps_result = main_db_con.select(
                b'SELECT season, episode FROM tv_episodes WHERE location = ? AND episode != ?',
                [ep_result[0][b'location'], epInfo[1]]
            )

            root_ep_obj = show_obj.getEpisode(epInfo[0], epInfo[1])
            root_ep_obj.relatedEps = []

            for cur_related_ep in related_eps_result:
                related_ep_obj = show_obj.getEpisode(cur_related_ep[b'season'], cur_related_ep[b'episode'])
                if related_ep_obj not in root_ep_obj.relatedEps:
                    root_ep_obj.relatedEps.append(related_ep_obj)

            root_ep_obj.rename()

        return self.redirect('/home/displayShow?show=' + show)

    def searchEpisode(self, show=None, season=None, episode=None, manual_search=None):
        """Search a ForcedSearch single episode using providers which are backlog enabled"""
        down_cur_quality = 0

        # retrieve the episode object and fail if we can't get one
        ep_obj = getEpisode(show, season, episode)
        if isinstance(ep_obj, str):
            return json.dumps({'result': 'failure'})

        # make a queue item for it and put it on the queue
        ep_queue_item = search_queue.ForcedSearchQueueItem(ep_obj.show, [ep_obj], bool(int(down_cur_quality)), bool(manual_search))

        sickbeard.forcedSearchQueueScheduler.action.add_item(ep_queue_item)

        # give the CPU a break and some time to start the queue
        time.sleep(cpu_presets[sickbeard.CPU_PRESET])

        if not ep_queue_item.started and ep_queue_item.success is None:
            return json.dumps(
                {'result': 'success'})  # I Actually want to call it queued, because the search hasnt been started yet!
        if ep_queue_item.started and ep_queue_item.success is None:
            return json.dumps({'result': 'success'})
        else:
            return json.dumps({'result': 'failure'})

    # ## Returns the current ep_queue_item status for the current viewed show.
    # Possible status: Downloaded, Snatched, etc...
    # Returns {'show': 279530, 'episodes' : ['episode' : 6, 'season' : 1, 'searchstatus' : 'queued', 'status' : 'running', 'quality': '4013']
    def getManualSearchStatus(self, show=None):

        episodes = collectEpisodesFromSearchThread(show)

        return json.dumps({'episodes': episodes})

    def searchEpisodeSubtitles(self, show=None, season=None, episode=None):
        # retrieve the episode object and fail if we can't get one
        ep_obj = getEpisode(show, season, episode)
        if isinstance(ep_obj, str):
            return json.dumps({'result': 'failure'})

        try:
            new_subtitles = ep_obj.download_subtitles()  # pylint: disable=no-member
        except Exception:
            return json.dumps({'result': 'failure'})

        if new_subtitles:
            new_languages = [subtitles.name_from_code(code) for code in new_subtitles]
            status = 'New subtitles downloaded: %s' % ', '.join(new_languages)
        else:
            status = 'No subtitles downloaded'

        ui.notifications.message(ep_obj.show.name, status)  # pylint: disable=no-member
        return json.dumps({'result': status, 'subtitles': ','.join(ep_obj.subtitles)})  # pylint: disable=no-member

    def setSceneNumbering(self, show, indexer, forSeason=None, forEpisode=None, forAbsolute=None, sceneSeason=None,
                          sceneEpisode=None, sceneAbsolute=None):

        # sanitize:
        if forSeason in ['null', '']:
            forSeason = None
        if forEpisode in ['null', '']:
            forEpisode = None
        if forAbsolute in ['null', '']:
            forAbsolute = None
        if sceneSeason in ['null', '']:
            sceneSeason = None
        if sceneEpisode in ['null', '']:
            sceneEpisode = None
        if sceneAbsolute in ['null', '']:
            sceneAbsolute = None

        showObj = Show.find(sickbeard.showList, int(show))

        # Check if this is an anime, because we can't set the Scene numbering for anime shows
        if showObj.is_anime and not forAbsolute:
            result = {
                'success': False,
                'errorMessage': 'You can\'t use the Scene numbering for anime shows. ' +
                'Use the Scene Absolute field, to configure a diverging episode number.',
                'sceneSeason': None,
                'sceneAbsolute': None
            }
            return json.dumps(result)
        elif showObj.is_anime:
            result = {
                'success': True,
                'forAbsolute': forAbsolute,
            }
        else:
            result = {
                'success': True,
                'forSeason': forSeason,
                'forEpisode': forEpisode,
            }

        # retrieve the episode object and fail if we can't get one
        if showObj.is_anime:
            ep_obj = getEpisode(show, absolute=forAbsolute)
        else:
            ep_obj = getEpisode(show, forSeason, forEpisode)

        if isinstance(ep_obj, str):
            result['success'] = False
            result['errorMessage'] = ep_obj
        elif showObj.is_anime:
            logger.log(u'setAbsoluteSceneNumbering for %s from %s to %s' %
                       (show, forAbsolute, sceneAbsolute), logger.DEBUG)

            show = int(show)
            indexer = int(indexer)
            forAbsolute = int(forAbsolute)
            if sceneAbsolute is not None:
                sceneAbsolute = int(sceneAbsolute)

            set_scene_numbering(show, indexer, absolute_number=forAbsolute, sceneAbsolute=sceneAbsolute)
        else:
            logger.log(u'setEpisodeSceneNumbering for %s from %sx%s to %sx%s' %
                       (show, forSeason, forEpisode, sceneSeason, sceneEpisode), logger.DEBUG)

            show = int(show)
            indexer = int(indexer)
            forSeason = int(forSeason)
            forEpisode = int(forEpisode)
            if sceneSeason is not None:
                sceneSeason = int(sceneSeason)
            if sceneEpisode is not None:
                sceneEpisode = int(sceneEpisode)

            set_scene_numbering(show, indexer, season=forSeason, episode=forEpisode, sceneSeason=sceneSeason,
                                sceneEpisode=sceneEpisode)

        if showObj.is_anime:
            sn = get_scene_absolute_numbering(show, indexer, forAbsolute)
            if sn:
                result['sceneAbsolute'] = sn
            else:
                result['sceneAbsolute'] = None
        else:
            sn = get_scene_numbering(show, indexer, forSeason, forEpisode)
            if sn:
                (result['sceneSeason'], result['sceneEpisode']) = sn
            else:
                (result['sceneSeason'], result['sceneEpisode']) = (None, None)

        return json.dumps(result)

    def retryEpisode(self, show, season, episode, down_cur_quality=0):
        # retrieve the episode object and fail if we can't get one
        ep_obj = getEpisode(show, season, episode)
        if isinstance(ep_obj, str):
            return json.dumps({'result': 'failure'})

        # make a queue item for it and put it on the queue
        ep_queue_item = search_queue.FailedQueueItem(ep_obj.show, [ep_obj], bool(int(down_cur_quality)))  # pylint: disable=no-member
        sickbeard.forcedSearchQueueScheduler.action.add_item(ep_queue_item)

        if not ep_queue_item.started and ep_queue_item.success is None:
            return json.dumps(
                {'result': 'success'})  # Search has not been started yet!
        if ep_queue_item.started and ep_queue_item.success is None:
            return json.dumps({'result': 'success'})
        else:
            return json.dumps({'result': 'failure'})

    @staticmethod
    def fetch_releasegroups(show_name):
        logger.log(u'ReleaseGroups: %s' % show_name, logger.INFO)
        if helpers.set_up_anidb_connection():
            try:
                anime = adba.Anime(sickbeard.ADBA_CONNECTION, name=show_name)
                groups = anime.get_groups()
                logger.log(u'ReleaseGroups: %s' % groups, logger.INFO)
                return json.dumps({'result': 'success', 'groups': groups})
            except AttributeError as error:
                logger.log(u'Unable to get ReleaseGroups: %s' % error, logger.DEBUG)

        return json.dumps({'result': 'failure'})
