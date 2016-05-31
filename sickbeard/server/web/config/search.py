# coding=utf-8

"""
Configure Searches
"""

from __future__ import unicode_literals

import os
from tornado.routes import route
import sickbeard
from sickbeard import (
    config, logger, ui,
)
from sickrage.helper.common import try_int
from sickrage.helper.encoding import ek
from sickbeard.server.web.core import PageTemplate
from sickbeard.server.web.config.handler import Config


@route('/config/search(/?.*)')
class ConfigSearch(Config):
    """
    Handler for Search configuration
    """
    def __init__(self, *args, **kwargs):
        super(ConfigSearch, self).__init__(*args, **kwargs)

    def index(self):
        """
        Render the Search configuration page
        """
        t = PageTemplate(rh=self, filename='config_search.mako')

        return t.render(submenu=self.ConfigMenu(), title='Config - Episode Search',
                        header='Search Settings', topmenu='config',
                        controller='config', action='search')

    def saveSearch(self, use_nzbs=None, use_torrents=None, nzb_dir=None, sab_username=None, sab_password=None,
                   sab_apikey=None, sab_category=None, sab_category_anime=None, sab_category_backlog=None,
                   sab_category_anime_backlog=None, sab_host=None, nzbget_username=None, nzbget_password=None,
                   nzbget_category=None, nzbget_category_backlog=None, nzbget_category_anime=None,
                   nzbget_category_anime_backlog=None, nzbget_priority=None, nzbget_host=None,
                   nzbget_use_https=None, backlog_days=None, backlog_frequency=None, dailysearch_frequency=None,
                   nzb_method=None, torrent_method=None, usenet_retention=None, download_propers=None,
                   check_propers_interval=None, allow_high_priority=None, sab_forced=None,
                   randomize_providers=None, use_failed_downloads=None, delete_failed=None,
                   torrent_dir=None, torrent_username=None, torrent_password=None, torrent_host=None,
                   torrent_label=None, torrent_label_anime=None, torrent_path=None, torrent_verify_cert=None,
                   torrent_seed_time=None, torrent_paused=None, torrent_high_bandwidth=None,
                   torrent_rpcurl=None, torrent_auth_type=None, ignore_words=None,
                   preferred_words=None, undesired_words=None, trackers_list=None, require_words=None,
                   ignored_subs_list=None, ignore_und_subs=None, cache_trimming=None, max_cache_age=None):
        """
        Save Search related settings
        """

        results = []

        if not config.change_NZB_DIR(nzb_dir):
            results += ['Unable to create directory {dir}, dir not changed.'.format(dir=ek(os.path.normpath, nzb_dir))]

        if not config.change_TORRENT_DIR(torrent_dir):
            results += ['Unable to create directory {dir}, dir not changed.'.format(dir=ek(os.path.normpath, torrent_dir))]

        config.change_DAILYSEARCH_FREQUENCY(dailysearch_frequency)

        config.change_BACKLOG_FREQUENCY(backlog_frequency)
        sickbeard.BACKLOG_DAYS = try_int(backlog_days, 7)

        sickbeard.CACHE_TRIMMING = config.checkbox_to_value(cache_trimming)
        sickbeard.MAX_CACHE_AGE = try_int(max_cache_age, 0)

        sickbeard.USE_NZBS = config.checkbox_to_value(use_nzbs)
        sickbeard.USE_TORRENTS = config.checkbox_to_value(use_torrents)

        sickbeard.NZB_METHOD = nzb_method
        sickbeard.TORRENT_METHOD = torrent_method
        sickbeard.USENET_RETENTION = try_int(usenet_retention, 500)

        sickbeard.IGNORE_WORDS = ignore_words if ignore_words else ''
        sickbeard.PREFERRED_WORDS = preferred_words if preferred_words else ''
        sickbeard.UNDESIRED_WORDS = undesired_words if undesired_words else ''
        sickbeard.TRACKERS_LIST = trackers_list if trackers_list else ''
        sickbeard.REQUIRE_WORDS = require_words if require_words else ''
        sickbeard.IGNORED_SUBS_LIST = ignored_subs_list if ignored_subs_list else ''
        sickbeard.IGNORE_UND_SUBS = config.checkbox_to_value(ignore_und_subs)

        sickbeard.RANDOMIZE_PROVIDERS = config.checkbox_to_value(randomize_providers)

        config.change_DOWNLOAD_PROPERS(download_propers)

        sickbeard.CHECK_PROPERS_INTERVAL = check_propers_interval

        sickbeard.ALLOW_HIGH_PRIORITY = config.checkbox_to_value(allow_high_priority)

        sickbeard.USE_FAILED_DOWNLOADS = config.checkbox_to_value(use_failed_downloads)
        sickbeard.DELETE_FAILED = config.checkbox_to_value(delete_failed)

        sickbeard.SAB_USERNAME = sab_username
        sickbeard.SAB_PASSWORD = sab_password
        sickbeard.SAB_APIKEY = sab_apikey.strip()
        sickbeard.SAB_CATEGORY = sab_category
        sickbeard.SAB_CATEGORY_BACKLOG = sab_category_backlog
        sickbeard.SAB_CATEGORY_ANIME = sab_category_anime
        sickbeard.SAB_CATEGORY_ANIME_BACKLOG = sab_category_anime_backlog
        sickbeard.SAB_HOST = config.clean_url(sab_host)
        sickbeard.SAB_FORCED = config.checkbox_to_value(sab_forced)

        sickbeard.NZBGET_USERNAME = nzbget_username
        sickbeard.NZBGET_PASSWORD = nzbget_password
        sickbeard.NZBGET_CATEGORY = nzbget_category
        sickbeard.NZBGET_CATEGORY_BACKLOG = nzbget_category_backlog
        sickbeard.NZBGET_CATEGORY_ANIME = nzbget_category_anime
        sickbeard.NZBGET_CATEGORY_ANIME_BACKLOG = nzbget_category_anime_backlog
        sickbeard.NZBGET_HOST = config.clean_host(nzbget_host)
        sickbeard.NZBGET_USE_HTTPS = config.checkbox_to_value(nzbget_use_https)
        sickbeard.NZBGET_PRIORITY = try_int(nzbget_priority, 100)

        sickbeard.TORRENT_USERNAME = torrent_username
        sickbeard.TORRENT_PASSWORD = torrent_password
        sickbeard.TORRENT_LABEL = torrent_label
        sickbeard.TORRENT_LABEL_ANIME = torrent_label_anime
        sickbeard.TORRENT_VERIFY_CERT = config.checkbox_to_value(torrent_verify_cert)
        sickbeard.TORRENT_PATH = torrent_path.rstrip('/\\')
        sickbeard.TORRENT_SEED_TIME = torrent_seed_time
        sickbeard.TORRENT_PAUSED = config.checkbox_to_value(torrent_paused)
        sickbeard.TORRENT_HIGH_BANDWIDTH = config.checkbox_to_value(torrent_high_bandwidth)
        sickbeard.TORRENT_HOST = config.clean_url(torrent_host)
        sickbeard.TORRENT_RPCURL = torrent_rpcurl
        sickbeard.TORRENT_AUTH_TYPE = torrent_auth_type

        sickbeard.save_config()

        if results:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                                   '<br>\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek(os.path.join, sickbeard.CONFIG_FILE))

        return self.redirect('/config/search/')
