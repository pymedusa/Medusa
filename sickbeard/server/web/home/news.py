# coding=utf-8

import ast
import datetime
import os
import re
import time

import adba
from libtrakt import TraktAPI
from libtrakt.exceptions import traktException
import markdown2
from requests.compat import unquote_plus, quote_plus
from tornado.routes import route

import sickbeard
from sickbeard import (
    classes, clients, config, db, helpers, logger,
    notifiers, processTV, sab, search_queue,
    subtitles, ui, show_name_helpers
)
from sickbeard.blackandwhitelist import BlackAndWhiteList, short_group_names
from sickbeard.common import (
    cpu_presets, Overview, Quality, statusStrings,
    UNAIRED, IGNORED, WANTED, FAILED, SKIPPED
)
from sickbeard.helpers import get_showname_from_indexer
from sickbeard.imdbPopular import imdb_popular
from sickbeard.indexers.indexer_exceptions import indexer_exception
from sickbeard.manual_search import (
    collectEpisodesFromSearchThread, get_provider_cache_results, getEpisode, update_finished_search_queue_item,
    SEARCH_STATUS_FINISHED, SEARCH_STATUS_SEARCHING, SEARCH_STATUS_QUEUED,
)
from sickbeard.scene_numbering import (
    get_scene_absolute_numbering, get_scene_absolute_numbering_for_show,
    get_scene_numbering, get_scene_numbering_for_show,
    get_xem_absolute_numbering_for_show, get_xem_numbering_for_show,
    set_scene_numbering,
)
from sickbeard.versionChecker import CheckVersion

from sickrage.helper.common import (
    sanitize_filename, try_int, enabled_providers,
)
from sickrage.helper.encoding import ek, ss
from sickrage.helper.exceptions import (
    ex,
    CantRefreshShowException,
    CantUpdateShowException,
    MultipleShowObjectsException,
    NoNFOException,
    ShowDirectoryNotFoundException,
)
from sickrage.show.Show import Show
from sickrage.system.Restart import Restart
from sickrage.system.Shutdown import Shutdown
from sickbeard.tv import TVEpisode
from sickbeard.server.web.core import WebRoot, PageTemplate

# Conditional imports
try:
    import json
except ImportError:
    import simplejson as json

from sickbeard.server.web.home.base import Home


@route('/news(/?.*)')
class HomeNews(Home):
    def __init__(self, *args, **kwargs):
        super(HomeNews, self).__init__(*args, **kwargs)

    def index(self):
        try:
            news = sickbeard.versionCheckScheduler.action.check_for_new_news(force=True)
        except Exception:
            logger.log(u'Could not load news from repo, giving a link!', logger.DEBUG)
            news = 'Could not load news from the repo. [Click here for news.md](' + sickbeard.NEWS_URL + ')'

        sickbeard.NEWS_LAST_READ = sickbeard.NEWS_LATEST
        sickbeard.NEWS_UNREAD = 0
        sickbeard.save_config()

        t = PageTemplate(rh=self, filename="markdown.mako")
        data = markdown2.markdown(news if news else "The was a problem connecting to github, please refresh and try again", extras=['header-ids'])

        return t.render(title="News", header="News", topmenu="system", data=data, controller="news", action="index")
