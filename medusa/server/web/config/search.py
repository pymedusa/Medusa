# coding=utf-8

"""Configure Searches."""

from __future__ import unicode_literals

import os

from medusa import (
    app,
    config,
    logger,
    ui,
)
from medusa.helper.common import try_int
from medusa.server.web.config.handler import Config
from medusa.server.web.core import PageTemplate

from tornroutes import route


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

        return t.render(submenu=self.ConfigMenu(),
                        controller='config', action='search')

    def saveSearch(self, use_nzbs=None, use_torrents=None, nzb_dir=None, sab_username=None, sab_password=None,
                   sab_apikey=None, sab_category=None, sab_category_anime=None, sab_category_backlog=None,
                   sab_category_anime_backlog=None, sab_host=None, nzbget_username=None, nzbget_password=None,
                   nzbget_category=None, nzbget_category_backlog=None, nzbget_category_anime=None,
                   nzbget_category_anime_backlog=None, nzbget_priority=None, nzbget_host=None,
                   nzbget_use_https=None, backlog_days=None, backlog_frequency=None, dailysearch_frequency=None,
                   nzb_method=None, torrent_method=None, usenet_retention=None, download_propers=None,
                   check_propers_interval=None, allow_high_priority=None, sab_forced=None, remove_from_client=None,
                   randomize_providers=None, use_failed_downloads=None, delete_failed=None, propers_search_days=None,
                   torrent_dir=None, torrent_username=None, torrent_password=None, torrent_host=None,
                   torrent_label=None, torrent_label_anime=None, torrent_path=None, torrent_verify_cert=None,
                   torrent_seed_time=None, torrent_paused=None, torrent_high_bandwidth=None,
                   torrent_rpcurl=None, torrent_auth_type=None, ignore_words=None, torrent_checker_frequency=None,
                   preferred_words=None, undesired_words=None, trackers_list=None, require_words=None,
                   ignored_subs_list=None, ignore_und_subs=None, cache_trimming=None, max_cache_age=None,
                   torrent_seed_location=None):
        """
        Save Search related settings
        """

        results = []

        if not config.change_NZB_DIR(nzb_dir):
            results += ['Unable to create directory {dir}, dir not changed.'.format(dir=os.path.normpath(nzb_dir))]

        if not config.change_TORRENT_DIR(torrent_dir):
            results += ['Unable to create directory {dir}, dir not changed.'.format(dir=os.path.normpath(torrent_dir))]

        config.change_DAILYSEARCH_FREQUENCY(dailysearch_frequency)
        config.change_TORRENT_CHECKER_FREQUENCY(torrent_checker_frequency)
        config.change_BACKLOG_FREQUENCY(backlog_frequency)
        app.BACKLOG_DAYS = try_int(backlog_days, 7)

        app.CACHE_TRIMMING = config.checkbox_to_value(cache_trimming)
        app.MAX_CACHE_AGE = try_int(max_cache_age, 0)

        app.USE_NZBS = config.checkbox_to_value(use_nzbs)
        app.USE_TORRENTS = config.checkbox_to_value(use_torrents)

        app.NZB_METHOD = nzb_method
        app.TORRENT_METHOD = torrent_method
        app.USENET_RETENTION = try_int(usenet_retention, 500)

        if app.TORRENT_METHOD != 'blackhole' and app.TORRENT_METHOD in ('transmission', 'deluge', 'deluged'):
            config.change_remove_from_client(remove_from_client)
        else:
            config.change_remove_from_client('false')

        app.IGNORE_WORDS = [_.strip() for _ in ignore_words.split(',')] if ignore_words else []
        app.PREFERRED_WORDS = [_.strip() for _ in preferred_words.split(',')] if preferred_words else []
        app.UNDESIRED_WORDS = [_.strip() for _ in undesired_words.split(',')] if undesired_words else []
        app.TRACKERS_LIST = [_.strip() for _ in trackers_list.split(',')] if trackers_list else []
        app.REQUIRE_WORDS = [_.strip() for _ in require_words.split(',')] if require_words else []
        app.IGNORED_SUBS_LIST = [_.strip() for _ in ignored_subs_list.split(',')] if ignored_subs_list else []
        app.IGNORE_UND_SUBS = config.checkbox_to_value(ignore_und_subs)

        app.RANDOMIZE_PROVIDERS = config.checkbox_to_value(randomize_providers)

        config.change_DOWNLOAD_PROPERS(download_propers)
        app.PROPERS_SEARCH_DAYS = try_int(propers_search_days, 2)
        config.change_PROPERS_FREQUENCY(check_propers_interval)

        app.ALLOW_HIGH_PRIORITY = config.checkbox_to_value(allow_high_priority)

        app.USE_FAILED_DOWNLOADS = config.checkbox_to_value(use_failed_downloads)
        app.DELETE_FAILED = config.checkbox_to_value(delete_failed)

        app.SAB_USERNAME = sab_username
        app.SAB_PASSWORD = sab_password
        app.SAB_APIKEY = sab_apikey.strip()
        app.SAB_CATEGORY = sab_category
        app.SAB_CATEGORY_BACKLOG = sab_category_backlog
        app.SAB_CATEGORY_ANIME = sab_category_anime
        app.SAB_CATEGORY_ANIME_BACKLOG = sab_category_anime_backlog
        app.SAB_HOST = config.clean_url(sab_host)
        app.SAB_FORCED = config.checkbox_to_value(sab_forced)

        app.NZBGET_USERNAME = nzbget_username
        app.NZBGET_PASSWORD = nzbget_password
        app.NZBGET_CATEGORY = nzbget_category
        app.NZBGET_CATEGORY_BACKLOG = nzbget_category_backlog
        app.NZBGET_CATEGORY_ANIME = nzbget_category_anime
        app.NZBGET_CATEGORY_ANIME_BACKLOG = nzbget_category_anime_backlog
        app.NZBGET_HOST = config.clean_host(nzbget_host)
        app.NZBGET_USE_HTTPS = config.checkbox_to_value(nzbget_use_https)
        app.NZBGET_PRIORITY = try_int(nzbget_priority, 100)

        app.TORRENT_USERNAME = torrent_username
        app.TORRENT_PASSWORD = torrent_password
        app.TORRENT_LABEL = torrent_label
        app.TORRENT_LABEL_ANIME = torrent_label_anime
        app.TORRENT_VERIFY_CERT = config.checkbox_to_value(torrent_verify_cert)
        app.TORRENT_PATH = torrent_path.rstrip('/\\')
        app.TORRENT_SEED_TIME = torrent_seed_time
        app.TORRENT_PAUSED = config.checkbox_to_value(torrent_paused)
        app.TORRENT_HIGH_BANDWIDTH = config.checkbox_to_value(torrent_high_bandwidth)
        app.TORRENT_HOST = config.clean_url(torrent_host)
        app.TORRENT_RPCURL = torrent_rpcurl
        app.TORRENT_AUTH_TYPE = torrent_auth_type
        app.TORRENT_SEED_LOCATION = torrent_seed_location.rstrip('/\\')

        app.instance.save_config()

        if results:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                                   '<br>\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', os.path.join(app.CONFIG_FILE))

        return self.redirect('/config/search/')
