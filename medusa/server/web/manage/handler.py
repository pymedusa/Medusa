# coding=utf-8

from __future__ import unicode_literals

import re

from medusa import (
    app,
    helpers,
)
from medusa.server.web.core import PageTemplate, WebRoot
from medusa.server.web.home import Home

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

    def episodeStatuses(self, status=None):
        """
        Serve manageEpisodeStatus page.

        [Converted to VueRouter].
        """
        return PageTemplate(rh=self, filename='index.mako').render()

    def changeIndexer(self):
        """
        Render manage/changeIndexer page.

        [Converted to VueRouter]
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
