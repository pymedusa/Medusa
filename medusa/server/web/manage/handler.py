# coding=utf-8

from __future__ import unicode_literals

import datetime
import json
import os
import re

from medusa import (
    app,
    db,
    helpers,
    image_cache,
    logger,
    network_timezones,
    sbdatetime,
    subtitles,
    ui,
)
from medusa.common import (
    DOWNLOADED,
    Overview,
    SNATCHED,
    SNATCHED_BEST,
    SNATCHED_PROPER,
)
from medusa.helper.common import (
    episode_num,
    try_int,
)
from medusa.helper.exceptions import (
    CantRefreshShowException,
    CantUpdateShowException,
)
from medusa.helpers import is_media_file
from medusa.indexers.utils import indexer_id_to_name, indexer_name_to_id
from medusa.network_timezones import app_timezone
from medusa.post_processor import PostProcessor
from medusa.server.web.core import PageTemplate, WebRoot
from medusa.server.web.home import Home
from medusa.show.show import Show
from medusa.tv import Episode, Series
from medusa.tv.series import SeriesIdentifier

from tornroutes import route


@route('/manage(/?.*)')
class Manage(Home, WebRoot):
    def __init__(self, *args, **kwargs):
        super(Manage, self).__init__(*args, **kwargs)

    def index(self):
        """
        Route to the manage-mass-update.vue component.
        [Converted to VueRouter]
        """
        t = PageTemplate(rh=self, filename='index.mako')
        return t.render()

    def episodeStatuses(self):
        """
        Serve manageEpisodeStatus page.

        [Converted to VueRouter].
        """
        return PageTemplate(rh=self, filename='index.mako').render()

    def subtitleMissed(self, whichSubs=None):
        """
        Serve manageEpisodeStatus page.

        [Converted to VueRouter].
        """
        return PageTemplate(rh=self, filename='index.mako').render()

    def backlogOverview(self):
        """
        Serve the backlogOverview page.

        [Converted to VueRouter]
        """
        return PageTemplate(rh=self, filename='index.mako').render()

    def manageTorrents(self):
        if re.search('localhost', app.TORRENT_HOST):

            if app.LOCALHOST_IP == '':
                webui_url = re.sub('localhost', helpers.get_lan_ip(), app.TORRENT_HOST)
            else:
                webui_url = re.sub('localhost', app.LOCALHOST_IP, app.TORRENT_HOST)
        else:
            webui_url = app.TORRENT_HOST

        if app.TORRENT_METHOD == 'utorrent':
            webui_url = '/'.join(s.strip('/') for s in (webui_url, 'gui/'))
        if app.TORRENT_METHOD == 'downloadstation':
            if helpers.check_url('{url}download/'.format(url=webui_url)):
                webui_url += 'download/'
            else:
                webui_url = 'https://github.com/pymedusa/Medusa/wiki/Download-Station'

        return self.redirect(webui_url)

    def failedDownloads(self):
        """
        Serve the backlogOverview page.

        [Converted to VueRouter]
        """
        return PageTemplate(rh=self, filename='index.mako').render()
