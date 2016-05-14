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


@route('/IRC(/?.*)')
class HomeIRC(Home):
    def __init__(self, *args, **kwargs):
        super(HomeIRC, self).__init__(*args, **kwargs)

    def index(self):

        t = PageTemplate(rh=self, filename="IRC.mako")
        return t.render(topmenu="system", header="IRC", title="IRC", controller="IRC", action="index")
