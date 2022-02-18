# coding=utf-8

from __future__ import unicode_literals

import markdown2

from medusa import app, logger
from medusa.server.web.core import PageTemplate
from medusa.server.web.home.handler import Home
from medusa.session.core import MedusaSafeSession

from tornroutes import route


@route('/changes(/?.*)')
class HomeChangeLog(Home):
    session = MedusaSafeSession()

    def __init__(self, *args, **kwargs):
        super(HomeChangeLog, self).__init__(*args, **kwargs)

    def index(self):
        # TODO: SESSION: Check if this needs some more explicit exception handling.
        changes = HomeChangeLog.session.get_text(app.CHANGES_URL)

        if not changes:
            logger.log('Could not load changes from repo, giving a link!', logger.DEBUG)
            changes = 'Could not load changes from the repo. [Click here for CHANGES.md]({url})'.format(url=app.CHANGES_URL)

        t = PageTemplate(rh=self, filename='markdown.mako')
        data = markdown2.markdown(
            changes if changes else 'The was a problem connecting to github, please refresh and try again', extras=['header-ids']
        )

        return t.render(title='Changelog', header='Changelog', data=data, controller='changes', action='index')
