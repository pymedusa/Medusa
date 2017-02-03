# coding=utf-8

from __future__ import unicode_literals

import markdown2
from tornroutes import route
from .handler import Home
from ..core import PageTemplate
from .... import app, logger
from ....session.core import Session


@route('/changes(/?.*)')
class HomeChangeLog(Home):
    def __init__(self, *args, **kwargs):
        super(HomeChangeLog, self).__init__(*args, **kwargs)

    def index(self):
        try:
            # TODO: SESSION: Check if this needs some more explicit exception handling.
            changes = Session().get(app.CHANGES_URL).text
        except Exception:
            logger.log('Could not load changes from repo, giving a link!', logger.DEBUG)
            changes = 'Could not load changes from the repo. [Click here for CHANGES.md]({url})'.format(url=app.CHANGES_URL)

        t = PageTemplate(rh=self, filename='markdown.mako')
        data = markdown2.markdown(changes if changes else 'The was a problem connecting to github, please refresh and try again', extras=['header-ids'])

        return t.render(title='Changelog', header='Changelog', topmenu='system', data=data, controller='changes', action='index')
