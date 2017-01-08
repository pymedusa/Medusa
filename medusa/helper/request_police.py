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

from ..bs4_parser import BS4Parser

import errno
import datetime
import logging
import requests
import traceback

from cachecontrol import CacheControlAdapter
from cachecontrol.cache import DictCache

from .. import app
from ..common import USER_AGENT
from common import http_code_description
import certifi
import cfscrape

try:
    from urllib.parse import splittype
except ImportError:
    from urllib2 import splittype

logger = logging.getLogger(__name__)


# Request police Exceptions.
class RequestPoliceException(Exception):
    """Generic Police Exception."""


class PoliceRequestScoreExceeded(RequestPoliceException):
    """Police Request Score Exception."""


class PoliceResponseScoreExceeded(RequestPoliceException):
    """Police Request Score Exception."""


class PoliceReservedDailyExceeded(RequestPoliceException):
    """Police Request Exception for exceeding the reserved daily search limit."""


class RequestPoliceInvalidConfiguration(RequestPoliceException):
    """Invalid or incomplete configuration provided."""


class PolicedSession(requests.Session):
    def __init__(self, cache_etags=True, serializer=None, heuristic=None, police=None):
        super(PolicedSession, self).__init__()
        adapter = CacheControlAdapter(
            DictCache(),
            cache_etags=cache_etags,
            serializer=serializer,
            heuristic=heuristic,
        )

        self.mount('http://', adapter)
        self.mount('https://', adapter)
        self.cache_controller = adapter.controller
        self.headers.update({'User-Agent': USER_AGENT, 'Accept-Encoding': 'gzip,deflate'})

        # This can be used to attach a police object
        self.police = police

    @classmethod
    def _request_defaults(cls, kwargs):
        hooks = kwargs.pop(u'hooks', None)
        cookies = kwargs.pop(u'cookies', None)
        verify = certifi.old_where() if all([app.SSL_VERIFY, kwargs.pop(u'verify', True)]) else False

        # request session proxies
        if app.PROXY_SETTING:
            logger.debug(u"Using global proxy: " + app.PROXY_SETTING)
            scheme, address = splittype(app.PROXY_SETTING)
            address = app.PROXY_SETTING if scheme else 'http://' + app.PROXY_SETTING
            proxies = {
                "http": address,
                "https": address,
            }
        else:
            proxies = None

        return hooks, cookies, verify, proxies

    @classmethod
    def _prepare_cf_req(cls, session, request):
        logger.debug(u'CloudFlare protection detected, trying to bypass it')

        try:
            tokens, user_agent = cfscrape.get_tokens(request.url)
            if request.cookies:
                request.cookies.update(tokens)
            else:
                request.cookies = tokens
            if request.headers:
                request.headers.update({u'User-Agent': user_agent})
            else:
                request.headers = {u'User-Agent': user_agent}
            logger.debug(u'CloudFlare protection successfully bypassed.')
            return session.prepare_request(request)
        except (ValueError, AttributeError) as error:
            logger.warning(u"Couldn't bypass CloudFlare's anti-bot protection. Error: {err_msg}", err_msg=error)

    def request(self, method, url, post_data=None, params=None, headers=None, timeout=30, session=None, **kwargs):
        response_type = kwargs.pop(u'returns', u'response')
        stream = kwargs.pop(u'stream', False)
        hooks, cookies, verify, proxies = self._request_defaults(kwargs)

        try:
            if self.police:
                [police_check(**kwargs) for police_check in self.police.enabled_police_request_hooks]

            req = requests.Request(method, url, data=post_data, params=params, hooks=hooks,
                                   headers=headers, cookies=cookies)
            prepped = self.prepare_request(req)
            resp = self.send(prepped, stream=stream, verify=verify, proxies=proxies, timeout=timeout,
                             allow_redirects=True)

            if not resp.ok:
                # Try to bypass CloudFlare's anti-bot protection
                if resp.status_code == 503 and resp.headers.get('server') == u'cloudflare-nginx':
                    cf_prepped = self._prepare_cf_req(session, req)
                    if cf_prepped:
                        cf_resp = session.send(cf_prepped, stream=stream, verify=verify, proxies=proxies,
                                               timeout=timeout, allow_redirects=True)
                        if cf_resp.ok:
                            return cf_resp

                logger.debug(u'Requested url {url} returned status code {status}: {desc}'.format
                             (url=resp.url, status=resp.status_code, desc=http_code_description(resp.status_code)))

                if response_type and response_type != u'response':
                    return None

        except requests.exceptions.RequestException as e:
            logger.debug(u'Error requesting url {url}. Error: {err_msg}', url=url, err_msg=e)
            return None
        except RequestPoliceException as e:
            logger.warning(e.message)
            return None
        except Exception as e:
            if u'ECONNRESET' in e or (hasattr(e, u'errno') and e.errno == errno.ECONNRESET):
                logger.warning(
                    u'Connection reset by peer accessing url {url}. Error: {err_msg}'.format(url=url, err_msg=e))
            else:
                logger.info(u'Unknown exception in url {url}. Error: {err_msg}', url=url, err_msg=e)
                logger.debug(traceback.format_exc())
            return None

        if self.police:
            try:
                [police_check(resp, **kwargs) for police_check in self.police.enabled_police_response_hooks]
            except RequestPoliceException as e:
                logger.warning(e.message)
        return resp


class RequestPolice(object):
    def __init__(self, enable_api_hit_cooldown=False, enable_daily_request_reserve=False):
        self.request_limit = 0
        # Keep a counter of the total number of requests for this provider.
        self.request_count = 0
        self.request_score = 0
        self.response_limit = 0
        self.response_count = 0
        self.response_score = 0
        self.api_request_count = 0
        self.api_grab_limit = None
        self.api_hit_limit_cooldown = 86400
        self.api_hit_limit_cooldown_clear = None
        self.next_allowed_request_date = None

        # request_check_newznab_daily_reserved_calls method attributes
        self.api_hit_limit = None # Moved here, as it's currently only used by daily reserve calls.
        self.daily_request_count = 0
        self.daily_reserve_calls = 0
        self.daily_reserve_calls_next_reset_date = None
        self.daily_reserve_search_mode = None

        # Methods that are run before the request has been send.
        self.enabled_police_request_hooks = [self.request_counter]
        # Methods that are run after a response has been received. Using the response object.
        self.enabled_police_response_hooks = []

        # Configuration
        if enable_api_hit_cooldown:
            self.enabled_police_request_hooks.append(self.request_check_nzb_api_limit)
            self.enabled_police_response_hooks.append(self.response_check_nzb_api_limit)

        if enable_daily_request_reserve:
            self.enabled_police_request_hooks.append(self.request_check_newznab_daily_reserved_calls)

    def request_counter(self, **kwargs):
        """Number of provider requests performed.

        These are not all counted as api hits. As also logins, snatches and newznab capability requests are counted.
        """
        if kwargs.get('api_hit'):
            self.request_count += 1

    def request_check_nzb_api_limit(self, **kwargs):
        """Request hook for checking if the api hit limit has been breached."""
        logger.info('Running request police request_check_nzb_api_limit.')
        if self.api_hit_limit_cooldown_clear and self.api_hit_limit_cooldown_clear > datetime.datetime.now():
            raise RequestPoliceException('Stil in api hit cooldown.')
        self.request_count = 0
        self.request_score = 0

    def response_check_nzb_api_limit(self, r, **kwargs):
        """Response hook for checking if the api hit limit has been breached."""
        logger.info('Running request police response_check_nzb_api_limit.')
        with BS4Parser(r.text, 'html5lib') as html:
            try:
                err_desc = html.error.attrs['description']
                if 'Request limit reached' in err_desc:
                    self.request_count = 1
                    self.request_score = 101
                    import re
                    m = re.search('Request limit reached.*\(([0-9]+)/([0-9]+)\)', err_desc)
                    if m:
                        self.api_hit_limit = int(m.group(2))
            except (AttributeError, TypeError):
                pass

            if self.request_score > self.request_limit:
                delta = datetime.timedelta(seconds=self.api_hit_limit_cooldown)
                self.api_hit_limit_cooldown_clear = datetime.datetime.now() + delta
                raise PoliceRequestScoreExceeded(
                    'Breached the providers api hit limit of {api_hit_limit}. '
                    'Cooldown until {cooldown_clear}'
                    .format(api_hit_limit=self.api_hit_limit,
                            cooldown_clear=self.api_hit_limit_cooldown_clear.strftime('%I:%M%p on %B %d, %Y'))
                )

    def request_check_newznab_daily_reserved_calls(self, **kwargs):
        try:
            if not all([self.api_hit_limit, self.daily_reserve_calls]):
                RequestPoliceInvalidConfiguration('Your missing the daily_reserve_search_mode paramater,'
                                                  'which is needed to determin the used providers search type.')

            self.daily_reserve_search_mode = kwargs.get('search_mode')
            if not self.daily_reserve_search_mode:
                return

            if self.daily_reserve_calls_next_reset_date:
                if self.daily_reserve_calls_next_reset_date > datetime.datetime.now():
                    raise PoliceReservedDailyExceeded(
                        'Stil in daily search reservation cooldown.'
                        'Meaning only daily searches are allowed to hit this provider at this time'
                    )
                else:
                    # We've reached midnight, let's reset the reset_date and the request_count,
                    # as now we need to start over
                    self.daily_reserve_calls_next_reset_date = None
                    self.daily_request_count = 0

            if (self.daily_reserve_search_mode != 'RSS' and self.api_hit_limit and
                    self.daily_request_count > self.api_hit_limit - self.daily_reserve_calls):
                # Set next reset to coming midnight.
                next_day_time = (datetime.datetime.now() + datetime.timedelta(days=1)).date()
                self.daily_reserve_calls_next_reset_date = datetime.datetime.combine(next_day_time, datetime.time())

                raise PoliceReservedDailyExceeded("We've exceeded the reserved [{reserved_calls}] calls for "
                                                  "daily search, we're canceling this request."
                                                  .format(reserved_calls=self.daily_reserve_calls))
        finally:
            # We're using this as a flag, so let's reset it for future use.
            self.daily_reserve_search_mode = None
            self.daily_request_count += 1


# as for backwards compatibility
def request_defaults(kwargs):
    logger.warning('Deprecation warning! Usage of helpers.get_url and request_defaults is deprecated, '
                   'please make use of the PolicedRequest session for all of your requests.')
    return PolicedSession._request_defaults(kwargs)


def prepare_cf_req(session, request):
    logger.warning('Deprecation warning! Usage of helpers.get_url and prepare_cf_req is deprecated, '
                   'please make use of the PolicedRequest session for all of your requests.')
    return PolicedSession._prepare_cf_req(session, request)
