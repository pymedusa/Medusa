# coding=utf-8

"""Search v2 core module."""

import datetime
import logging
import threading

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

    def collect_rss(self):
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
                log.debug(u'Not checking for needed episodes of {0} because the show is paused', cur_show.name)
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

    def _get_best_results(self):
        self.get_best_results_started = True
        # Rest of the default get_best_results logic.

    def _snatch_results(self):
        self.snatch_results_started = True

    def start(self):

        self._collect_from_cache()

        if self.search_results:
            self._get_best_results()
        elif self.collect_from_providers_started:
            self._collect_from_providers()
            self._get_best_results()

        self._snatch_results()


class BacklogSearch(SearchBase):
    def __init__(self, search_request):
        super(BacklogSearch, self).__init__(search_request)
        self.states = (
            ('collect_from_cache_started', self.collect_from_cache_started),
            ('get_best_results_started', self.collect_from_providers_started),
            ('get_best_results_started', self.get_best_results_started)
        )


class CollectRss(SearchBase):
    def __init__(self, search_request):
        super(CollectRss, self).__init__(search_request)

        self.states = (
            ('collect_rss', self.collect_rss)
        )

    def start(self):
        self.collect_rss()


class DailySearch(SearchBase):
    def __init__(self, search_request):
        super(DailySearch, self).__init__(search_request)

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


