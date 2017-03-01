# coding=utf-8

from __future__ import unicode_literals

import datetime
import logging
from ..bs4_parser import BS4Parser
from core import MedusaSession
from exceptions import (PolicedRequestDailyExceeded, PolicedRequestException, PolicedRequestInvalidConfiguration,
                        PolicedRequestScoreExceeded)

logger = logging.getLogger(__name__)


class PolicedSession(MedusaSession):
    """Policed Session class."""

    def __init__(self, *args, **kwargs):
        """Initialize the class."""
        kwargs['cache_control'] = {'cache_etags': True, 'serializer': None, 'heuristic': None}

        super(PolicedSession, self).__init__(*args, **kwargs)

        # Generic attributes
        self.request_count = 0
        self.request_score = 0
        self.request_limit = 100

        # Api hit cooldown
        self.enable_api_hit_cooldown = kwargs.get('enable_api_hit_cooldown')
        self.api_hit_limit_cooldown = 86400
        self.api_hit_limit_cooldown_clear = None
        self.next_allowed_request_date = None

        # request_check_newznab_daily_reserved_calls method attributes
        self.api_hit_limit = None  # Moved here, as it's currently only used by daily reserve calls.
        self.daily_request_count = 0
        self.daily_reserve_calls = kwargs.get('daily_reserve_calls')
        self.daily_reserve_calls_next_reset_date = None
        self.daily_reserve_search_mode = None

        # Methods that are run before the request has been send.
        self.enabled_police_request_hooks = [self.request_counter]
        # Methods that are run after a response has been received. Using the response object.
        self.enabled_police_response_hooks = []

        self.configure_hooks()

    def request(self, method, url, *args, **kwargs):
        """Request URL using given params."""
        try:
            police_options = kwargs.pop('police_options', {})
            _ = [police_check(**police_options) for police_check in self.enabled_police_request_hooks]
            r = super(PolicedSession, self).request(method, url, *args, **kwargs)
            _ = [police_check(r, **police_options) for police_check in self.enabled_police_response_hooks]
            return r
        except PolicedRequestException as e:
            logger.warning(e.message)
            return None

    def configure_hooks(self):
        """Based on the RequestPolice attributes, enable/disable hooks."""
        # Methods that are run before the request has been send.
        self.enabled_police_request_hooks = [self.request_counter]
        # Methods that are run after a response has been received. Using the response object.
        self.enabled_police_response_hooks = []

        if self.enable_api_hit_cooldown:
            self.enabled_police_request_hooks.append(self.request_check_nzb_api_limit)
            self.enabled_police_response_hooks.append(self.response_check_nzb_api_limit)

        if self.daily_reserve_calls:
            self.enabled_police_request_hooks.append(self.request_check_newznab_daily_reserved_calls)

    def request_counter(self, **store):
        """Number of provider requests performed.

        These are not all counted as api hits. As also logins, snatches and newznab capability requests are counted.
        """
        if store.get('api_hit'):
            self.request_count += 1

    def request_check_nzb_api_limit(self):
        """Request hook for checking if the api hit limit has been breached."""
        logger.info('Running request police request_check_nzb_api_limit.')
        if self.api_hit_limit_cooldown_clear and self.api_hit_limit_cooldown_clear > datetime.datetime.now():
            raise PolicedRequestException('Stil in api hit cooldown.')
        self.request_count = 0
        self.request_score = 0

    def response_check_nzb_api_limit(self, r):
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
                raise PolicedRequestScoreExceeded(
                    'Breached the providers api hit limit of {api_hit_limit}. '
                    'Cooldown until {cooldown_clear}'
                    .format(api_hit_limit=self.api_hit_limit,
                            cooldown_clear=self.api_hit_limit_cooldown_clear.strftime('%I:%M%p on %B %d, %Y'))
                )

    def request_check_newznab_daily_reserved_calls(self, **kwargs):
        """Check if we reached reserved calls and if we do, don't request URL."""
        try:
            if not all([self.api_hit_limit, self.daily_reserve_calls]):
                PolicedRequestInvalidConfiguration('Your missing the daily_reserve_search_mode paramater,'
                                                  'which is needed to determin the used providers search type.')

            self.daily_reserve_search_mode = kwargs.get('search_mode')
            if not self.daily_reserve_search_mode:
                return

            if self.daily_reserve_calls_next_reset_date:
                if self.daily_reserve_calls_next_reset_date > datetime.datetime.now():
                    raise PolicedRequestDailyExceeded(
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

                raise PolicedRequestDailyExceeded("We've exceeded the reserved [{reserved_calls}] calls for "
                                                  "daily search, we're canceling this request."
                                                  .format(reserved_calls=self.daily_reserve_calls))
        finally:
            # We're using this as a flag, so let's reset it for future use.
            self.daily_reserve_search_mode = None
            self.daily_request_count += 1


class RateLimitedSession(MedusaSession):
    """Rate limited Session class."""

    def __init__(self, max_requests, request_period, **kwargs):
        """Initialize the class."""
        super(RateLimitedSession, self).__init__(**kwargs)
        self.max_requests = max_requests
        self.request_period = request_period
        self.num_requests = 0

    def request(self, *args, **kwargs):
        """Request URL if limit not exceeded."""
        if datetime.datetime.now() > self.reset_time():
            self.num_requests = 0

        if not kwargs.pop('ignore_limit'):
            self.num_requests += 1
            if self.num_requests >= self.max_requests:
                raise Exception('Limit exceeded')
        return super(RateLimitedSession, self).request(*args, **kwargs)


class ThrottledSession(MedusaSession):
    """
    A Throttled Session that rate limits requests.
    """
    def __init__(self, throttle, **kwargs):
        super(ThrottledSession, self).__init__(**kwargs)
        self.throttle = throttle
        if self.throttle:
            self.request = self.throttle(super(ThrottledSession, self).request)
