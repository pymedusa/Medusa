# coding=utf-8

"""Search v2 core module."""

import datetime
import errno
import logging
import threading
import requests
from socket import timeout as socket_timeout

from . import FORCED_SEARCH, MANUAL_SEARCH, DAILY_SEARCH, BACKLOG_SEARCH, FAILED_SEARCH, PROPER_SEARCH

from medusa import (
    app,
    common,
    db,
)

from medusa.helper.common import (
    enabled_providers,
    episode_num,
)

from medusa.common import (
    MULTI_EP_RESULT,
    Quality,
    SEASON_RESULT,
    SNATCHED,
    SNATCHED_BEST,
    SNATCHED_PROPER,
    UNKNOWN,
)

from medusa.helper.exceptions import AuthException


from medusa.logger.adapters.style import BraceAdapter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class SearchBase(object):
    def __init__(self, search_request):
        # Pass the search segment, options and providers.
        self.search_request = search_request

        # Keep track of the search results
        self.search_results = []

        # Keep track of process
        self.collect_rss_started = False
        self.collect_from_cache_started = False
        self.collect_from_providers_started = False
        self.get_best_results_started = False
        self.snatch_results_started = False

    def _collect_rss(self):
        self.collect_rss_started = True

        # FIXME: Replace with a proper throw/catch exception.
        assert self.search_request.providers, 'Missing list of enabled RSS providers.'

        for cur_provider in self.search_request.providers:
            threading.currentThread().name = u'{thread} :: [{provider}]'.format(thread=threading.currentThread().name,
                                                                                provider=cur_provider.name)
            cur_provider.cache.update_cache()

    def _collect_from_cache(self):
        self.collect_from_cache_started = True

        show_list = app.showList
        from_date = datetime.date.fromordinal(1)
        episodes = []

        # Get a list of episode objects that we want to use to search the cache.
        for series in show_list:
            if series.paused:
                log.debug(u'Not checking for needed episodes of {0} because the show is paused', series.name)
                continue
            episodes.extend(series.wanted_episodes(from_date))

        # Search each RSS / Daily enabled provider cache table.
        for cur_provider in self.search_request.providers:
            threading.currentThread().name = u'{thread} :: [{provider}]'.format(thread=threading.currentThread().name,
                                                                                provider=cur_provider.name)
            try:
                self.search_results += cur_provider.search_rss(episodes)
            except AuthException as error:
                log.error(u'Authentication error: {0}', error.message)
                continue
            except Exception as error:
                log.exception(u'Error while searching {0}, skipping: {1!r}', cur_provider.name, error)
                continue

    def _collect_from_providers(self):
        self.collect_from_providers_started = True
        # Rest of the default collect_from_providers logic.

        assert self.search_request.segment, 'You need to pass a segment with a list of episode objects.'
        series = self.search_request.segment[0].series

        for cur_provider in self.search_request.providers:
            threading.currentThread().name = u'{thread} :: [{provider}]'.format(thread=threading.currentThread().name,
                                                                                provider=cur_provider.name)

            if cur_provider.anime_only and not series.is_anime:
                log.debug(u'{0} is not an anime, skipping', series.name)
                continue

            search_count = 0
            search_mode = cur_provider.search_mode

            # Always search for episode when manually searching when in sponly
            if search_mode == u'sponly' and (self.search_request.options.search_type in (FORCED_SEARCH, MANUAL_SEARCH)):
                search_mode = u'eponly'

            if self.search_request.options.search_type == MANUAL_SEARCH and self.search_request.options.season_search:
                search_mode = u'sponly'

            while True:
                search_count += 1

                if search_mode == u'eponly':
                    log.info(u'Performing episode search for {0}', series.name)
                else:
                    log.info(u'Performing season pack search for {0}', series.name)

                try:
                    search_results = cur_provider.search_episodes(self.search_request.segment, self.search_request, search_mode)
                except AuthException as error:
                    log.error(u'Authentication error: {0!r}', error)
                    break
                except socket_timeout as error:
                    log.debug(u'Connection timed out (sockets) while searching {0}. Error: {1!r}',
                              cur_provider.name, error)
                    break
                except (requests.exceptions.HTTPError, requests.exceptions.TooManyRedirects) as error:
                    log.debug(u'HTTP error while searching {0}. Error: {1!r}',
                              cur_provider.name, error)
                    break
                except requests.exceptions.ConnectionError as error:
                    log.debug(u'Connection error while searching {0}. Error: {1!r}',
                              cur_provider.name, error)
                    break
                except requests.exceptions.Timeout as error:
                    log.debug(u'Connection timed out while searching {0}. Error: {1!r}',
                              cur_provider.name, error)
                    break
                except requests.exceptions.ContentDecodingError as error:
                    log.debug(u'Content-Encoding was gzip, but content was not compressed while searching {0}.'
                              u' Error: {1!r}', cur_provider.name, error)
                    break
                except Exception as error:
                    if u'ECONNRESET' in error or (hasattr(error, u'errno') and error.errno == errno.ECONNRESET):
                        log.warning(u'Connection reseted by peer while searching {0}. Error: {1!r}',
                                    cur_provider.name, error)
                    else:
                        log.exception(u'Unknown exception while searching {0}. Error: {1!r}',
                                      cur_provider.name, error)
                    break

                if search_results:
                    # make a list of all the results for this provider
                    self.search_results += search_results
                    break

                elif not cur_provider.search_fallback or search_count == 2:
                    break

                # Don't fallback when doing manual season search
                if self.search_request.options.season_search:
                    break

                if search_mode == u'sponly':
                    log.debug(u'Fallback episode search initiated')
                    search_mode = u'eponly'
                else:
                    log.debug(u'Fallback season pack search initiate')
                    search_mode = u'sponly'

    def _get_best_results(self):
        self.get_best_results_started = True
        # Rest of the default get_best_results logic.

    def _snatch_results(self):
        self.snatch_results_started = True

    def start(self):
        log.warning('Please dont run start directly from the base class.')


class BacklogSearch(SearchBase):
    def __init__(self, search_request):
        super(BacklogSearch, self).__init__(search_request)
        self.states = (
            ('collect_from_cache_started', self.collect_from_cache_started),
            ('get_best_results_started', self.collect_from_providers_started),
            ('get_best_results_started', self.get_best_results_started)
        )
        # This needs to be overwritten if started as FORCED_SEARCH or MANUAL_SEARCH
        self.search_request.options.search_type = BACKLOG_SEARCH

    def start(self):
        self._collect_from_cache()

        all_searches_satisfied = None
        if self.search_results:
            # TODO: This needs to be implemented in _get_best_results().
            all_searches_satisfied = self._get_best_results()

        if not all_searches_satisfied:
            self._collect_from_providers()
            self._get_best_results()

        self._snatch_results()


class CollectRss(SearchBase):
    def __init__(self, search_request):
        super(CollectRss, self).__init__(search_request)

        self.states = (
            ('collect_rss', self.collect_rss_started)
        )

    def start(self):
        self._collect_rss()


class DailySearch(SearchBase):
    def __init__(self, search_request):
        super(DailySearch, self).__init__(search_request)
        self.search_request.options.search_type = DAILY_SEARCH

    def start(self):

        self._collect_from_cache()

        if self.search_results:
            self._get_best_results()
            self._snatch_results()


class FailedSearch(SearchBase):
    def __init__(self, search_request):
        super(FailedSearch, self).__init__(search_request)

        self.update_failed_started = False

        self.states = (
            ('update_failed_started', self.update_failed_started),
            ('collect_from_cache_started', self.collect_from_cache_started),
            ('get_best_results_started', self.collect_from_providers_started),
            ('get_best_results_started', self.get_best_results_started)
        )

        self.search_request.options.search_type = FAILED_SEARCH

    def _update_failed(self):
        self.update_failed_started = True

    def start(self):

        self._update_failed()

        self._collect_from_cache()

        if self.search_results:
            self._get_best_results()
        elif self.collect_from_providers_started:
            self._collect_from_providers()
            self._get_best_results()

        self._snatch_results()


class ProperSearch(SearchBase):
    def __init__(self, search_request):
        super(ProperSearch, self).__init__(search_request)
        self.search_request.options.search_type = PROPER_SEARCH


