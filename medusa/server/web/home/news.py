# coding=utf-8

from __future__ import unicode_literals

import markdown2
from tornroutes import route
from .handler import Home
from ..core import PageTemplate
from .... import app, logger


@route('/news(/?.*)')
class HomeNews(Home):
    def __init__(self, *args, **kwargs):
        super(HomeNews, self).__init__(*args, **kwargs)

    def index(self):
        try:
            news = app.version_check_scheduler.action.check_for_new_news(force=True)
        except Exception:
            logger.log('Could not load news from repo, giving a link!', logger.DEBUG)
            news = 'Could not load news from the repo. [Click here for news.md]({url})'.format(url=app.NEWS_URL)

        app.NEWS_LAST_READ = app.NEWS_LATEST
        app.NEWS_UNREAD = 0
        app.instance.save_config()

        t = PageTemplate(rh=self, filename='markdown.mako')
        data = markdown2.markdown(news if news else 'The was a problem connecting to GitHub, please refresh and try again', extras=['header-ids'])

        return t.render(title='News', header='News', topmenu='system', data=data, controller='news', action='index')
