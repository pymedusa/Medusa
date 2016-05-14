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


@route('/changes(/?.*)')
class HomeChangeLog(Home):
    def __init__(self, *args, **kwargs):
        super(HomeChangeLog, self).__init__(*args, **kwargs)

    def index(self):
        try:
            changes = helpers.getURL('https://cdn.pymedusa.com/sickrage-news/CHANGES.md', session=helpers.make_session(), returns='text')
        except Exception:
            logger.log(u'Could not load changes from repo, giving a link!', logger.DEBUG)
            changes = 'Could not load changes from the repo. [Click here for CHANGES.md](https://cdn.pymedusa.com/sickrage-news/CHANGES.md)'

        t = PageTemplate(rh=self, filename="markdown.mako")
        data = markdown2.markdown(changes if changes else "The was a problem connecting to github, please refresh and try again", extras=['header-ids'])

        return t.render(title="Changelog", header="Changelog", topmenu="system", data=data, controller="changes", action="index")
