# coding=utf-8

from __future__ import unicode_literals

import os
import threading
from posixpath import join

from medusa import (
    app,
    logger,
)
from medusa.helpers import (
    create_https_certificates,
    generate_api_key,
)
from medusa.server.api.v1.core import ApiHandler
from medusa.server.api.v2.alias import AliasHandler
from medusa.server.api.v2.alias_source import (
    AliasSourceHandler,
    AliasSourceOperationHandler,
)
from medusa.server.api.v2.auth import AuthHandler
from medusa.server.api.v2.base import NotFoundHandler
from medusa.server.api.v2.config import ConfigHandler
from medusa.server.api.v2.episode import EpisodeHandler
from medusa.server.api.v2.internal import InternalHandler
from medusa.server.api.v2.log import LogHandler
from medusa.server.api.v2.show import ShowHandler
from medusa.server.api.v2.show_asset import ShowAssetHandler
from medusa.server.api.v2.show_legacy import ShowLegacyHandler
from medusa.server.api.v2.show_operation import ShowOperationHandler
from medusa.server.api.v2.stats import StatsHandler
from medusa.server.web import (
    CalendarHandler,
    KeyHandler,
    LoginHandler,
    LogoutHandler,
    TokenHandler,
)
from medusa.server.web.core.base import AuthenticatedStaticFileHandler
from medusa.ws import MedusaWebSocketHandler

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import (
    Application,
    RedirectHandler,
    StaticFileHandler,
    url,
)

from tornroutes import route


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
        # /api/v2/show/tvdb1234/episode
        EpisodeHandler.create_app_handler(base),

        # /api/v2/show/tvdb1234/operation
        ShowOperationHandler.create_app_handler(base),
        # /api/v2/show/tvdb1234/asset
        ShowAssetHandler.create_app_handler(base),
        # /api/v2/show/tvdb1234/legacy
        ShowLegacyHandler.create_app_handler(base),  # To be removed
        # /api/v2/show/tvdb1234
        ShowHandler.create_app_handler(base),

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
                    logger.log('Unable to create CERT/KEY files, disabling HTTPS')
                    app.ENABLE_HTTPS = False
                    self.enable_https = False

            if not (os.path.exists(self.https_cert) and os.path.exists(self.https_key)):
                logger.log('Disabled HTTPS because of missing CERT and KEY files', logger.WARNING)
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
        )

        self.app.add_handlers('.*$', get_apiv2_handlers(self.options['api_v2_root']))

        # Websocket handler
        self.app.add_handlers(".*$", [
            (r'{base}/ui(/?.*)'.format(base=self.options['web_socket']), MedusaWebSocketHandler.WebSocketUIHandler)
        ])

        # Static File Handlers
        self.app.add_handlers('.*$', [
            # favicon
            (r'{base}/(favicon\.ico)'.format(base=self.options['theme_path']), StaticFileHandler,
             {'path': os.path.join(self.options['theme_data_root'], 'assets', 'img/ico/favicon.ico')}),

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
        if self.enable_https:
            protocol = 'https'
            self.server = HTTPServer(self.app, ssl_options={'certfile': self.https_cert, 'keyfile': self.https_key})
        else:
            protocol = 'http'
            self.server = HTTPServer(self.app)

        logger.log('Starting Medusa on {scheme}://{host}:{port}{web_root}/'.format
                   (scheme=protocol,
                    host=self.options['host'],
                    port=self.options['port'],
                    web_root=self.options['theme_path']))

        try:
            self.server.listen(self.options['port'], self.options['host'])
        except Exception:
            if app.LAUNCH_BROWSER and not self.daemon:
                app.instance.launch_browser('https' if app.ENABLE_HTTPS else 'http', self.options['port'], app.WEB_ROOT)
                logger.log('Launching browser and exiting')
            logger.log('Could not start the web server on port {port}, already in use!'.format(port=self.options['port']))
            os._exit(1)  # pylint: disable=protected-access

        try:
            self.io_loop = IOLoop.current()
            IOLoop.current().start()
        except (IOError, ValueError):
            # Ignore errors like 'ValueError: I/O operation on closed kqueue fd'. These might be thrown during a reload.
            pass

    def shutDown(self):
        self.alive = False
        IOLoop.current().stop()
