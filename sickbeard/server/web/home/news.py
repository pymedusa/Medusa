# coding=utf-8

from __future__ import unicode_literals

import markdown2
from tornado.routes import route
import sickbeard
from sickbeard import logger
from sickbeard.server.web.core import PageTemplate
from sickbeard.server.web.home.handler import Home


@route('/news(/?.*)')
class HomeNews(Home):
    def __init__(self, *args, **kwargs):
        super(HomeNews, self).__init__(*args, **kwargs)

    def index(self):
        try:
            news = sickbeard.versionCheckScheduler.action.check_for_new_news(force=True)
        except Exception:
            logger.log('Could not load news from repo, giving a link!', logger.DEBUG)
            news = 'Could not load news from the repo. [Click here for news.md]({url})'.format(url=sickbeard.NEWS_URL)

        sickbeard.NEWS_LAST_READ = sickbeard.NEWS_LATEST
        sickbeard.NEWS_UNREAD = 0
        sickbeard.save_config()

        t = PageTemplate(rh=self, filename='markdown.mako')
        data = markdown2.markdown(news if news else 'The was a problem connecting to github, please refresh and try again', extras=['header-ids'])

        return t.render(title='News', header='News', topmenu='system', data=data, controller='news', action='index')
