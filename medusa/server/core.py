# coding=utf-8

from __future__ import unicode_literals

import os
import threading

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application, RedirectHandler, StaticFileHandler, url
from tornroutes import route
from .api.v1.core import ApiHandler
from .web import CalendarHandler, KeyHandler, LoginHandler, LogoutHandler
from .. import app, logger
from ..helpers import create_https_certificates, generate_api_key


def get_apiv2_handlers(base):
    """Return api v2 handlers."""
    from .api.v2.config import ConfigHandler
    from .api.v2.log import LogHandler
    from .api.v2.show import ShowHandler
    from .api.v2.auth import LoginHandler
    from .api.v2.asset import AssetHandler
    from .api.v2.base import NotFoundHandler

    show_id = r'(?P<show_indexer>[a-z]+)(?P<show_id>\d+)'
    ep_id = r'(?:(?:s(?P<season>\d{1,2})(?:e(?P<episode>\d{1,2}))?)|(?:e(?P<absolute_episode>\d{1,3}))|(?P<air_date>\d{4}\-\d{2}\-\d{2}))'
    query = r'(?P<query>[\w]+)'
    query_extended = r'(?P<query>[\w \(\)%]+)'  # This also accepts the space char, () and %
    log_level = r'(?P<log_level>[a-zA-Z]+)'
    asset_group = r'(?P<asset_group>[a-zA-Z0-9]+)'

    return [
        (r'{base}/show(?:/{show_id}(?:/{ep_id})?(?:/{query})?)?/?'.format(base=base, show_id=show_id, ep_id=ep_id, query=query), ShowHandler),
        (r'{base}/config(?:/{query})?/?'.format(base=base, query=query), ConfigHandler),
        (r'{base}/log(?:/{log_level})?/?'.format(base=base, log_level=log_level), LogHandler),
        (r'{base}/auth/login(/?)'.format(base=base), LoginHandler),
        (r'{base}/asset(?:/{asset_group})(?:/{query})?/?'.format(base=base, asset_group=asset_group, query=query_extended), AssetHandler),
        (r'{base}(/?.*)'.format(base=base), NotFoundHandler)
    ]


class AppWebServer(threading.Thread):  # pylint: disable=too-many-instance-attributes
    def __init__(self, options=None, io_loop=None):
        threading.Thread.__init__(self)
        self.daemon = True
        self.alive = True
        self.name = 'TORNADO'
        self.io_loop = io_loop or IOLoop.current()

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

        # video root
        if app.ROOT_DIRS:
            root_dirs = app.ROOT_DIRS.split('|')
            self.video_root = root_dirs[int(root_dirs[0]) + 1]
        else:
            self.video_root = None

        # web root
        if self.options['web_root']:
            app.WEB_ROOT = self.options['web_root'] = ('/' + self.options['web_root'].lstrip('/').strip('/'))

        # api root
        if not app.API_KEY:
            app.API_KEY = generate_api_key()
        self.options['api_root'] = r'{root}/api/(?:v1/)?{key}'.format(root=app.WEB_ROOT, key=app.API_KEY)
        self.options['api_v2_root'] = r'{root}/api/v2'.format(root=app.WEB_ROOT)

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
            login_url=r'{root}/login/'.format(root=self.options['web_root']),
        )

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
            (r'{base}/login(/?)'.format(base=self.options['web_root']), LoginHandler),
            (r'{base}/logout(/?)'.format(base=self.options['web_root']), LogoutHandler),

            # Web calendar handler (Needed because option Unprotected calendar)
            (r'{base}/calendar'.format(base=self.options['web_root']), CalendarHandler),

            # webui handlers
        ] + self._get_webui_routes())

        self.app.add_handlers('.*$', get_apiv2_handlers(self.options['api_v2_root']))

        # Static File Handlers
        self.app.add_handlers('.*$', [
            # favicon
            (r'{base}/(favicon\.ico)'.format(base=self.options['web_root']), StaticFileHandler,
             {'path': os.path.join(self.options['data_root'], 'images/ico/favicon.ico')}),

            # images
            (r'{base}/images/(.*)'.format(base=self.options['web_root']), StaticFileHandler,
             {'path': os.path.join(self.options['data_root'], 'images')}),

            # cached images
            (r'{base}/cache/images/(.*)'.format(base=self.options['web_root']), StaticFileHandler,
             {'path': os.path.join(app.CACHE_DIR, 'images')}),

            # css
            (r'{base}/css/(.*)'.format(base=self.options['web_root']), StaticFileHandler,
             {'path': os.path.join(self.options['data_root'], 'css')}),

            # javascript
            (r'{base}/js/(.*)'.format(base=self.options['web_root']), StaticFileHandler,
             {'path': os.path.join(self.options['data_root'], 'js')}),

            # fonts
            (r'{base}/fonts/(.*)'.format(base=self.options['web_root']), StaticFileHandler,
             {'path': os.path.join(self.options['data_root'], 'fonts')}),

            # videos
            (r'{base}/videos/(.*)'.format(base=self.options['web_root']), StaticFileHandler,
             {'path': self.video_root})
        ])

    def _get_webui_routes(self):
        webroot = self.options['web_root']
        route._routes = list(reversed([url(webroot + u.regex.pattern, u.handler_class, u.kwargs, u.name) for u in route.get_routes()]))
        return route.get_routes()

    def run(self):
        if self.enable_https:
            protocol = 'https'
            self.server = HTTPServer(self.app, ssl_options={'certfile': self.https_cert, 'keyfile': self.https_key})
        else:
            protocol = 'http'
            self.server = HTTPServer(self.app)

        logger.log('Starting Medusa on {scheme}://{host}:{port}/'.format
                   (scheme=protocol, host=self.options['host'], port=self.options['port']))

        try:
            self.server.listen(self.options['port'], self.options['host'])
        except Exception:
            if app.LAUNCH_BROWSER and not self.daemon:
                app.instance.launch_browser('https' if app.ENABLE_HTTPS else 'http', self.options['port'], app.WEB_ROOT)
                logger.log('Launching browser and exiting')
            logger.log('Could not start the web server on port {port}, already in use!'.format(port=self.options['port']))
            os._exit(1)  # pylint: disable=protected-access

        try:
            self.io_loop.start()
            self.io_loop.close(True)
        except (IOError, ValueError):
            # Ignore errors like 'ValueError: I/O operation on closed kqueue fd'. These might be thrown during a reload.
            pass

    def shutDown(self):
        self.alive = False
        self.io_loop.stop()
