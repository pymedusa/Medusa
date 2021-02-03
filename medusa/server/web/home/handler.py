# coding=utf-8

from __future__ import unicode_literals

import json
import os
import time
from datetime import date
from textwrap import dedent

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
from medusa.clients import torrent
from medusa.clients.nzb import (
    nzbget,
    sab,
)
from medusa.common import (
    ARCHIVED,
    DOWNLOADED,
    FAILED,
    Quality,
    SKIPPED,
    SNATCHED,
    SNATCHED_BEST,
    SNATCHED_PROPER,
    UNAIRED,
    WANTED,
    cpu_presets,
)
from medusa.helper.exceptions import (
    AnidbAdbaConnectionException,
    CantRefreshShowException,
    CantUpdateShowException,
    ShowDirectoryNotFoundException,
    ex,
)
from medusa.helpers.anidb import get_release_groups_for_anime
from medusa.indexers.api import indexerApi
from medusa.indexers.utils import indexer_name_to_id
from medusa.scene_exceptions import (
    get_all_scene_exceptions
)
from medusa.scene_numbering import (
    get_scene_absolute_numbering,
    get_scene_numbering,
    get_xem_numbering_for_show,
    set_scene_numbering,
    xem_refresh,
)
from medusa.search import SearchType
from medusa.search.manual import (
    collect_episodes_from_search_thread,
    update_finished_search_queue_item,
)
from medusa.search.queue import (
    BacklogQueueItem,
    SnatchQueueItem,
)
from medusa.server.web.core import (
    PageTemplate,
    WebRoot,
)
from medusa.show.show import Show
from medusa.tv.cache import Cache
from medusa.tv.series import Series, SeriesIdentifier
from medusa.updater.version_checker import CheckVersion

from requests.compat import (
    quote_plus,
    unquote_plus,
)

from six import iteritems, text_type
from six.moves import map

from tornroutes import route

import trakt
from trakt.errors import TraktException


@route('/home(/?.*)')
class Home(WebRoot):
    def __init__(self, *args, **kwargs):
        super(Home, self).__init__(*args, **kwargs)

    def _genericMessage(self, subject, message):
        t = PageTemplate(rh=self, filename='genericMessage.mako')
        return t.render(message=message, subject=subject, title='')

    def index(self):
        """
        Render the home page.

        [Converted to VueRouter]
        """
        t = PageTemplate(rh=self, filename='index.mako')
        return t.render()

    @staticmethod
    def show_statistics():
        pre_today = [SKIPPED, WANTED, FAILED]
        snatched = [SNATCHED, SNATCHED_PROPER, SNATCHED_BEST]
        downloaded = [DOWNLOADED, ARCHIVED]

        def query_in(items):
            return '({0})'.format(','.join(map(text_type, items)))

        query = dedent("""\
            SELECT showid, indexer,
              SUM(
                season > 0 AND
                episode > 0 AND
                airdate > 1 AND
                status IN {status_quality}
              ) AS ep_snatched,
              SUM(
                season > 0 AND
                episode > 0 AND
                airdate > 1 AND
                status IN {status_download}
              ) AS ep_downloaded,
              SUM(
                season > 0 AND
                episode > 0 AND
                airdate > 1 AND (
                  (airdate <= {today} AND status IN {status_pre_today})
                  OR status IN {status_both}
                )
              ) AS ep_total,
              (SELECT airdate FROM tv_episodes
               WHERE showid=tv_eps.showid AND
                     indexer=tv_eps.indexer AND
                     airdate >= {today} AND
                     (status = {unaired} OR status = {wanted})
               ORDER BY airdate ASC
               LIMIT 1
              ) AS ep_airs_next,
              (SELECT airdate FROM tv_episodes
               WHERE showid=tv_eps.showid AND
                     indexer=tv_eps.indexer AND
                     airdate > 1 AND
                     status <> {unaired}
               ORDER BY airdate DESC
               LIMIT 1
              ) AS ep_airs_prev,
              SUM(file_size) AS show_size
            FROM tv_episodes tv_eps
            GROUP BY showid, indexer
        """).format(status_quality=query_in(snatched), status_download=query_in(downloaded),
                    status_pre_today=query_in(pre_today), status_both=query_in(snatched + downloaded),
                    skipped=SKIPPED, wanted=WANTED, unaired=UNAIRED, today=date.today().toordinal())

        main_db_con = db.DBConnection()
        sql_result = main_db_con.select(query)

        show_stat = {}
        max_download_count = 1000
        for cur_result in sql_result:
            show_stat[(cur_result['indexer'], cur_result['showid'])] = cur_result
            if cur_result['ep_total'] > max_download_count:
                max_download_count = cur_result['ep_total']

        max_download_count *= 100

        return show_stat, max_download_count

    def is_alive(self, *args, **kwargs):
        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Headers', 'x-requested-with')

        return json.dumps({
            'pid': app.PID if app.started else ''
        })

    @staticmethod
    def testSABnzbd(host=None, username=None, password=None, apikey=None):
        host = config.clean_url(host)

        try:
            connection, acces_msg = sab.get_sab_access_method(host)
        except Exception as error:
            logger.log('Error while testing SABnzbd connection: {error}'.format(error=error), logger.WARNING)
            return 'Error while testing connection. Check warning logs.'

        if connection:
            authed, auth_msg = sab.test_authentication(host, username, password, apikey)  # @UnusedVariable
            if authed:
                return 'Success. Connected and authenticated'
            else:
                return 'Authentication failed. SABnzbd expects {access!r} as authentication method, {auth}'.format(
                    access=acces_msg, auth=auth_msg)
        else:
            return 'Unable to connect to host'

    @staticmethod
    def testNZBget(host=None, username=None, password=None, use_https=False):
        try:
            connected_status = nzbget.test_nzb(host, username, password, config.checkbox_to_value(use_https))
        except Exception as error:
            logger.log('Error while testing NZBget connection: {error}'.format(error=error), logger.WARNING)
            return 'Error while testing connection. Check warning logs.'
        if connected_status:
            return 'Success. Connected and authenticated'
        else:
            return 'Unable to connect to host'

    @staticmethod
    def testTorrent(torrent_method=None, host=None, username=None, password=None):
        # @TODO: Move this to the validation section of each PATCH/PUT method for torrents
        host = config.clean_url(host)

        try:
            client = torrent.get_client_class(torrent_method)

            _, acces_msg = client(host, username, password).test_authentication()
        except Exception as error:
            logger.log('Error while testing {torrent} connection: {error}'.format(
                torrent=torrent_method or 'torrent', error=error), logger.WARNING)
            return 'Error while testing connection. Check warning logs.'

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
    def testDiscord(discord_webhook=None, discord_tts=False):
        result, message = notifiers.discord_notifier.test_notify(discord_webhook, config.checkbox_to_value(discord_tts))
        if result:
            return 'Discord notification succeeded. Check your Discord channels to make sure it worked'
        else:
            return 'Error sending Discord notification: {msg}'.format(msg=message)

    @staticmethod
    def testslack(slack_webhook=None):
        result = notifiers.slack_notifier.test_notify(slack_webhook)
        if result:
            return 'Slack notification succeeded. Check your Slack channel to make sure it worked'
        else:
            return 'Error sending Slack notification'

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
        for curHost in [x.strip() for x in host if x.strip()]:
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

        host = config.clean_hosts(host)
        final_result = ''
        for curHost in [x.strip() for x in host if x.strip()]:
            cur_result = notifiers.plex_notifier.test_notify_pht(unquote_plus(curHost), username, password)
            if len(cur_result.split(':')) > 2 and 'OK' in cur_result.split(':')[2]:
                final_result += 'Successful test notice sent to Plex Home Theater ... {host}<br>\n'.format(host=unquote_plus(curHost))
            else:
                final_result += 'Test failed for Plex Home Theater ... {host}<br>\n'.format(host=unquote_plus(cur_result))

        ui.notifications.message('Tested Plex Home Theater(s)', final_result)

        return final_result

    def testPMS(self, host=None, username=None, password=None, plex_server_token=None):
        self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')

        if password is not None and set('*') == set(password):
            password = app.PLEX_SERVER_PASSWORD

        host = config.clean_hosts(host)
        final_result = ''

        cur_result = notifiers.plex_notifier.test_notify_pms(host, username, password, plex_server_token)
        if cur_result is None:
            final_result += 'Successful test of Plex Media Server(s) ... {host}<br>\n'.format(host=unquote_plus(', '.join(host)))
        elif cur_result is False:
            final_result += 'Test failed, No Plex Media Server host specified<br>\n'
        else:
            final_result += 'Test failed for Plex Media Server(s) ... {host}<br>\n'.format(host=unquote_plus(cur_result))

        ui.notifications.message('Tested Plex Media Server(s)', final_result)

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
                'message': 'NMJ Database found at: {host}'.format(host=host),
                'database': app.NMJv2_DATABASE,
            })
        else:
            return json.dumps({
                'message': 'Unable to find NMJ Database at location: {db_loc}. '
                           'Is the right location selected and PCH running?'.format(db_loc=dbloc),
                'database': ''
            })

    @staticmethod
    def requestTraktDeviceCodeOauth():
        """Start Trakt OAuth device auth. Send request."""
        logger.log('Start a new Oauth device authentication request. Request is valid for 60 minutes.', logger.INFO)
        try:
            app.TRAKT_DEVICE_CODE = trakt.get_device_code(app.TRAKT_API_KEY, app.TRAKT_API_SECRET)
        except TraktException as error:
            logger.log('Unable to get trakt device code. Error: {error!r}'.format(error=error), logger.WARNING)
            return json.dumps({'result': False})

        return json.dumps(app.TRAKT_DEVICE_CODE)

    @staticmethod
    def checkTrakTokenOauth():
        """Check if the Trakt device OAuth request has been authenticated."""
        logger.log('Start Trakt token request', logger.INFO)

        if not app.TRAKT_DEVICE_CODE.get('requested'):
            logger.log('You need to request a token before checking authentication', logger.WARNING)
            return json.dumps({'result': 'need to request first', 'error': True})

        if (app.TRAKT_DEVICE_CODE.get('requested') + app.TRAKT_DEVICE_CODE.get('requested')) < time.time():
            logger.log('Trakt token Request expired', logger.INFO)
            return json.dumps({'result': 'request expired', 'error': True})

        if not app.TRAKT_DEVICE_CODE.get('device_code'):
            logger.log('You need to request a token before checking authentication. Missing device code.', logger.WARNING)
            return json.dumps({'result': 'need to request first', 'error': True})

        try:
            response = trakt.get_device_token(
                app.TRAKT_DEVICE_CODE.get('device_code'), app.TRAKT_API_KEY, app.TRAKT_API_SECRET, store=True
            )
        except TraktException as error:
            logger.log('Unable to get trakt device token. Error: {error!r}'.format(error=error), logger.WARNING)
            return json.dumps({'result': 'Trakt error while retrieving device token', 'error': True})

        if response.ok:
            response_json = response.json()
            app.TRAKT_ACCESS_TOKEN, app.TRAKT_REFRESH_TOKEN = \
                response_json.get('access_token'), response_json.get('refresh_token')
            return json.dumps({'result': 'succesfully updated trakt access and refresh token', 'error': False})
        else:
            if response.status_code == 400:
                return json.dumps({'result': 'device code has not been activated yet', 'error': True})
            if response.status_code == 409:
                return json.dumps({'result': 'already activated this code', 'error': False})

        logger.log(u'Something went wrong', logger.DEBUG)
        return json.dumps({'result': 'Something went wrong'})

    @staticmethod
    def testTrakt(blacklist_name=None):
        return notifiers.trakt_notifier.test_notify(blacklist_name)

    @staticmethod
    def forceTraktSync():
        """Force a trakt sync, depending on the notification settings, library is synced with watchlist and/or collection."""
        return json.dumps({'result': ('Could not start sync', 'Sync Started')[app.trakt_checker_scheduler.forceRun()]})

    @staticmethod
    def loadShowNotifyLists():
        data = {}
        size = 0
        for show in app.showList:
            notify_list = {
                'emails': '',
                'prowlAPIs': '',
            }
            if show.notify_list:
                notify_list = show.notify_list

            data[show.identifier.slug] = {
                'id': show.show_id,
                'name': show.name,
                'slug': show.identifier.slug,
                'list': notify_list['emails'],
                'prowl_notify_list': notify_list['prowlAPIs']
            }
            size += 1
        data['_size'] = size
        return json.dumps(data)

    @staticmethod
    def saveShowNotifyList(show=None, emails=None, prowlAPIs=None):
        series_identifier = SeriesIdentifier.from_slug(show)
        series_obj = Series.find_by_identifier(series_identifier)

        # Create a new dict, to force the "dirty" flag on the Series object.
        entries = {'emails': '', 'prowlAPIs': ''}

        if not series_obj:
            return 'show missing'

        if series_obj.notify_list:
            entries.update(series_obj.notify_list)

        if emails is not None:
            entries['emails'] = emails

        if prowlAPIs is not None:
            entries['prowlAPIs'] = prowlAPIs

        series_obj.notify_list = entries
        series_obj.save_to_db()

        return 'OK'

    @staticmethod
    def testEmail(host=None, port=None, smtp_from=None, use_tls=None, user=None, pwd=None, to=None):
        host = config.clean_host(host)
        if notifiers.email_notifier.test_notify(host, port, smtp_from, use_tls, user, pwd, to):
            return 'Test email sent successfully! Check inbox.'
        else:
            return 'ERROR: {error}'.format(error=notifiers.email_notifier.last_err)

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
    def testJoin(api=None, device=None):
        result = notifiers.join_notifier.test_notify(api, device)
        if result.get('success'):
            return 'Join notification succeeded. Check your device to make sure it worked'
        else:
            return 'Error sending Join notification: {0}'.format(result.get('error'))

    @staticmethod
    def getPushbulletDevices(api=None):
        result = notifiers.pushbullet_notifier.get_devices(api)
        if result:
            return result
        else:
            return 'Error sending Pushbullet notification'

    def status(self):
        """
        Render the status page.

        [Converted to VueRouter]
        """
        return PageTemplate(rh=self, filename='index.mako').render()

    def restart(self):
        """
        Render the restart page.

        [Converted to VueRouter]
        """
        return PageTemplate(rh=self, filename='index.mako').render()

    def shutdown(self):
        """
        Render the shutdown page.

        [Converted to VueRouter]
        """
        return PageTemplate(rh=self, filename='index.mako').render()

    def update(self):
        """
        Render the update page.

        [Converted to VueRouter]
        """
        return PageTemplate(rh=self, filename='index.mako').render()

    def updateCheck(self, pid=None):
        if text_type(pid) != text_type(app.PID):
            return self.redirect('/home/')

        app.version_check_scheduler.action.check_for_new_version(force=True)
        app.version_check_scheduler.action.check_for_new_news(force=True)

        return self.redirect('/{page}/'.format(page=app.DEFAULT_PAGE))

    def branchCheckout(self, branch):
        if app.BRANCH != branch:
            app.BRANCH = branch
            ui.notifications.message('Checking out branch: ', branch)
            return self.update(app.PID, branch)
        else:
            ui.notifications.message('Already on branch: ', branch)
            return self.redirect('/{page}/'.format(page=app.DEFAULT_PAGE))

    @staticmethod
    def branchForceUpdate():
        return {
            'currentBranch': app.BRANCH,
            'resetBranches': app.GIT_RESET_BRANCHES,
            'branches': [branch for branch in app.version_check_scheduler.action.list_remote_branches()]
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
            logger.log(u"Checkout branch couldn't compare DB version.", logger.WARNING)
            return json.dumps({
                'status': 'error',
                'message': 'General exception',
            })

    def getSeasonSceneExceptions(self, showslug=None):
        """Get show name scene exceptions per season

        :param indexer: The shows indexer
        :param indexer_id: The shows indexer_id
        :return: A json with the scene exceptions per season.
        """
        identifier = SeriesIdentifier.from_slug(showslug)
        series_obj = Series.find_by_identifier(identifier)

        return json.dumps({
            'seasonExceptions': {season: list(exception_name) for season, exception_name
                                 in iteritems(get_all_scene_exceptions(series_obj))},
            'xemNumbering': {tvdb_season_ep[0]: anidb_season_ep[0]
                             for (tvdb_season_ep, anidb_season_ep)
                             in iteritems(get_xem_numbering_for_show(series_obj, refresh_data=False))}
        })

    def displayShow(self, showslug):
        """
        Render the home page.

        [Converted to VueRouter]
        """
        try:
            identifier = SeriesIdentifier.from_slug(showslug)
            series_obj = Series.find_by_identifier(identifier)
        except (ValueError, TypeError):
            return self._genericMessage('Error', 'Invalid series: {show_slug}'.format(show_slug=showslug))

        if series_obj is None:
            return self._genericMessage('Error', 'Show not in show list')

        t = PageTemplate(rh=self, filename='index.mako')

        return t.render(
            controller='home', action='displayShow',
        )

    def pickManualSearch(self, provider=None, identifier=None):
        """
        Tries to Perform the snatch for a manualSelected episode, episodes or season pack.

        @param provider: The provider id, passed as usenet_crawler and not the provider name (Usenet-Crawler)
        @param identifier: The provider's cache table's identifier (unique).

        @return: A json with a {'success': true} or false.
        """
        # Try to retrieve the cached result from the providers cache table.
        provider_obj = providers.get_provider_class(provider)

        try:
            cached_result = Cache(provider_obj).load_from_row(identifier)
        except Exception as msg:
            error_message = "Couldn't read cached results. Error: {error}".format(error=msg)
            logger.log(error_message)
            return self._genericMessage('Error', error_message)

        if not cached_result or not all([cached_result['url'],
                                         cached_result['quality'],
                                         cached_result['name'],
                                         cached_result['indexer'],
                                         cached_result['indexerid'],
                                         cached_result['season'] is not None,
                                         provider]):
            return self._genericMessage('Error', "Cached result doesn't have all needed info to snatch episode")

        try:
            series_obj = Show.find_by_id(app.showList, cached_result['indexer'], cached_result['indexerid'])
        except (ValueError, TypeError):
            return self._genericMessage('Error', 'Invalid show ID: {0}'.format(cached_result['indexerid']))

        if not series_obj:
            return self._genericMessage('Error', 'Could not find a show with id {0} in the list of shows, '
                                                 'did you remove the show?'.format(cached_result['indexerid']))

        search_result = provider_obj.get_result(series=series_obj, cache=cached_result)
        search_result.search_type = SearchType.MANUAL_SEARCH

        # Create the queue item
        snatch_queue_item = SnatchQueueItem(search_result.series, search_result.episodes, search_result)

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

    def snatchSelection(self, showslug, **query_args):
        """
        Render the home page.

        [Converted to VueRouter]
        """
        # @TODO: add more comprehensive show validation
        try:
            identifier = SeriesIdentifier.from_slug(showslug)
            series_obj = Series.find_by_identifier(identifier)
        except (ValueError, TypeError):
            return self._genericMessage('Error', 'Invalid show: {series}'.format(series=showslug))

        if series_obj is None:
            return self._genericMessage('Error', 'Show not in show list')

        t = PageTemplate(rh=self, filename='index.mako')

        return t.render(
            controller='home', action='snatchSelection'
        )

    @staticmethod
    def check_show_for_language(series_obj, language):
        """
        Request the show in a specific language from the indexer.

        :param series_obj: (Series) Show object
        :param language: Language two-letter country code. For ex: 'en'
        :returns: True if show is found in language else False
        """

        # Get the Indexer used by the show
        show_indexer = indexerApi(series_obj.indexer)

        # Add the language to the show indexer's parameters
        params = show_indexer.api_params.copy()
        params.update({
            'language': language,
            'episodes': False,
        })

        # Create an indexer with the updated parameters
        indexer = show_indexer.indexer(**params)

        if language in indexer.config['valid_languages']:
            return True

    def massEditShow(
        self, indexername=None, seriesid=None, location=None, allowed_qualities=None, preferred_qualities=None,
        season_folders=None, paused=None, air_by_date=None, sports=None, dvd_order=None, subtitles=None,
        anime=None, scene=None, defaultEpStatus=None
    ):
        """
        A variation of the original `editShow`, where `directCall` is always true.

        This route as been added specifically for the usage in the massEditSubmit route.
        It's called when trying to mass edit show configurations.
        This route should be removed after vueifying manage_massEdit.mako.
        """
        allowed_qualities = allowed_qualities or []
        preferred_qualities = preferred_qualities or []

        errors = 0

        if not indexername or not seriesid:
            logger.log('No show was selected (indexer: {indexer}, show: {show})'.format(
                indexer=indexername, show=seriesid), logger.WARNING)
            errors += 1
            return errors

        series_obj = Show.find_by_id(app.showList, indexer_name_to_id(indexername), seriesid)

        if not series_obj:
            logger.log('Unable to find the specified show: {indexer}{show}'.format(
                indexer=indexername, show=seriesid), logger.WARNING)
            errors += 1
            return errors

        season_folders = config.checkbox_to_value(season_folders)
        dvd_order = config.checkbox_to_value(dvd_order)
        paused = config.checkbox_to_value(paused)
        air_by_date = config.checkbox_to_value(air_by_date)
        scene = config.checkbox_to_value(scene)
        sports = config.checkbox_to_value(sports)
        anime = config.checkbox_to_value(anime)
        subtitles = config.checkbox_to_value(subtitles)

        do_update_scene_numbering = not (scene == series_obj.scene and anime == series_obj.anime)

        if not isinstance(allowed_qualities, list):
            allowed_qualities = [allowed_qualities]

        if not isinstance(preferred_qualities, list):
            preferred_qualities = [preferred_qualities]

        with series_obj.lock:
            new_quality = Quality.combine_qualities([int(q) for q in allowed_qualities],
                                                    [int(q) for q in preferred_qualities])
            series_obj.quality = new_quality

            # reversed for now
            if bool(series_obj.season_folders) != bool(season_folders):
                series_obj.season_folders = season_folders
                try:
                    app.show_queue_scheduler.action.refreshShow(series_obj)
                except CantRefreshShowException as error:
                    errors += 1
                    logger.log("Unable to refresh show '{show}': {error!r}".format
                               (show=series_obj.name, error=error), logger.WARNING)

            # Check if we should erase parsed cached results for that show
            do_erase_parsed_cache = False
            for item in [('scene', scene), ('anime', anime), ('sports', sports),
                         ('air_by_date', air_by_date), ('dvd_order', dvd_order)]:
                if getattr(series_obj, item[0]) != item[1]:
                    do_erase_parsed_cache = True
                    # Break if at least one setting was changed
                    break

            series_obj.paused = paused
            series_obj.scene = scene
            series_obj.anime = anime
            series_obj.sports = sports
            series_obj.subtitles = subtitles
            series_obj.air_by_date = air_by_date
            series_obj.default_ep_status = int(defaultEpStatus)
            series_obj.dvd_order = dvd_order

            # if we change location clear the db of episodes, change it, write to db, and rescan
            old_location = os.path.normpath(series_obj._location)
            new_location = os.path.normpath(location)
            if old_location != new_location:
                changed_location = True
                logger.log('Changing show location to: {new}'.format(new=new_location), logger.INFO)
                if not os.path.isdir(new_location):
                    if app.CREATE_MISSING_SHOW_DIRS:
                        logger.log("Show directory doesn't exist, creating it", logger.INFO)
                        try:
                            os.mkdir(new_location)
                        except OSError as error:
                            errors += 1
                            changed_location = False
                            logger.log("Unable to create the show directory '{location}'. Error: {msg}".format
                                       (location=new_location, msg=error), logger.WARNING)
                        else:
                            logger.log('New show directory created', logger.INFO)
                            helpers.chmod_as_parent(new_location)
                    else:
                        changed_location = False
                        logger.log("New location '{location}' does not exist. "
                                   "Enable setting 'Create missing show dirs'".format
                                   (location=location), logger.WARNING)

                # Save new location to DB only if we changed it
                if changed_location:
                    series_obj.location = new_location

                if changed_location and os.path.isdir(new_location):
                    try:
                        app.show_queue_scheduler.action.refreshShow(series_obj)
                    except CantRefreshShowException as error:
                        errors += 1
                        logger.log("Unable to refresh show '{show}'. Error: {error!r}".format
                                   (show=series_obj.name, error=error), logger.WARNING)

            # Save all settings changed while in series_obj.lock
            series_obj.save_to_db()

        if do_update_scene_numbering or do_erase_parsed_cache:
            try:
                xem_refresh(series_obj)
            except CantUpdateShowException as error:
                errors += 1
                logger.log("Unable to update scene numbering for show '{show}': {error!r}".format
                           (show=series_obj.name, error=error), logger.WARNING)

            # Must erase cached DB results when toggling scene numbering
            self.erase_cache(series_obj)

            # Erase parsed cached names as we are changing scene numbering
            series_obj.flush_episodes()
            series_obj.erase_cached_parse()

            # Need to refresh show as we updated scene numbering or changed show format
            try:
                app.show_queue_scheduler.action.refreshShow(series_obj)
            except CantRefreshShowException as error:
                errors += 1
                logger.log("Unable to refresh show '{show}'. Please manually trigger a full show refresh. "
                           'Error: {error!r}'.format(show=series_obj.name, error=error), logger.WARNING)

        return errors

    def editShow(self, **query_args):
        """
        Render the editShow page.

        [Converted to VueRouter]
        """
        return PageTemplate(rh=self, filename='index.mako').render()

    @staticmethod
    def erase_cache(series_obj):
        try:
            main_db_con = db.DBConnection('cache.db')
            for cur_provider in providers.sorted_provider_list():
                # Let's check if this provider table already exists
                table_exists = main_db_con.select(
                    'SELECT name '
                    'FROM sqlite_master '
                    "WHERE type='table' AND name=?",
                    [cur_provider.get_id()]
                )
                if not table_exists:
                    continue
                try:
                    main_db_con.action(
                        "DELETE FROM '{provider}' "
                        'WHERE indexerid = ?'.format(provider=cur_provider.get_id()),
                        [series_obj.series_id]
                    )
                except Exception:
                    logger.log(u'Unable to delete cached results for provider {provider} for show: {show}'.format
                               (provider=cur_provider, show=series_obj.name), logger.DEBUG)

        except Exception:
            logger.log(u'Unable to delete cached results for show: {show}'.format
                       (show=series_obj.name), logger.DEBUG)

    def togglePause(self, showslug=None):
        # @TODO: Replace with PUT to update the state var /api/v2/show/{id}
        identifier = SeriesIdentifier.from_slug(showslug)
        error, series_obj = Show.pause(identifier.indexer.slug, identifier.id)

        if error is not None:
            return self._genericMessage('Error', error)

        ui.notifications.message('{show} has been {state}'.format
                                 (show=series_obj.name, state='paused' if series_obj.paused else 'resumed'))

        return self.redirect('/home/displayShow?showslug={series_obj.slug}'.format(series_obj=series_obj))

    def deleteShow(self, showslug=None, full=0):
        # @TODO: Replace with DELETE to delete the show resource /api/v2/show/{id}
        if showslug:
            identifier = SeriesIdentifier.from_slug(showslug)
            error, series_obj = Show.delete(identifier.indexer.slug, identifier.id, full)

            if error is not None:
                return self._genericMessage('Error', error)

            ui.notifications.message('{show} has been {state} {details}'.format(
                show=series_obj.name,
                state='trashed' if app.TRASH_REMOVE_SHOW else 'deleted',
                details='(with all related media)' if full else '(media untouched)',
            ))

            time.sleep(cpu_presets[app.CPU_PRESET])

        # Remove show from 'RECENT SHOWS' in 'Shows' menu
        app.SHOWS_RECENT = [show for show in app.SHOWS_RECENT if show['showSlug'] != showslug]

        # Don't redirect to the default page, so the user can confirm that the show was deleted
        return self.redirect('/home/')

    def refreshShow(self, showslug=None):
        # @TODO: Replace with status=refresh from PATCH /api/v2/show/{id}
        identifier = SeriesIdentifier.from_slug(showslug)
        error, series_obj = Show.refresh(identifier.indexer.slug, identifier.id)

        # This is a show validation error
        if error is not None and series_obj is None:
            return self._genericMessage('Error', error)

        # This is a refresh error
        if error is not None:
            ui.notifications.error('Unable to refresh this show.', error)

        time.sleep(cpu_presets[app.CPU_PRESET])

        return self.redirect('/home/displayShow?showslug={series_obj.slug}'.format(series_obj=series_obj))

    def updateShow(self, showslug=None):
        # @TODO: Replace with status=update or status=updating from PATCH /api/v2/show/{id}
        if showslug is None:
            return self._genericMessage('Error', 'Invalid show ID')

        identifier = SeriesIdentifier.from_slug(showslug)
        series_obj = Series.find_by_identifier(identifier)

        if series_obj is None:
            return self._genericMessage('Error', 'Unable to find the specified show')

        # force the update
        try:
            app.show_queue_scheduler.action.updateShow(series_obj)
        except CantUpdateShowException as e:
            ui.notifications.error('Unable to update this show.', ex(e))

        # just give it some time
        time.sleep(cpu_presets[app.CPU_PRESET])

        return self.redirect('/home/displayShow?showslug={series_obj.slug}'.format(series_obj=series_obj))

    def subtitleShow(self, showslug=None):
        if showslug is None:
            return self._genericMessage('Error', 'Invalid show ID')

        identifier = SeriesIdentifier.from_slug(showslug)
        series_obj = Series.find_by_identifier(identifier)

        if series_obj is None:
            return self._genericMessage('Error', 'Unable to find the specified show')

        # search and download subtitles
        app.show_queue_scheduler.action.download_subtitles(series_obj)

        time.sleep(cpu_presets[app.CPU_PRESET])

        return self.redirect('/home/displayShow?showslug={series_obj.slug}'.format(series_obj=series_obj))

    def updateKODI(self, showslug=None):
        series_name = series_obj = None
        if showslug:
            identifier = SeriesIdentifier.from_slug(showslug)
            series_obj = Series.find_by_identifier(identifier)

            if series_obj is None:
                return self._genericMessage('Error', 'Unable to find the specified show')

            series_name = quote_plus(series_obj.name.encode('utf-8'))

        if app.KODI_UPDATE_ONLYFIRST:
            host = app.KODI_HOST[0].strip()
        else:
            host = ', '.join(app.KODI_HOST)

        if notifiers.kodi_notifier.update_library(series_name=series_name):
            ui.notifications.message('Library update command sent to KODI host(s): {host}'.format(host=host))
        else:
            ui.notifications.error('Unable to contact one or more KODI host(s): {host}'.format(host=host))

        if series_obj:
            return self.redirect('/home/displayShow?showslug={series_obj.slug}'.format(series_obj=series_obj))
        else:
            return self.redirect('/home/')

    def updatePLEX(self):
        if None is notifiers.plex_notifier.update_library():
            ui.notifications.message(
                'Library update command sent to Plex Media Server host: {host}'.format(host=', '.join(app.PLEX_SERVER_HOST)))
        else:
            ui.notifications.error('Unable to contact Plex Media Server host: {host}'.format(host=', '.join(app.PLEX_SERVER_HOST)))
        return self.redirect('/home/')

    def updateEMBY(self, showslug=None):
        series_obj = None
        if showslug:
            identifier = SeriesIdentifier.from_slug(showslug)
            series_obj = Series.find_by_identifier(identifier)

            if series_obj is None:
                return self._genericMessage('Error', 'Unable to find the specified show')

        if notifiers.emby_notifier.update_library(series_obj):
            ui.notifications.message(
                'Library update command sent to Emby host: {host}'.format(host=app.EMBY_HOST))
        else:
            ui.notifications.error('Unable to contact Emby host: {host}'.format(host=app.EMBY_HOST))

        if series_obj:
            return self.redirect('/home/displayShow?showslug={series_obj.slug}'.format(series_obj=series_obj))
        else:
            return self.redirect('/home/')

    def testRename(self, showslug=None):
        if not showslug:
            return self._genericMessage('Error', 'You must specify a show')

        identifier = SeriesIdentifier.from_slug(showslug)
        series_obj = Series.find_by_identifier(identifier)

        if series_obj is None:
            return self._genericMessage('Error', 'Show not in show list')

        try:
            series_obj.validate_location  # @UnusedVariable
        except ShowDirectoryNotFoundException:
            return self._genericMessage('Error', "Can't rename episodes when the show dir is missing.")

        ep_obj_list = series_obj.get_all_episodes(has_location=True)
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
        return t.render(ep_obj_list=ep_obj_rename_list, show=series_obj,
                        controller='home', action='previewRename')

    def doRename(self, showslug=None, eps=None):
        if not all([showslug, eps]):
            error_message = 'You must specify a show and at least one episode'
            return self._genericMessage('Error', error_message)

        series_obj = Series.find_by_identifier(SeriesIdentifier.from_slug(showslug))

        if series_obj is None:
            error_message = 'Error', 'Show not in show list'
            return self._genericMessage('Error', error_message)

        try:
            series_obj.validate_location  # @UnusedVariable
        except ShowDirectoryNotFoundException:
            return self._genericMessage('Error', "Can't rename episodes when the show dir is missing.")

        if eps is None:
            return self.redirect('/home/displayShow?showslug={series_obj.slug}'.format(series_obj=series_obj))

        main_db_con = db.DBConnection()
        for cur_ep in eps.split('|'):
            season_no, episode_no = cur_ep.lstrip('s').split('e')

            # this is probably the worst possible way to deal with double eps
            # but I've kinda painted myself into a corner here with this stupid database
            ep_result = main_db_con.select(
                'SELECT location '
                'FROM tv_episodes '
                'WHERE indexer = ? AND showid = ? AND season = ? AND episode = ? AND 5=5',
                [series_obj.indexer, series_obj.series_id, season_no, episode_no])
            if not ep_result:
                logger.log(u'Unable to find an episode for {episode}, skipping'.format
                           (episode=cur_ep), logger.WARNING)
                continue
            related_eps_result = main_db_con.select(
                'SELECT season, episode '
                'FROM tv_episodes '
                'WHERE location = ? AND episode != ?',
                [ep_result[0]['location'], episode_no]
            )

            root_ep_obj = series_obj.get_episode(season_no, episode_no)
            root_ep_obj.related_episodes = []

            for cur_related_ep in related_eps_result:
                related_ep_obj = series_obj.get_episode(cur_related_ep['season'], cur_related_ep['episode'])
                if related_ep_obj not in root_ep_obj.related_episodes:
                    root_ep_obj.related_episodes.append(related_ep_obj)

            root_ep_obj.rename()

        return self.redirect('/home/displayShow?showslug={series_obj.slug}'.format(series_obj=series_obj))

    def searchEpisode(self, showslug=None, season=None, episode=None):
        """Search for a single episode using a Backlog Search using providers that are backlog enabled."""
        # retrieve the episode object and fail if we can't get one0
        series_obj = Series.find_by_identifier(SeriesIdentifier.from_slug(showslug))
        ep_obj = series_obj.get_episode(season, episode)
        if not ep_obj:
            return json.dumps({
                'result': 'failure',
            })

        # make a queue item for it and put it on the queue
        ep_queue_item = BacklogQueueItem(ep_obj.series, [ep_obj])

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

    def getManualSearchStatus(self, showslug=None):
        """
        Returns the current ep_queue_item status for the current viewed show.
        Possible status: Downloaded, Snatched, etc...
        Returns {'show': 279530, 'episodes' : ['episode' : 6, 'season' : 1, 'searchstatus' : 'queued', 'status' : 'running', 'quality': '4013']
        :param indexername: Name of indexer. For ex. 'tvdb', 'tmdb', 'tvmaze'
        :param seriesid: Id of series as identified by the indexer
        :return:
        """
        series_obj = None
        if showslug:
            identifier = SeriesIdentifier.from_slug(showslug)
            series_obj = Series.find_by_identifier(identifier)
        episodes = collect_episodes_from_search_thread(series_obj)

        return json.dumps({
            'episodes': episodes,
        })

    def searchEpisodeSubtitles(self, showslug=None, season=None, episode=None, lang=None):
        # retrieve the episode object and fail if we can't get one
        series_obj = Series.find_by_identifier(SeriesIdentifier.from_slug(showslug))
        ep_obj = series_obj.get_episode(season, episode)
        if not ep_obj:
            return json.dumps({
                'result': 'failure',
            })

        try:
            if lang:
                logger.log('Manual re-downloading subtitles for {show} with language {lang}'.format
                           (show=ep_obj.series.name, lang=lang))
            new_subtitles = ep_obj.download_subtitles(lang=lang)
        except Exception as error:
            return json.dumps({
                'result': 'failure',
                'description': 'Error while downloading subtitles: {error}'.format(error=error)
            })

        if new_subtitles:
            new_languages = [subtitles.name_from_code(code) for code in new_subtitles]
            description = 'New subtitles downloaded: {languages}'.format(languages=', '.join(new_languages))
            result = 'success'
        else:
            new_languages = []
            description = 'No subtitles downloaded'
            result = 'failure'

        ui.notifications.message(ep_obj.series.name, description)
        return json.dumps({
            'result': result,
            'subtitles': ep_obj.subtitles,
            'languages': new_languages,
            'description': description
        })

    def manualSearchSubtitles(self, showslug=None, season=None, episode=None, release_id=None, picked_id=None):
        mode = 'downloading' if picked_id else 'searching'
        description = ''

        logger.log('Starting to manual {mode} subtitles'.format(mode=mode))
        try:
            if release_id:
                # Release ID is sent when using postpone
                release = app.RELEASES_IN_PP[int(release_id)]
                indexer_name = release['indexername']
                series_id = release['seriesid']
                season = release['season']
                episode = release['episode']
                filepath = release['release']
                identifier = SeriesIdentifier.from_id(indexer_name_to_id(indexer_name), series_id)
            else:
                filepath = None
                identifier = SeriesIdentifier.from_slug(showslug)

            series_obj = Series.find_by_identifier(identifier)
            ep_obj = series_obj.get_episode(season, episode)
            video_path = filepath or ep_obj.location
            release_name = ep_obj.release_name or os.path.basename(video_path)
        except IndexError:
            ui.notifications.message('Outdated list', 'Please refresh page and try again')
            logger.log('Outdated list. Please refresh page and try again', logger.WARNING)
            return json.dumps({
                'result': 'failure',
                'description': 'Outdated list. Please refresh page and try again'
            })
        except (ValueError, TypeError) as e:
            ui.notifications.message('Error', 'Please check logs')
            logger.log('Error while manual {mode} subtitles. Error: {error_msg}'.format
                       (mode=mode, error_msg=e), logger.ERROR)
            return json.dumps({
                'result': 'failure',
                'description': 'Error while manual {mode} subtitles. Error: {error_msg}'.format(mode=mode, error_msg=e)
            })

        if not os.path.isfile(video_path):
            ui.notifications.message(ep_obj.series.name, "Video file no longer exists. Can't search for subtitles")
            logger.log('Video file no longer exists: {video_file}'.format(video_file=video_path), logger.DEBUG)
            return json.dumps({
                'result': 'failure',
                'description': 'Video file no longer exists: {video_file}'.format(video_file=video_path)
            })

        if mode == 'searching':
            logger.log('Manual searching subtitles for: {0}'.format(release_name))
            found_subtitles = subtitles.list_subtitles(tv_episode=ep_obj, video_path=video_path)
            if found_subtitles:
                ui.notifications.message(ep_obj.series.name, 'Found {} subtitles'.format(len(found_subtitles)))
            else:
                ui.notifications.message(ep_obj.series.name, 'No subtitle found')
            if found_subtitles:
                result = 'success'
            else:
                result = 'failure'
                description = 'No subtitles found'
            subtitles_result = found_subtitles
        else:
            logger.log('Manual downloading subtitles for: {0}'.format(release_name))
            new_manual_subtitle = subtitles.save_subtitle(tv_episode=ep_obj, subtitle_id=picked_id,
                                                          video_path=video_path)
            if new_manual_subtitle:
                ui.notifications.message(ep_obj.series.name,
                                         'Subtitle downloaded: {0}'.format(','.join(new_manual_subtitle)))
            else:
                ui.notifications.message(ep_obj.series.name, 'Failed to download subtitle for {0}'.format(release_name))
            if new_manual_subtitle:
                result = 'success'
            else:
                result = 'failure'
                description = 'Failed to download subtitle for {0}'.format(release_name)

            subtitles_result = new_manual_subtitle

        return json.dumps({
            'result': result,
            'release': release_name,
            'subtitles': subtitles_result,
            'description': description
        })

    def setSceneNumbering(self, showslug=None, forSeason=None, forEpisode=None, forAbsolute=None, sceneSeason=None,
                          sceneEpisode=None, sceneAbsolute=None):

        # sanitize:
        forSeason = None if forSeason in ['null', ''] else forSeason
        forEpisode = None if forEpisode in ['null', ''] else forEpisode
        forAbsolute = None if forAbsolute in ['null', ''] else forAbsolute
        sceneSeason = None if sceneSeason in ['null', ''] else sceneSeason
        sceneEpisode = None if sceneEpisode in ['null', ''] else sceneEpisode
        sceneAbsolute = None if sceneAbsolute in ['null', ''] else sceneAbsolute

        identifier = SeriesIdentifier.from_slug(showslug)
        series_obj = Series.find_by_identifier(identifier)

        if not series_obj:
            return json.dumps({
                'success': False,
                'errorMessage': 'Could not find show {show_slug} to set scene numbering'.format(show_slug=series_obj.slug),
            })

        # Check if this is an anime, because we can't set the Scene numbering for anime shows
        if series_obj.is_anime and forAbsolute is None:
            return json.dumps({
                'success': False,
                'errorMessage': "You can't use the Scene numbering for anime shows. "
                                'Use the Scene Absolute field, to configure a diverging episode number.',
                'sceneSeason': None,
                'sceneAbsolute': None,
            })
        elif not series_obj.is_anime and (forSeason is None or forEpisode is None):
            return json.dumps({
                'success': False,
                'errorMessage': "You can't use the Scene Absolute for non-anime shows. "
                                'Use the scene field, to configure a diverging episode number.',
                'sceneSeason': None,
                'sceneAbsolute': None,
            })
        elif series_obj.is_anime:
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
        if series_obj.is_anime:
            ep_obj = series_obj.get_episode(absolute_number=forAbsolute)
        else:
            ep_obj = series_obj.get_episode(forSeason, forEpisode)

        if not ep_obj:
            result.update({
                'success': False,
                'errorMessage': ep_obj,
            })
        elif series_obj.is_anime:
            logger.log(u'Set absolute scene numbering for {show} from {absolute} to {scene_absolute}'.format
                       (show=series_obj.slug, absolute=forAbsolute, scene_absolute=sceneAbsolute), logger.DEBUG)

            forAbsolute = int(forAbsolute)
            if sceneAbsolute is not None:
                sceneAbsolute = int(sceneAbsolute)

            set_scene_numbering(series_obj, absolute_number=forAbsolute, scene_absolute=sceneAbsolute)
        else:
            logger.log(u'setEpisodeSceneNumbering for {show} from {season}x{episode} to {scene_season}x{scene_episode}'.format
                       (show=series_obj.indexerid, season=forSeason, episode=forEpisode,
                        scene_season=sceneSeason, scene_episode=sceneEpisode), logger.DEBUG)

            forSeason = int(forSeason)
            forEpisode = int(forEpisode)
            if sceneSeason is not None:
                sceneSeason = int(sceneSeason)
            if sceneEpisode is not None:
                sceneEpisode = int(sceneEpisode)

            set_scene_numbering(
                series_obj, season=forSeason, episode=forEpisode,
                scene_season=sceneSeason, scene_episode=sceneEpisode
            )

        if series_obj.is_anime:
            sn = get_scene_absolute_numbering(series_obj, forAbsolute)
            result['sceneAbsolute'] = sn
        else:
            sn = get_scene_numbering(series_obj, forEpisode, forSeason)
            (result['sceneSeason'], result['sceneEpisode']) = sn

        return json.dumps(result)

    @staticmethod
    def fetch_releasegroups(series_name):
        """Api route for retrieving anidb release groups for an anime show."""
        logger.log(u'ReleaseGroups: {show}'.format(show=series_name), logger.INFO)
        try:
            groups = get_release_groups_for_anime(series_name)
            logger.log(u'ReleaseGroups: {groups}'.format(groups=groups), logger.INFO)
        except AnidbAdbaConnectionException as error:
            logger.log(u'Unable to get ReleaseGroups: {error}'.format(error=error), logger.DEBUG)
        else:
            return json.dumps({
                'result': 'success',
                'groups': groups,
            })

        return json.dumps({
            'result': 'failure',
        })
