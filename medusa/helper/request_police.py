# coding=utf-8
# Author: p0psicles
#
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
# pylint:disable=too-many-lines
"""Request Police Class for monitoring requests responses, and throttling or breaking where needed."""

import datetime
import errno
import logging
import traceback

from cachecontrol import CacheControlAdapter
from cachecontrol.cache import DictCache

import certifi

import cfscrape

from common import http_code_description

import requests

from requests.utils import dict_from_cookiejar

from .. import app
from ..bs4_parser import BS4Parser
from ..common import USER_AGENT


try:
    from urllib.parse import splittype
except ImportError:
    from urllib2 import splittype









    @classmethod
    def get_url_hook(cls, r, **kwargs):
        """Get URL hook."""
        logger.debug('{method} URL: {url} [Status: {status}]', method=r.request.method, url=r.request.url,
                     status=r.status_code)

        if r.request.method == 'POST':
            logger.debug('With post data: {data}', data=r.request.body)

    @classmethod
    def cloudflare_hook(cls, r, **kwargs):
        """Try to bypass CloudFlare's anti-bot protection."""
        if not r.ok:
            if r.status_code == 503 and r.headers.get('server') == u'cloudflare-nginx':
                logger.debug(u'CloudFlare protection detected, trying to bypass it')

                try:
                    tokens, user_agent = cfscrape.get_tokens(r.request.url)
                    cookies = dict_from_cookiejar(r.request._cookies)
                    if tokens:
                        cookies.update(tokens)

                    if r.request.headers:
                        r.request.headers.update({u'User-Agent': user_agent})
                    else:
                        r.request.headers = {u'User-Agent': user_agent}

                    logger.debug(u'CloudFlare protection successfully bypassed.')

                    # Disable the hooks, to prevent a loop.
                    r.request.hooks = {}

                    new_session = requests.Session()
                    r.request.prepare_cookies(cookies)
                    cf_resp = new_session.send(r.request, stream=kwargs.get('stream'), verify=kwargs.get('verify'),
                                               proxies=kwargs.get('proxies'), timeout=kwargs.get('timeout'),
                                               allow_redirects=True)

                    if cf_resp.ok:
                        return cf_resp

                except (ValueError, AttributeError) as error:
                    logger.warning(u"Couldn't bypass CloudFlare's anti-bot protection. Error: {err_msg}", err_msg=error)
                    return

            logger.debug(u'Requested url {url} returned status code {status}: {desc}'.format
                         (url=r.url, status=r.status_code, desc=http_code_description(r.status_code)))






