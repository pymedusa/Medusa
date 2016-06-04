# coding=utf-8

from __future__ import unicode_literals

import json
import datetime
import os
import re
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from mako.exceptions import RichTraceback
from mako.lookup import TemplateLookup
from mako.runtime import UNDEFINED
from mako.template import Template as MakoTemplate
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
    classes, db, helpers, logger, network_timezones, ui
)
from sickbeard.server.api.core import function_mapper
from sickrage.helper.encoding import ek
from sickrage.media.ShowBanner import ShowBanner
from sickrage.media.ShowFanArt import ShowFanArt
from sickrage.media.ShowNetworkLogo import ShowNetworkLogo
from sickrage.media.ShowPoster import ShowPoster
from sickrage.show.ComingEpisodes import ComingEpisodes

mako_lookup = None
mako_cache = None
mako_path = None


def get_lookup():
    global mako_lookup  # pylint: disable=global-statement
    global mako_cache  # pylint: disable=global-statement
    global mako_path  # pylint: disable=global-statement

    if mako_path is None:
        mako_path = ek(os.path.join, sickbeard.PROG_DIR, 'gui/{gui_name}/views/'.format(gui_name=sickbeard.GUI_NAME))
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
    """
    Mako page template
    """
    def __init__(self, rh, filename):
        lookup = get_lookup()
        self.template = lookup.get_template(filename)

        self.arguments = {
            'srRoot': sickbeard.WEB_ROOT,
            'sbHttpPort': sickbeard.WEB_PORT,
            'sbHttpsPort': sickbeard.WEB_PORT,
            'sbHttpsEnabled': sickbeard.ENABLE_HTTPS,
            'sbHandleReverseProxy': sickbeard.HANDLE_REVERSE_PROXY,
            'sbThemeName': sickbeard.THEME_NAME,
            'sbDefaultPage': sickbeard.DEFAULT_PAGE,
            'loggedIn': rh.get_current_user(),
            'sbStartTime': rh.startTime,
            'numErrors': len(classes.ErrorViewer.errors),
            'numWarnings': len(classes.WarningViewer.errors),
            'sbPID': str(sickbeard.PID),
            'title': 'FixME',
            'header': 'FixME',
            'topmenu': 'FixME',
            'submenu': [],
            'controller': 'FixME',
            'action': 'FixME',
            'show': UNDEFINED,
            'newsBadge': '',
            'toolsBadge': '',
            'toolsBadgeClass': '',
        }

        if rh.request.headers['Host'][0] == '[':
            self.arguments['sbHost'] = re.match(r'^\[.*\]', rh.request.headers['Host'], re.X | re.M | re.S).group(0)
        else:
            self.arguments['sbHost'] = re.match(r'^[^:]+', rh.request.headers['Host'], re.X | re.M | re.S).group(0)
        if 'X-Forwarded-Host' in rh.request.headers:
            self.arguments['sbHost'] = rh.request.headers['X-Forwarded-Host']
        if 'X-Forwarded-Port' in rh.request.headers:
            self.arguments['sbHttpsPort'] = rh.request.headers['X-Forwarded-Port']
        if 'X-Forwarded-Proto' in rh.request.headers:
            self.arguments['sbHttpsEnabled'] = True if rh.request.headers['X-Forwarded-Proto'] == 'https' else False

        error_count = len(classes.ErrorViewer.errors)
        warning_count = len(classes.WarningViewer.errors)

        if sickbeard.NEWS_UNREAD:
            self.arguments['newsBadge'] = ' <span class="badge">{news}</span>'.format(news=sickbeard.NEWS_UNREAD)

        num_combined = error_count + warning_count + sickbeard.NEWS_UNREAD
        if num_combined:
            if error_count:
                self.arguments['toolsBadgeClass'] = ' btn-danger'
            elif warning_count:
                self.arguments['toolsBadgeClass'] = ' btn-warning'
            self.arguments['toolsBadge'] = ' <span class="badge{type}">{number}</span>'.format(
                type=self.arguments['toolsBadgeClass'], number=num_combined)

    def render(self, *args, **kwargs):
        """
        Render the Page template
        """
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
            for (filename, lineno, function, line) in kwargs['backtrace'].traceback:
                logger.log(u'File {name}, line {line}, in {func}'.format
                           (name=filename, line=lineno, func=function), logger.DEBUG)
            logger.log(u'{name}: {error}'.format
                       (name=kwargs['backtrace'].error.__class__.__name__, error=kwargs['backtrace'].error))
            return get_lookup().get_template('500.mako').render_unicode(*args, **kwargs)


class BaseHandler(RequestHandler):
    """
    Base Handler for the server
    """
    startTime = 0.

    def __init__(self, *args, **kwargs):
        self.startTime = time.time()

        super(BaseHandler, self).__init__(*args, **kwargs)

    # def set_default_headers(self):
    #     self.set_header(
    #         'Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0'
    #     )

    def write_error(self, status_code, **kwargs):
        """
        Base error Handler for 404's
        """
        # handle 404 http errors
        if status_code == 404:
            url = self.request.uri
            if sickbeard.WEB_ROOT and self.request.uri.startswith(sickbeard.WEB_ROOT):
                url = url[len(sickbeard.WEB_ROOT) + 1:]

            if url[:3] != 'api':
                t = PageTemplate(rh=self, filename='404.mako')
                return self.finish(t.render(title='404', header='Oops'))
            else:
                self.finish('Wrong API key used')

        elif self.settings.get('debug') and 'exc_info' in kwargs:
            exc_info = kwargs['exc_info']
            trace_info = ''.join(['{line}<br>'.format(line=line) for line in traceback.format_exception(*exc_info)])
            request_info = ''.join(['<strong>{key}</strong>: {value}<br>'.format(key=k, value=v)
                                    for k, v in self.request.__dict__.items()])
            error = exc_info[1]

            self.set_header('Content-Type', 'text/html')
            self.finish(
                """
                <html>
                    <title>{title}</title>
                    <body>
                        <h2>Error</h2>
                        <p>{error}</p>
                        <h2>Traceback</h2>
                        <p>{trace}</p>
                        <h2>Request Info</h2>
                        <p>{request}</p>
                        <button onclick="window.location='{root}/errorlogs/';">View Log(Errors)</button>
                     </body>
                </html>
                """.format(title=error, error=error, trace=trace_info, request=request_info, root=sickbeard.WEB_ROOT)
            )

    def redirect(self, url, permanent=False, status=None):
        """
        Sends a redirect to the given (optionally relative) URL.

        ----->>>>> NOTE: Removed self.finish <<<<<-----

        If the ``status`` argument is specified, that value is used as the
        HTTP status code; otherwise either 301 (permanent) or 302
        (temporary) is chosen based on the ``permanent`` argument.
        The default is 302 (temporary).
        """
        if not url.startswith(sickbeard.WEB_ROOT):
            url = sickbeard.WEB_ROOT + url

        if self._headers_written:
            raise Exception('Cannot redirect after headers have been written')
        if status is None:
            status = 301 if permanent else 302
        else:
            assert isinstance(status, int)
            assert 300 <= status <= 399
        self.set_status(status)
        self.set_header('Location', urljoin(utf8(self.request.uri),
                                            utf8(url)))

    def get_current_user(self):
        if not isinstance(self, UI) and sickbeard.WEB_USERNAME and sickbeard.WEB_PASSWORD:
            return self.get_secure_cookie('sickrage_user')
        else:
            return True


class WebHandler(BaseHandler):
    """
    Base Handler for the web server
    """
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
            logger.log(u'Failed doing web ui request {route!r}: {error}'.format
                       (route=route, error=traceback.format_exc()), logger.DEBUG)
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
            logger.log(u'Failed doing web ui callback: {error}'.format(error=traceback.format_exc()), logger.ERROR)
            raise

    # post uses get method
    post = get


@route('(.*)(/?)')
class WebRoot(WebHandler):
    """
    Base Handler for the web server
    """
    def __init__(self, *args, **kwargs):
        super(WebRoot, self).__init__(*args, **kwargs)

    def index(self):
        return self.redirect('/{page}/'.format(page=sickbeard.DEFAULT_PAGE))

    def robots_txt(self):
        """ Keep web crawlers out """
        self.set_header('Content-Type', 'text/plain')
        return 'User-agent: *\nDisallow: /'

    def apibuilder(self):
        def titler(x):
            return (helpers.remove_article(x), x)[not x or sickbeard.SORT_ARTICLE]

        main_db_con = db.DBConnection(row_type='dict')
        shows = sorted(sickbeard.showList, lambda x, y: cmp(titler(x.name), titler(y.name)))
        episodes = {}

        results = main_db_con.select(
            b'SELECT episode, season, showid '
            b'FROM tv_episodes '
            b'ORDER BY season ASC, episode ASC'
        )

        for result in results:
            if result[b'showid'] not in episodes:
                episodes[result[b'showid']] = {}

            if result[b'season'] not in episodes[result[b'showid']]:
                episodes[result[b'showid']][result[b'season']] = []

            episodes[result[b'showid']][result[b'season']].append(result[b'episode'])

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
        return self.redirect('/home/')

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

        return self.redirect('/history/')

    def toggleDisplayShowSpecials(self, show):

        sickbeard.DISPLAY_SHOW_SPECIALS = not sickbeard.DISPLAY_SHOW_SPECIALS

        return self.redirect('/home/displayShow?show={show}'.format(show=show))

    def setScheduleLayout(self, layout):
        if layout not in ('poster', 'banner', 'list', 'calendar'):
            layout = 'banner'

        if layout == 'calendar':
            sickbeard.COMING_EPS_SORT = 'date'

        sickbeard.COMING_EPS_LAYOUT = layout

        return self.redirect('/schedule/')

    def toggleScheduleDisplayPaused(self):

        sickbeard.COMING_EPS_DISPLAY_PAUSED = not sickbeard.COMING_EPS_DISPLAY_PAUSED

        return self.redirect('/schedule/')

    def setScheduleSort(self, sort):
        if sort not in ('date', 'network', 'show'):
            sort = 'date'

        if sickbeard.COMING_EPS_LAYOUT == 'calendar':
            sort \
                = 'date'

        sickbeard.COMING_EPS_SORT = sort

        return self.redirect('/schedule/')

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
                        controller='schedule', action='index')


@route('/ui(/?.*)')
class UI(WebRoot):
    def __init__(self, *args, **kwargs):
        super(UI, self).__init__(*args, **kwargs)

    @staticmethod
    def add_message():
        ui.notifications.message('Test 1', 'This is test number 1')
        ui.notifications.error('Test 2', 'This is test number 2')

        return 'ok'

    def get_messages(self):
        self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')
        self.set_header('Content-Type', 'application/json')
        messages = {}
        cur_notification_num = 1
        for cur_notification in ui.notifications.get_notifications(self.request.remote_ip):
            messages['notification-{number}'.format(number=cur_notification_num)] = {
                'title': cur_notification.title,
                'message': cur_notification.message,
                'type': cur_notification.type,
            }
            cur_notification_num += 1

        return json.dumps(messages)
