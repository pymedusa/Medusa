# coding=utf-8

import ast
import datetime
import os
import re
import time

import adba
from libtrakt import TraktAPI
from libtrakt.exceptions import traktException
import markdown2
from requests.compat import unquote_plus, quote_plus
from tornado.routes import route

import sickbeard
from sickbeard import (
    classes, clients, config, db, helpers, logger,
    notifiers, processTV, sab, search_queue,
    subtitles, ui, show_name_helpers
)
from sickbeard.blackandwhitelist import BlackAndWhiteList, short_group_names
from sickbeard.common import (
    cpu_presets, Overview, Quality, statusStrings,
    UNAIRED, IGNORED, WANTED, FAILED, SKIPPED
)
from sickbeard.helpers import get_showname_from_indexer
from sickbeard.imdbPopular import imdb_popular
from sickbeard.indexers.indexer_exceptions import indexer_exception
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
    sanitize_filename, try_int, enabled_providers,
)
from sickrage.helper.encoding import ek, ss
from sickrage.helper.exceptions import (
    ex,
    CantRefreshShowException,
    CantUpdateShowException,
    MultipleShowObjectsException,
    NoNFOException,
    ShowDirectoryNotFoundException,
)
from sickrage.show.Show import Show
from sickrage.system.Restart import Restart
from sickrage.system.Shutdown import Shutdown
from sickbeard.tv import TVEpisode
from sickbeard.server.web.core import WebRoot, PageTemplate


# Conditional imports
try:
    import json
except ImportError:
    import simplejson as json


@route('/home(/?.*)')
class Home(WebRoot):
    def __init__(self, *args, **kwargs):
        super(Home, self).__init__(*args, **kwargs)

    def _genericMessage(self, subject, message):
        t = PageTemplate(rh=self, filename="genericMessage.mako")
        return t.render(message=message, subject=subject, topmenu="home", title="")

    def index(self):
        t = PageTemplate(rh=self, filename="home.mako")
        if sickbeard.ANIME_SPLIT_HOME:
            shows = []
            anime = []
            for show in sickbeard.showList:
                if show.is_anime:
                    anime.append(show)
                else:
                    shows.append(show)
            showlists = [["Shows", shows], ["Anime", anime]]
        else:
            showlists = [["Shows", sickbeard.showList]]

        stats = self.show_statistics()
        return t.render(title="Home", header="Show List", topmenu="home", showlists=showlists, show_stat=stats[0], max_download_count=stats[1], controller="home", action="index")

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
            show_stat[cur_result['showid']] = cur_result
            if cur_result['ep_total'] > max_download_count:
                max_download_count = cur_result['ep_total']

        max_download_count *= 100

        return show_stat, max_download_count

    def is_alive(self, *args, **kwargs):
        if 'callback' in kwargs and '_' in kwargs:
            callback, _ = kwargs['callback'], kwargs['_']
        else:
            return "Error: Unsupported Request. Send jsonp request with 'callback' variable in the query string."

        # self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')
        self.set_header('Content-Type', 'text/javascript')
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Headers', 'x-requested-with')

        if sickbeard.started:
            return callback + '(' + json.dumps(
                {"msg": str(sickbeard.PID)}) + ');'
        else:
            return callback + '(' + json.dumps({"msg": "nope"}) + ');'

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
                return "Success. Connected and authenticated"
            else:
                return "Authentication failed. SABnzbd expects '" + accesMsg + "' as authentication method, '" + authMsg + "'"
        else:
            return "Unable to connect to host"

    @staticmethod
    def testTorrent(torrent_method=None, host=None, username=None, password=None):

        host = config.clean_url(host)

        client = clients.getClientIstance(torrent_method)

        _, accesMsg = client(host, username, password).testAuthentication()

        return accesMsg

    @staticmethod
    def testFreeMobile(freemobile_id=None, freemobile_apikey=None):

        result, message = notifiers.freemobile_notifier.test_notify(freemobile_id, freemobile_apikey)
        if result:
            return "SMS sent successfully"
        else:
            return "Problem sending SMS: " + message

    @staticmethod
    def testTelegram(telegram_id=None, telegram_apikey=None):

        result, message = notifiers.telegram_notifier.test_notify(telegram_id, telegram_apikey)
        if result:
            return "Telegram notification succeeded. Check your Telegram clients to make sure it worked"
        else:
            return "Error sending Telegram notification: " + message

    @staticmethod
    def testGrowl(host=None, password=None):
        # self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')

        host = config.clean_host(host, default_port=23053)

        result = notifiers.growl_notifier.test_notify(host, password)
        if password is None or password == '':
            pw_append = ''
        else:
            pw_append = " with password: " + password

        if result:
            return "Registered and Tested growl successfully " + unquote_plus(host) + pw_append
        else:
            return "Registration and Testing of growl failed " + unquote_plus(host) + pw_append

    @staticmethod
    def testProwl(prowl_api=None, prowl_priority=0):

        result = notifiers.prowl_notifier.test_notify(prowl_api, prowl_priority)
        if result:
            return "Test prowl notice sent successfully"
        else:
            return "Test prowl notice failed"

    @staticmethod
    def testBoxcar2(accesstoken=None):

        result = notifiers.boxcar2_notifier.test_notify(accesstoken)
        if result:
            return "Boxcar2 notification succeeded. Check your Boxcar2 clients to make sure it worked"
        else:
            return "Error sending Boxcar2 notification"

    @staticmethod
    def testPushover(userKey=None, apiKey=None):

        result = notifiers.pushover_notifier.test_notify(userKey, apiKey)
        if result:
            return "Pushover notification succeeded. Check your Pushover clients to make sure it worked"
        else:
            return "Error sending Pushover notification"

    @staticmethod
    def twitterStep1():
        return notifiers.twitter_notifier._get_authorization()  # pylint: disable=protected-access

    @staticmethod
    def twitterStep2(key):

        result = notifiers.twitter_notifier._get_credentials(key)  # pylint: disable=protected-access
        logger.log(u"result: " + str(result))
        if result:
            return "Key verification successful"
        else:
            return "Unable to verify key"

    @staticmethod
    def testTwitter():

        result = notifiers.twitter_notifier.test_notify()
        if result:
            return "Tweet successful, check your twitter to make sure it worked"
        else:
            return "Error sending tweet"

    @staticmethod
    def testKODI(host=None, username=None, password=None):

        host = config.clean_hosts(host)
        finalResult = ''
        for curHost in [x.strip() for x in host.split(",")]:
            curResult = notifiers.kodi_notifier.test_notify(unquote_plus(curHost), username, password)
            if len(curResult.split(":")) > 2 and 'OK' in curResult.split(":")[2]:
                finalResult += "Test KODI notice sent successfully to " + unquote_plus(curHost)
            else:
                finalResult += "Test KODI notice failed to " + unquote_plus(curHost)
            finalResult += "<br>\n"

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
            return "Tried sending desktop notification via libnotify"
        else:
            return notifiers.libnotify.diagnose()

    @staticmethod
    def testEMBY(host=None, emby_apikey=None):

        host = config.clean_host(host)
        result = notifiers.emby_notifier.test_notify(unquote_plus(host), emby_apikey)
        if result:
            return "Test notice sent successfully to " + unquote_plus(host)
        else:
            return "Test notice failed to " + unquote_plus(host)

    @staticmethod
    def testNMJ(host=None, database=None, mount=None):

        host = config.clean_host(host)
        result = notifiers.nmj_notifier.test_notify(unquote_plus(host), database, mount)
        if result:
            return "Successfully started the scan update"
        else:
            return "Test failed to start the scan update"

    @staticmethod
    def settingsNMJ(host=None):

        host = config.clean_host(host)
        result = notifiers.nmj_notifier.notify_settings(unquote_plus(host))
        if result:
            return '{"message": "Got settings from %(host)s", "database": "%(database)s", "mount": "%(mount)s"}' % {
                "host": host, "database": sickbeard.NMJ_DATABASE, "mount": sickbeard.NMJ_MOUNT}
        else:
            return '{"message": "Failed! Make sure your Popcorn is on and NMJ is running. (see Log & Errors -> Debug for detailed info)", "database": "", "mount": ""}'

    @staticmethod
    def testNMJv2(host=None):

        host = config.clean_host(host)
        result = notifiers.nmjv2_notifier.test_notify(unquote_plus(host))
        if result:
            return "Test notice sent successfully to " + unquote_plus(host)
        else:
            return "Test notice failed to " + unquote_plus(host)

    @staticmethod
    def settingsNMJv2(host=None, dbloc=None, instance=None):

        host = config.clean_host(host)
        result = notifiers.nmjv2_notifier.notify_settings(unquote_plus(host), dbloc, instance)
        if result:
            return '{"message": "NMJ Database found at: %(host)s", "database": "%(database)s"}' % {"host": host,
                                                                                                   "database": sickbeard.NMJv2_DATABASE}
        else:
            return '{"message": "Unable to find NMJ Database at location: %(dbloc)s. Is the right location selected and PCH running?", "database": ""}' % {
                "dbloc": dbloc}

    @staticmethod
    def getTraktToken(trakt_pin=None):

        trakt_api = TraktAPI(sickbeard.SSL_VERIFY, sickbeard.TRAKT_TIMEOUT)
        response = trakt_api.traktToken(trakt_pin)
        if response:
            return "Trakt Authorized"
        return "Trakt Not Authorized!"

    @staticmethod
    def testTrakt(username=None, blacklist_name=None):
        return notifiers.trakt_notifier.test_notify(username, blacklist_name)

    @staticmethod
    def loadShowNotifyLists():

        main_db_con = db.DBConnection()
        rows = main_db_con.select("SELECT show_id, show_name, notify_list FROM tv_shows ORDER BY show_name ASC")

        data = {}
        size = 0
        for r in rows:
            NotifyList = {'emails': '', 'prowlAPIs': ''}
            if r['notify_list'] and len(r['notify_list']) > 0:
                # First, handle legacy format (emails only)
                if not r['notify_list'][0] == '{':
                    NotifyList['emails'] = r['notify_list']
                else:
                    NotifyList = dict(ast.literal_eval(r['notify_list']))

            data[r['show_id']] = {
                'id': r['show_id'],
                'name': r['show_name'],
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
        for subs in main_db_con.select("SELECT notify_list FROM tv_shows WHERE show_id = ?", [show]):
            if subs['notify_list'] and len(subs['notify_list']) > 0:
                # First, handle legacy format (emails only)
                if not subs['notify_list'][0] == '{':
                    entries['emails'] = subs['notify_list']
                else:
                    entries = dict(ast.literal_eval(subs['notify_list']))

        if emails is not None:
            entries['emails'] = emails
            if not main_db_con.action("UPDATE tv_shows SET notify_list = ? WHERE show_id = ?", [str(entries), show]):
                return 'ERROR'

        if prowlAPIs is not None:
            entries['prowlAPIs'] = prowlAPIs
            if not main_db_con.action("UPDATE tv_shows SET notify_list = ? WHERE show_id = ?", [str(entries), show]):
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
            return "Test NMA notice sent successfully"
        else:
            return "Test NMA notice failed"

    @staticmethod
    def testPushalot(authorizationToken=None):

        result = notifiers.pushalot_notifier.test_notify(authorizationToken)
        if result:
            return "Pushalot notification succeeded. Check your Pushalot clients to make sure it worked"
        else:
            return "Error sending Pushalot notification"

    @staticmethod
    def testPushbullet(api=None):

        result = notifiers.pushbullet_notifier.test_notify(api)
        if result:
            return "Pushbullet notification succeeded. Check your device to make sure it worked"
        else:
            return "Error sending Pushbullet notification"

    @staticmethod
    def getPushbulletDevices(api=None):
        # self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')

        result = notifiers.pushbullet_notifier.get_devices(api)
        if result:
            return result
        else:
            return "Error sending Pushbullet notification"

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

        t = PageTemplate(rh=self, filename="status.mako")
        return t.render(title='Status', header='Status', topmenu='system',
                        tvdirFree=tvdirFree, rootDir=rootDir,
                        controller="home", action="status")

    def shutdown(self, pid=None):
        if not Shutdown.stop(pid):
            return self.redirect('/' + sickbeard.DEFAULT_PAGE + '/')

        title = "Shutting down"
        message = "Medusa is shutting down..."

        return self._genericMessage(title, message)

    def restart(self, pid=None):
        if not Restart.restart(pid):
            return self.redirect('/' + sickbeard.DEFAULT_PAGE + '/')

        t = PageTemplate(rh=self, filename="restart.mako")

        return t.render(title="Home", header="Restarting Medusa", topmenu="system",
                        controller="home", action="restart")

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

                t = PageTemplate(rh=self, filename="restart.mako")
                return t.render(title="Home", header="Restarting Medusa", topmenu="home",
                                controller="home", action="restart")
            else:
                return self._genericMessage("Update Failed",
                                            "Update wasn't successful, not restarting. Check your log for more information.")
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
            logger.log(u"Checkout branch has a new DB version - Upgrade", logger.DEBUG)
            return json.dumps({"status": "success", 'message': 'upgrade'})
        elif db_status == 'equal':
            logger.log(u"Checkout branch has the same DB version - Equal", logger.DEBUG)
            return json.dumps({"status": "success", 'message': 'equal'})
        elif db_status == 'downgrade':
            logger.log(u"Checkout branch has an old DB version - Downgrade", logger.DEBUG)
            return json.dumps({"status": "success", 'message': 'downgrade'})
        else:
            logger.log(u"Checkout branch couldn't compare DB version.", logger.ERROR)
            return json.dumps({"status": "error", 'message': 'General exception'})

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
            return self._genericMessage("Error", "Invalid show ID: %s" % str(show))

        if showObj is None:
            return self._genericMessage("Error", "Show not in show list")

        main_db_con = db.DBConnection()
        seasonResults = main_db_con.select(
            "SELECT DISTINCT season FROM tv_episodes WHERE showid = ? AND season IS NOT NULL ORDER BY season DESC",
            [showObj.indexerid]
        )

        min_season = 0 if sickbeard.DISPLAY_SHOW_SPECIALS else 1

        sql_results = main_db_con.select(
            "SELECT * FROM tv_episodes WHERE showid = ? and season >= ? ORDER BY season DESC, episode DESC",
            [showObj.indexerid, min_season]
        )

        t = PageTemplate(rh=self, filename="displayShow.mako")
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
            curEpCat = showObj.getOverview(curResult["status"])
            if curEpCat:
                epCats[str(curResult["season"]) + "x" + str(curResult["episode"])] = curEpCat
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
            sortedShowLists = [["Shows", sorted(shows, lambda x, y: cmp(titler(x.name), titler(y.name)))],
                               ["Anime", sorted(anime, lambda x, y: cmp(titler(x.name), titler(y.name)))]]
        else:
            sortedShowLists = [
                ["Shows", sorted(sickbeard.showList, lambda x, y: cmp(titler(x.name), titler(y.name)))]]

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
            epCats=epCats, all_scene_exceptions=showObj.exceptions,
            scene_numbering=get_scene_numbering_for_show(indexerid, indexer),
            xem_numbering=get_xem_numbering_for_show(indexerid, indexer),
            scene_absolute_numbering=get_scene_absolute_numbering_for_show(indexerid, indexer),
            xem_absolute_numbering=get_xem_absolute_numbering_for_show(indexerid, indexer),
            title=showObj.name,
            controller="home",
            action="displayShow",
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
            cached_result = main_db_con.action("SELECT * FROM '%s' WHERE rowid = ?" %
                                               provider, [rowid], fetchone=True)
        except Exception as e:
            logger.log("Couldn't read cached results. Error: {}".format(e))
            return self._genericMessage("Error", "Couldn't read cached results. Error: {}".format(e))

        if not cached_result or not all([cached_result['url'],
                                         cached_result['quality'],
                                         cached_result['name'],
                                         cached_result['indexerid'],
                                         cached_result['season'],
                                         provider]):
            return self._genericMessage("Error", "Cached result doesn't have all needed info to snatch episode")

        if manual_search_type == 'season':
            try:
                main_db_con = db.DBConnection()
                season_pack_episodes_result = main_db_con.action("SELECT episode FROM tv_episodes WHERE showid = ? and season = ?",
                                                                 [cached_result['indexerid'], cached_result['season']])
            except Exception as e:
                logger.log("Couldn't read episodes for season pack result. Error: {}".format(e))
                return self._genericMessage("Error", "Couldn't read episodes for season pack result. Error: {}".format(e))

            season_pack_episodes = []
            for item in season_pack_episodes_result:
                season_pack_episodes.append(int(item['episode']))

        try:
            show = int(cached_result['indexerid'])  # fails if show id ends in a period SickRage/sickrage-issues#65
            show_obj = Show.find(sickbeard.showList, show)
        except (ValueError, TypeError):
            return self._genericMessage("Error", "Invalid show ID: {0}".format(show))

        if not show_obj:
            return self._genericMessage("Error", "Could not find a show with id {0} in the list of shows, did you remove the show?".format(show))

        # Create a list of episode object(s)
        # if multi-episode: |1|2|
        # if single-episode: |1|
        # TODO:  Handle Season Packs: || (no episode)
        episodes = season_pack_episodes if manual_search_type == 'season' else cached_result['episodes'].strip("|").split("|")
        ep_objs = []
        for episode in episodes:
            if episode:
                ep_objs.append(TVEpisode(show_obj, int(cached_result['season']), int(episode)))

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

    def manualSearchCheckCache(self, show, season, episode, manual_search_type, **kwargs):
        """ Periodic check if the searchthread is still running for the selected show/season/ep
        and if there are new results in the cache.db
        """

        REFRESH_RESULTS = 'refresh'

        # To prevent it from keeping searching when no providers have been enabled
        if not enabled_providers('manualsearch'):
            return {'result': SEARCH_STATUS_FINISHED}

        # Let's try to get the timestamps for the last search per provider
        if kwargs:
            # Only need the first provided dict
            last_prov_updates = kwargs.iteritems().next()[0]
            last_prov_updates = json.loads(last_prov_updates.replace("'", '"'))
        else:
            last_prov_updates = {}

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
            table_exists = main_db_con.select("SELECT name FROM sqlite_master WHERE type='table' AND name=?", [provider])
            if not table_exists:
                continue
            # Check if the cache table has a result for this show + season + ep wich has a later timestamp, then last_update
            needs_update = main_db_con.select("SELECT * FROM '%s' WHERE episodes LIKE ? AND season = ? AND indexerid = ? \
                                              AND time > ?"
                                              % provider, ["%|" + sql_episode + "|%", season, show, int(last_update)])

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

    def snatchSelection(self, show=None, season=None, episode=None, manual_search_type="episode",
                        perform_search=0, down_cur_quality=0, show_all_results=0):
        """ The view with results for the manual selected show/episode """

        INDEXER_TVDB = 1
        # TODO: add more comprehensive show validation
        try:
            show = int(show)  # fails if show id ends in a period SickRage/sickrage-issues#65
            showObj = Show.find(sickbeard.showList, show)
        except (ValueError, TypeError):
            return self._genericMessage("Error", "Invalid show ID: %s" % str(show))

        if showObj is None:
            return self._genericMessage("Error", "Show not in show list")

        # Retrieve cache results from providers
        search_show = {'show': show, 'season': season, 'episode': episode, 'manual_search_type': manual_search_type}

        provider_results = get_provider_cache_results(INDEXER_TVDB, perform_search=perform_search,
                                                      show_all_results=show_all_results, **search_show)

        t = PageTemplate(rh=self, filename="snatchSelection.mako")
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
            sortedShowLists = [["Shows", sorted(shows, lambda x, y: cmp(titler(x.name), titler(y.name)))],
                               ["Anime", sorted(anime, lambda x, y: cmp(titler(x.name), titler(y.name)))]]
        else:
            sortedShowLists = [
                ["Shows", sorted(sickbeard.showList, lambda x, y: cmp(titler(x.name), titler(y.name)))]]

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
            episode_status_result = main_db_con.action("SELECT date, action, provider, resource FROM history WHERE showid = ? AND \
                                                        season = ? AND episode = ? AND (action LIKE '%02' OR action LIKE '%04'\
                                                        OR action LIKE '%09' OR action LIKE '%11' OR action LIKE '%12') \
                                                        ORDER BY date DESC", [indexerid, season, episode])
            if episode_status_result:
                for item in episode_status_result:
                    episode_history.append(dict(item))
        except Exception as e:
            logger.log("Couldn't read latest episode statust. Error: {}".format(e))

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
            controller="home",
            action="snatchSelection",
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
            "SELECT description FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?",
            (int(show), int(season), int(episode)))
        return result['description'] if result else 'Episode not found.'

    @staticmethod
    def sceneExceptions(show):
        exceptionsList = sickbeard.scene_exceptions.get_all_scene_exceptions(show)
        if not exceptionsList:
            return "No scene exceptions"

        out = []
        for season, names in iter(sorted(exceptionsList.iteritems())):
            if season == -1:
                season = "*"
            out.append("S" + str(season) + ": " + ", ".join(names))
        return "<br>".join(out)

    def editShow(self, show=None, location=None, anyQualities=[], bestQualities=[],
                 exceptions_list=[], flatten_folders=None, paused=None, directCall=False,
                 air_by_date=None, sports=None, dvdorder=None, indexerLang=None,
                 subtitles=None, rls_ignore_words=None, rls_require_words=None,
                 anime=None, blacklist=None, whitelist=None, scene=None,
                 defaultEpStatus=None, quality_preset=None):

        anidb_failed = False
        if show is None:
            errString = "Invalid show ID: " + str(show)
            if directCall:
                return [errString]
            else:
                return self._genericMessage("Error", errString)

        showObj = Show.find(sickbeard.showList, int(show))

        if not showObj:
            errString = "Unable to find the specified show: " + str(show)
            if directCall:
                return [errString]
            else:
                return self._genericMessage("Error", errString)

        showObj.exceptions = sickbeard.scene_exceptions.get_scene_exceptions(showObj.indexerid)

        if try_int(quality_preset, None):
            bestQualities = []

        if not location and not anyQualities and not bestQualities and not flatten_folders:
            t = PageTemplate(rh=self, filename="editShow.mako")

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
                                blacklist=blacklist, title='Edit Show', header='Edit Show', controller="home", action="editShow")
            else:
                return t.render(show=show, scene_exceptions=scene_exceptions, title='Edit Show', header='Edit Show',
                                controller="home", action="editShow")

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
                    errors.append("Unable to refresh this show: " + ex(e))

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
                logger.log(ek(os.path.normpath, showObj._location) + " != " + ek(os.path.normpath, location), logger.DEBUG)  # pylint: disable=protected-access
                if not ek(os.path.isdir, location) and not sickbeard.CREATE_MISSING_SHOW_DIRS:
                    errors.append("New location <tt>%s</tt> does not exist" % location)

                # don't bother if we're going to update anyway
                elif not do_update:
                    # change it
                    try:
                        showObj.location = location
                        try:
                            sickbeard.showQueueScheduler.action.refreshShow(showObj)
                        except CantRefreshShowException as e:
                            errors.append("Unable to refresh this show:" + ex(e))
                            # grab updated info from TVDB
                            # showObj.loadEpisodesFromIndexer()
                            # rescan the episodes in the new folder
                    except NoNFOException:
                        errors.append(
                            "The folder at <tt>%s</tt> doesn't contain a tvshow.nfo - copy your files to that folder before you change the directory in Medusa." % location)

            # save it to the DB
            showObj.saveToDB()

        # force the update
        if do_update:
            try:
                sickbeard.showQueueScheduler.action.updateShow(showObj, True)
                time.sleep(cpu_presets[sickbeard.CPU_PRESET])
            except CantUpdateShowException as e:
                errors.append("Unable to update show: {0}".format(str(e)))

        if do_update_exceptions:
            try:
                sickbeard.scene_exceptions.update_scene_exceptions(showObj.indexerid, exceptions_list)  # @UndefinedVdexerid)
                time.sleep(cpu_presets[sickbeard.CPU_PRESET])
            except CantUpdateShowException:
                errors.append("Unable to force an update on scene exceptions of the show.")

        if do_update_scene_numbering:
            try:
                sickbeard.scene_numbering.xem_refresh(showObj.indexerid, showObj.indexer)
                time.sleep(cpu_presets[sickbeard.CPU_PRESET])
            except CantUpdateShowException:
                errors.append("Unable to force an update on scene numbering of the show.")

            # Must erase cached results when toggling scene numbering
            self.erase_cache(showObj)

        if directCall:
            return errors

        if len(errors) > 0:
            ui.notifications.error('%d error%s while saving changes:' % (len(errors), "" if len(errors) == 1 else "s"),
                                   '<ul>' + '\n'.join(['<li>%s</li>' % error for error in errors]) + "</ul>")

        return self.redirect("/home/displayShow?show=" + show)

    def erase_cache(self, showObj):

        try:
            main_db_con = db.DBConnection('cache.db')
            for cur_provider in sickbeard.providers.sortedProviderList():
                # Let's check if this provider table already exists
                table_exists = main_db_con.select("SELECT name FROM sqlite_master WHERE type='table' AND name=?", [cur_provider.get_id()])
                if not table_exists:
                    continue
                try:
                    main_db_con.action("DELETE FROM '%s' WHERE indexerid = ?" % cur_provider.get_id(), [showObj.indexerid])
                except Exception:
                    logger.log(u"Unable to delete cached results for provider {} for show: {}".format(cur_provider, showObj.name), logger.DEBUG)

        except Exception:
            logger.log(u"Unable to delete cached results for show: {}".format(showObj.name), logger.DEBUG)

    def togglePause(self, show=None):
        error, show = Show.pause(show)

        if error is not None:
            return self._genericMessage('Error', error)

        ui.notifications.message('%s has been %s' % (show.name, ('resumed', 'paused')[show.paused]))

        return self.redirect("/home/displayShow?show=%i" % show.indexerid)

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

        return self.redirect("/home/displayShow?show=" + str(show.indexerid))

    def updateShow(self, show=None, force=0):

        if show is None:
            return self._genericMessage("Error", "Invalid show ID")

        showObj = Show.find(sickbeard.showList, int(show))

        if showObj is None:
            return self._genericMessage("Error", "Unable to find the specified show")

        # force the update
        try:
            sickbeard.showQueueScheduler.action.updateShow(showObj, bool(force))
        except CantUpdateShowException as e:
            ui.notifications.error("Unable to update this show.", ex(e))

        # just give it some time
        time.sleep(cpu_presets[sickbeard.CPU_PRESET])

        return self.redirect("/home/displayShow?show=" + str(showObj.indexerid))

    def subtitleShow(self, show=None, force=0):

        if show is None:
            return self._genericMessage("Error", "Invalid show ID")

        showObj = Show.find(sickbeard.showList, int(show))

        if showObj is None:
            return self._genericMessage("Error", "Unable to find the specified show")

        # search and download subtitles
        sickbeard.showQueueScheduler.action.download_subtitles(showObj, bool(force))

        time.sleep(cpu_presets[sickbeard.CPU_PRESET])

        return self.redirect("/home/displayShow?show=" + str(showObj.indexerid))

    def updateKODI(self, show=None):
        showName = None
        showObj = None

        if show:
            showObj = Show.find(sickbeard.showList, int(show))
            if showObj:
                showName = quote_plus(showObj.name.encode('utf-8'))

        if sickbeard.KODI_UPDATE_ONLYFIRST:
            host = sickbeard.KODI_HOST.split(",")[0].strip()
        else:
            host = sickbeard.KODI_HOST

        if notifiers.kodi_notifier.update_library(showName=showName):
            ui.notifications.message("Library update command sent to KODI host(s): " + host)
        else:
            ui.notifications.error("Unable to contact one or more KODI host(s): " + host)

        if showObj:
            return self.redirect('/home/displayShow?show=' + str(showObj.indexerid))
        else:
            return self.redirect('/home/')

    def updatePLEX(self):
        if None is notifiers.plex_notifier.update_library():
            ui.notifications.message(
                "Library update command sent to Plex Media Server host: " + sickbeard.PLEX_SERVER_HOST)
        else:
            ui.notifications.error("Unable to contact Plex Media Server host: " + sickbeard.PLEX_SERVER_HOST)
        return self.redirect('/home/')

    def updateEMBY(self, show=None):
        showObj = None

        if show:
            showObj = Show.find(sickbeard.showList, int(show))

        if notifiers.emby_notifier.update_library(showObj):
            ui.notifications.message(
                "Library update command sent to Emby host: " + sickbeard.EMBY_HOST)
        else:
            ui.notifications.error("Unable to contact Emby host: " + sickbeard.EMBY_HOST)

        if showObj:
            return self.redirect('/home/displayShow?show=' + str(showObj.indexerid))
        else:
            return self.redirect('/home/')

    def setStatus(self, show=None, eps=None, status=None, direct=False):

        if not all([show, eps, status]):
            errMsg = "You must specify a show and at least one episode"
            if direct:
                ui.notifications.error('Error', errMsg)
                return json.dumps({'result': 'error'})
            else:
                return self._genericMessage("Error", errMsg)

        # Use .has_key() since it is overridden for statusStrings in common.py
        if status not in statusStrings:
            errMsg = "Invalid status"
            if direct:
                ui.notifications.error('Error', errMsg)
                return json.dumps({'result': 'error'})
            else:
                return self._genericMessage("Error", errMsg)

        showObj = Show.find(sickbeard.showList, int(show))

        if not showObj:
            errMsg = "Error", "Show not in show list"
            if direct:
                ui.notifications.error('Error', errMsg)
                return json.dumps({'result': 'error'})
            else:
                return self._genericMessage("Error", errMsg)

        segments = {}
        trakt_data = []
        if eps:

            sql_l = []
            for curEp in eps.split('|'):

                if not curEp:
                    logger.log(u"curEp was empty when trying to setStatus", logger.DEBUG)

                logger.log(u"Attempting to set status on episode " + curEp + " to " + status, logger.DEBUG)

                epInfo = curEp.split('x')

                if not all(epInfo):
                    logger.log(u"Something went wrong when trying to setStatus, epInfo[0]: %s, epInfo[1]: %s" % (epInfo[0], epInfo[1]), logger.DEBUG)
                    continue

                epObj = showObj.getEpisode(epInfo[0], epInfo[1])

                if not epObj:
                    return self._genericMessage("Error", "Episode couldn't be retrieved")

                if int(status) in [WANTED, FAILED]:
                    # figure out what episodes are wanted so we can backlog them
                    if epObj.season in segments:
                        segments[epObj.season].append(epObj)
                    else:
                        segments[epObj.season] = [epObj]

                with epObj.lock:
                    # don't let them mess up UNAIRED episodes
                    if epObj.status == UNAIRED:
                        logger.log(u"Refusing to change status of " + curEp + " because it is UNAIRED", logger.WARNING)
                        continue

                    if int(status) in Quality.DOWNLOADED and epObj.status not in Quality.SNATCHED + \
                            Quality.SNATCHED_PROPER + Quality.SNATCHED_BEST + Quality.DOWNLOADED + [IGNORED] and not ek(os.path.isfile, epObj.location):
                        logger.log(u"Refusing to change status of " + curEp + " to DOWNLOADED because it's not SNATCHED/DOWNLOADED", logger.WARNING)
                        continue

                    if int(status) == FAILED and epObj.status not in Quality.SNATCHED + Quality.SNATCHED_PROPER + \
                            Quality.SNATCHED_BEST + Quality.DOWNLOADED + Quality.ARCHIVED:
                        logger.log(u"Refusing to change status of " + curEp + " to FAILED because it's not SNATCHED/DOWNLOADED", logger.WARNING)
                        continue

                    if epObj.status in Quality.DOWNLOADED + Quality.ARCHIVED and int(status) == WANTED:
                        logger.log(u"Removing release_name for episode as you want to set a downloaded episode back to wanted, so obviously you want it replaced")
                        epObj.release_name = ""

                    epObj.status = int(status)

                    # mass add to database
                    sql_l.append(epObj.get_sql())

                    trakt_data.append((epObj.season, epObj.episode))

            data = notifiers.trakt_notifier.trakt_episode_data_generate(trakt_data)

            if sickbeard.USE_TRAKT and sickbeard.TRAKT_SYNC_WATCHLIST:
                if int(status) in [WANTED, FAILED]:
                    logger.log(u"Add episodes, showid: indexerid " + str(showObj.indexerid) + ", Title " + str(showObj.name) + " to Watchlist", logger.DEBUG)
                    upd = "add"
                elif int(status) in [IGNORED, SKIPPED] + Quality.DOWNLOADED + Quality.ARCHIVED:
                    logger.log(u"Remove episodes, showid: indexerid " + str(showObj.indexerid) + ", Title " + str(showObj.name) + " from Watchlist", logger.DEBUG)
                    upd = "remove"

                if data:
                    notifiers.trakt_notifier.update_watchlist(showObj, data_episode=data, update=upd)

            if len(sql_l) > 0:
                main_db_con = db.DBConnection()
                main_db_con.mass_action(sql_l)

        if int(status) == WANTED and not showObj.paused:
            msg = "Backlog was automatically started for the following seasons of <b>" + showObj.name + "</b>:<br>"
            msg += '<ul>'

            for season, segment in segments.iteritems():
                cur_backlog_queue_item = search_queue.BacklogQueueItem(showObj, segment)
                sickbeard.searchQueueScheduler.action.add_item(cur_backlog_queue_item)

                msg += "<li>Season " + str(season) + "</li>"
                logger.log(u"Sending backlog for " + showObj.name + " season " + str(
                    season) + " because some eps were set to wanted")

            msg += "</ul>"

            if segments:
                ui.notifications.message("Backlog started", msg)
        elif int(status) == WANTED and showObj.paused:
            logger.log(u"Some episodes were set to wanted, but " + showObj.name + " is paused. Not adding to Backlog until show is unpaused")

        if int(status) == FAILED:
            msg = "Retrying Search was automatically started for the following season of <b>" + showObj.name + "</b>:<br>"
            msg += '<ul>'

            for season, segment in segments.iteritems():
                cur_failed_queue_item = search_queue.FailedQueueItem(showObj, segment)
                sickbeard.searchQueueScheduler.action.add_item(cur_failed_queue_item)

                msg += "<li>Season " + str(season) + "</li>"
                logger.log(u"Retrying Search for " + showObj.name + " season " + str(
                    season) + " because some eps were set to failed")

            msg += "</ul>"

            if segments:
                ui.notifications.message("Retry Search started", msg)

        if direct:
            return json.dumps({'result': 'success'})
        else:
            return self.redirect("/home/displayShow?show=" + show)

    def testRename(self, show=None):

        if show is None:
            return self._genericMessage("Error", "You must specify a show")

        showObj = Show.find(sickbeard.showList, int(show))

        if showObj is None:
            return self._genericMessage("Error", "Show not in show list")

        try:
            showObj.location  # @UnusedVariable
        except ShowDirectoryNotFoundException:
            return self._genericMessage("Error", "Can't rename episodes when the show dir is missing.")

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

        t = PageTemplate(rh=self, filename="testRename.mako")
        submenu = [{'title': 'Edit', 'path': 'home/editShow?show=%d' % showObj.indexerid, 'icon': 'ui-icon ui-icon-pencil'}]

        return t.render(submenu=submenu, ep_obj_list=ep_obj_rename_list,
                        show=showObj, title='Preview Rename',
                        header='Preview Rename',
                        controller="home", action="previewRename")

    def doRename(self, show=None, eps=None):
        if show is None or eps is None:
            errMsg = "You must specify a show and at least one episode"
            return self._genericMessage("Error", errMsg)

        show_obj = Show.find(sickbeard.showList, int(show))

        if show_obj is None:
            errMsg = "Error", "Show not in show list"
            return self._genericMessage("Error", errMsg)

        try:
            show_obj.location  # @UnusedVariable
        except ShowDirectoryNotFoundException:
            return self._genericMessage("Error", "Can't rename episodes when the show dir is missing.")

        if eps is None:
            return self.redirect("/home/displayShow?show=" + show)

        main_db_con = db.DBConnection()
        for curEp in eps.split('|'):

            epInfo = curEp.split('x')

            # this is probably the worst possible way to deal with double eps but I've kinda painted myself into a corner here with this stupid database
            ep_result = main_db_con.select(
                "SELECT location FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ? AND 5=5",
                [show, epInfo[0], epInfo[1]])
            if not ep_result:
                logger.log(u"Unable to find an episode for " + curEp + ", skipping", logger.WARNING)
                continue
            related_eps_result = main_db_con.select(
                "SELECT season, episode FROM tv_episodes WHERE location = ? AND episode != ?",
                [ep_result[0]["location"], epInfo[1]]
            )

            root_ep_obj = show_obj.getEpisode(epInfo[0], epInfo[1])
            root_ep_obj.relatedEps = []

            for cur_related_ep in related_eps_result:
                related_ep_obj = show_obj.getEpisode(cur_related_ep["season"], cur_related_ep["episode"])
                if related_ep_obj not in root_ep_obj.relatedEps:
                    root_ep_obj.relatedEps.append(related_ep_obj)

            root_ep_obj.rename()

        return self.redirect("/home/displayShow?show=" + show)

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
            logger.log(u"setAbsoluteSceneNumbering for %s from %s to %s" %
                       (show, forAbsolute, sceneAbsolute), logger.DEBUG)

            show = int(show)
            indexer = int(indexer)
            forAbsolute = int(forAbsolute)
            if sceneAbsolute is not None:
                sceneAbsolute = int(sceneAbsolute)

            set_scene_numbering(show, indexer, absolute_number=forAbsolute, sceneAbsolute=sceneAbsolute)
        else:
            logger.log(u"setEpisodeSceneNumbering for %s from %sx%s to %sx%s" %
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


@route('/IRC(/?.*)')
class HomeIRC(Home):
    def __init__(self, *args, **kwargs):
        super(HomeIRC, self).__init__(*args, **kwargs)

    def index(self):

        t = PageTemplate(rh=self, filename="IRC.mako")
        return t.render(topmenu="system", header="IRC", title="IRC", controller="IRC", action="index")


@route('/news(/?.*)')
class HomeNews(Home):
    def __init__(self, *args, **kwargs):
        super(HomeNews, self).__init__(*args, **kwargs)

    def index(self):
        try:
            news = sickbeard.versionCheckScheduler.action.check_for_new_news(force=True)
        except Exception:
            logger.log(u'Could not load news from repo, giving a link!', logger.DEBUG)
            news = 'Could not load news from the repo. [Click here for news.md](' + sickbeard.NEWS_URL + ')'

        sickbeard.NEWS_LAST_READ = sickbeard.NEWS_LATEST
        sickbeard.NEWS_UNREAD = 0
        sickbeard.save_config()

        t = PageTemplate(rh=self, filename="markdown.mako")
        data = markdown2.markdown(news if news else "The was a problem connecting to github, please refresh and try again", extras=['header-ids'])

        return t.render(title="News", header="News", topmenu="system", data=data, controller="news", action="index")


@route('/changes(/?.*)')
class HomeChangeLog(Home):
    def __init__(self, *args, **kwargs):
        super(HomeChangeLog, self).__init__(*args, **kwargs)

    def index(self):
        try:
            changes = helpers.getURL('https://cdn.pymedusa.com/sickrage-news/CHANGES.md', session=helpers.make_session(), returns='text')
        except Exception:
            logger.log(u'Could not load changes from repo, giving a link!', logger.DEBUG)
            changes = 'Could not load changes from the repo. [Click here for CHANGES.md](https://cdn.pymedusa.com/sickrage-news/CHANGES.md)'

        t = PageTemplate(rh=self, filename="markdown.mako")
        data = markdown2.markdown(changes if changes else "The was a problem connecting to github, please refresh and try again", extras=['header-ids'])

        return t.render(title="Changelog", header="Changelog", topmenu="system", data=data, controller="changes", action="index")


@route('/home/postprocess(/?.*)')
class HomePostProcess(Home):
    def __init__(self, *args, **kwargs):
        super(HomePostProcess, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename="home_postprocess.mako")
        return t.render(title='Post Processing', header='Post Processing', topmenu='home', controller="home", action="postProcess")

    # TODO: PR to NZBtoMedia so that we can rename dir to proc_dir, and type to proc_type.
    # Using names of builtins as var names is bad
    # pylint: disable=redefined-builtin
    def processEpisode(self, dir=None, nzbName=None, jobName=None, quiet=None, process_method=None, force=None,
                       is_priority=None, delete_on="0", failed="0", type="auto", *args, **kwargs):

        def argToBool(argument):
            if isinstance(argument, basestring):
                _arg = argument.strip().lower()
            else:
                _arg = argument

            if _arg in ['1', 'on', 'true', True]:
                return True
            elif _arg in ['0', 'off', 'false', False]:
                return False

            return argument

        if not dir:
            return self.redirect("/home/postprocess/")
        else:
            nzbName = ss(nzbName) if nzbName else nzbName

            result = processTV.processDir(
                ss(dir), nzbName, process_method=process_method, force=argToBool(force),
                is_priority=argToBool(is_priority), delete_on=argToBool(delete_on), failed=argToBool(failed), proc_type=type
            )

            if quiet is not None and int(quiet) == 1:
                return result

            result = result.replace("\n", "<br>\n")
            return self._genericMessage("Postprocessing results", result)


@route('/addShows(/?.*)')
class HomeAddShows(Home):
    def __init__(self, *args, **kwargs):
        super(HomeAddShows, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename="addShows.mako")
        return t.render(title='Add Shows', header='Add Shows', topmenu='home', controller="addShows", action="index")

    @staticmethod
    def getIndexerLanguages():
        result = sickbeard.indexerApi().config['valid_languages']

        return json.dumps({'results': result})

    @staticmethod
    def sanitizeFileName(name):
        return sanitize_filename(name)

    @staticmethod
    def searchIndexersForShowName(search_term, lang=None, indexer=None):
        if not lang or lang == 'null':
            lang = sickbeard.INDEXER_DEFAULT_LANGUAGE

        search_term = search_term.encode('utf-8')

        searchTerms = [search_term]

        # If search term ends with what looks like a year, enclose it in ()
        matches = re.match(r'^(.+ |)([12][0-9]{3})$', search_term)
        if matches:
            searchTerms.append("%s(%s)" % (matches.group(1), matches.group(2)))

        for searchTerm in searchTerms:
            # If search term begins with an article, let's also search for it without
            matches = re.match(r'^(?:a|an|the) (.+)$', searchTerm, re.I)
            if matches:
                searchTerms.append(matches.group(1))

        results = {}
        final_results = []

        # Query Indexers for each search term and build the list of results
        for indexer in sickbeard.indexerApi().indexers if not int(indexer) else [int(indexer)]:
            lINDEXER_API_PARMS = sickbeard.indexerApi(indexer).api_params.copy()
            lINDEXER_API_PARMS['language'] = lang
            lINDEXER_API_PARMS['custom_ui'] = classes.AllShowsListUI
            t = sickbeard.indexerApi(indexer).indexer(**lINDEXER_API_PARMS)

            logger.log(u"Searching for Show with searchterm(s): %s on Indexer: %s" % (
                searchTerms, sickbeard.indexerApi(indexer).name), logger.DEBUG)
            for searchTerm in searchTerms:
                try:
                    indexerResults = t[searchTerm]
                    # add search results
                    results.setdefault(indexer, []).extend(indexerResults)
                except indexer_exception as error:
                    logger.log(u'Error searching for show: {}'.format(ex(error)))

        for i, shows in results.iteritems():
            final_results.extend({(sickbeard.indexerApi(i).name, i, sickbeard.indexerApi(i).config["show_url"], int(show['id']),
                                   show['seriesname'], show['firstaired']) for show in shows})

        lang_id = sickbeard.indexerApi().config['langabbv_to_id'][lang]
        return json.dumps({'results': final_results, 'langid': lang_id})

    def massAddTable(self, rootDir=None):
        t = PageTemplate(rh=self, filename="home_massAddTable.mako")

        if not rootDir:
            return "No folders selected."
        elif not isinstance(rootDir, list):
            root_dirs = [rootDir]
        else:
            root_dirs = rootDir

        root_dirs = [unquote_plus(x) for x in root_dirs]

        if sickbeard.ROOT_DIRS:
            default_index = int(sickbeard.ROOT_DIRS.split('|')[0])
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
                file_list = ek(os.listdir, root_dir)
            except Exception:
                continue

            for cur_file in file_list:

                try:
                    cur_path = ek(os.path.normpath, ek(os.path.join, root_dir, cur_file))
                    if not ek(os.path.isdir, cur_path):
                        continue
                except Exception:
                    continue

                cur_dir = {
                    'dir': cur_path,
                    'display_dir': '<b>' + ek(os.path.dirname, cur_path) + os.sep + '</b>' + ek(
                        os.path.basename,
                        cur_path),
                }

                # see if the folder is in KODI already
                dirResults = main_db_con.select("SELECT indexer_id FROM tv_shows WHERE location = ? LIMIT 1", [cur_path])

                if dirResults:
                    cur_dir['added_already'] = True
                else:
                    cur_dir['added_already'] = False

                dir_list.append(cur_dir)

                indexer_id = show_name = indexer = None
                for cur_provider in sickbeard.metadata_provider_dict.values():
                    if not (indexer_id and show_name):
                        (indexer_id, show_name, indexer) = cur_provider.retrieveShowMetadata(cur_path)

                        # default to TVDB if indexer was not detected
                        if show_name and not (indexer or indexer_id):
                            (_, idxr, i) = helpers.searchIndexerForShowID(show_name, indexer, indexer_id)

                            # set indexer and indexer_id from found info
                            if not indexer and idxr:
                                indexer = idxr

                            if not indexer_id and i:
                                indexer_id = i

                cur_dir['existing_info'] = (indexer_id, show_name, indexer)

                if indexer_id and Show.find(sickbeard.showList, indexer_id):
                    cur_dir['added_already'] = True
        return t.render(dirList=dir_list)

    def newShow(self, show_to_add=None, other_shows=None, search_string=None):
        """
        Display the new show page which collects a tvdb id, folder, and extra options and
        posts them to addNewShow
        """
        t = PageTemplate(rh=self, filename="addShows_newShow.mako")

        indexer, show_dir, indexer_id, show_name = self.split_extra_show(show_to_add)

        if indexer_id and indexer and show_name:
            use_provided_info = True
        else:
            use_provided_info = False

        # use the given show_dir for the indexer search if available
        if not show_dir:
            if search_string:
                default_show_name = search_string
            else:
                default_show_name = ''

        elif not show_name:
            default_show_name = re.sub(r' \(\d{4}\)', '',
                                       ek(os.path.basename, ek(os.path.normpath, show_dir)).replace('.', ' '))
        else:
            default_show_name = show_name

        # carry a list of other dirs if given
        if not other_shows:
            other_shows = []
        elif not isinstance(other_shows, list):
            other_shows = [other_shows]

        provided_indexer_id = int(indexer_id or 0)
        provided_indexer_name = show_name

        provided_indexer = int(indexer or sickbeard.INDEXER_DEFAULT)

        return t.render(
            enable_anime_options=True, use_provided_info=use_provided_info,
            default_show_name=default_show_name, other_shows=other_shows,
            provided_show_dir=show_dir, provided_indexer_id=provided_indexer_id,
            provided_indexer_name=provided_indexer_name, provided_indexer=provided_indexer,
            indexers=sickbeard.indexerApi().indexers, whitelist=[], blacklist=[], groups=[],
            title='New Show', header='New Show', topmenu='home',
            controller="addShows", action="newShow"
        )

    def trendingShows(self, traktList=None):
        """
        Display the new show page which collects a tvdb id, folder, and extra options and
        posts them to addNewShow
        """
        if traktList is None:
            traktList = ""

        traktList = traktList.lower()

        if traktList == "trending":
            page_title = "Trending Shows"
        elif traktList == "popular":
            page_title = "Popular Shows"
        elif traktList == "anticipated":
            page_title = "Most Anticipated Shows"
        elif traktList == "collected":
            page_title = "Most Collected Shows"
        elif traktList == "watched":
            page_title = "Most Watched Shows"
        elif traktList == "played":
            page_title = "Most Played Shows"
        elif traktList == "recommended":
            page_title = "Recommended Shows"
        elif traktList == "newshow":
            page_title = "New Shows"
        elif traktList == "newseason":
            page_title = "Season Premieres"
        else:
            page_title = "Most Anticipated Shows"

        t = PageTemplate(rh=self, filename="addShows_trendingShows.mako")
        return t.render(title=page_title, header=page_title, enable_anime_options=False,
                        traktList=traktList, controller="addShows", action="trendingShows")

    def getTrendingShows(self, traktList=None):
        """
        Display the new show page which collects a tvdb id, folder, and extra options and
        posts them to addNewShow
        """
        t = PageTemplate(rh=self, filename="trendingShows.mako")
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

        trending_shows = []

        trakt_api = TraktAPI(sickbeard.SSL_VERIFY, sickbeard.TRAKT_TIMEOUT)

        try:
            not_liked_show = ""
            if sickbeard.TRAKT_ACCESS_TOKEN != '':
                library_shows = trakt_api.traktRequest("sync/collection/shows?extended=full") or []
                if sickbeard.TRAKT_BLACKLIST_NAME is not None and sickbeard.TRAKT_BLACKLIST_NAME:
                    not_liked_show = trakt_api.traktRequest("users/" + sickbeard.TRAKT_USERNAME + "/lists/" + sickbeard.TRAKT_BLACKLIST_NAME + "/items") or []
                else:
                    logger.log(u"Trakt blacklist name is empty", logger.DEBUG)

            if traktList not in ["recommended", "newshow", "newseason"]:
                limit_show = "?limit=" + str(100 + len(not_liked_show)) + "&"
            else:
                limit_show = "?"

            shows = trakt_api.traktRequest(page_url + limit_show + "extended=full,images") or []

            if sickbeard.TRAKT_ACCESS_TOKEN != '':
                library_shows = trakt_api.traktRequest("sync/collection/shows?extended=full") or []

            for show in shows:
                try:
                    if 'show' not in show:
                        show['show'] = show

                    if not Show.find(sickbeard.showList, [int(show['show']['ids']['tvdb'])]):
                        if sickbeard.TRAKT_ACCESS_TOKEN != '':
                            if show['show']['ids']['tvdb'] not in (lshow['show']['ids']['tvdb'] for lshow in library_shows):
                                if not_liked_show:
                                    if show['show']['ids']['tvdb'] not in (show['show']['ids']['tvdb'] for show in not_liked_show if show['type'] == 'show'):
                                        trending_shows += [show]
                                else:
                                    trending_shows += [show]
                        else:
                            if not_liked_show:
                                if show['show']['ids']['tvdb'] not in (show['show']['ids']['tvdb'] for show in not_liked_show if show['type'] == 'show'):
                                    trending_shows += [show]
                            else:
                                trending_shows += [show]

                except MultipleShowObjectsException:
                    continue

            if sickbeard.TRAKT_BLACKLIST_NAME != '':
                blacklist = True
            else:
                blacklist = False

        except traktException as e:
            logger.log(u"Could not connect to Trakt service: %s" % ex(e), logger.WARNING)

        return t.render(blacklist=blacklist, trending_shows=trending_shows)

    def popularShows(self):
        """
        Fetches data from IMDB to show a list of popular shows.
        """
        t = PageTemplate(rh=self, filename="addShows_popularShows.mako")
        e = None

        try:
            popular_shows = imdb_popular.fetch_popular_shows()
        except Exception as e:
            # print traceback.format_exc()
            popular_shows = None

        return t.render(title="Popular Shows", header="Popular Shows",
                        popular_shows=popular_shows, imdb_exception=e,
                        topmenu="home",
                        controller="addShows", action="popularShows")

    def addShowToBlacklist(self, indexer_id):
        # URL parameters
        data = {'shows': [{'ids': {'tvdb': indexer_id}}]}

        trakt_api = TraktAPI(sickbeard.SSL_VERIFY, sickbeard.TRAKT_TIMEOUT)

        trakt_api.traktRequest("users/" + sickbeard.TRAKT_USERNAME + "/lists/" + sickbeard.TRAKT_BLACKLIST_NAME + "/items", data, method='POST')

        return self.redirect('/addShows/trendingShows/')

    def existingShows(self):
        """
        Prints out the page to add existing shows from a root dir
        """
        t = PageTemplate(rh=self, filename="addShows_addExistingShow.mako")
        return t.render(enable_anime_options=False, title='Existing Show',
                        header='Existing Show', topmenu="home",
                        controller="addShows", action="addExistingShow")

    def addShowByID(self, indexer_id, show_name, indexer="TVDB", which_series=None,
                    indexer_lang=None, root_dir=None, default_status=None,
                    quality_preset=None, any_qualities=None, best_qualities=None,
                    flatten_folders=None, subtitles=None, full_show_path=None,
                    other_shows=None, skip_show=None, provided_indexer=None,
                    anime=None, scene=None, blacklist=None, whitelist=None,
                    default_status_after=None, default_flatten_folders=None,
                    configure_show_options=None):

        if indexer != "TVDB":
            tvdb_id = helpers.getTVDBFromID(indexer_id, indexer.upper())
            if not tvdb_id:
                logger.log(u"Unable to to find tvdb ID to add %s" % show_name)
                ui.notifications.error(
                    "Unable to add %s" % show_name,
                    "Could not add %s.  We were unable to locate the tvdb id at this time." % show_name
                )
                return

            indexer_id = try_int(tvdb_id, None)

        if Show.find(sickbeard.showList, int(indexer_id)):
            return

        # Sanitize the paramater anyQualities and bestQualities. As these would normally be passed as lists
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

            quality = Quality.combineQualities([int(q) for q in any_qualities], [int(q) for q in best_qualities])

            location = root_dir

        else:
            default_status = sickbeard.STATUS_DEFAULT
            quality = sickbeard.QUALITY_DEFAULT
            flatten_folders = sickbeard.FLATTEN_FOLDERS_DEFAULT
            subtitles = sickbeard.SUBTITLES_DEFAULT
            anime = sickbeard.ANIME_DEFAULT
            scene = sickbeard.SCENE_DEFAULT
            default_status_after = sickbeard.STATUS_DEFAULT_AFTER

            if sickbeard.ROOT_DIRS:
                root_dirs = sickbeard.ROOT_DIRS.split('|')
                location = root_dirs[int(root_dirs[0]) + 1]
            else:
                location = None

        if not location:
            logger.log(u"There was an error creating the show, "
                       u"no root directory setting found", logger.WARNING)
            return "No root directories setup, please go back and add one."

        show_name = get_showname_from_indexer(1, indexer_id)
        show_dir = None

        # add the show
        sickbeard.showQueueScheduler.action.addShow(1, int(indexer_id), show_dir, int(default_status), quality, flatten_folders,
                                                    indexer_lang, subtitles, anime, scene, None, blacklist, whitelist,
                                                    int(default_status_after), root_dir=location)

        ui.notifications.message('Show added', 'Adding the specified show {0}'.format(show_name))

        # done adding show
        return self.redirect('/home/')

    def addNewShow(self, whichSeries=None, indexerLang=None, rootDir=None, defaultStatus=None,
                   quality_preset=None, anyQualities=None, bestQualities=None, flatten_folders=None, subtitles=None,
                   fullShowPath=None, other_shows=None, skipShow=None, providedIndexer=None, anime=None,
                   scene=None, blacklist=None, whitelist=None, defaultStatusAfter=None):
        """
        Receive tvdb id, dir, and other options and create a show from them. If extra show dirs are
        provided then it forwards back to newShow, if not it goes to /home.
        """

        if indexerLang is None:
            indexerLang = sickbeard.INDEXER_DEFAULT_LANGUAGE

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
            return "Missing params, no Indexer ID or folder:" + repr(whichSeries) + " and " + repr(
                rootDir) + "/" + repr(fullShowPath)

        # figure out what show we're adding and where
        series_pieces = whichSeries.split('|')
        if (whichSeries and rootDir) or (whichSeries and fullShowPath and len(series_pieces) > 1):
            if len(series_pieces) < 6:
                logger.log(u"Unable to add show due to show selection. Not anough arguments: %s" % (repr(series_pieces)),
                           logger.ERROR)
                ui.notifications.error("Unknown error. Unable to add show due to problem with show selection.")
                return self.redirect('/addShows/existingShows/')

            indexer = int(series_pieces[1])
            indexer_id = int(series_pieces[3])
            # Show name was sent in UTF-8 in the form
            show_name = series_pieces[4].decode('utf-8')
        else:
            # if no indexer was provided use the default indexer set in General settings
            if not providedIndexer:
                providedIndexer = sickbeard.INDEXER_DEFAULT

            indexer = int(providedIndexer)
            indexer_id = int(whichSeries)
            show_name = ek(os.path.basename, ek(os.path.normpath, fullShowPath))

        # use the whole path if it's given, or else append the show name to the root dir to get the full show path
        if fullShowPath:
            show_dir = ek(os.path.normpath, fullShowPath)
        else:
            show_dir = ek(os.path.join, rootDir, sanitize_filename(show_name))

        # blanket policy - if the dir exists you should have used "add existing show" numbnuts
        if ek(os.path.isdir, show_dir) and not fullShowPath:
            ui.notifications.error("Unable to add show", "Folder " + show_dir + " exists already")
            return self.redirect('/addShows/existingShows/')

        # don't create show dir if config says not to
        if sickbeard.ADD_SHOWS_WO_DIR:
            logger.log(u"Skipping initial creation of " + show_dir + " due to config.ini setting")
        else:
            dir_exists = helpers.makeDir(show_dir)
            if not dir_exists:
                logger.log(u"Unable to create the folder " + show_dir + ", can't add the show", logger.ERROR)
                ui.notifications.error("Unable to add show",
                                       "Unable to create the folder " + show_dir + ", can't add the show")
                # Don't redirect to default page because user wants to see the new show
                return self.redirect("/home/")
            else:
                helpers.chmodAsParent(show_dir)

        # prepare the inputs for passing along
        scene = config.checkbox_to_value(scene)
        anime = config.checkbox_to_value(anime)
        flatten_folders = config.checkbox_to_value(flatten_folders)
        subtitles = config.checkbox_to_value(subtitles)

        if whitelist:
            whitelist = short_group_names(whitelist)
        if blacklist:
            blacklist = short_group_names(blacklist)

        if not anyQualities:
            anyQualities = []
        if not bestQualities or try_int(quality_preset, None):
            bestQualities = []
        if not isinstance(anyQualities, list):
            anyQualities = [anyQualities]
        if not isinstance(bestQualities, list):
            bestQualities = [bestQualities]
        newQuality = Quality.combineQualities([int(q) for q in anyQualities], [int(q) for q in bestQualities])

        # add the show
        sickbeard.showQueueScheduler.action.addShow(indexer, indexer_id, show_dir, int(defaultStatus), newQuality,
                                                    flatten_folders, indexerLang, subtitles, anime,
                                                    scene, None, blacklist, whitelist, int(defaultStatusAfter))
        ui.notifications.message('Show added', 'Adding the specified show into ' + show_dir)

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
        # grab a list of other shows to add, if provided
        if not shows_to_add:
            shows_to_add = []
        elif not isinstance(shows_to_add, list):
            shows_to_add = [shows_to_add]

        shows_to_add = [unquote_plus(x) for x in shows_to_add]

        promptForSettings = config.checkbox_to_value(promptForSettings)

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

                if not show_dir or not indexer_id or not show_name:
                    continue

                indexer_id_given.append((int(indexer), show_dir, int(indexer_id), show_name))

        # if they want me to prompt for settings then I will just carry on to the newShow page
        if promptForSettings and shows_to_add:
            return self.newShow(shows_to_add[0], shows_to_add[1:])

        # if they don't want me to prompt for settings then I can just add all the nfo shows now
        num_added = 0
        for cur_show in indexer_id_given:
            indexer, show_dir, indexer_id, show_name = cur_show

            if indexer is not None and indexer_id is not None:
                # add the show
                sickbeard.showQueueScheduler.action.addShow(
                    indexer, indexer_id, show_dir,
                    default_status=sickbeard.STATUS_DEFAULT,
                    quality=sickbeard.QUALITY_DEFAULT,
                    flatten_folders=sickbeard.FLATTEN_FOLDERS_DEFAULT,
                    subtitles=sickbeard.SUBTITLES_DEFAULT,
                    anime=sickbeard.ANIME_DEFAULT,
                    scene=sickbeard.SCENE_DEFAULT,
                    default_status_after=sickbeard.STATUS_DEFAULT_AFTER
                )
                num_added += 1

        if num_added:
            ui.notifications.message("Shows Added",
                                     "Automatically added " + str(num_added) + " from their existing metadata files")

        # if we're done then go home
        if not dirs_only:
            return self.redirect('/home/')

        # for the remaining shows we need to prompt for each one, so forward this on to the newShow page
        return self.newShow(dirs_only[0], dirs_only[1:])
