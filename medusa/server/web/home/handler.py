# coding=utf-8

from __future__ import unicode_literals

import ast
import json
import os
import time
from datetime import date, datetime

import adba

from medusa import (
    app,
    config,
    db,
    helpers,
    logger,
    notifiers,
    providers,
    subtitles,
    ui,
)
from medusa.black_and_white_list import (
    BlackAndWhiteList,
    short_group_names,
)
from medusa.clients import torrent
from medusa.clients.nzb import (
    nzbget,
    sab,
)
from medusa.common import (
    DOWNLOADED,
    FAILED,
    IGNORED,
    Overview,
    Quality,
    SKIPPED,
    SNATCHED,
    SNATCHED_BEST,
    SNATCHED_PROPER,
    UNAIRED,
    WANTED,
    cpu_presets,
    statusStrings,
)
from medusa.failed_history import prepare_failed_name
from medusa.helper.common import (
    enabled_providers,
    try_int,
)
from medusa.helper.exceptions import (
    CantRefreshShowException,
    CantUpdateShowException,
    ShowDirectoryNotFoundException,
    ex,
)
from medusa.indexers.indexer_api import indexerApi
from medusa.indexers.indexer_config import INDEXER_TVDBV2
from medusa.indexers.indexer_exceptions import (
    IndexerException,
    IndexerShowNotFoundInLanguage,
)
from medusa.providers.generic_provider import GenericProvider
from medusa.sbdatetime import sbdatetime
from medusa.scene_exceptions import (
    get_all_scene_exceptions,
    get_scene_exceptions,
    update_scene_exceptions,
)
from medusa.scene_numbering import (
    get_scene_absolute_numbering,
    get_scene_absolute_numbering_for_show,
    get_scene_numbering,
    get_scene_numbering_for_show,
    get_xem_absolute_numbering_for_show,
    get_xem_numbering_for_show,
    set_scene_numbering,
    xem_refresh,
)
from medusa.search.manual import (
    SEARCH_STATUS_FINISHED,
    SEARCH_STATUS_QUEUED,
    SEARCH_STATUS_SEARCHING,
    collect_episodes_from_search_thread,
    get_episode,
    get_provider_cache_results,
    update_finished_search_queue_item,
)
from medusa.search.queue import (
    BacklogQueueItem,
    FailedQueueItem,
    ForcedSearchQueueItem,
    ManualSnatchQueueItem,
)
from medusa.server.web.core import (
    PageTemplate,
    WebRoot,
)
from medusa.show.history import History
from medusa.show.show import Show
from medusa.system.restart import Restart
from medusa.system.shutdown import Shutdown
from medusa.version_checker import CheckVersion

from requests.compat import (
    quote_plus,
    unquote_plus,
)
from six import iteritems
from tornroutes import route
from traktor import (
    MissingTokenException,
    TokenExpiredException,
    TraktApi,
    TraktException,
)


@route('/home(/?.*)')
class Home(WebRoot):
    def __init__(self, *args, **kwargs):
        super(Home, self).__init__(*args, **kwargs)

    def _genericMessage(self, subject, message):
        t = PageTemplate(rh=self, filename='genericMessage.mako')
        return t.render(message=message, subject=subject, topmenu='home', title='')

    def index(self):
        t = PageTemplate(rh=self, filename='home.mako')
        selected_root = int(app.SELECTED_ROOT)
        shows_dir = None
        if selected_root is not None and app.ROOT_DIRS:
            backend_pieces = app.ROOT_DIRS.split('|')
            backend_dirs = backend_pieces[1:]
            shows_dir = backend_dirs[selected_root] if selected_root != -1 else None

        shows = []
        if app.ANIME_SPLIT_HOME:
            anime = []
            for show in app.showList:
                if shows_dir and not show._location.startswith(shows_dir):
                    continue
                if show.is_anime:
                    anime.append(show)
                else:
                    shows.append(show)
            show_lists = [['Shows', shows], ['Anime', anime]]
        else:
            for show in app.showList:
                if shows_dir and not show._location.startswith(shows_dir):
                    continue
                shows.append(show)
            show_lists = [['Shows', shows]]

        stats = self.show_statistics()
        return t.render(title='Home', header='Show List', topmenu='home', show_lists=show_lists, show_stat=stats[0], max_download_count=stats[1], controller='home', action='index')

    @staticmethod
    def show_statistics():
        main_db_con = db.DBConnection()

        snatched = Quality.SNATCHED + Quality.SNATCHED_PROPER + Quality.SNATCHED_BEST
        downloaded = Quality.DOWNLOADED + Quality.ARCHIVED

        sql_result = main_db_con.select(
            b"""
            SELECT showid,
              (SELECT COUNT(*) FROM tv_episodes
               WHERE showid=tv_eps.showid AND
                     season > 0 AND
                     episode > 0 AND
                     airdate > 1 AND
                     status IN {status_quality}
              ) AS ep_snatched,
              (SELECT COUNT(*) FROM tv_episodes
               WHERE showid=tv_eps.showid AND
                     season > 0 AND
                     episode > 0 AND
                     airdate > 1 AND
                     status IN {status_download}
              ) AS ep_downloaded,
              (SELECT COUNT(*) FROM tv_episodes
               WHERE showid=tv_eps.showid AND
                     season > 0 AND
                     episode > 0 AND
                     airdate > 1 AND
                     ((airdate <= {today} AND (status = {skipped} OR
                                               status = {wanted} OR
                                               status = {failed})) OR
                      (status IN {status_quality}) OR
                      (status IN {status_download}))
              ) AS ep_total,
              (SELECT airdate FROM tv_episodes
               WHERE showid=tv_eps.showid AND
                     airdate >= {today} AND
                     (status = {unaired} OR status = {wanted})
               ORDER BY airdate ASC
               LIMIT 1
              ) AS ep_airs_next,
              (SELECT airdate FROM tv_episodes
               WHERE showid=tv_eps.showid AND
                     airdate > 1 AND
                     status <> {unaired}
               ORDER BY airdate DESC
               LIMIT 1
              ) AS ep_airs_prev,
              (SELECT SUM(file_size) FROM tv_episodes
               WHERE showid=tv_eps.showid
              ) AS show_size
            FROM tv_episodes tv_eps
            GROUP BY showid
            """.format(status_quality='({statuses})'.format(statuses=','.join([str(x) for x in snatched])),
                       status_download='({statuses})'.format(statuses=','.join([str(x) for x in downloaded])),
                       skipped=SKIPPED, wanted=WANTED, unaired=UNAIRED, failed=FAILED,
                       today=date.today().toordinal())
        )

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

        return '{callback}({msg});'.format(
            callback=callback,
            msg=json.dumps({
                'msg': '{pid}'.format(
                    pid=app.PID if app.started else 'nope')
            })
        )

    @staticmethod
    # @TODO: Replace with /api/v2/config/kodi, check if enabled === true
    def haveKODI():
        return app.USE_KODI and app.KODI_UPDATE_LIBRARY

    @staticmethod
    # @TODO: Replace with /api/v2/config/plex, check if enabled === true
    def havePLEX():
        return app.USE_PLEX_SERVER and app.PLEX_UPDATE_LIBRARY

    @staticmethod
    # @TODO: Replace with /api/v2/config/emby, check if enabled === true
    def haveEMBY():
        return app.USE_EMBY

    @staticmethod
    # @TODO: Replace with /api/v2/config/torrents, check if enabled === true
    def haveTORRENT():
        return bool(app.USE_TORRENTS and app.TORRENT_METHOD != 'blackhole' and
                    (app.ENABLE_HTTPS and app.TORRENT_HOST[:5] == 'https' or not
                     app.ENABLE_HTTPS and app.TORRENT_HOST[:5] == 'http:'))

    @staticmethod
    def testSABnzbd(host=None, username=None, password=None, apikey=None):
        host = config.clean_url(host)

        connection, acces_msg = sab.getSabAccesMethod(host)
        if connection:
            authed, auth_msg = sab.testAuthentication(host, username, password, apikey)  # @UnusedVariable
            if authed:
                return 'Success. Connected and authenticated'
            else:
                return 'Authentication failed. SABnzbd expects {access!r} as authentication method, {auth!r}'.format(
                    access=acces_msg, auth=auth_msg)
        else:
            return 'Unable to connect to host'

    @staticmethod
    def testNZBget(host=None, username=None, password=None, use_https=False):
        connected_status = nzbget.testNZB(host, username, password, config.checkbox_to_value(use_https))
        if connected_status:
            return 'Success. Connected and authenticated'
        else:
            return 'Unable to connect to host'

    @staticmethod
    def testTorrent(torrent_method=None, host=None, username=None, password=None):
        # @TODO: Move this to the validation section of each PATCH/PUT method for torrents
        host = config.clean_url(host)

        client = torrent.get_client_class(torrent_method)

        _, acces_msg = client(host, username, password).test_authentication()

        return acces_msg

    @staticmethod
    def testFreeMobile(freemobile_id=None, freemobile_apikey=None):
        result, message = notifiers.freemobile_notifier.test_notify(freemobile_id, freemobile_apikey)
        if result:
            return 'SMS sent successfully'
        else:
            return 'Problem sending SMS: {msg}'.format(msg=message)

    @staticmethod
    def testTelegram(telegram_id=None, telegram_apikey=None):
        result, message = notifiers.telegram_notifier.test_notify(telegram_id, telegram_apikey)
        if result:
            return 'Telegram notification succeeded. Check your Telegram clients to make sure it worked'
        else:
            return 'Error sending Telegram notification: {msg}'.format(msg=message)

    @staticmethod
    def testGrowl(host=None, password=None):
        success = 'Registered and Tested growl successfully'
        failure = 'Registration and Testing of growl failed'

        host = config.clean_host(host, default_port=23053)
        result = notifiers.growl_notifier.test_notify(host, password)

        return '{message} {host}{password}'.format(
            message=success if result else failure,
            host=unquote_plus(host),
            password=' with password: {pwd}'.format(pwd=password) if password else ''
        )

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
        logger.log(u'result: {result}'.format(result=result))

        return 'Key verification successful' if result else 'Unable to verify key'

    @staticmethod
    def testTwitter():
        result = notifiers.twitter_notifier.test_notify()
        return 'Tweet successful, check your twitter to make sure it worked' if result else 'Error sending tweet'

    @staticmethod
    def testKODI(host=None, username=None, password=None):
        host = config.clean_hosts(host)
        final_result = ''
        for curHost in [x.strip() for x in host.split(',')]:
            cur_result = notifiers.kodi_notifier.test_notify(unquote_plus(curHost), username, password)
            if len(cur_result.split(':')) > 2 and 'OK' in cur_result.split(':')[2]:
                final_result += 'Test KODI notice sent successfully to {host}<br>\n'.format(host=unquote_plus(curHost))
            else:
                final_result += 'Test KODI notice failed to {host}<br>\n'.format(host=unquote_plus(curHost))

        return final_result

    def testPHT(self, host=None, username=None, password=None):
        self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')

        if None is not password and set('*') == set(password):
            password = app.PLEX_CLIENT_PASSWORD

        final_result = ''
        for curHost in [x.strip() for x in host.split(',')]:
            cur_result = notifiers.plex_notifier.test_notify_pht(unquote_plus(curHost), username, password)
            if len(cur_result.split(':')) > 2 and 'OK' in cur_result.split(':')[2]:
                final_result += 'Successful test notice sent to Plex Home Theater ... {host}<br>\n'.format(host=unquote_plus(curHost))
            else:
                final_result += 'Test failed for Plex Home Theater ... {host}<br>\n'.format(host=unquote_plus(curHost))

        ui.notifications.message('Tested Plex Home Theater(s): ', unquote_plus(host.replace(',', ', ')))

        return final_result

    def testPMS(self, host=None, username=None, password=None, plex_server_token=None):
        self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')

        if password is not None and set('*') == set(password):
            password = app.PLEX_SERVER_PASSWORD

        final_result = ''

        cur_result = notifiers.plex_notifier.test_notify_pms(unquote_plus(host), username, password, plex_server_token)
        if cur_result is None:
            final_result += 'Successful test of Plex Media Server(s) ... {host}<br>\n'.format(host=unquote_plus(host.replace(',', ', ')))
        elif cur_result is False:
            final_result += 'Test failed, No Plex Media Server host specified<br>\n'
        else:
            final_result += 'Test failed for Plex Media Server(s) ... {host}<br>\n'.format(host=unquote_plus(host.replace(',', ', ')))

        ui.notifications.message('Tested Plex Media Server host(s): ', unquote_plus(host.replace(',', ', ')))

        return final_result

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
            return 'Test notice sent successfully to {host}'.format(host=unquote_plus(host))
        else:
            return 'Test notice failed to {host}'.format(host=unquote_plus(host))

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
            return json.dumps({
                'message': 'Got settings from {host}'.format(host=host),
                'database': app.NMJ_DATABASE,
                'mount': app.NMJ_MOUNT,
            })
        else:
            return json.dumps({
                'message': 'Failed! Make sure your Popcorn is on and NMJ is running. '
                           '(see Log & Errors -> Debug for detailed info)',
                'database': '',
                'mount': '',
            })

    @staticmethod
    def testNMJv2(host=None):
        host = config.clean_host(host)
        result = notifiers.nmjv2_notifier.test_notify(unquote_plus(host))
        if result:
            return 'Test notice sent successfully to {host}'.format(host=unquote_plus(host))
        else:
            return 'Test notice failed to {host}'.format(host=unquote_plus(host))

    @staticmethod
    def settingsNMJv2(host=None, dbloc=None, instance=None):
        host = config.clean_host(host)
        result = notifiers.nmjv2_notifier.notify_settings(unquote_plus(host), dbloc, instance)
        if result:
            return json.dumps({
                "message": "NMJ Database found at: {host}".format(host=host),
                "database": app.NMJv2_DATABASE,
            })
        else:
            return json.dumps({
                "message": "Unable to find NMJ Database at location: {db_loc}. "
                           "Is the right location selected and PCH running?".format(db_loc=dbloc),
                "database": ""
            })

    @staticmethod
    def getTraktToken(trakt_pin=None):
        trakt_settings = {"trakt_api_key": app.TRAKT_API_KEY,
                          "trakt_api_secret": app.TRAKT_API_SECRET}
        trakt_api = TraktApi(app.SSL_VERIFY, app.TRAKT_TIMEOUT, **trakt_settings)
        response = None
        try:
            (access_token, refresh_token) = trakt_api.get_token(app.TRAKT_REFRESH_TOKEN, trakt_pin=trakt_pin)
            if access_token and refresh_token:
                app.TRAKT_ACCESS_TOKEN = access_token
                app.TRAKT_REFRESH_TOKEN = refresh_token
                response = trakt_api.validate_account()
        except MissingTokenException:
            ui.notifications.error('You need to get a PIN and authorize Medusa app')
            return 'You need to get a PIN and authorize Medusa app'
        except TokenExpiredException:
            # Clear existing tokens
            app.TRAKT_ACCESS_TOKEN = ''
            app.TRAKT_REFRESH_TOKEN = ''
            ui.notifications.error('TOKEN expired. Reload page, get a new PIN and authorize Medusa app')
            return 'TOKEN expired. Reload page, get a new PIN and authorize Medusa app'
        except TraktException:
            ui.notifications.error("Connection error. Click 'Authorize Medusa' button again")
            return "Connection error. Click 'Authorize Medusa' button again"
        if response:
            ui.notifications.message('Trakt Authorized')
            return "Trakt Authorized"
        ui.notifications.error('Connection error. Reload the page to get new token!')
        return "Trakt Not Authorized!"

    @staticmethod
    def testTrakt(username=None, blacklist_name=None):
        return notifiers.trakt_notifier.test_notify(username, blacklist_name)

    @staticmethod
    def forceTraktSync():
        """Force a trakt sync, depending on the notification settings, library is synced with watchlist and/or collection."""
        return json.dumps({'result': ('Could not start sync', 'Sync Started')[app.trakt_checker_scheduler.forceRun()]})

    @staticmethod
    def loadShowNotifyLists():
        main_db_con = db.DBConnection()
        rows = main_db_con.select(
            b'SELECT show_id, show_name, notify_list '
            b'FROM tv_shows '
            b'ORDER BY show_name ASC'
        )

        data = {}
        size = 0
        for r in rows:
            notify_list = {
                'emails': '',
                'prowlAPIs': '',
            }
            if r[b'notify_list']:
                # First, handle legacy format (emails only)
                if not r[b'notify_list'][0] == '{':
                    notify_list['emails'] = r[b'notify_list']
                else:
                    notify_list = dict(ast.literal_eval(r[b'notify_list']))

            data[r[b'show_id']] = {
                'id': r[b'show_id'],
                'name': r[b'show_name'],
                'list': notify_list['emails'],
                'prowl_notify_list': notify_list['prowlAPIs']
            }
            size += 1
        data['_size'] = size
        return json.dumps(data)

    @staticmethod
    def saveShowNotifyList(show=None, emails=None, prowlAPIs=None):
        entries = {'emails': '', 'prowlAPIs': ''}
        main_db_con = db.DBConnection()

        # Get current data
        sql_results = main_db_con.select(
            b'SELECT notify_list '
            b'FROM tv_shows '
            b'WHERE show_id = ?',
            [show]
        )
        for subs in sql_results:
            if subs[b'notify_list']:
                # First, handle legacy format (emails only)
                if not subs[b'notify_list'][0] == '{':
                    entries['emails'] = subs[b'notify_list']
                else:
                    entries = dict(ast.literal_eval(subs[b'notify_list']))

        if emails is not None:
            entries['emails'] = emails
            if not main_db_con.action(
                    b'UPDATE tv_shows '
                    b'SET notify_list = ? '
                    b'WHERE show_id = ?',
                    [str(entries), show]
            ):
                return 'ERROR'

        if prowlAPIs is not None:
            entries['prowlAPIs'] = prowlAPIs
            if not main_db_con.action(
                    b'UPDATE tv_shows '
                    b'SET notify_list = ? '
                    b'WHERE show_id = ?',
                    [str(entries), show]
            ):
                return 'ERROR'

        return 'OK'

    @staticmethod
    def testEmail(host=None, port=None, smtp_from=None, use_tls=None, user=None, pwd=None, to=None):
        host = config.clean_host(host)
        if notifiers.email_notifier.test_notify(host, port, smtp_from, use_tls, user, pwd, to):
            return 'Test email sent successfully! Check inbox.'
        else:
            return 'ERROR: {error}'.format(error=notifiers.email_notifier.last_err)

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
        if result.get('success'):
            return 'Pushbullet notification succeeded. Check your device to make sure it worked'
        else:
            return 'Error sending Pushbullet notification: {0}'.format(result.get('error'))

    @staticmethod
    def getPushbulletDevices(api=None):
        result = notifiers.pushbullet_notifier.get_devices(api)
        if result:
            return result
        else:
            return 'Error sending Pushbullet notification'

    def status(self):
        tv_dir_free = helpers.get_disk_space_usage(app.TV_DOWNLOAD_DIR)
        root_dir = {}
        if app.ROOT_DIRS:
            backend_pieces = app.ROOT_DIRS.split('|')
            backend_dirs = backend_pieces[1:]
        else:
            backend_dirs = []

        if backend_dirs:
            for subject in backend_dirs:
                root_dir[subject] = helpers.get_disk_space_usage(subject)

        t = PageTemplate(rh=self, filename='status.mako')
        return t.render(title='Status', header='Status', topmenu='system',
                        tvdirFree=tv_dir_free, rootDir=root_dir,
                        controller='home', action='status')

    def shutdown(self, pid=None):
        if not Shutdown.stop(pid):
            return self.redirect('/{page}/'.format(page=app.DEFAULT_PAGE))

        title = 'Shutting down'
        message = 'Medusa is shutting down...'

        return self._genericMessage(title, message)

    def restart(self, pid=None):
        if not Restart.restart(pid):
            return self.redirect('/{page}/'.format(page=app.DEFAULT_PAGE))

        t = PageTemplate(rh=self, filename='restart.mako')

        return t.render(title='Home', header='Restarting Medusa', topmenu='system',
                        controller='home', action='restart')

    def updateCheck(self, pid=None):
        if str(pid) != str(app.PID):
            return self.redirect('/home/')

        app.version_check_scheduler.action.check_for_new_version(force=True)
        app.version_check_scheduler.action.check_for_new_news(force=True)

        return self.redirect('/{page}/'.format(page=app.DEFAULT_PAGE))

    def update(self, pid=None, branch=None):
        if str(pid) != str(app.PID):
            return self.redirect('/home/')

        checkversion = CheckVersion()
        backup = checkversion.updater and checkversion._runbackup()  # pylint: disable=protected-access

        if backup is True:
            if branch:
                checkversion.updater.branch = branch

            if checkversion.updater.need_update() and checkversion.updater.update():
                # do a hard restart
                app.events.put(app.events.SystemEvent.RESTART)

                t = PageTemplate(rh=self, filename='restart.mako')
                return t.render(title='Home', header='Restarting Medusa', topmenu='home',
                                controller='home', action='restart')
            else:
                return self._genericMessage('Update Failed',
                                            'Update wasn\'t successful, not restarting. Check your log for more information.')
        else:
            return self.redirect('/{page}/'.format(page=app.DEFAULT_PAGE))

    def branchCheckout(self, branch):
        if app.BRANCH != branch:
            app.BRANCH = branch
            ui.notifications.message('Checking out branch: ', branch)
            return self.update(app.PID, branch)
        else:
            ui.notifications.message('Already on branch: ', branch)
            return self.redirect('/{page}/'.format(page=app.DEFAULT_PAGE))

    def branchForceUpdate(self):
        return {
            'currentBranch': app.BRANCH,
            'resetBranches': app.GIT_RESET_BRANCHES,
            'branches': [branch for branch in app.version_check_scheduler.action.list_remote_branches() if branch not in app.GIT_RESET_BRANCHES]
        }

    @staticmethod
    def getDBcompare():
        checkversion = CheckVersion()  # @TODO: replace with settings var
        db_status = checkversion.getDBcompare()

        if db_status == 'upgrade':
            logger.log(u'Checkout branch has a new DB version - Upgrade', logger.DEBUG)
            return json.dumps({
                'status': 'success',
                'message': 'upgrade',
            })
        elif db_status == 'equal':
            logger.log(u'Checkout branch has the same DB version - Equal', logger.DEBUG)
            return json.dumps({
                'status': 'success',
                'message': 'equal',
            })
        elif db_status == 'downgrade':
            logger.log(u'Checkout branch has an old DB version - Downgrade', logger.DEBUG)
            return json.dumps({
                'status': 'success',
                'message': 'downgrade',
            })
        else:
            logger.log(u'Checkout branch couldn\'t compare DB version.', logger.WARNING)
            return json.dumps({
                'status': 'error',
                'message': 'General exception',
            })

    def getSeasonSceneExceptions(self, indexer, indexer_id):
        """Get show name scene exceptions per season

        :param indexer: The shows indexer
        :param indexer_id: The shows indexer_id
        :return: A json with the scene exceptions per season.
        """
        return json.dumps({
            'seasonExceptions': {season: list(exception_name) for season, exception_name
                                 in iteritems(get_all_scene_exceptions(indexer_id))},
            'xemNumbering': {tvdb_season_ep[0]: anidb_season_ep[0]
                             for (tvdb_season_ep, anidb_season_ep)
                             in iteritems(get_xem_numbering_for_show(indexer_id, indexer, refresh_data=False))}
        })

    def displayShow(self, show=None):
        # @TODO: add more comprehensive show validation
        try:
            show = int(show)  # fails if show id ends in a period SickRage/sickrage-issues#65
            show_obj = Show.find(app.showList, show)
        except (ValueError, TypeError):
            return self._genericMessage('Error', 'Invalid show ID: {show}'.format(show=show))

        if show_obj is None:
            return self._genericMessage('Error', 'Show not in show list')

        main_db_con = db.DBConnection()
        season_results = main_db_con.select(
            b'SELECT DISTINCT season '
            b'FROM tv_episodes '
            b'WHERE showid = ? AND  season IS NOT NULL '
            b'ORDER BY season DESC',
            [show_obj.indexerid]
        )

        min_season = 0 if app.DISPLAY_SHOW_SPECIALS else 1

        sql_results = main_db_con.select(
            b'SELECT * '
            b'FROM tv_episodes '
            b'WHERE showid = ? AND season >= ? '
            b'ORDER BY season DESC, episode DESC',
            [show_obj.indexerid, min_season]
        )

        t = PageTemplate(rh=self, filename='displayShow.mako')
        submenu = [{
            'title': 'Edit',
            'path': 'home/editShow?show={show}'.format(show=show_obj.indexerid),
            'icon': 'ui-icon ui-icon-pencil',
        }]

        try:
            show_loc = (show_obj.location, True)
        except ShowDirectoryNotFoundException:
            show_loc = (show_obj._location, False)  # pylint: disable=protected-access

        show_message = ''

        if app.show_queue_scheduler.action.isBeingAdded(show_obj):
            show_message = 'This show is in the process of being downloaded - the info below is incomplete.'

        elif app.show_queue_scheduler.action.isBeingUpdated(show_obj):
            show_message = 'The information on this page is in the process of being updated.'

        elif app.show_queue_scheduler.action.isBeingRefreshed(show_obj):
            show_message = 'The episodes below are currently being refreshed from disk'

        elif app.show_queue_scheduler.action.isBeingSubtitled(show_obj):
            show_message = 'Currently downloading subtitles for this show'

        elif app.show_queue_scheduler.action.isInRefreshQueue(show_obj):
            show_message = 'This show is queued to be refreshed.'

        elif app.show_queue_scheduler.action.isInUpdateQueue(show_obj):
            show_message = 'This show is queued and awaiting an update.'

        elif app.show_queue_scheduler.action.isInSubtitleQueue(show_obj):
            show_message = 'This show is queued and awaiting subtitles download.'

        if not app.show_queue_scheduler.action.isBeingAdded(show_obj):
            if not app.show_queue_scheduler.action.isBeingUpdated(show_obj):
                submenu.append({
                    'title': 'Resume' if show_obj.paused else 'Pause',
                    'path': 'home/togglePause?show={show}'.format(show=show_obj.indexerid),
                    'icon': 'ui-icon ui-icon-{state}'.format(state='play' if show_obj.paused else 'pause'),
                })
                submenu.append({
                    'title': 'Remove',
                    'path': 'home/deleteShow?show={show}'.format(show=show_obj.indexerid),
                    'class': 'removeshow',
                    'confirm': True,
                    'icon': 'ui-icon ui-icon-trash',
                })
                submenu.append({
                    'title': 'Re-scan files',
                    'path': 'home/refreshShow?show={show}'.format(show=show_obj.indexerid),
                    'icon': 'ui-icon ui-icon-refresh',
                })
                submenu.append({
                    'title': 'Force Full Update',
                    'path': 'home/updateShow?show={show}'.format(show=show_obj.indexerid),
                    'icon': 'ui-icon ui-icon-transfer-e-w',
                })
                submenu.append({
                    'title': 'Update show in KODI',
                    'path': 'home/updateKODI?show={show}'.format(show=show_obj.indexerid),
                    'requires': self.haveKODI(),
                    'icon': 'menu-icon-kodi',
                })
                submenu.append({
                    'title': 'Update show in Emby',
                    'path': 'home/updateEMBY?show={show}'.format(show=show_obj.indexerid),
                    'requires': self.haveEMBY(),
                    'icon': 'menu-icon-emby',
                })
                submenu.append({
                    'title': 'Preview Rename',
                    'path': 'home/testRename?show={show}'.format(show=show_obj.indexerid),
                    'icon': 'ui-icon ui-icon-tag',
                })

                if app.USE_SUBTITLES and not app.show_queue_scheduler.action.isBeingSubtitled(
                        show_obj) and show_obj.subtitles:
                    submenu.append({
                        'title': 'Download Subtitles',
                        'path': 'home/subtitleShow?show={show}'.format(show=show_obj.indexerid),
                        'icon': 'menu-icon-backlog',
                    })

        ep_counts = {
            Overview.SKIPPED: 0,
            Overview.WANTED: 0,
            Overview.QUAL: 0,
            Overview.GOOD: 0,
            Overview.UNAIRED: 0,
            Overview.SNATCHED: 0,
            Overview.SNATCHED_PROPER: 0,
            Overview.SNATCHED_BEST: 0
        }
        ep_cats = {}

        for cur_result in sql_results:
            cur_ep_cat = show_obj.get_overview(cur_result[b'status'], manually_searched=cur_result[b'manually_searched'])
            if cur_ep_cat:
                ep_cats['{season}x{episode}'.format(season=cur_result[b'season'], episode=cur_result[b'episode'])] = cur_ep_cat
                ep_counts[cur_ep_cat] += 1

        def titler(x):
            return (helpers.remove_article(x), x)[not x or app.SORT_ARTICLE]

        if app.ANIME_SPLIT_HOME:
            shows = []
            anime = []
            for show in app.showList:
                if show.is_anime:
                    anime.append(show)
                else:
                    shows.append(show)
            sorted_show_lists = [
                ['Shows', sorted(shows, lambda x, y: cmp(titler(x.name).lower(), titler(y.name).lower()))],
                ['Anime', sorted(anime, lambda x, y: cmp(titler(x.name).lower(), titler(y.name).lower()))]
            ]
        else:
            sorted_show_lists = [
                ['Shows', sorted(app.showList, lambda x, y: cmp(titler(x.name).lower(), titler(y.name).lower()))]
            ]

        bwl = None
        if show_obj.is_anime:
            bwl = show_obj.release_groups

        show_obj.exceptions = get_scene_exceptions(show_obj.indexerid, show_obj.indexer)

        indexerid = int(show_obj.indexerid)
        indexer = int(show_obj.indexer)

        # Delete any previous occurrances
        for index, recentShow in enumerate(app.SHOWS_RECENT):
            if recentShow['indexerid'] == indexerid:
                del app.SHOWS_RECENT[index]

        # Only track 5 most recent shows
        del app.SHOWS_RECENT[4:]

        # Insert most recent show
        app.SHOWS_RECENT.insert(0, {
            'indexerid': indexerid,
            'name': show_obj.name,
        })

        return t.render(
            submenu=submenu[::-1], showLoc=show_loc, show_message=show_message,
            show=show_obj, sql_results=sql_results, season_results=season_results,
            sortedShowLists=sorted_show_lists, bwl=bwl, ep_counts=ep_counts,
            ep_cats=ep_cats, all_scene_exceptions=' | '.join(show_obj.exceptions),
            scene_numbering=get_scene_numbering_for_show(indexerid, indexer),
            xem_numbering=get_xem_numbering_for_show(indexerid, indexer, refresh_data=False),
            scene_absolute_numbering=get_scene_absolute_numbering_for_show(indexerid, indexer),
            xem_absolute_numbering=get_xem_absolute_numbering_for_show(indexerid, indexer),
            title=show_obj.name, controller='home', action='displayShow',
        )

    def pickManualSearch(self, provider=None, rowid=None, manual_search_type='episode'):
        """
        Tries to Perform the snatch for a manualSelected episode, episodes or season pack.

        @param provider: The provider id, passed as usenet_crawler and not the provider name (Usenet-Crawler)
        @param rowid: The provider's cache table's rowid. (currently the implicit sqlites rowid is used, needs to be replaced in future)
        @param manual_search_type: Episode or Season search

        @return: A json with a {'success': true} or false.
        """

        # Try to retrieve the cached result from the providers cache table.
        # @TODO: the implicit sqlite rowid is used, should be replaced with an explicit PK column

        try:
            main_db_con = db.DBConnection('cache.db')
            cached_result = main_db_con.action(
                b'SELECT * '
                b'FROM \'{provider}\' '
                b'WHERE rowid = ?'.format(provider=provider),
                [rowid],
                fetchone=True
            )
        except Exception as msg:
            error_message = 'Couldn\'t read cached results. Error: {error}'.format(error=msg)
            logger.log(error_message)
            return self._genericMessage('Error', error_message)

        if not cached_result or not all([cached_result[b'url'],
                                         cached_result[b'quality'],
                                         cached_result[b'name'],
                                         cached_result[b'indexerid'],
                                         cached_result[b'season'] is not None,
                                         provider]):
            return self._genericMessage('Error', "Cached result doesn't have all needed info to snatch episode")

        try:
            show = int(cached_result[b'indexerid'])  # fails if show id ends in a period SickRage/sickrage-issues#65
            show_obj = Show.find(app.showList, show)
        except (ValueError, TypeError):
            return self._genericMessage('Error', 'Invalid show ID: {0}'.format(show))

        if not show_obj:
            return self._genericMessage('Error', 'Could not find a show with id {0} in the list of shows, did you remove the show?'.format(show))

        # Create a list of episode object(s)
        # Multi-episode: |1|2|
        # Single-episode: |1|
        # Season pack: || so we need to get all episodes from season and create all ep objects
        ep_objs = []
        if manual_search_type == 'episode':
            for episode in cached_result[b'episodes'].strip('|').split('|'):
                ep_objs.append(show_obj.get_episode(int(cached_result[b'season']), int(episode)))
        elif manual_search_type == 'season':
            ep_objs.extend(show_obj.get_all_episodes(int(cached_result[b'season'])))

        # Create the queue item
        snatch_queue_item = ManualSnatchQueueItem(show_obj, ep_objs, provider, cached_result)

        # Add the queue item to the queue
        app.manual_snatch_scheduler.action.add_item(snatch_queue_item)

        while snatch_queue_item.success is not False:
            if snatch_queue_item.started and snatch_queue_item.success:
                # If the snatch was successfull we'll need to update the original searched segment,
                # with the new status: SNATCHED (2)
                update_finished_search_queue_item(snatch_queue_item)
                return json.dumps({
                    'result': 'success',
                })
            time.sleep(1)

        return json.dumps({
            'result': 'failure',
        })

    def manualSearchCheckCache(self, show, season, episode, manual_search_type='episode', **last_prov_updates):
        """ Periodic check if the searchthread is still running for the selected show/season/ep
        and if there are new results in the cache.db
        """

        refresh_results = 'refresh'

        # Check if all params are integer. When JS issue, it can send show='undefined'
        try:
            int(show)
            int(episode)
            int(season)
        except ValueError:
            return {'result': 'error'}

        # To prevent it from keeping searching when no providers have been enabled
        if not enabled_providers('manualsearch'):
            return {'result': SEARCH_STATUS_FINISHED}

        main_db_con = db.DBConnection('cache.db')

        episodes_in_search = collect_episodes_from_search_thread(show)

        # Check if the requested ep is in a search thread
        searched_item = [search for search in episodes_in_search
                         if all((str(search.get('show')) == show,
                                 str(search.get('season')) == season,
                                 str(search.get('episode')) == episode))]

        # # No last_prov_updates available, let's assume we need to refresh until we get some
        # if not last_prov_updates:
        #     return {'result': REFRESH_RESULTS}

        sql_episode = '' if manual_search_type == 'season' else episode

        for provider, last_update in iteritems(last_prov_updates):
            table_exists = main_db_con.select(
                b'SELECT name '
                b'FROM sqlite_master '
                b'WHERE type=\'table\' AND name=?',
                [provider]
            )
            if not table_exists:
                continue
            # Check if the cache table has a result for this show + season + ep wich has a later timestamp, then last_update
            needs_update = main_db_con.select(
                b'SELECT * '
                b'FROM \'{provider}\' '
                b'WHERE episodes LIKE ? AND season = ? AND indexerid = ?  AND time > ?'.format(provider=provider),
                ['%|{episodes}|%'.format(episodes=sql_episode), season, show, int(last_update)]
            )

            if needs_update:
                return {'result': refresh_results}

        # If the item is queued multiple times (don't know if this is possible),
        # but then check if as soon as a search has finished
        # Move on and show results
        # Return a list of queues the episode has been found in
        search_status = [item.get('searchstatus') for item in searched_item]
        if not searched_item or all([last_prov_updates,
                                     SEARCH_STATUS_QUEUED not in search_status,
                                     SEARCH_STATUS_SEARCHING not in search_status,
                                     SEARCH_STATUS_FINISHED in search_status]):
            # If the ep not anymore in the QUEUED or SEARCHING Thread, and it has the status finished,
            # return it as finished
            return {'result': SEARCH_STATUS_FINISHED}

        # Force a refresh when the last_prov_updates is empty due to the tables not existing yet.
        # This can be removed if we make sure the provider cache tables always exist prior to the
        # start of the first search
        if not last_prov_updates and SEARCH_STATUS_FINISHED in search_status:
            return {'result': refresh_results}

        return {'result': searched_item[0]['searchstatus']}

    def snatchSelection(self, show=None, season=None, episode=None, manual_search_type='episode',
                        perform_search=0, down_cur_quality=0, show_all_results=0):
        """ The view with results for the manual selected show/episode """

        # @TODO: add more comprehensive show validation
        try:
            show = int(show)  # fails if show id ends in a period SickRage/sickrage-issues#65
            show_obj = Show.find(app.showList, show)
        except (ValueError, TypeError):
            return self._genericMessage('Error', 'Invalid show ID: {show}'.format(show=show))

        if show_obj is None:
            return self._genericMessage('Error', 'Show not in show list')

        # Retrieve cache results from providers
        search_show = {'show': show, 'season': season, 'episode': episode, 'manual_search_type': manual_search_type}

        provider_results = get_provider_cache_results(INDEXER_TVDBV2, perform_search=perform_search,
                                                      show_all_results=show_all_results, **search_show)

        t = PageTemplate(rh=self, filename='snatchSelection.mako')
        submenu = [{
            'title': 'Edit',
            'path': 'home/editShow?show={show}'.format(show=show_obj.indexerid),
            'icon': 'ui-icon ui-icon-pencil'
        }]

        try:
            show_loc = (show_obj.location, True)
        except ShowDirectoryNotFoundException:
            show_loc = (show_obj._location, False)  # pylint: disable=protected-access

        show_message = app.show_queue_scheduler.action.getQueueActionMessage(show_obj)

        if not app.show_queue_scheduler.action.isBeingAdded(show_obj):
            if not app.show_queue_scheduler.action.isBeingUpdated(show_obj):
                submenu.append({
                    'title': 'Resume' if show_obj.paused else 'Pause',
                    'path': 'home/togglePause?show={show}'.format(show=show_obj.indexerid),
                    'icon': 'ui-icon ui-icon-{state}'.format(state='play' if show_obj.paused else 'pause'),
                })
                submenu.append({
                    'title': 'Remove',
                    'path': 'home/deleteShow?show={show}'.format(show=show_obj.indexerid),
                    'class': 'removeshow',
                    'confirm': True,
                    'icon': 'ui-icon ui-icon-trash',
                })
                submenu.append({
                    'title': 'Re-scan files',
                    'path': 'home/refreshShow?show={show}'.format(show=show_obj.indexerid),
                    'icon': 'ui-icon ui-icon-refresh',
                })
                submenu.append({
                    'title': 'Force Full Update',
                    'path': 'home/updateShow?show={show}'.format(show=show_obj.indexerid),
                    'icon': 'ui-icon ui-icon-transfer-e-w',
                })
                submenu.append({
                    'title': 'Update show in KODI',
                    'path': 'home/updateKODI?show={show}'.format(show=show_obj.indexerid),
                    'requires': self.haveKODI(),
                    'icon': 'submenu-icon-kodi',
                })
                submenu.append({
                    'title': 'Update show in Emby',
                    'path': 'home/updateEMBY?show={show}'.format(show=show_obj.indexerid),
                    'requires': self.haveEMBY(),
                    'icon': 'ui-icon ui-icon-refresh',
                })
                submenu.append({
                    'title': 'Preview Rename',
                    'path': 'home/testRename?show={show}'.format(show=show_obj.indexerid),
                    'icon': 'ui-icon ui-icon-tag',
                })

                if app.USE_SUBTITLES and not app.show_queue_scheduler.action.isBeingSubtitled(
                        show_obj) and show_obj.subtitles:
                    submenu.append({
                        'title': 'Download Subtitles',
                        'path': 'home/subtitleShow?show={show}'.format(show=show_obj.indexerid),
                        'icon': 'ui-icon ui-icon-comment',
                    })

        def titler(x):
            return (helpers.remove_article(x), x)[not x or app.SORT_ARTICLE]

        if app.ANIME_SPLIT_HOME:
            shows = []
            anime = []
            for show in app.showList:
                if show.is_anime:
                    anime.append(show)
                else:
                    shows.append(show)
            sorted_show_lists = [
                ['Shows', sorted(shows, lambda x, y: cmp(titler(x.name), titler(y.name)))],
                ['Anime', sorted(anime, lambda x, y: cmp(titler(x.name), titler(y.name)))]]
        else:
            sorted_show_lists = [
                ['Shows', sorted(app.showList, lambda x, y: cmp(titler(x.name), titler(y.name)))]]

        bwl = None
        if show_obj.is_anime:
            bwl = show_obj.release_groups

        show_obj.exceptions = get_scene_exceptions(show_obj.indexerid, show_obj.indexer)

        indexer_id = int(show_obj.indexerid)
        indexer = int(show_obj.indexer)

        # Delete any previous occurrances
        for index, recentShow in enumerate(app.SHOWS_RECENT):
            if recentShow['indexerid'] == indexer_id:
                del app.SHOWS_RECENT[index]

        # Only track 5 most recent shows
        del app.SHOWS_RECENT[4:]

        # Insert most recent show
        app.SHOWS_RECENT.insert(0, {
            'indexerid': indexer_id,
            'name': show_obj.name,
        })

        episode_history = []
        try:
            main_db_con = db.DBConnection()
            episode_status_result = main_db_con.action(
                b'SELECT date, action, provider, resource, resource_size '
                b'FROM history '
                b'WHERE showid = ? '
                b'AND season = ? '
                b'AND episode = ? '
                b'AND (action LIKE \'%02\' OR action LIKE \'%04\' OR action LIKE \'%09\' OR action LIKE \'%11\' OR action LIKE \'%12\') '
                b'ORDER BY date DESC',
                [indexer_id, season, episode]
            )
            episode_history = [dict(row) for row in episode_status_result]
            for i in episode_history:
                i['status'], i['quality'] = Quality.split_composite_status(i['action'])
                i['action_date'] = sbdatetime.sbfdatetime(datetime.strptime(str(i['date']), History.date_format), show_seconds=True)
                i['resource_file'] = os.path.basename(i['resource'])
                i['status_name'] = statusStrings[i['status']]
                if i['status'] == DOWNLOADED:
                    i['status_color_style'] = 'downloaded'
                elif i['status'] in (SNATCHED, SNATCHED_PROPER, SNATCHED_BEST):
                    i['status_color_style'] = 'snatched'
                elif i['status'] == FAILED:
                    i['status_color_style'] = 'failed'
                provider = providers.get_provider_class(GenericProvider.make_id(i['provider']))
                if provider is not None:
                    i['provider_name'] = provider.name
                    i['provider_img_link'] = 'images/providers/' + provider.image_name()
                else:
                    i['provider_name'] = i['provider'] if i['provider'] != '-1' else 'Unknown'
                    i['provider_img_link'] = ''

            # Compare manual search results with history and set status
            for provider_result in provider_results['found_items']:
                failed_statuses = [FAILED, ]
                snatched_statuses = [SNATCHED, SNATCHED_PROPER, SNATCHED_BEST]
                if any([item for item in episode_history
                        if all([prepare_failed_name(provider_result['name']) in item['resource'],
                                item['provider'] in (provider_result['provider'], provider_result['release_group'],),
                                item['status'] in failed_statuses])
                        ]):
                    provider_result['status_highlight'] = 'failed'
                elif any([item for item in episode_history
                          if all([provider_result['name'] in item['resource'],
                                  item['provider'] in (provider_result['provider'],),
                                  item['status'] in snatched_statuses,
                                  item['resource_size'] == provider_result['size']],)
                          ]):
                    provider_result['status_highlight'] = 'snatched'
                else:
                    provider_result['status_highlight'] = ''

        # TODO: Remove the catchall, make sure we only catch expected exceptions!
        except Exception as msg:
            logger.log("Couldn't read latest episode status. Error: {error}".format(error=msg))

        # There is some logic for this in the partials/showheader.mako page.
        main_db_con = db.DBConnection()
        season_results = main_db_con.select(
            b'SELECT DISTINCT season '
            b'FROM tv_episodes '
            b'WHERE showid = ? AND  season IS NOT NULL '
            b'ORDER BY season DESC',
            [show_obj.indexerid]
        )

        min_season = 0 if app.DISPLAY_SHOW_SPECIALS else 1

        sql_results = main_db_con.select(
            b'SELECT * '
            b'FROM tv_episodes '
            b'WHERE showid = ? AND season >= ? '
            b'ORDER BY season DESC, episode DESC',
            [show_obj.indexerid, min_season]
        )

        ep_counts = {
            Overview.SKIPPED: 0,
            Overview.WANTED: 0,
            Overview.QUAL: 0,
            Overview.GOOD: 0,
            Overview.UNAIRED: 0,
            Overview.SNATCHED: 0,
            Overview.SNATCHED_PROPER: 0,
            Overview.SNATCHED_BEST: 0
        }

        ep_cats = {}

        for cur_result in sql_results:
            cur_ep_cat = show_obj.get_overview(cur_result[b'status'],
                                               manually_searched=cur_result[b'manually_searched'])
            if cur_ep_cat:
                ep_cats['{season}x{episode}'.format(season=cur_result[b'season'],
                                                    episode=cur_result[b'episode'])] = cur_ep_cat
                ep_counts[cur_ep_cat] += 1

        return t.render(
            submenu=submenu[::-1], showLoc=show_loc, show_message=show_message,
            show=show_obj, provider_results=provider_results, episode=episode,
            sortedShowLists=sorted_show_lists, bwl=bwl, season=season, manual_search_type=manual_search_type,
            all_scene_exceptions=' | '.join(show_obj.exceptions),
            scene_numbering=get_scene_numbering_for_show(indexer_id, indexer),
            xem_numbering=get_xem_numbering_for_show(indexer_id, indexer, refresh_data=False),
            scene_absolute_numbering=get_scene_absolute_numbering_for_show(indexer_id, indexer),
            xem_absolute_numbering=get_xem_absolute_numbering_for_show(indexer_id, indexer),
            title=show_obj.name, controller='home', action='snatchSelection',
            episode_history=episode_history, season_results=season_results, sql_results=sql_results,
            ep_counts=ep_counts, ep_cats=ep_cats
        )

    @staticmethod
    def sceneExceptions(show):
        # @TODO: Replace with plot from GET /api/v2/show/{id}
        exceptions_list = get_all_scene_exceptions(show)
        if not exceptions_list:
            return 'No scene exceptions'

        out = []
        for season, names in iter(sorted(iteritems(exceptions_list))):
            if season == -1:
                season = '*'
            out.append('S{season}: {names}'.format(season=season, names=', '.join(names)))
        return '<br>'.join(out)

    @staticmethod
    def check_show_for_language(show_obj, language):
        """
        Request the show in a specific language from the indexer.

        :param show_obj: (Series) Show object
        :param language: Language two-letter country code. For ex: 'en'
        :returns: True if show is found in language else False
        """

        # Get the Indexer used by the show
        show_indexer = indexerApi(show_obj.indexer)

        # Add the language to the show indexer's parameters
        params = show_indexer.api_params.copy()
        params.update({
            'language': language,
            'episodes': False,
        })

        # Create an indexer with the updated parameters
        indexer = show_indexer.indexer(**params)

        if language in indexer.config['valid_languages']:
            indexer[show_obj.indexerid]
            return True

    def editShow(self, show=None, location=None, allowed_qualities=None, preferred_qualities=None,
                 exceptions_list=None, flatten_folders=None, paused=None, directCall=False,
                 air_by_date=None, sports=None, dvd_order=None, indexer_lang=None,
                 subtitles=None, rls_ignore_words=None, rls_require_words=None,
                 anime=None, blacklist=None, whitelist=None, scene=None,
                 defaultEpStatus=None, quality_preset=None):
        # @TODO: Replace with PATCH /api/v2/show/{id}

        allowed_qualities = allowed_qualities or []
        preferred_qualities = preferred_qualities or []
        exceptions = exceptions_list or set()

        anidb_failed = False
        errors = []

        if show is None:
            error_string = 'Invalid show ID: {show}'.format(show=show)
            if directCall:
                return [error_string]
            else:
                return self._genericMessage('Error', error_string)

        show_obj = Show.find(app.showList, int(show))

        if not show_obj:
            error_string = 'Unable to find the specified show: {show}'.format(show=show)
            if directCall:
                return [error_string]
            else:
                return self._genericMessage('Error', error_string)

        show_obj.exceptions = get_scene_exceptions(show_obj.indexerid, show_obj.indexer)

        if try_int(quality_preset, None):
            preferred_qualities = []

        if not location and not allowed_qualities and not preferred_qualities and not flatten_folders:
            t = PageTemplate(rh=self, filename='editShow.mako')

            if show_obj.is_anime:
                if not show_obj.release_groups:
                    show_obj.release_groups = BlackAndWhiteList(show_obj.indexerid)
                whitelist = show_obj.release_groups.whitelist
                blacklist = show_obj.release_groups.blacklist

                groups = []
                if helpers.set_up_anidb_connection() and not anidb_failed:
                    try:
                        anime = adba.Anime(app.ADBA_CONNECTION, name=show_obj.name)
                        groups = anime.get_groups()
                    except Exception as msg:
                        ui.notifications.error('Unable to retreive Fansub Groups from AniDB.')
                        logger.log(u'Unable to retreive Fansub Groups from AniDB. Error is {0}'.format(str(msg)), logger.DEBUG)

            with show_obj.lock:
                show = show_obj
                scene_exceptions = get_scene_exceptions(show_obj.indexerid, show_obj.indexer)

            if show_obj.is_anime:
                return t.render(show=show, scene_exceptions=scene_exceptions, groups=groups, whitelist=whitelist,
                                blacklist=blacklist, title='Edit Show', header='Edit Show', controller='home', action='editShow')
            else:
                return t.render(show=show, scene_exceptions=scene_exceptions, title='Edit Show', header='Edit Show',
                                controller='home', action='editShow')

        flatten_folders = not config.checkbox_to_value(flatten_folders)  # UI inverts this value
        dvd_order = config.checkbox_to_value(dvd_order)
        paused = config.checkbox_to_value(paused)
        air_by_date = config.checkbox_to_value(air_by_date)
        scene = config.checkbox_to_value(scene)
        sports = config.checkbox_to_value(sports)
        anime = config.checkbox_to_value(anime)
        subtitles = config.checkbox_to_value(subtitles)

        do_update = False
        if show_obj.lang != indexer_lang:
            msg = (
                '{{status}} {language}'
                ' for {indexer_name} show {show_id}'.format(
                    language=indexer_lang,
                    show_id=show_obj.indexerid,
                    indexer_name=indexerApi(show_obj.indexer).name,
                )
            )
            status = 'Unexpected result when changing language to'
            log_level = logger.WARNING
            language = show_obj.lang
            try:
                do_update = self.check_show_for_language(
                    show_obj,
                    indexer_lang,
                )
            except IndexerShowNotFoundInLanguage:
                status = 'Could not change language to'
            except IndexerException as e:
                status = u'Failed getting show in'
                msg += u' Please try again later. Error: {err}'.format(
                    err=e.message,
                )
            else:
                language = indexer_lang
                status = 'Changing language to'
                log_level = logger.INFO
            finally:
                indexer_lang = language
                msg = msg.format(status=status)
                if log_level >= logger.WARNING:
                    errors.append(msg)
                logger.log(msg, log_level)

        if scene == show_obj.scene and anime == show_obj.anime:
            do_update_scene_numbering = False
        else:
            do_update_scene_numbering = True

        if not isinstance(allowed_qualities, list):
            allowed_qualities = [allowed_qualities]

        if not isinstance(preferred_qualities, list):
            preferred_qualities = [preferred_qualities]

        if isinstance(exceptions, list):
            exceptions = set(exceptions)

        if not isinstance(exceptions, set):
            exceptions = {exceptions}

        # If directCall from mass_edit_update no scene exceptions handling or
        # blackandwhite list handling
        if directCall:
            do_update_exceptions = False
        else:
            if exceptions == show_obj.exceptions:
                do_update_exceptions = False
            else:
                do_update_exceptions = True

            with show_obj.lock:
                if anime:
                    if not show_obj.release_groups:
                        show_obj.release_groups = BlackAndWhiteList(show_obj.indexerid)

                    if whitelist:
                        shortwhitelist = short_group_names(whitelist)
                        show_obj.release_groups.set_white_keywords(shortwhitelist)
                    else:
                        show_obj.release_groups.set_white_keywords([])

                    if blacklist:
                        shortblacklist = short_group_names(blacklist)
                        show_obj.release_groups.set_black_keywords(shortblacklist)
                    else:
                        show_obj.release_groups.set_black_keywords([])

        with show_obj.lock:
            new_quality = Quality.combine_qualities([int(q) for q in allowed_qualities], [int(q) for q in preferred_qualities])
            show_obj.quality = new_quality

            # reversed for now
            if bool(show_obj.flatten_folders) != bool(flatten_folders):
                show_obj.flatten_folders = flatten_folders
                try:
                    app.show_queue_scheduler.action.refreshShow(show_obj)
                except CantRefreshShowException as msg:
                    errors.append('Unable to refresh this show: {error}'.format(error=msg))

            show_obj.paused = paused
            show_obj.scene = scene
            show_obj.anime = anime
            show_obj.sports = sports
            show_obj.subtitles = subtitles
            show_obj.air_by_date = air_by_date
            show_obj.default_ep_status = int(defaultEpStatus)

            if not directCall:
                show_obj.lang = indexer_lang
                show_obj.dvd_order = dvd_order
                show_obj.rls_ignore_words = rls_ignore_words.strip()
                show_obj.rls_require_words = rls_require_words.strip()

            # if we change location clear the db of episodes, change it, write to db, and rescan
            old_location = os.path.normpath(show_obj._location)
            new_location = os.path.normpath(location)
            if old_location != new_location:
                logger.log('{old} != {new}'.format(old=old_location, new=new_location), logger.DEBUG)  # pylint: disable=protected-access
                if not os.path.isdir(location) and not app.CREATE_MISSING_SHOW_DIRS:
                    errors.append('New location <tt>{location}</tt> does not exist'.format(location=location))

                # don't bother if we're going to update anyway
                elif not do_update:
                    # change it
                    try:
                        show_obj.location = location
                        try:
                            app.show_queue_scheduler.action.refreshShow(show_obj)
                        except CantRefreshShowException as msg:
                            errors.append('Unable to refresh this show:{error}'.format(error=msg))
                            # grab updated info from TVDB
                            # show_obj.load_episodes_from_indexer()
                            # rescan the episodes in the new folder
                    except ShowDirectoryNotFoundException:
                        errors.append('The folder at <tt>{location}</tt> doesn\'t contain a tvshow.nfo - '
                                      'copy your files to that folder before you change the directory in Medusa.'.format
                                      (location=location))

            # save it to the DB
            show_obj.save_to_db()

        # force the update
        if do_update:
            try:
                app.show_queue_scheduler.action.updateShow(show_obj)
                time.sleep(cpu_presets[app.CPU_PRESET])
            except CantUpdateShowException as msg:
                errors.append('Unable to update show: {0}'.format(str(msg)))

        if do_update_exceptions:
            try:
                update_scene_exceptions(show_obj.indexerid, show_obj.indexer, exceptions)  # @UndefinedVdexerid)
                time.sleep(cpu_presets[app.CPU_PRESET])
            except CantUpdateShowException:
                errors.append('Unable to force an update on scene exceptions of the show.')

        if do_update_scene_numbering:
            try:
                xem_refresh(show_obj.indexerid, show_obj.indexer)
                time.sleep(cpu_presets[app.CPU_PRESET])
            except CantUpdateShowException:
                errors.append('Unable to force an update on scene numbering of the show.')

            # Must erase cached results when toggling scene numbering
            self.erase_cache(show_obj)

        if directCall:
            return errors

        if errors:
            ui.notifications.error(
                '{num} error{s} while saving changes:'.format(num=len(errors), s='s' if len(errors) > 1 else ''),
                '<ul>\n{list}\n</ul>'.format(list='\n'.join(['<li>{items}</li>'.format(items=error_item)
                                                             for error_item in errors])))

        return self.redirect('/home/displayShow?show={show}'.format(show=show))

    def erase_cache(self, show_obj):
        try:
            main_db_con = db.DBConnection('cache.db')
            for cur_provider in providers.sorted_provider_list():
                # Let's check if this provider table already exists
                table_exists = main_db_con.select(
                    b'SELECT name '
                    b'FROM sqlite_master '
                    b'WHERE type=\'table\' AND name=?',
                    [cur_provider.get_id()]
                )
                if not table_exists:
                    continue
                try:
                    main_db_con.action(
                        b'DELETE FROM \'{provider}\' '
                        b'WHERE indexerid = ?'.format(provider=cur_provider.get_id()),
                        [show_obj.indexerid]
                    )
                except Exception:
                    logger.log(u'Unable to delete cached results for provider {provider} for show: {show}'.format
                               (provider=cur_provider, show=show_obj.name), logger.DEBUG)

        except Exception:
            logger.log(u'Unable to delete cached results for show: {show}'.format
                       (show=show_obj.name), logger.DEBUG)

    def togglePause(self, show=None):
        # @TODO: Replace with PUT to update the state var /api/v2/show/{id}
        error, show_obj = Show.pause(show)

        if error is not None:
            return self._genericMessage('Error', error)

        ui.notifications.message('{show} has been {state}'.format
                                 (show=show_obj.name, state='paused' if show_obj.paused else 'resumed'))

        return self.redirect('/home/displayShow?show={show}'.format(show=show_obj.indexerid))

    def deleteShow(self, show=None, full=0):
        # @TODO: Replace with DELETE to delete the show resource /api/v2/show/{id}
        if show:
            error, show_obj = Show.delete(show, full)

            if error is not None:
                return self._genericMessage('Error', error)

            ui.notifications.message('{show} has been {state} {details}'.format(
                show=show_obj.name,
                state='trashed' if app.TRASH_REMOVE_SHOW else 'deleted',
                details='(with all related media)' if full else '(media untouched)',
            ))

            time.sleep(cpu_presets[app.CPU_PRESET])

        # Remove show from 'RECENT SHOWS' in 'Shows' menu
        app.SHOWS_RECENT = [x for x in app.SHOWS_RECENT if x['indexerid'] != show_obj.indexerid]

        # Don't redirect to the default page, so the user can confirm that the show was deleted
        return self.redirect('/home/')

    def refreshShow(self, show=None):
        # @TODO: Replace with status=refresh from PATCH /api/v2/show/{id}
        error, show_obj = Show.refresh(show)

        # This is a show validation error
        if error is not None and show_obj is None:
            return self._genericMessage('Error', error)

        # This is a refresh error
        if error is not None:
            ui.notifications.error('Unable to refresh this show.', error)

        time.sleep(cpu_presets[app.CPU_PRESET])

        return self.redirect('/home/displayShow?show={show}'.format(show=show_obj.indexerid))

    def updateShow(self, show=None):
        # @TODO: Replace with status=update or status=updating from PATCH /api/v2/show/{id}
        if show is None:
            return self._genericMessage('Error', 'Invalid show ID')

        show_obj = Show.find(app.showList, int(show))

        if show_obj is None:
            return self._genericMessage('Error', 'Unable to find the specified show')

        # force the update
        try:
            app.show_queue_scheduler.action.updateShow(show_obj)
        except CantUpdateShowException as e:
            ui.notifications.error('Unable to update this show.', ex(e))

        # just give it some time
        time.sleep(cpu_presets[app.CPU_PRESET])

        return self.redirect('/home/displayShow?show={show}'.format(show=show_obj.indexerid))

    def subtitleShow(self, show=None):
        if show is None:
            return self._genericMessage('Error', 'Invalid show ID')

        show_obj = Show.find(app.showList, int(show))

        if show_obj is None:
            return self._genericMessage('Error', 'Unable to find the specified show')

        # search and download subtitles
        app.show_queue_scheduler.action.download_subtitles(show_obj)

        time.sleep(cpu_presets[app.CPU_PRESET])

        return self.redirect('/home/displayShow?show={show}'.format(show=show_obj.indexerid))

    def updateKODI(self, show=None):
        show_name = None
        show_obj = None

        if show:
            show_obj = Show.find(app.showList, int(show))
            if show_obj:
                show_name = quote_plus(show_obj.name.encode('utf-8'))

        if app.KODI_UPDATE_ONLYFIRST:
            host = app.KODI_HOST.split(',')[0].strip()
        else:
            host = app.KODI_HOST

        if notifiers.kodi_notifier.update_library(showName=show_name):
            ui.notifications.message('Library update command sent to KODI host(s): {host}'.format(host=host))
        else:
            ui.notifications.error('Unable to contact one or more KODI host(s): {host}'.format(host=host))

        if show_obj:
            return self.redirect('/home/displayShow?show={show}'.format(show=show_obj.indexerid))
        else:
            return self.redirect('/home/')

    def updatePLEX(self):
        if None is notifiers.plex_notifier.update_library():
            ui.notifications.message(
                'Library update command sent to Plex Media Server host: {host}'.format(host=app.PLEX_SERVER_HOST))
        else:
            ui.notifications.error('Unable to contact Plex Media Server host: {host}'.format(host=app.PLEX_SERVER_HOST))
        return self.redirect('/home/')

    def updateEMBY(self, show=None):
        show_obj = None

        if show:
            show_obj = Show.find(app.showList, int(show))

        if notifiers.emby_notifier.update_library(show_obj):
            ui.notifications.message(
                'Library update command sent to Emby host: {host}'.format(host=app.EMBY_HOST))
        else:
            ui.notifications.error('Unable to contact Emby host: {host}'.format(host=app.EMBY_HOST))

        if show_obj:
            return self.redirect('/home/displayShow?show={show}'.format(show=show_obj.indexerid))
        else:
            return self.redirect('/home/')

    def setStatus(self, show=None, eps=None, status=None, direct=False):
        # @TODO: Merge this with the other PUT commands for /api/v2/show/{id}
        if not all([show, eps, status]):
            error_message = 'You must specify a show and at least one episode'
            if direct:
                ui.notifications.error('Error', error_message)
                return json.dumps({
                    'result': 'error',
                })
            else:
                return self._genericMessage('Error', error_message)

        # Use .has_key() since it is overridden for statusStrings in common.py
        if status not in statusStrings:
            error_message = 'Invalid status'
            if direct:
                ui.notifications.error('Error', error_message)
                return json.dumps({
                    'result': 'error',
                })
            else:
                return self._genericMessage('Error', error_message)

        show_obj = Show.find(app.showList, int(show))

        if not show_obj:
            error_message = 'Error', 'Show not in show list'
            if direct:
                ui.notifications.error('Error', error_message)
                return json.dumps({
                    'result': 'error',
                })
            else:
                return self._genericMessage('Error', error_message)

        segments = {}
        trakt_data = []
        if eps:

            sql_l = []
            for cur_ep in eps.split('|'):

                if not cur_ep:
                    logger.log(u'Current episode was empty when trying to set status', logger.DEBUG)

                logger.log(u'Attempting to set status on episode {episode} to {status}'.format
                           (episode=cur_ep, status=status), logger.DEBUG)

                ep_info = cur_ep.split('x')

                if not all(ep_info):
                    logger.log(u'Something went wrong when trying to set status, season: {season}, episode: {episode}'.format
                               (season=ep_info[0], episode=ep_info[1]), logger.DEBUG)
                    continue

                ep_obj = show_obj.get_episode(ep_info[0], ep_info[1])

                if not ep_obj:
                    return self._genericMessage('Error', 'Episode couldn\'t be retrieved')

                if int(status) in [WANTED, FAILED]:
                    # figure out what episodes are wanted so we can backlog them
                    if ep_obj.season in segments:
                        segments[ep_obj.season].append(ep_obj)
                    else:
                        segments[ep_obj.season] = [ep_obj]

                with ep_obj.lock:
                    # don't let them mess up UNAIRED episodes
                    if ep_obj.status == UNAIRED:
                        logger.log(u'Refusing to change status of {episode} because it is UNAIRED'.format
                                   (episode=cur_ep), logger.WARNING)
                        continue

                    snatched_qualities = Quality.SNATCHED + Quality.SNATCHED_PROPER + Quality.SNATCHED_BEST
                    if all([int(status) in Quality.DOWNLOADED,
                            ep_obj.status not in snatched_qualities + Quality.DOWNLOADED + [IGNORED],
                            not os.path.isfile(ep_obj.location)]):
                        logger.log(u'Refusing to change status of {episode} to DOWNLOADED '
                                   u'because it\'s not SNATCHED/DOWNLOADED'.format
                                   (episode=cur_ep), logger.WARNING)
                        continue

                    if all([int(status) == FAILED,
                            ep_obj.status not in snatched_qualities + Quality.DOWNLOADED + Quality.ARCHIVED]):
                        logger.log(u'Refusing to change status of {episode} to FAILED '
                                   u'because it\'s not SNATCHED/DOWNLOADED'.format(episode=cur_ep), logger.WARNING)
                        continue

                    if all([int(status) == WANTED,
                            ep_obj.status in Quality.DOWNLOADED + Quality.ARCHIVED]):
                        logger.log(u'Removing release_name for episode as as episode was changed to WANTED')
                        ep_obj.release_name = ''

                    if ep_obj.manually_searched and int(status) == WANTED:
                        logger.log(u"Resetting 'manually searched' flag as episode was changed to WANTED", logger.DEBUG)
                        ep_obj.manually_searched = False

                    ep_obj.status = int(status)

                    # mass add to database
                    sql_l.append(ep_obj.get_sql())

                    trakt_data.append((ep_obj.season, ep_obj.episode))

            data = notifiers.trakt_notifier.trakt_episode_data_generate(trakt_data)

            if app.USE_TRAKT and app.TRAKT_SYNC_WATCHLIST:
                if int(status) in [WANTED, FAILED]:
                    upd = 'Add'
                elif int(status) in [IGNORED, SKIPPED] + Quality.DOWNLOADED + Quality.ARCHIVED:
                    upd = 'Remove'

                logger.log(u'{action} episodes, showid: indexerid {show.indexerid}, Title {show.name} to Watchlist'.format
                           (action=upd, show=show_obj), logger.DEBUG)

                if data:
                    notifiers.trakt_notifier.update_watchlist(show_obj, data_episode=data, update=upd.lower())

            if sql_l:
                main_db_con = db.DBConnection()
                main_db_con.mass_action(sql_l)

        if int(status) == WANTED and not show_obj.paused:
            msg = 'Backlog was automatically started for the following seasons of <b>{show}</b>:<br>'.format(show=show_obj.name)
            msg += '<ul>'

            for season, segment in iteritems(segments):
                cur_backlog_queue_item = BacklogQueueItem(show_obj, segment)
                app.search_queue_scheduler.action.add_item(cur_backlog_queue_item)

                msg += '<li>Season {season}</li>'.format(season=season)
                logger.log(u'Sending backlog for {show} season {season} '
                           u'because some eps were set to wanted'.format
                           (show=show_obj.name, season=season))

            msg += '</ul>'

            if segments:
                ui.notifications.message('Backlog started', msg)
        elif int(status) == WANTED and show_obj.paused:
            logger.log(u'Some episodes were set to wanted, but {show} is paused. '
                       u'Not adding to Backlog until show is unpaused'.format
                       (show=show_obj.name))

        if int(status) == FAILED:
            msg = 'Retrying Search was automatically started for the following season of <b>{show}</b>:<br>'.format(show=show_obj.name)
            msg += '<ul>'

            for season, segment in iteritems(segments):
                cur_failed_queue_item = FailedQueueItem(show_obj, segment)
                app.search_queue_scheduler.action.add_item(cur_failed_queue_item)

                msg += '<li>Season {season}</li>'.format(season=season)
                logger.log(u'Retrying Search for {show} season {season} '
                           u'because some eps were set to failed'.format
                           (show=show_obj.name, season=season))

            msg += '</ul>'

            if segments:
                ui.notifications.message('Retry Search started', msg)

        if direct:
            return json.dumps({
                'result': 'success',
            })
        else:
            return self.redirect('/home/displayShow?show={show}'.format(show=show))

    def testRename(self, show=None):
        if show is None:
            return self._genericMessage('Error', 'You must specify a show')

        show_obj = Show.find(app.showList, int(show))

        if show_obj is None:
            return self._genericMessage('Error', 'Show not in show list')

        try:
            show_obj.location  # @UnusedVariable
        except ShowDirectoryNotFoundException:
            return self._genericMessage('Error', 'Can\'t rename episodes when the show dir is missing.')

        ep_obj_list = show_obj.get_all_episodes(has_location=True)
        ep_obj_list = [x for x in ep_obj_list if x.location]
        ep_obj_rename_list = []
        for ep_obj in ep_obj_list:
            has_already = False
            for check in ep_obj.related_episodes + [ep_obj]:
                if check in ep_obj_rename_list:
                    has_already = True
                    break
            if not has_already:
                ep_obj_rename_list.append(ep_obj)

        if ep_obj_rename_list:
            ep_obj_rename_list.reverse()

        t = PageTemplate(rh=self, filename='testRename.mako')
        submenu = [{
            'title': 'Edit',
            'path': 'home/editShow?show={show}'.format(show=show_obj.indexerid),
            'icon': 'ui-icon ui-icon-pencil'
        }]

        return t.render(submenu=submenu[::-1], ep_obj_list=ep_obj_rename_list,
                        show=show_obj, title='Preview Rename',
                        header='Preview Rename',
                        controller='home', action='previewRename')

    def doRename(self, show=None, eps=None):
        if show is None or eps is None:
            error_message = 'You must specify a show and at least one episode'
            return self._genericMessage('Error', error_message)

        show_obj = Show.find(app.showList, int(show))

        if show_obj is None:
            error_message = 'Error', 'Show not in show list'
            return self._genericMessage('Error', error_message)

        try:
            show_obj.location  # @UnusedVariable
        except ShowDirectoryNotFoundException:
            return self._genericMessage('Error', 'Can\'t rename episodes when the show dir is missing.')

        if eps is None:
            return self.redirect('/home/displayShow?show={show}'.format(show=show))

        main_db_con = db.DBConnection()
        for cur_ep in eps.split('|'):

            ep_info = cur_ep.split('x')

            # this is probably the worst possible way to deal with double eps but I've kinda painted myself into a corner here with this stupid database
            ep_result = main_db_con.select(
                b'SELECT location '
                b'FROM tv_episodes '
                b'WHERE showid = ? AND season = ? AND episode = ? AND 5=5',
                [show, ep_info[0], ep_info[1]])
            if not ep_result:
                logger.log(u'Unable to find an episode for {episode}, skipping'.format
                           (episode=cur_ep), logger.WARNING)
                continue
            related_eps_result = main_db_con.select(
                b'SELECT season, episode '
                b'FROM tv_episodes '
                b'WHERE location = ? AND episode != ?',
                [ep_result[0][b'location'], ep_info[1]]
            )

            root_ep_obj = show_obj.get_episode(ep_info[0], ep_info[1])
            root_ep_obj.related_episodes = []

            for cur_related_ep in related_eps_result:
                related_ep_obj = show_obj.get_episode(cur_related_ep[b'season'], cur_related_ep[b'episode'])
                if related_ep_obj not in root_ep_obj.related_episodes:
                    root_ep_obj.related_episodes.append(related_ep_obj)

            root_ep_obj.rename()

        return self.redirect('/home/displayShow?show={show}'.format(show=show))

    def searchEpisode(self, show=None, season=None, episode=None, manual_search=None):
        """Search a ForcedSearch single episode using providers which are backlog enabled."""
        down_cur_quality = 0

        # retrieve the episode object and fail if we can't get one
        ep_obj = get_episode(show, season, episode)
        if isinstance(ep_obj, str):
            return json.dumps({
                'result': 'failure',
            })

        # make a queue item for it and put it on the queue
        ep_queue_item = ForcedSearchQueueItem(ep_obj.show, [ep_obj], bool(int(down_cur_quality)), bool(manual_search))

        app.forced_search_queue_scheduler.action.add_item(ep_queue_item)

        # give the CPU a break and some time to start the queue
        time.sleep(cpu_presets[app.CPU_PRESET])

        if not ep_queue_item.started and ep_queue_item.success is None:
            return json.dumps({
                'result': 'success',
            })  # I Actually want to call it queued, because the search hasn't been started yet!
        if ep_queue_item.started and ep_queue_item.success is None:
            return json.dumps({
                'result': 'success',
            })
        else:
            return json.dumps({
                'result': 'failure',
            })

    # ## Returns the current ep_queue_item status for the current viewed show.
    # Possible status: Downloaded, Snatched, etc...
    # Returns {'show': 279530, 'episodes' : ['episode' : 6, 'season' : 1, 'searchstatus' : 'queued', 'status' : 'running', 'quality': '4013']
    def getManualSearchStatus(self, show=None):
        episodes = collect_episodes_from_search_thread(show)

        return json.dumps({
            'episodes': episodes,
        })

    def searchEpisodeSubtitles(self, show=None, season=None, episode=None, lang=None):
        # retrieve the episode object and fail if we can't get one
        ep_obj = get_episode(show, season, episode)
        if isinstance(ep_obj, str):
            return json.dumps({
                'result': 'failure',
            })

        try:
            if lang:
                logger.log("Manual re-downloading subtitles for {show} with language {lang}".format
                           (show=ep_obj.show.name, lang=lang))
            new_subtitles = ep_obj.download_subtitles(lang=lang)
        except Exception:
            return json.dumps({
                'result': 'failure',
            })

        if new_subtitles:
            new_languages = [subtitles.name_from_code(code) for code in new_subtitles]
            status = 'New subtitles downloaded: {languages}'.format(languages=', '.join(new_languages))
            result = 'success'
        else:
            new_languages = []
            status = 'No subtitles downloaded'
            result = 'failure'

        ui.notifications.message(ep_obj.show.name, status)
        return json.dumps({
            'result': result,
            'subtitles': ','.join(ep_obj.subtitles),
            'new_subtitles': ','.join(new_languages),
        })

    def manual_search_subtitles(self, show=None, season=None, episode=None, release_id=None, picked_id=None):
        mode = 'downloading' if picked_id else 'searching'
        logger.log('Starting to manual {mode} subtitles'.format(mode=mode))
        try:
            if release_id:
                # Release ID is sent when using postpone
                release = app.RELEASES_IN_PP[int(release_id)]
                show = release['show']
                season = release['season']
                episode = release['episode']
                filepath = release['release']
            else:
                filepath = None
            show = int(show)
            show_obj = Show.find(app.showList, show)
            ep_obj = show_obj.get_episode(season, episode)
            video_path = filepath or ep_obj.location
            release_name = ep_obj.release_name or os.path.basename(video_path)
        except IndexError:
            ui.notifications.message('Outdated list', 'Please refresh page and try again')
            logger.log('Outdated list. Please refresh page and try again', logger.WARNING)
            return json.dumps({'result': 'failure'})
        except (ValueError, TypeError) as e:
            ui.notifications.message('Error', "Please check logs")
            logger.log('Error while manual {mode} subtitles. Error: {error_msg}'.format
                       (mode=mode, error_msg=e), logger.ERROR)
            return json.dumps({'result': 'failure'})

        if not os.path.isfile(video_path):
            ui.notifications.message(ep_obj.show.name, "Video file no longer exists. Can't search for subtitles")
            logger.log('Video file no longer exists: {video_file}'.format(video_file=video_path), logger.DEBUG)
            return json.dumps({'result': 'failure'})

        try:
            if mode == 'searching':
                logger.log("Manual searching subtitles for: {0}".format(release_name))
                found_subtitles = subtitles.list_subtitles(tv_episode=ep_obj, video_path=video_path)
                if found_subtitles:
                    ui.notifications.message(ep_obj.show.name, 'Found {} subtitles'.format(len(found_subtitles)))
                else:
                    ui.notifications.message(ep_obj.show.name, 'No subtitle found')
                result = 'success' if found_subtitles else 'failure'
                subtitles_result = found_subtitles
            elif mode == 'downloading':
                logger.log("Manual downloading subtitles for: {0}".format(release_name))
                new_manual_subtitle = subtitles.save_subtitle(tv_episode=ep_obj, subtitle_id=picked_id, video_path=video_path)
                if new_manual_subtitle:
                    ui.notifications.message(ep_obj.show.name, 'Subtitle downloaded: {0}'.format(','.join(new_manual_subtitle)))
                else:
                    ui.notifications.message(ep_obj.show.name, 'Failed to download subtitle for {0}'.format(release_name))
                result = 'success' if new_manual_subtitle else 'failure'
                subtitles_result = new_manual_subtitle
            else:
                raise ValueError

            return json.dumps({
                'result': result,
                'release': release_name,
                'subtitles': subtitles_result
            })
        except Exception as e:
            ui.notifications.message(ep_obj.show.name, 'Failed to manual {0} subtitles'.format(mode))
            logger.log('Error while manual {mode} subtitles. Error: {error_msg}'.format
                       (mode=mode, error_msg=e), logger.ERROR)
            return json.dumps({'result': 'failure'})

    def setSceneNumbering(self, show, indexer, forSeason=None, forEpisode=None, forAbsolute=None, sceneSeason=None,
                          sceneEpisode=None, sceneAbsolute=None):

        # sanitize:
        forSeason = None if forSeason in ['null', ''] else forSeason
        forEpisode = None if forEpisode in ['null', ''] else forEpisode
        forAbsolute = None if forAbsolute in ['null', ''] else forAbsolute
        sceneSeason = None if sceneSeason in ['null', ''] else sceneSeason
        sceneEpisode = None if sceneEpisode in ['null', ''] else sceneEpisode
        sceneAbsolute = None if sceneAbsolute in ['null', ''] else sceneAbsolute

        show_obj = Show.find(app.showList, int(show))

        # Check if this is an anime, because we can't set the Scene numbering for anime shows
        if show_obj.is_anime and not forAbsolute:
            return json.dumps({
                'success': False,
                'errorMessage': 'You can\'t use the Scene numbering for anime shows. '
                                'Use the Scene Absolute field, to configure a diverging episode number.',
                'sceneSeason': None,
                'sceneAbsolute': None,
            })
        elif show_obj.is_anime:
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
        if show_obj.is_anime:
            ep_obj = get_episode(show, absolute=forAbsolute)
        else:
            ep_obj = get_episode(show, forSeason, forEpisode)

        if isinstance(ep_obj, str):
            result.update({
                'success': False,
                'errorMessage': ep_obj,
            })
        elif show_obj.is_anime:
            logger.log(u'Set absolute scene numbering for {show} from {absolute} to {scene_absolute}'.format
                       (show=show, absolute=forAbsolute, scene_absolute=sceneAbsolute), logger.DEBUG)

            show = int(show)
            indexer = int(indexer)
            forAbsolute = int(forAbsolute)
            if sceneAbsolute is not None:
                sceneAbsolute = int(sceneAbsolute)

            set_scene_numbering(show, indexer, absolute_number=forAbsolute, sceneAbsolute=sceneAbsolute)
        else:
            logger.log(u'setEpisodeSceneNumbering for {show} from {season}x{episode} to {scene_season}x{scene_episode}'.format
                       (show=show, season=forSeason, episode=forEpisode,
                        scene_season=sceneSeason, scene_episode=sceneEpisode), logger.DEBUG)

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

        if show_obj.is_anime:
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
        ep_obj = get_episode(show, season, episode)
        if isinstance(ep_obj, str):
            return json.dumps({
                'result': 'failure',
            })

        # make a queue item for it and put it on the queue
        ep_queue_item = FailedQueueItem(ep_obj.show, [ep_obj], bool(int(down_cur_quality)))  # pylint: disable=no-member
        app.forced_search_queue_scheduler.action.add_item(ep_queue_item)

        if not ep_queue_item.started and ep_queue_item.success is None:
            return json.dumps(
                {'result': 'success',
                 })  # Search has not been started yet!
        if ep_queue_item.started and ep_queue_item.success is None:
            return json.dumps({
                'result': 'success',
            })
        else:
            return json.dumps({
                'result': 'failure',
            })

    @staticmethod
    def fetch_releasegroups(show_name):
        logger.log(u'ReleaseGroups: {show}'.format(show=show_name), logger.INFO)
        if helpers.set_up_anidb_connection():
            try:
                anime = adba.Anime(app.ADBA_CONNECTION, name=show_name)
                groups = anime.get_groups()
                logger.log(u'ReleaseGroups: {groups}'.format(groups=groups), logger.INFO)
                return json.dumps({
                    'result': 'success',
                    'groups': groups,
                })
            except AttributeError as msg:
                logger.log(u'Unable to get ReleaseGroups: {error}'.format(error=msg), logger.DEBUG)

        return json.dumps({
            'result': 'failure',
        })
