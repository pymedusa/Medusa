# coding=utf-8

from __future__ import unicode_literals

from medusa.server.web.core import PageTemplate
from medusa.server.web.manage.handler import Manage

from tornroutes import route


@route('/manage/manageSearches(/?.*)')
class ManageSearches(Manage):
    def __init__(self, *args, **kwargs):
        super(ManageSearches, self).__init__(*args, **kwargs)

    def index(self):
        """
        Render the home page.

        [Converted to VueRouter]
        """
        t = PageTemplate(rh=self, filename='index.mako')
        return t.render()
