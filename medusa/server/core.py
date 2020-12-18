# coding=utf-8

from __future__ import unicode_literals

import logging
import os
import threading
from posixpath import join

from medusa import app
from medusa.helpers import (
    create_https_certificates,
    generate_api_key,
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.server.api.v1.core import ApiHandler
from medusa.server.api.v2.alias import AliasHandler
from medusa.server.api.v2.alias_source import (
    AliasSourceHandler,
    AliasSourceOperationHandler,
)
from medusa.server.api.v2.auth import AuthHandler
from medusa.server.api.v2.base import BaseRequestHandler, NotFoundHandler
from medusa.server.api.v2.config import ConfigHandler
from medusa.server.api.v2.episode_history import EpisodeHistoryHandler
from medusa.server.api.v2.episodes import EpisodeHandler
from medusa.server.api.v2.history import HistoryHandler
from medusa.server.api.v2.internal import InternalHandler
from medusa.server.api.v2.log import LogHandler
from medusa.server.api.v2.providers import ProvidersHandler
from medusa.server.api.v2.search import SearchHandler
from medusa.server.api.v2.series import SeriesHandler
from medusa.server.api.v2.series_asset import SeriesAssetHandler
from medusa.server.api.v2.series_legacy import SeriesLegacyHandler
from medusa.server.api.v2.series_operation import SeriesOperationHandler
from medusa.server.api.v2.stats import StatsHandler
from medusa.server.api.v2.system import SystemHandler
from medusa.server.web import (
    CalendarHandler,
    KeyHandler,
    LoginHandler,
    LogoutHandler,
    TokenHandler,
)
from medusa.server.web.core.base import AuthenticatedStaticFileHandler
from medusa.ws.handler import WebSocketUIHandler

import six

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import (
    Application,
    RedirectHandler,
    StaticFileHandler,
    url,
)

from tornroutes import route


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


def clean_url_path(*args, **kwargs):
    """Make sure we end with a clean route."""
    end_with_slash = kwargs.pop('end_with_slash', False)
    build_path = ''
    for arg in args:
        build_path = join(build_path.strip('/'), arg.strip('/'))

    build_path = '/' + build_path if build_path else ''

    if end_with_slash:
        build_path += '/'

    return build_path


def get_apiv2_handlers(base):
    """Return api v2 handlers."""
    return [

        # Order: Most specific to most generic

        # /api/v2/providers
        ProvidersHandler.create_app_handler(base),

        # /api/v2/history/tvdb1234/episode
        EpisodeHistoryHandler.create_app_handler(base),

        # /api/v2/history
        HistoryHandler.create_app_handler(base),

        # /api/v2/search
        SearchHandler.create_app_handler(base),

        # /api/v2/series/tvdb1234/episode
        EpisodeHandler.create_app_handler(base),

        # /api/v2/series/tvdb1234/operation
        SeriesOperationHandler.create_app_handler(base),
        # /api/v2/series/tvdb1234/asset
        SeriesAssetHandler.create_app_handler(base),
        # /api/v2/series/tvdb1234/legacy
        SeriesLegacyHandler.create_app_handler(base),  # To be removed
        # /api/v2/series/tvdb1234
        SeriesHandler.create_app_handler(base),

        # /api/v2/config
        ConfigHandler.create_app_handler(base),

        # /api/v2/stats
        StatsHandler.create_app_handler(base),

        # /api/v2/internal
        InternalHandler.create_app_handler(base),

        # /api/v2/log
        LogHandler.create_app_handler(base),

        # /api/v2/alias-source/xem/operation
        AliasSourceOperationHandler.create_app_handler(base),
        # /api/v2/alias-source
        AliasSourceHandler.create_app_handler(base),

        # /api/v2/alias
        AliasHandler.create_app_handler(base),

        # /api/v2/system
        SystemHandler.create_app_handler(base),

        # /api/v2/authenticate
        AuthHandler.create_app_handler(base),

        # Always keep this last!
        NotFoundHandler.create_app_handler(base)
    ]


class AppWebServer(threading.Thread):
    def __init__(self, options=None):
        threading.Thread.__init__(self)
        self.daemon = True
        self.alive = True
        self.name = 'TORNADO'

        self.options = options or {}
        self.options.setdefault('port', 8081)
        self.options.setdefault('host', '0.0.0.0')
        self.options.setdefault('log_dir', None)
        self.options.setdefault('username', '')
        self.options.setdefault('password', '')
        self.options.setdefault('web_root', '/')
        assert isinstance(self.options['port'], int)
        assert 'data_root' in self.options

        self.server = None
        self.io_loop = None

        # video root
        if app.ROOT_DIRS:
            root_dirs = app.ROOT_DIRS
            self.video_root = root_dirs[int(root_dirs[0]) + 1]
        else:
            self.video_root = None

        # web root
        if self.options['web_root']:
            app.WEB_ROOT = self.options['web_root'] = clean_url_path(self.options['web_root'])

        # Configure root to selected theme.
        app.WEB_ROOT = self.options['theme_path'] = clean_url_path(app.WEB_ROOT)

        # Configure the directory to the theme's data root.
        app.THEME_DATA_ROOT = self.options['theme_data_root'] = os.path.join(self.options['data_root'], app.THEME_NAME)

        # api root
        if not app.API_KEY:
            app.API_KEY = generate_api_key()
        self.options['api_root'] = r'{root}/api/(?:v1/)?{key}'.format(root=app.WEB_ROOT, key=app.API_KEY)
        self.options['api_v2_root'] = r'{root}/api/v2'.format(root=app.WEB_ROOT)

        # websocket root
        self.options['web_socket'] = r'{root}/ws'.format(root=app.WEB_ROOT)

        # tornado setup
        self.enable_https = self.options['enable_https']
        self.https_cert = self.options['https_cert']
        self.https_key = self.options['https_key']

        if self.enable_https:
            # If either the HTTPS certificate or key do not exist, make some self-signed ones.
            if not (self.https_cert and os.path.exists(self.https_cert)) or not (
                    self.https_key and os.path.exists(self.https_key)):
                if not create_https_certificates(self.https_cert, self.https_key):
                    log.info('Unable to create CERT/KEY files, disabling HTTPS')
                    app.ENABLE_HTTPS = False
                    self.enable_https = False

            if not (os.path.exists(self.https_cert) and os.path.exists(self.https_key)):
                log.warning('Disabled HTTPS because of missing CERT and KEY files')
                app.ENABLE_HTTPS = False
                self.enable_https = False

        # Load the app
        self.app = Application(
            [],
            debug=True,
            autoreload=False,
            gzip=app.WEB_USE_GZIP,
            xheaders=app.HANDLE_REVERSE_PROXY,
            cookie_secret=app.WEB_COOKIE_SECRET,
            login_url=r'{root}/login/'.format(root=self.options['theme_path']),
            log_function=self.log_request,
        )

        self.app.add_handlers('.*$', get_apiv2_handlers(self.options['api_v2_root']))

        # Websocket handler
        self.app.add_handlers('.*$', [
            (r'{base}/ui(/?.*)'.format(base=self.options['web_socket']), WebSocketUIHandler)
        ])

        # Static File Handlers
        self.app.add_handlers('.*$', [
            # favicon
            (r'{base}/favicon\.ico()'.format(base=self.options['theme_path']), StaticFileHandler,
             {'path': os.path.join(self.options['theme_data_root'], 'assets', 'img', 'ico', 'favicon.ico')}),

            # images
            (r'{base}/images/(.*)'.format(base=self.options['theme_path']), StaticFileHandler,
             {'path': os.path.join(self.options['theme_data_root'], 'assets', 'img')}),

            # cached images
            (r'{base}/cache/images/(.*)'.format(base=self.options['theme_path']), StaticFileHandler,
             {'path': os.path.join(app.CACHE_DIR, 'images')}),

            # css
            (r'{base}/css/(.*)'.format(base=self.options['theme_path']), StaticFileHandler,
             {'path': os.path.join(self.options['theme_data_root'], 'assets', 'css')}),

            # javascript
            (r'{base}/js/(.*)'.format(base=self.options['theme_path']), StaticFileHandler,
             {'path': os.path.join(self.options['theme_data_root'], 'assets', 'js')}),

            # fonts
            (r'{base}/fonts/(.*)'.format(base=self.options['theme_path']), StaticFileHandler,
             {'path': os.path.join(self.options['theme_data_root'], 'assets', 'fonts')}),

            # videos
            (r'{base}/videos/(.*)'.format(base=self.options['theme_path']), StaticFileHandler,
             {'path': self.video_root}),

            # vue dist
            (r'{base}/vue/dist/(.*)'.format(base=self.options['theme_path']), StaticFileHandler,
             {'path': os.path.join(self.options['theme_data_root'], 'vue')}),

            # vue index.html
            (r'{base}/vue/?.*()'.format(base=self.options['theme_path']), AuthenticatedStaticFileHandler,
             {'path': os.path.join(self.options['theme_data_root'], 'index.html'), 'default_filename': 'index.html'}),
        ])

        # Used for hot-swapping themes
        # This is the 2nd rule from the end, because the last one is always `self.app.wildcard_router`
        self.app.static_file_handlers = self.app.default_router.rules[-2]

        # API v1 handlers
        self.app.add_handlers('.*$', [
            # Main handler
            (r'{base}(/?.*)'.format(base=self.options['api_root']), ApiHandler),

            # Key retrieval
            (r'{base}/getkey(/?.*)'.format(base=self.options['web_root']), KeyHandler),

            # Builder redirect
            (r'{base}/api/builder'.format(base=self.options['web_root']),
             RedirectHandler, {'url': '{base}/apibuilder/'.format(base=self.options['web_root'])}),

            # Webui login/logout handlers
            (r'{base}/login(/?)'.format(base=self.options['theme_path']), LoginHandler),
            (r'{base}/logout(/?)'.format(base=self.options['theme_path']), LogoutHandler),

            (r'{base}/token(/?)'.format(base=self.options['web_root']), TokenHandler),

            # Web calendar handler (Needed because option Unprotected calendar)
            (r'{base}/calendar'.format(base=self.options['web_root']), CalendarHandler),

            # webui handlers
        ] + self._get_webui_routes())

    def _get_webui_routes(self):
        webroot = self.options['theme_path']
        route._routes = list(reversed([url(webroot + u.regex.pattern, u.handler_class, u.kwargs, u.name) for u in route.get_routes()]))
        return route.get_routes()

    def run(self):
        # Start event loop in python3
        if six.PY3:
            import asyncio
            import sys

            # We need to set the WindowsSelectorEventLoop event loop on python 3 (3.8 and higher) running on windows
            if sys.platform == 'win32':
                try:
                    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                except AttributeError:  # Only available since Python 3.7.0
                    pass
            asyncio.set_event_loop(asyncio.new_event_loop())

        if self.enable_https:
            protocol = 'https'
            self.server = HTTPServer(self.app, ssl_options={'certfile': self.https_cert, 'keyfile': self.https_key})
        else:
            protocol = 'http'
            self.server = HTTPServer(self.app)

        log.info('Starting Medusa on {scheme}://{host}:{port}{web_root}/', {
            'scheme': protocol, 'host': self.options['host'],
            'port': self.options['port'], 'web_root': self.options['theme_path']
        })

        try:
            self.server.listen(self.options['port'], self.options['host'])
        except Exception as ex:
            if app.LAUNCH_BROWSER and not self.daemon:
                app.instance.launch_browser('https' if app.ENABLE_HTTPS else 'http', self.options['port'], app.WEB_ROOT)
                log.info('Launching browser and exiting')
            log.info('Could not start the web server on port {port}. Exception: {ex}', {
                'port': self.options['port'],
                'ex': ex
            })
            os._exit(1)  # pylint: disable=protected-access

        try:
            self.io_loop = IOLoop.current()
            self.io_loop.start()
        except (IOError, ValueError):
            # Ignore errors like 'ValueError: I/O operation on closed kqueue fd'. These might be thrown during a reload.
            pass

    def shutDown(self):
        self.alive = False
        self.io_loop.stop()

    def log_request(self, handler):
        """
        Write a completed HTTP request to the logs.

        This method handles logging Tornado requests.
        """
        if not app.WEB_LOG:
            return

        level = None
        if handler.get_status() < 400:
            level = logging.INFO
        elif handler.get_status() < 500:
            # Don't log normal APIv2 RESTful responses as warnings
            if isinstance(handler, BaseRequestHandler):
                level = logging.INFO
            else:
                level = logging.WARNING
        else:
            # If a real exception was raised in APIv2,
            # let `BaseRequestHandler.log_exception` handle the logging
            if not isinstance(handler, BaseRequestHandler):
                level = logging.ERROR

        if level is None:
            return

        log.log(
            level,
            '{status} {summary} {time:.2f}ms',
            {
                'status': handler.get_status(),
                'summary': handler._request_summary(),
                'time': 1000.0 * handler.request.request_time()
            }
        )
