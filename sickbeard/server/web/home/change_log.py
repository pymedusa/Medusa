# coding=utf-8

from __future__ import unicode_literals

import markdown2
from tornado.routes import route
from sickbeard import (
    helpers, logger,
)
from sickbeard.server.web.core import PageTemplate
from sickbeard.server.web.home.handler import Home


@route('/changes(/?.*)')
class HomeChangeLog(Home):
    def __init__(self, *args, **kwargs):
        super(HomeChangeLog, self).__init__(*args, **kwargs)

    def index(self):
        try:
            changes = helpers.getURL('https://cdn.pymedusa.com/sickrage-news/CHANGES.md', session=helpers.make_session(), returns='text')
        except Exception:
            logger.log('Could not load changes from repo, giving a link!', logger.DEBUG)
            changes = 'Could not load changes from the repo. [Click here for CHANGES.md](https://cdn.pymedusa.com/sickrage-news/CHANGES.md)'

        t = PageTemplate(rh=self, filename='markdown.mako')
        data = markdown2.markdown(changes if changes else 'The was a problem connecting to github, please refresh and try again', extras=['header-ids'])

        return t.render(title='Changelog', header='Changelog', topmenu='system', data=data, controller='changes', action='index')
