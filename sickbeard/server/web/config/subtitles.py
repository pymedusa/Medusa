# coding=utf-8

"""
Configure Subtitle searching
"""

from __future__ import unicode_literals

import os
from tornado.routes import route
import sickbeard
from sickbeard import (
    config, logger, subtitles, ui,
)
from sickrage.helper.encoding import ek
from sickbeard.server.web.core import PageTemplate
from sickbeard.server.web.config.handler import Config


@route('/config/subtitles(/?.*)')
class ConfigSubtitles(Config):
    """
    Handler for Subtitle Search configuration
    """
    def __init__(self, *args, **kwargs):
        super(ConfigSubtitles, self).__init__(*args, **kwargs)

    def index(self):
        """
        Render the Subtitle Search configuration page
        """
        t = PageTemplate(rh=self, filename='config_subtitles.mako')

        return t.render(submenu=self.ConfigMenu(), title='Config - Subtitles',
                        header='Subtitles', topmenu='config',
                        controller='config', action='subtitles')

    def saveSubtitles(self, use_subtitles=None, subtitles_plugins=None, subtitles_languages=None, subtitles_dir=None, subtitles_perfect_match=None,
                      service_order=None, subtitles_history=None, subtitles_finder_frequency=None,
                      subtitles_multi=None, embedded_subtitles_all=None, subtitles_extra_scripts=None, subtitles_pre_scripts=None, subtitles_hearing_impaired=None,
                      addic7ed_user=None, addic7ed_pass=None, itasa_user=None, itasa_pass=None, legendastv_user=None, legendastv_pass=None, opensubtitles_user=None, opensubtitles_pass=None,
                      subtitles_download_in_pp=None, subtitles_keep_only_wanted=None):
        """
        Save Subtitle Search related settings
        """
        results = []

        config.change_SUBTITLES_FINDER_FREQUENCY(subtitles_finder_frequency)
        config.change_USE_SUBTITLES(use_subtitles)

        sickbeard.SUBTITLES_LANGUAGES = [code.strip() for code in subtitles_languages.split(',') if code.strip() in subtitles.subtitle_code_filter()] if subtitles_languages else []
        sickbeard.SUBTITLES_DIR = subtitles_dir
        sickbeard.SUBTITLES_PERFECT_MATCH = config.checkbox_to_value(subtitles_perfect_match)
        sickbeard.SUBTITLES_HISTORY = config.checkbox_to_value(subtitles_history)
        sickbeard.EMBEDDED_SUBTITLES_ALL = config.checkbox_to_value(embedded_subtitles_all)
        sickbeard.SUBTITLES_HEARING_IMPAIRED = config.checkbox_to_value(subtitles_hearing_impaired)
        sickbeard.SUBTITLES_MULTI = 1 if len(sickbeard.SUBTITLES_LANGUAGES) > 1 else config.checkbox_to_value(subtitles_multi)
        sickbeard.SUBTITLES_DOWNLOAD_IN_PP = config.checkbox_to_value(subtitles_download_in_pp)
        sickbeard.SUBTITLES_KEEP_ONLY_WANTED = config.checkbox_to_value(subtitles_keep_only_wanted)
        sickbeard.SUBTITLES_EXTRA_SCRIPTS = [x.strip() for x in subtitles_extra_scripts.split('|') if x.strip()]
        sickbeard.SUBTITLES_PRE_SCRIPTS = [x.strip() for x in subtitles_pre_scripts.split('|') if x.strip()]

        # Subtitles services
        services_str_list = service_order.split()
        subtitles_services_list = []
        subtitles_services_enabled = []
        for curServiceStr in services_str_list:
            cur_service, cur_enabled = curServiceStr.split(':')
            subtitles_services_list.append(cur_service)
            subtitles_services_enabled.append(int(cur_enabled))

        sickbeard.SUBTITLES_SERVICES_LIST = subtitles_services_list
        sickbeard.SUBTITLES_SERVICES_ENABLED = subtitles_services_enabled

        sickbeard.ADDIC7ED_USER = addic7ed_user or ''
        sickbeard.ADDIC7ED_PASS = addic7ed_pass or ''
        sickbeard.ITASA_USER = itasa_user or ''
        sickbeard.ITASA_PASS = itasa_pass or ''
        sickbeard.LEGENDASTV_USER = legendastv_user or ''
        sickbeard.LEGENDASTV_PASS = legendastv_pass or ''
        sickbeard.OPENSUBTITLES_USER = opensubtitles_user or ''
        sickbeard.OPENSUBTITLES_PASS = opensubtitles_pass or ''

        sickbeard.save_config()
        # Reset provider pool so next time we use the newest settings
        subtitles.get_provider_pool.invalidate()

        if results:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                                   '<br>\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek(os.path.join, sickbeard.CONFIG_FILE))

        return self.redirect('/config/subtitles/')
