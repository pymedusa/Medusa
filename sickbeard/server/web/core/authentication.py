# coding=utf-8

"""
Authentication Handlers:
Login, Logout and API key
"""

from __future__ import unicode_literals

import traceback
from tornado.web import RequestHandler
import sickbeard
from sickbeard import (
    helpers, logger, notifiers,
)
from sickbeard.server.web.core.base import BaseHandler, PageTemplate


class KeyHandler(RequestHandler):
    """
    Handler for API Keys
    """
    def __init__(self, *args, **kwargs):
        super(KeyHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        """
        Get api key as json response.
        """
        api_key = None

        try:
            username = sickbeard.WEB_USERNAME
            password = sickbeard.WEB_PASSWORD

            if (self.get_argument('u', None) == username or not username) and \
                    (self.get_argument('p', None) == password or not password):
                api_key = sickbeard.API_KEY

            self.finish({'success': api_key is not None, 'api_key': api_key})
        except Exception:
            logger.log('Failed doing key request: {error}'.format(error=traceback.format_exc()), logger.ERROR)
            self.finish({'success': False, 'error': 'Failed returning results'})


class LoginHandler(BaseHandler):
    """
    Handler for Login
    """
    def get(self, *args, **kwargs):
        """
        Render the Login page
        """
        if self.get_current_user():
            self.redirect('/{page}/'.format(page=sickbeard.DEFAULT_PAGE))
        else:
            t = PageTemplate(rh=self, filename='login.mako')
            self.finish(t.render(title='Login', header='Login', topmenu='login'))

    def post(self, *args, **kwargs):
        """
        Submit Login
        """

        api_key = None

        username = sickbeard.WEB_USERNAME
        password = sickbeard.WEB_PASSWORD

        if all([(self.get_argument('username') == username or not username),
                (self.get_argument('password') == password or not password)]):
            api_key = sickbeard.API_KEY

        if sickbeard.NOTIFY_ON_LOGIN and not helpers.is_ip_private(self.request.remote_ip):
            notifiers.notify_login(self.request.remote_ip)

        if api_key:
            remember_me = int(self.get_argument('remember_me', default=0) or 0)
            self.set_secure_cookie('sickrage_user', api_key, expires_days=30 if remember_me else None)
            logger.log('User logged into the Medusa web interface', logger.INFO)
        else:
            logger.log('User attempted a failed login to the Medusa web interface from IP: {ip}'.format
                       (ip=self.request.remote_ip), logger.WARNING)

        self.redirect('/{page}/'.format(page=sickbeard.DEFAULT_PAGE))


class LogoutHandler(BaseHandler):
    """
    Handler for Logout
    """
    def get(self, *args, **kwargs):
        """
        Logout and redirect to the Login page
        """
        self.clear_cookie('sickrage_user')
        self.redirect('/login/')
