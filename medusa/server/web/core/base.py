# coding=utf-8

from __future__ import unicode_literals

import os
import re
import time
import traceback
from builtins import str
from concurrent.futures import ThreadPoolExecutor

from mako.exceptions import RichTraceback
from mako.lookup import TemplateLookup
from mako.runtime import UNDEFINED
from mako.template import Template as MakoTemplate

from medusa import (
    app,
    db,
    exception_handler,
    helpers,
    logger,
)
from medusa.server.api.v1.core import function_mapper

from requests.compat import urljoin

from six import (
    iteritems,
    viewitems,
)

from tornado.concurrent import run_on_executor
from tornado.escape import utf8
from tornado.gen import coroutine
from tornado.web import (
    HTTPError,
    RequestHandler,
    StaticFileHandler,
    addslash,
    authenticated,
)

from tornroutes import route


mako_lookup = None
mako_cache = None
mako_path = None


def get_lookup():
    global mako_lookup  # pylint: disable=global-statement
    global mako_cache  # pylint: disable=global-statement
    global mako_path  # pylint: disable=global-statement

    if mako_path is None:
        mako_path = os.path.join(app.THEME_DATA_ROOT, 'templates/')
    if mako_cache is None:
        mako_cache = os.path.join(app.CACHE_DIR, 'mako')
    if mako_lookup is None:
        use_strict = app.BRANCH and app.BRANCH != 'master'
        mako_lookup = TemplateLookup(directories=[mako_path],
                                     module_directory=mako_cache,
                                     #  format_exceptions=True,
                                     strict_undefined=use_strict,
                                     filesystem_checks=True)
    return mako_lookup


class PageTemplate(MakoTemplate):
    """Mako page template."""

    def __init__(self, rh, filename):
        lookup = get_lookup()
        self.template = lookup.get_template(filename)

        base_url = (rh.request.headers.get('X-Forwarded-Proto', rh.request.protocol) + '://' +
                    rh.request.headers.get('X-Forwarded-Host', rh.request.host))

        self.arguments = {
            'sbHttpPort': app.WEB_PORT,
            'sbHttpsPort': app.WEB_PORT,
            'sbHttpsEnabled': app.ENABLE_HTTPS,
            'sbHandleReverseProxy': app.HANDLE_REVERSE_PROXY,
            'sbThemeName': app.THEME_NAME,
            'sbDefaultPage': app.DEFAULT_PAGE,
            'loggedIn': rh.get_current_user(),
            'sbStartTime': rh.startTime,
            'sbPID': str(app.PID),
            'title': 'FixME',
            'header': 'FixME',
            'submenu': [],
            'controller': 'FixME',
            'action': 'FixME',
            'show': UNDEFINED,
            'base_url': base_url + app.WEB_ROOT + '/',
            'realpage': '',
            'full_url': base_url + rh.request.uri
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

    def render(self, *args, **kwargs):
        """Render the Page template."""
        for key in self.arguments:
            if key not in kwargs:
                kwargs[key] = self.arguments[key]

        kwargs['makoStartTime'] = time.time()
        try:
            return self.template.render_unicode(*args, **kwargs)
        except Exception:
            kwargs['backtrace'] = RichTraceback()
            for (filename, lineno, function, _) in kwargs['backtrace'].traceback:
                logger.log(u'File {name}, line {line}, in {func}'.format
                           (name=filename, line=lineno, func=function), logger.DEBUG)
            logger.log(u'{name}: {error}'.format
                       (name=kwargs['backtrace'].error.__class__.__name__, error=kwargs['backtrace'].error))
            return get_lookup().get_template('500.mako').render_unicode(*args, **kwargs)


class BaseHandler(RequestHandler):
    """Base Handler for the server."""

    startTime = 0.

    def __init__(self, *args, **kwargs):
        self.startTime = time.time()

        super(BaseHandler, self).__init__(*args, **kwargs)

    def write_error(self, status_code, **kwargs):
        """Base error Handler for 404's."""
        # handle 404 http errors
        if status_code == 404:
            url = self.request.uri
            if app.WEB_ROOT and self.request.uri.startswith(app.WEB_ROOT):
                url = url[len(app.WEB_ROOT) + 1:]

            if url[:3] != 'api':
                t = PageTemplate(rh=self, filename='404.mako')
                return self.finish(t.render())
            else:
                self.finish('Wrong API key used')

        elif self.settings.get('debug') and 'exc_info' in kwargs:
            exc_info = kwargs['exc_info']
            trace_info = ''.join(['{line}<br>'.format(line=line) for line in traceback.format_exception(*exc_info)])
            request_info = ''.join(['<strong>{key}</strong>: {value}<br>'.format(key=k, value=v)
                                    for k, v in viewitems(self.request.__dict__)])
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
                """.format(title=error, error=error, trace=trace_info, request=request_info, root=app.WEB_ROOT)
            )

    def redirect(self, url, permanent=False, status=None):
        """Send a redirect to the given (optionally relative) URL.

        ----->>>>> NOTE: Removed self.finish <<<<<-----

        If the ``status`` argument is specified, that value is used as the
        HTTP status code; otherwise either 301 (permanent) or 302
        (temporary) is chosen based on the ``permanent`` argument.
        The default is 302 (temporary).
        """
        if not url.startswith(app.WEB_ROOT):
            url = app.WEB_ROOT + url

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
        if app.WEB_USERNAME and app.WEB_PASSWORD:
            return self.get_secure_cookie(app.SECURE_TOKEN)
        return True


class WebHandler(BaseHandler):
    """Base Handler for the web server."""

    executor = ThreadPoolExecutor(thread_name_prefix='Thread')

    def __init__(self, *args, **kwargs):
        super(WebHandler, self).__init__(*args, **kwargs)

    @authenticated
    @coroutine
    def get(self, route, *args, **kwargs):
        try:
            # route -> method obj
            route = route.strip('/').replace('.', '_').replace('-', '_') or 'index'
            method = getattr(self, route)

            results = yield self.async_call(method)
            self.finish(results)

        except Exception:
            logger.log(u'Failed doing web ui get request {route!r}: {error}'.format
                       (route=route, error=traceback.format_exc()), logger.DEBUG)
            raise HTTPError(404)

    @authenticated
    @coroutine
    def post(self, route, *args, **kwargs):
        try:
            # route -> method obj
            route = route.strip('/').replace('.', '_').replace('-', '_') or 'index'
            method = getattr(self, route)

            results = yield self.async_call(method)
            self.finish(results)

        except Exception:
            logger.log(u'Failed doing web ui post request {route!r}: {error}'.format
                       (route=route, error=traceback.format_exc()), logger.DEBUG)
            raise HTTPError(404)

    @run_on_executor
    def async_call(self, function):
        try:
            kwargs = self.request.arguments
            for arg, value in iteritems(kwargs):
                if len(value) == 1:
                    kwargs[arg] = self.get_argument(arg)

            result = function(**kwargs)
            return result
        except Exception as e:
            exception_handler.handle(e)


@route('(.*)(/?)')
class WebRoot(WebHandler):
    """Base Handler for the web server."""

    def __init__(self, *args, **kwargs):
        super(WebRoot, self).__init__(*args, **kwargs)

    def index(self):
        return self.redirect('/{page}/'.format(page=app.DEFAULT_PAGE))

    def not_found(self):
        """
        Fallback 404 route.

        [Converted to VueRouter]
        """
        t = PageTemplate(rh=self, filename='index.mako')
        return t.render()

    def server_error(self):
        """
        Fallback 500 route.

        [Converted to VueRouter]
        """
        t = PageTemplate(rh=self, filename='index.mako')
        return t.render()

    def robots_txt(self):
        """Keep web crawlers out."""
        self.set_header('Content-Type', 'text/plain')
        return 'User-agent: *\nDisallow: /'

    def apibuilder(self):
        def titler(x):
            return (helpers.remove_article(x), x)[not x or app.SORT_ARTICLE]

        main_db_con = db.DBConnection(row_type='dict')
        shows = sorted(app.showList, key=lambda x: titler(x.name.lower()))
        episodes = {}

        results = main_db_con.select(
            b'SELECT episode, season, indexer, showid '
            b'FROM tv_episodes '
            b'ORDER BY season ASC, episode ASC'
        )

        for result in results:
            if result[b'showid'] not in episodes:
                episodes[result[b'showid']] = {}

            if result[b'season'] not in episodes[result[b'showid']]:
                episodes[result[b'showid']][result[b'season']] = []

            episodes[result[b'showid']][result[b'season']].append(result[b'episode'])

        if len(app.API_KEY) == 32:
            apikey = app.API_KEY
        else:
            apikey = 'API Key not generated'

        t = PageTemplate(rh=self, filename='apiBuilder.mako')
        return t.render(title='API Builder', header='API Builder', shows=shows, episodes=episodes, apikey=apikey,
                        commands=function_mapper)

    @staticmethod
    def setPosterSortBy(sort):
        # @TODO: Replace this with poster.sort.field={name, date, network, progress} PATCH /api/v2/config/layout
        if sort not in ('name', 'date', 'network', 'progress', 'indexer'):
            sort = 'name'

        app.POSTER_SORTBY = sort
        app.instance.save_config()

    @staticmethod
    def setPosterSortDir(direction):
        # @TODO: Replace this with poster.sort.dir={asc, desc} PATCH /api/v2/config/layout
        app.POSTER_SORTDIR = int(direction)
        app.instance.save_config()


class AuthenticatedStaticFileHandler(StaticFileHandler):
    def __init__(self, *args, **kwargs):
        super(AuthenticatedStaticFileHandler, self).__init__(*args, **kwargs)

    def get_current_user(self):
        if app.WEB_USERNAME and app.WEB_PASSWORD:
            return self.get_secure_cookie(app.SECURE_TOKEN)
        return True

    @addslash
    @authenticated
    def get(self, *args, **kwargs):
        super(AuthenticatedStaticFileHandler, self).get(*args, **kwargs)
