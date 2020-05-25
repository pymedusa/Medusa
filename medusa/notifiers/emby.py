# coding=utf-8

"""Emby notifier module."""
from __future__ import unicode_literals

import json
import logging

from medusa import app
from medusa.helper.exceptions import ex
from medusa.indexers.config import INDEXER_TVDBV2, INDEXER_TVRAGE
from medusa.indexers.utils import indexer_id_to_name, mappings
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSession

from requests.exceptions import HTTPError, RequestException

from six import text_type

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    """Emby notifier class."""

    def __init__(self):
        self.session = MedusaSession()

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

        url = 'http://{host}/emby/Notifications/Admin'.format(host=host)
        data = json.dumps({
            'Name': 'Medusa',
            'Description': message,
            'ImageUrl': app.LOGO_URL
        })
        try:
            resp = self.session.post(
                url=url,
                data=data,
                headers={
                    'X-MediaBrowser-Token': emby_apikey,
                    'Content-Type': 'application/json'
                }
            )
            resp.raise_for_status()

            if resp.text:
                log.debug('EMBY: HTTP response: {0}', resp.text.replace('\n', ''))

            log.info('EMBY: Successfully sent a test notification.')
            return True

        except (HTTPError, RequestException) as error:
            log.warning('EMBY: Warning: Unable to contact Emby at {url}: {error}',
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
                log.debug('EMBY: No host specified, check your settings')
                return False

            if show:
                # EMBY only supports TVDB ids
                provider = 'tvdbid'
                if show.indexer == INDEXER_TVDBV2:
                    tvdb_id = show.indexerid
                else:
                    # Try using external ids to get a TVDB id
                    tvdb_id = show.externals.get(mappings[INDEXER_TVDBV2], None)

                if tvdb_id is None:
                    if show.indexer == INDEXER_TVRAGE:
                        log.warning('EMBY: TVRage indexer no longer valid')
                    else:
                        log.warning(
                            'EMBY: Unable to find a TVDB ID for {series},'
                            ' and {indexer} indexer is unsupported',
                            {'series': show.name, 'indexer': indexer_id_to_name(show.indexer)}
                        )
                    return False

                params = {
                    provider: text_type(tvdb_id)
                }
            else:
                params = {}

            url = 'http://{host}/emby/Library/Series/Updated'.format(host=app.EMBY_HOST)
            try:
                resp = self.session.post(
                    url=url,
                    params=params,
                    headers={
                        'X-MediaBrowser-Token': app.EMBY_APIKEY
                    }
                )
                resp.raise_for_status()

                if resp.text:
                    log.debug('EMBY: HTTP response: {0}', resp.text.replace('\n', ''))

                log.info('EMBY: Successfully sent a "Series Library Updated" command.')
                return True

            except (HTTPError, RequestException) as error:
                log.warning('EMBY: Warning: Unable to contact Emby at {url}: {error}',
                            {'url': url, 'error': ex(error)})
                return False
