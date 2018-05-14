# coding=utf-8

"""Emby notifier module."""
from __future__ import unicode_literals

import json
import logging
from builtins import object

from medusa import app
from medusa.helper.exceptions import ex
from medusa.logger.adapters.style import BraceAdapter

from requests.compat import urlencode

from six.moves.urllib.error import URLError
from six.moves.urllib.request import Request, urlopen

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    """Emby notifier class."""

    def _notify_emby(self, message, host=None, emby_apikey=None):
        """
        Notify Emby host via HTTP API.

        :return: True for no issue or False if there was an error
        """
        # fill in omitted parameters
        if not host:
            host = app.EMBY_HOST
        if not emby_apikey:
            emby_apikey = app.EMBY_APIKEY

        url = 'http://%s/emby/Notifications/Admin' % host
        values = {'Name': 'Medusa', 'Description': message, 'ImageUrl': app.LOGO_URL}
        data = json.dumps(values)
        try:
            req = Request(url, data)
            req.add_header('X-MediaBrowser-Token', emby_apikey)
            req.add_header('Content-Type', 'application/json')

            response = urlopen(req)
            result = response.read()
            response.close()

            log.debug(u'EMBY: HTTP response: {0}', result.replace('\n', ''))
            return True

        except (URLError, IOError) as error:
            log.warning(u'EMBY: Warning: Unable to contact Emby at {url}: {error}',
                        {'url': url, 'error': ex(error)})
            return False


##############################################################################
# Public functions
##############################################################################

    def test_notify(self, host, emby_apikey):
        """
        Sends a test notification.

        :return: True for no issue or False if there was an error
        """
        return self._notify_emby('This is a test notification from Medusa', host, emby_apikey)

    def update_library(self, show=None):
        """
        Update the Emby Media Server host via HTTP API.

        :return: True for no issue or False if there was an error
        """
        if app.USE_EMBY:
            if not app.EMBY_HOST:
                log.debug(u'EMBY: No host specified, check your settings')
                return False

            if show:
                if show.indexer == 1:
                    provider = 'tvdb'
                elif show.indexer == 2:
                    log.warning(u'EMBY: TVRage Provider no longer valid')
                    return False
                else:
                    log.warning(u'EMBY: Provider unknown')
                    return False
                query = '?%sid=%s' % (provider, show.indexerid)
            else:
                query = ''

            url = 'http://%s/emby/Library/Series/Updated%s' % (app.EMBY_HOST, query)
            values = {}
            data = urlencode(values)
            try:
                req = Request(url, data)
                req.add_header('X-MediaBrowser-Token', app.EMBY_APIKEY)

                response = urlopen(req)
                result = response.read()
                response.close()

                log.debug(u'EMBY: HTTP response: {0}', result.replace('\n', ''))
                return True

            except (URLError, IOError) as error:
                log.warning(u'EMBY: Warning: Unable to contact Emby at {url}: {error}',
                            {'url': url, 'error': ex(error)})
                return False
