# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# Git: https://github.com/PyMedusa/SickRage.git
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.

# pylint: disable=abstract-method,too-many-lines

import datetime
import io
import os
import re
import traceback
import time

from concurrent.futures import ThreadPoolExecutor
from dateutil import tz
from mako.template import Template as MakoTemplate
from mako.lookup import TemplateLookup
from mako.exceptions import RichTraceback
from mako.runtime import UNDEFINED
from requests.compat import urljoin
from tornado.concurrent import run_on_executor
from tornado.escape import utf8
from tornado.gen import coroutine
from tornado.ioloop import IOLoop
from tornado.process import cpu_count
from tornado.routes import route
from tornado.web import RequestHandler, HTTPError, authenticated

import sickbeard
from sickbeard import (
    classes, db, helpers, logger,
    network_timezones, notifiers, ui,
)
from sickbeard.browser import foldersAtPath
from sickrage.helper.common import try_int
from sickrage.helper.encoding import ek
from sickrage.media.ShowBanner import ShowBanner
from sickrage.media.ShowFanArt import ShowFanArt
from sickrage.media.ShowNetworkLogo import ShowNetworkLogo
from sickrage.media.ShowPoster import ShowPoster
from sickrage.show.ComingEpisodes import ComingEpisodes
from sickrage.show.History import History as HistoryTool

from sickbeard.server.api.core import function_mapper

# Conditional imports
try:
    import json
except ImportError:
    import simplejson as json

mako_lookup = None
mako_cache = None
mako_path = None


def get_lookup():
    global mako_lookup  # pylint: disable=global-statement
    global mako_cache  # pylint: disable=global-statement
    global mako_path  # pylint: disable=global-statement

    if mako_path is None:
        mako_path = ek(os.path.join, sickbeard.PROG_DIR, "gui/" + sickbeard.GUI_NAME + "/views/")
    if mako_cache is None:
        mako_cache = ek(os.path.join, sickbeard.CACHE_DIR, 'mako')
    if mako_lookup is None:
        use_strict = sickbeard.BRANCH and sickbeard.BRANCH != 'master'
        mako_lookup = TemplateLookup(directories=[mako_path],
                                     module_directory=mako_cache,
                                     #  format_exceptions=True,
                                     strict_undefined=use_strict,
                                     filesystem_checks=True)
    return mako_lookup


class PageTemplate(MakoTemplate):
    def __init__(self, rh, filename):
        self.arguments = {}

        lookup = get_lookup()
        self.template = lookup.get_template(filename)

        self.arguments['srRoot'] = sickbeard.WEB_ROOT
        self.arguments['sbHttpPort'] = sickbeard.WEB_PORT
        self.arguments['sbHttpsPort'] = sickbeard.WEB_PORT
        self.arguments['sbHttpsEnabled'] = sickbeard.ENABLE_HTTPS
        self.arguments['sbHandleReverseProxy'] = sickbeard.HANDLE_REVERSE_PROXY
        self.arguments['sbThemeName'] = sickbeard.THEME_NAME
        self.arguments['sbDefaultPage'] = sickbeard.DEFAULT_PAGE
        self.arguments['loggedIn'] = rh.get_current_user()
        self.arguments['sbStartTime'] = rh.startTime

        if rh.request.headers['Host'][0] == '[':
            self.arguments['sbHost'] = re.match(r"^\[.*\]", rh.request.headers['Host'], re.X | re.M | re.S).group(0)
        else:
            self.arguments['sbHost'] = re.match(r"^[^:]+", rh.request.headers['Host'], re.X | re.M | re.S).group(0)

        if "X-Forwarded-Host" in rh.request.headers:
            self.arguments['sbHost'] = rh.request.headers['X-Forwarded-Host']
        if "X-Forwarded-Port" in rh.request.headers:
            sbHttpPort = rh.request.headers['X-Forwarded-Port']
            self.arguments['sbHttpsPort'] = sbHttpPort
        if "X-Forwarded-Proto" in rh.request.headers:
            self.arguments['sbHttpsEnabled'] = True if rh.request.headers['X-Forwarded-Proto'] == 'https' else False

        self.arguments['numErrors'] = len(classes.ErrorViewer.errors)
        self.arguments['numWarnings'] = len(classes.WarningViewer.errors)
        self.arguments['sbPID'] = str(sickbeard.PID)

        self.arguments['title'] = "FixME"
        self.arguments['header'] = "FixME"
        self.arguments['topmenu'] = "FixME"
        self.arguments['submenu'] = []
        self.arguments['controller'] = "FixME"
        self.arguments['action'] = "FixME"
        self.arguments['show'] = UNDEFINED
        self.arguments['newsBadge'] = ''
        self.arguments['toolsBadge'] = ''
        self.arguments['toolsBadgeClass'] = ''

        error_count = len(classes.ErrorViewer.errors)
        warning_count = len(classes.WarningViewer.errors)

        if sickbeard.NEWS_UNREAD:
            self.arguments['newsBadge'] = ' <span class="badge">' + str(sickbeard.NEWS_UNREAD) + '</span>'

        numCombined = error_count + warning_count + sickbeard.NEWS_UNREAD
        if numCombined:
            if error_count:
                self.arguments['toolsBadgeClass'] = ' btn-danger'
            elif warning_count:
                self.arguments['toolsBadgeClass'] = ' btn-warning'
            self.arguments['toolsBadge'] = ' <span class="badge' + self.arguments['toolsBadgeClass'] + '">' + str(numCombined) + '</span>'

    def render(self, *args, **kwargs):
        for key in self.arguments:
            if key not in kwargs:
                kwargs[key] = self.arguments[key]

        kwargs['makoStartTime'] = time.time()
        try:
            return self.template.render_unicode(*args, **kwargs)
        except Exception:
            kwargs['title'] = '500'
            kwargs['header'] = 'Mako Error'
            kwargs['backtrace'] = RichTraceback()
            return get_lookup().get_template('500.mako').render_unicode(*args, **kwargs)


class BaseHandler(RequestHandler):
    startTime = 0.

    def __init__(self, *args, **kwargs):
        self.startTime = time.time()

        super(BaseHandler, self).__init__(*args, **kwargs)

    # def set_default_headers(self):
    #     self.set_header(
    #         'Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0'
    #     )

    def write_error(self, status_code, **kwargs):
        # handle 404 http errors
        if status_code == 404:
            url = self.request.uri
            if sickbeard.WEB_ROOT and self.request.uri.startswith(sickbeard.WEB_ROOT):
                url = url[len(sickbeard.WEB_ROOT) + 1:]

            if url[:3] != 'api':
                t = PageTemplate(rh=self, filename="404.mako")
                return self.finish(t.render(title='404', header='Oops'))
            else:
                self.finish('Wrong API key used')

        elif self.settings.get("debug") and "exc_info" in kwargs:
            exc_info = kwargs["exc_info"]
            trace_info = ''.join(["%s<br>" % line for line in traceback.format_exception(*exc_info)])
            request_info = ''.join(["<strong>%s</strong>: %s<br>" % (k, self.request.__dict__[k]) for k in
                                    self.request.__dict__.keys()])
            error = exc_info[1]

            self.set_header('Content-Type', 'text/html')
            self.finish(
                """
                <html>
                    <title>%s</title>
                    <body>
                        <h2>Error</h2>
                        <p>%s</p>
                        <h2>Traceback</h2>
                        <p>%s</p>
                        <h2>Request Info</h2>
                        <p>%s</p>
                        <button onclick="window.location='%s/errorlogs/';">View Log(Errors)</button>
                     </body>
                </html>
                """ % (error, error, trace_info, request_info, sickbeard.WEB_ROOT)
            )

    def redirect(self, url, permanent=False, status=None):
        """Sends a redirect to the given (optionally relative) URL.

        ----->>>>> NOTE: Removed self.finish <<<<<-----

        If the ``status`` argument is specified, that value is used as the
        HTTP status code; otherwise either 301 (permanent) or 302
        (temporary) is chosen based on the ``permanent`` argument.
        The default is 302 (temporary).
        """
        if not url.startswith(sickbeard.WEB_ROOT):
            url = sickbeard.WEB_ROOT + url

        if self._headers_written:
            raise Exception("Cannot redirect after headers have been written")
        if status is None:
            status = 301 if permanent else 302
        else:
            assert isinstance(status, int) and 300 <= status <= 399
        self.set_status(status)
        self.set_header("Location", urljoin(utf8(self.request.uri),
                                                     utf8(url)))

    def get_current_user(self):
        if not isinstance(self, UI) and sickbeard.WEB_USERNAME and sickbeard.WEB_PASSWORD:
            return self.get_secure_cookie('sickrage_user')
        else:
            return True


class WebHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        super(WebHandler, self).__init__(*args, **kwargs)
        self.io_loop = IOLoop.current()

    executor = ThreadPoolExecutor(cpu_count())

    @authenticated
    @coroutine
    def get(self, route, *args, **kwargs):
        try:
            # route -> method obj
            route = route.strip('/').replace('.', '_') or 'index'
            method = getattr(self, route)

            results = yield self.async_call(method)
            self.finish(results)

        except Exception:
            logger.log(u'Failed doing webui request "%s": %s' % (route, traceback.format_exc()), logger.DEBUG)
            raise HTTPError(404)

    @run_on_executor
    def async_call(self, function):
        try:
            kwargs = self.request.arguments
            for arg, value in kwargs.iteritems():
                if len(value) == 1:
                    kwargs[arg] = value[0]

            result = function(**kwargs)
            return result
        except Exception:
            logger.log(u'Failed doing webui callback: %s' % (traceback.format_exc()), logger.ERROR)
            raise

    # post uses get method
    post = get


class LoginHandler(BaseHandler):
    def get(self, *args, **kwargs):

        if self.get_current_user():
            self.redirect('/' + sickbeard.DEFAULT_PAGE + '/')
        else:
            t = PageTemplate(rh=self, filename="login.mako")
            self.finish(t.render(title="Login", header="Login", topmenu="login"))

    def post(self, *args, **kwargs):

        api_key = None

        username = sickbeard.WEB_USERNAME
        password = sickbeard.WEB_PASSWORD

        if (self.get_argument('username') == username or not username) \
                and (self.get_argument('password') == password or not password):
            api_key = sickbeard.API_KEY

        if sickbeard.NOTIFY_ON_LOGIN and not helpers.is_ip_private(self.request.remote_ip):
            notifiers.notify_login(self.request.remote_ip)

        if api_key:
            remember_me = int(self.get_argument('remember_me', default=0) or 0)
            self.set_secure_cookie('sickrage_user', api_key, expires_days=30 if remember_me > 0 else None)
            logger.log(u'User logged into the Medusa web interface', logger.INFO)
        else:
            logger.log(u'User attempted a failed login to the Medusa web interface from IP: ' + self.request.remote_ip, logger.WARNING)

        self.redirect('/' + sickbeard.DEFAULT_PAGE + '/')


class LogoutHandler(BaseHandler):
    def get(self, *args, **kwargs):
        self.clear_cookie("sickrage_user")
        self.redirect('/login/')


class KeyHandler(RequestHandler):
    def __init__(self, *args, **kwargs):
        super(KeyHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        api_key = None

        try:
            username = sickbeard.WEB_USERNAME
            password = sickbeard.WEB_PASSWORD

            if (self.get_argument('u', None) == username or not username) and \
                    (self.get_argument('p', None) == password or not password):
                api_key = sickbeard.API_KEY

            self.finish({'success': api_key is not None, 'api_key': api_key})
        except Exception:
            logger.log(u'Failed doing key request: %s' % (traceback.format_exc()), logger.ERROR)
            self.finish({'success': False, 'error': 'Failed returning results'})


@route('(.*)(/?)')
class WebRoot(WebHandler):
    def __init__(self, *args, **kwargs):
        super(WebRoot, self).__init__(*args, **kwargs)

    def index(self):
        return self.redirect('/' + sickbeard.DEFAULT_PAGE + '/')

    def robots_txt(self):
        """ Keep web crawlers out """
        self.set_header('Content-Type', 'text/plain')
        return "User-agent: *\nDisallow: /"

    def apibuilder(self):
        def titler(x):
            return (helpers.remove_article(x), x)[not x or sickbeard.SORT_ARTICLE]

        main_db_con = db.DBConnection(row_type='dict')
        shows = sorted(sickbeard.showList, lambda x, y: cmp(titler(x.name), titler(y.name)))
        episodes = {}

        results = main_db_con.select(
            'SELECT episode, season, showid '
            'FROM tv_episodes '
            'ORDER BY season ASC, episode ASC'
        )

        for result in results:
            if result['showid'] not in episodes:
                episodes[result['showid']] = {}

            if result['season'] not in episodes[result['showid']]:
                episodes[result['showid']][result['season']] = []

            episodes[result['showid']][result['season']].append(result['episode'])

        if len(sickbeard.API_KEY) == 32:
            apikey = sickbeard.API_KEY
        else:
            apikey = 'API Key not generated'

        t = PageTemplate(rh=self, filename='apiBuilder.mako')
        return t.render(title='API Builder', header='API Builder', shows=shows, episodes=episodes, apikey=apikey,
                        commands=function_mapper)

    def showPoster(self, show=None, which=None):
        media = None
        media_format = ('normal', 'thumb')[which in ('banner_thumb', 'poster_thumb', 'small')]

        if which[0:6] == 'banner':
            media = ShowBanner(show, media_format)
        elif which[0:6] == 'fanart':
            media = ShowFanArt(show, media_format)
        elif which[0:6] == 'poster':
            media = ShowPoster(show, media_format)
        elif which[0:7] == 'network':
            media = ShowNetworkLogo(show, media_format)

        if media is not None:
            self.set_header('Content-Type', media.get_media_type())

            return media.get_media()

        return None

    def setHomeLayout(self, layout):

        if layout not in ('poster', 'small', 'banner', 'simple', 'coverflow'):
            layout = 'poster'

        sickbeard.HOME_LAYOUT = layout
        # Don't redirect to default page so user can see new layout
        return self.redirect("/home/")

    @staticmethod
    def setPosterSortBy(sort):

        if sort not in ('name', 'date', 'network', 'progress'):
            sort = 'name'

        sickbeard.POSTER_SORTBY = sort
        sickbeard.save_config()

    @staticmethod
    def setPosterSortDir(direction):

        sickbeard.POSTER_SORTDIR = int(direction)
        sickbeard.save_config()

    def setHistoryLayout(self, layout):

        if layout not in ('compact', 'detailed'):
            layout = 'detailed'

        sickbeard.HISTORY_LAYOUT = layout

        return self.redirect("/history/")

    def toggleDisplayShowSpecials(self, show):

        sickbeard.DISPLAY_SHOW_SPECIALS = not sickbeard.DISPLAY_SHOW_SPECIALS

        return self.redirect("/home/displayShow?show=" + show)

    def setScheduleLayout(self, layout):
        if layout not in ('poster', 'banner', 'list', 'calendar'):
            layout = 'banner'

        if layout == 'calendar':
            sickbeard.COMING_EPS_SORT = 'date'

        sickbeard.COMING_EPS_LAYOUT = layout

        return self.redirect("/schedule/")

    def toggleScheduleDisplayPaused(self):

        sickbeard.COMING_EPS_DISPLAY_PAUSED = not sickbeard.COMING_EPS_DISPLAY_PAUSED

        return self.redirect("/schedule/")

    def setScheduleSort(self, sort):
        if sort not in ('date', 'network', 'show'):
            sort = 'date'

        if sickbeard.COMING_EPS_LAYOUT == 'calendar':
            sort \
                = 'date'

        sickbeard.COMING_EPS_SORT = sort

        return self.redirect("/schedule/")

    def schedule(self, layout=None):
        next_week = datetime.date.today() + datetime.timedelta(days=7)
        next_week1 = datetime.datetime.combine(next_week, datetime.time(tzinfo=network_timezones.sb_timezone))
        results = ComingEpisodes.get_coming_episodes(ComingEpisodes.categories, sickbeard.COMING_EPS_SORT, False)
        today = datetime.datetime.now().replace(tzinfo=network_timezones.sb_timezone)

        submenu = [
            {
                'title': 'Sort by:',
                'path': {
                    'Date': 'setScheduleSort/?sort=date',
                    'Show': 'setScheduleSort/?sort=show',
                    'Network': 'setScheduleSort/?sort=network',
                }
            },
            {
                'title': 'Layout:',
                'path': {
                    'Banner': 'setScheduleLayout/?layout=banner',
                    'Poster': 'setScheduleLayout/?layout=poster',
                    'List': 'setScheduleLayout/?layout=list',
                    'Calendar': 'setScheduleLayout/?layout=calendar',
                }
            },
            {
                'title': 'View Paused:',
                'path': {
                    'Hide': 'toggleScheduleDisplayPaused'
                } if sickbeard.COMING_EPS_DISPLAY_PAUSED else {
                    'Show': 'toggleScheduleDisplayPaused'
                }
            },
        ]

        # Allow local overriding of layout parameter
        if layout and layout in ('poster', 'banner', 'list', 'calendar'):
            layout = layout
        else:
            layout = sickbeard.COMING_EPS_LAYOUT

        t = PageTemplate(rh=self, filename='schedule.mako')
        return t.render(submenu=submenu, next_week=next_week1, today=today, results=results, layout=layout,
                        title='Schedule', header='Schedule', topmenu='schedule',
                        controller="schedule", action="index")


class CalendarHandler(BaseHandler):
    def get(self):
        if sickbeard.CALENDAR_UNPROTECTED:
            self.write(self.calendar())
        else:
            self.calendar_auth()

    @authenticated
    def calendar_auth(self):
        self.write(self.calendar())

    # Raw iCalendar implementation by Pedro Jose Pereira Vieito (@pvieito).
    #
    # iCalendar (iCal) - Standard RFC 5545 <http://tools.ietf.org/html/rfc5546>
    # Works with iCloud, Google Calendar and Outlook.
    def calendar(self):
        """ Provides a subscribeable URL for iCal subscriptions
        """

        logger.log(u"Receiving iCal request from %s" % self.request.remote_ip)

        # Create a iCal string
        ical = 'BEGIN:VCALENDAR\r\n'
        ical += 'VERSION:2.0\r\n'
        ical += 'X-WR-CALNAME:Medusa\r\n'
        ical += 'X-WR-CALDESC:Medusa\r\n'
        ical += 'PRODID://Sick-Beard Upcoming Episodes//\r\n'

        future_weeks = try_int(self.get_argument('future', 52), 52)
        past_weeks = try_int(self.get_argument('past', 52), 52)

        # Limit dates
        past_date = (datetime.date.today() + datetime.timedelta(weeks=-past_weeks)).toordinal()
        future_date = (datetime.date.today() + datetime.timedelta(weeks=future_weeks)).toordinal()

        # Get all the shows that are not paused and are currently on air (from kjoconnor Fork)
        main_db_con = db.DBConnection()
        calendar_shows = main_db_con.select(
            "SELECT show_name, indexer_id, network, airs, runtime FROM tv_shows WHERE ( status = 'Continuing' OR status = 'Returning Series' ) AND paused != '1'")
        for show in calendar_shows:
            # Get all episodes of this show airing between today and next month
            episode_list = main_db_con.select(
                "SELECT indexerid, name, season, episode, description, airdate FROM tv_episodes WHERE airdate >= ? AND airdate < ? AND showid = ?",
                (past_date, future_date, int(show["indexer_id"])))

            utc = tz.gettz('GMT')

            for episode in episode_list:

                air_date_time = network_timezones.parse_date_time(episode['airdate'], show["airs"],
                                                                  show['network']).astimezone(utc)
                air_date_time_end = air_date_time + datetime.timedelta(
                    minutes=try_int(show["runtime"], 60))

                # Create event for episode
                ical += 'BEGIN:VEVENT\r\n'
                ical += 'DTSTART:' + air_date_time.strftime("%Y%m%d") + 'T' + air_date_time.strftime(
                    "%H%M%S") + 'Z\r\n'
                ical += 'DTEND:' + air_date_time_end.strftime(
                    "%Y%m%d") + 'T' + air_date_time_end.strftime(
                        "%H%M%S") + 'Z\r\n'
                if sickbeard.CALENDAR_ICONS:
                    ical += 'X-GOOGLE-CALENDAR-CONTENT-ICON:https://lh3.googleusercontent.com/-Vp_3ZosvTgg/VjiFu5BzQqI/AAAAAAAA_TY/3ZL_1bC0Pgw/s16-Ic42/medusa.png\r\n'
                    ical += 'X-GOOGLE-CALENDAR-CONTENT-DISPLAY:CHIP\r\n'
                ical += u'SUMMARY: {0} - {1}x{2} - {3}\r\n'.format(
                    show['show_name'], episode['season'], episode['episode'], episode['name']
                )
                ical += 'UID:Medusa-' + str(datetime.date.today().isoformat()) + '-' + \
                    show['show_name'].replace(" ", "-") + '-E' + str(episode['episode']) + \
                    'S' + str(episode['season']) + '\r\n'
                if episode['description']:
                    ical += u'DESCRIPTION: {0} on {1} \\n\\n {2}\r\n'.format(
                        (show['airs'] or '(Unknown airs)'),
                        (show['network'] or 'Unknown network'),
                        episode['description'].splitlines()[0])
                else:
                    ical += 'DESCRIPTION:' + (show['airs'] or '(Unknown airs)') + ' on ' + (
                        show['network'] or 'Unknown network') + '\r\n'

                ical += 'END:VEVENT\r\n'

        # Ending the iCal
        ical += 'END:VCALENDAR'

        return ical


@route('/ui(/?.*)')
class UI(WebRoot):
    def __init__(self, *args, **kwargs):
        super(UI, self).__init__(*args, **kwargs)

    @staticmethod
    def add_message():
        ui.notifications.message('Test 1', 'This is test number 1')
        ui.notifications.error('Test 2', 'This is test number 2')

        return "ok"

    def get_messages(self):
        self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')
        self.set_header("Content-Type", "application/json")
        messages = {}
        cur_notification_num = 1
        for cur_notification in ui.notifications.get_notifications(self.request.remote_ip):
            messages[u'notification-{num}'.format(num=cur_notification_num)] = {
                u'title': u'{title}'.format(title=cur_notification.title),
                u'message': u'{message}'.format(message=cur_notification.message),
                u'type': u'{type}'.format(type=cur_notification.type),
            }
            cur_notification_num += 1

        return json.dumps(messages)


@route('/browser(/?.*)')
class WebFileBrowser(WebRoot):
    def __init__(self, *args, **kwargs):
        super(WebFileBrowser, self).__init__(*args, **kwargs)

    def index(self, path='', includeFiles=False, *args, **kwargs):
        self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')
        self.set_header("Content-Type", "application/json")
        return json.dumps(foldersAtPath(path, True, bool(int(includeFiles))))

    def complete(self, term, includeFiles=0, *args, **kwargs):
        self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')
        self.set_header("Content-Type", "application/json")
        paths = [entry['path'] for entry in foldersAtPath(ek(os.path.dirname, term), includeFiles=bool(int(includeFiles)))
                 if 'path' in entry]

        return json.dumps(paths)


@route('/history(/?.*)')
class History(WebRoot):
    def __init__(self, *args, **kwargs):
        super(History, self).__init__(*args, **kwargs)

        self.history = HistoryTool()

    def index(self, limit=None):

        if limit is None:
            if sickbeard.HISTORY_LIMIT:
                limit = int(sickbeard.HISTORY_LIMIT)
            else:
                limit = 100
        else:
            limit = try_int(limit, 100)

        sickbeard.HISTORY_LIMIT = limit

        sickbeard.save_config()

        history = self.history.get(limit)

        t = PageTemplate(rh=self, filename="history.mako")
        submenu = [
            {'title': 'Clear History', 'path': 'history/clearHistory', 'icon': 'ui-icon ui-icon-trash', 'class': 'clearhistory', 'confirm': True},
            {'title': 'Trim History', 'path': 'history/trimHistory', 'icon': 'menu-icon-cut', 'class': 'trimhistory', 'confirm': True},
        ]

        return t.render(historyResults=history.detailed, compactResults=history.compact, limit=limit,
                        submenu=submenu, title='History', header='History',
                        topmenu="history", controller="history", action="index")

    def clearHistory(self):
        self.history.clear()

        ui.notifications.message('History cleared')

        return self.redirect("/history/")

    def trimHistory(self):
        self.history.trim()

        ui.notifications.message('Removed history entries older than 30 days')

        return self.redirect("/history/")


@route('/errorlogs(/?.*)')
class ErrorLogs(WebRoot):
    def __init__(self, *args, **kwargs):
        super(ErrorLogs, self).__init__(*args, **kwargs)

    def ErrorLogsMenu(self, level):
        menu = [
            {'title': 'Clear Errors', 'path': 'errorlogs/clearerrors/', 'requires': self.haveErrors() and level == logger.ERROR, 'icon': 'ui-icon ui-icon-trash'},
            {'title': 'Clear Warnings', 'path': 'errorlogs/clearerrors/?level=' + str(logger.WARNING), 'requires': self.haveWarnings() and level == logger.WARNING, 'icon': 'ui-icon ui-icon-trash'},
            {'title': 'Submit Errors', 'path': 'errorlogs/submit_errors/', 'requires': self.haveErrors() and level == logger.ERROR, 'class': 'submiterrors', 'confirm': True, 'icon': 'ui-icon ui-icon-arrowreturnthick-1-n'},
        ]

        return menu

    def index(self, level=logger.ERROR):
        try:
            level = int(level)
        except Exception:
            level = logger.ERROR

        t = PageTemplate(rh=self, filename="errorlogs.mako")
        return t.render(header="Logs &amp; Errors", title="Logs &amp; Errors",
                        topmenu="system", submenu=self.ErrorLogsMenu(level),
                        logLevel=level, controller="errorlogs", action="index")

    @staticmethod
    def haveErrors():
        if len(classes.ErrorViewer.errors) > 0:
            return True

    @staticmethod
    def haveWarnings():
        if len(classes.WarningViewer.errors) > 0:
            return True

    def clearerrors(self, level=logger.ERROR):
        if int(level) == logger.WARNING:
            classes.WarningViewer.clear()
        else:
            classes.ErrorViewer.clear()

        return self.redirect("/errorlogs/viewlog/")

    def viewlog(self, minLevel=logger.INFO, logFilter="<NONE>", logSearch=None, maxLines=1000):

        def Get_Data(Levelmin, data_in, lines_in, regex, Filter, Search, mlines):

            lastLine = False
            numLines = lines_in
            numToShow = min(maxLines, numLines + len(data_in))

            finalData = []

            for x in reversed(data_in):
                match = re.match(regex, x)

                if match:
                    level = match.group(7)
                    logName = match.group(8)
                    if level not in logger.LOGGING_LEVELS:
                        lastLine = False
                        continue

                    if logSearch and logSearch.lower() in x.lower():
                        lastLine = True
                        finalData.append(x)
                        numLines += 1
                    elif not logSearch and logger.LOGGING_LEVELS[level] >= minLevel and (logFilter == '<NONE>' or logName.startswith(logFilter)):
                        lastLine = True
                        finalData.append(x)
                        numLines += 1
                    else:
                        lastLine = False
                        continue

                elif lastLine:
                    finalData.append("AA" + x)
                    numLines += 1

                if numLines >= numToShow:
                    return finalData

            return finalData

        t = PageTemplate(rh=self, filename="viewlogs.mako")

        minLevel = int(minLevel)

        logNameFilters = {
            '<NONE>': u'&lt;No Filter&gt;',
            'DAILYSEARCHER': u'Daily Searcher',
            'BACKLOG': u'Backlog',
            'SHOWUPDATER': u'Show Updater',
            'CHECKVERSION': u'Check Version',
            'SHOWQUEUE': u'Show Queue',
            'SEARCHQUEUE': u'Search Queue (All)',
            'SEARCHQUEUE-DAILY-SEARCH': u'Search Queue (Daily Searcher)',
            'SEARCHQUEUE-BACKLOG': u'Search Queue (Backlog)',
            'SEARCHQUEUE-MANUAL': u'Search Queue (Manual)',
            'SEARCHQUEUE-FORCED': u'Search Queue (Forced)',
            'SEARCHQUEUE-RETRY': u'Search Queue (Retry/Failed)',
            'SEARCHQUEUE-RSS': u'Search Queue (RSS)',
            'SHOWQUEUE-FORCE-UPDATE': u'Search Queue (Forced Update)',
            'SHOWQUEUE-UPDATE': u'Search Queue (Update)',
            'SHOWQUEUE-REFRESH': u'Search Queue (Refresh)',
            'SHOWQUEUE-FORCE-REFRESH': u'Search Queue (Forced Refresh)',
            'FINDPROPERS': u'Find Propers',
            'POSTPROCESSER': u'Postprocesser',
            'FINDSUBTITLES': u'Find Subtitles',
            'TRAKTCHECKER': u'Trakt Checker',
            'EVENT': u'Event',
            'ERROR': u'Error',
            'TORNADO': u'Tornado',
            'Thread': u'Thread',
            'MAIN': u'Main',
        }

        if logFilter not in logNameFilters:
            logFilter = '<NONE>'

        regex = r"^(\d\d\d\d)\-(\d\d)\-(\d\d)\s*(\d\d)\:(\d\d):(\d\d)\s*([A-Z]+)\s*(.+?)\s*\:\:\s*(.*)$"

        data = []

        if ek(os.path.isfile, logger.log_file):
            with io.open(logger.log_file, 'r', encoding='utf-8') as f:
                data = Get_Data(minLevel, f.readlines(), 0, regex, logFilter, logSearch, maxLines)

        for i in range(1, int(sickbeard.LOG_NR)):
            if ek(os.path.isfile, logger.log_file + "." + str(i)) and (len(data) <= maxLines):
                with io.open(logger.log_file + "." + str(i), 'r', encoding='utf-8') as f:
                    data += Get_Data(minLevel, f.readlines(), len(data), regex, logFilter, logSearch, maxLines)

        return t.render(
            header="Log File", title="Logs", topmenu="system",
            logLines=u"".join(data), minLevel=minLevel, logNameFilters=logNameFilters,
            logFilter=logFilter, logSearch=logSearch,
            controller="errorlogs", action="viewlogs")

    def submit_errors(self):
        submitter_result, issue_id = logger.submit_errors()
        logger.log(submitter_result, (logger.INFO, logger.WARNING)[issue_id is None])
        submitter_notification = ui.notifications.error if issue_id is None else ui.notifications.message
        submitter_notification(submitter_result)

        return self.redirect("/errorlogs/")
