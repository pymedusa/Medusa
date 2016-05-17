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


@route('/home/postprocess(/?.*)')
class HomePostProcess(Home):
    def __init__(self, *args, **kwargs):
        super(HomePostProcess, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename="home_postprocess.mako")
        return t.render(title='Post Processing', header='Post Processing', topmenu='home', controller="home", action="postProcess")

    # TODO: PR to NZBtoMedia so that we can rename dir to proc_dir, and type to proc_type.
    # Using names of builtins as var names is bad
    # pylint: disable=redefined-builtin
    def processEpisode(self, dir=None, nzbName=None, jobName=None, quiet=None, process_method=None, force=None,
                       is_priority=None, delete_on="0", failed="0", type="auto", *args, **kwargs):

        def argToBool(argument):
            if isinstance(argument, basestring):
                _arg = argument.strip().lower()
            else:
                _arg = argument

            if _arg in ['1', 'on', 'true', True]:
                return True
            elif _arg in ['0', 'off', 'false', False]:
                return False

            return argument

        if not dir:
            return self.redirect("/home/postprocess/")
        else:
            nzbName = ss(nzbName) if nzbName else nzbName

            result = processTV.processDir(
                ss(dir), nzbName, process_method=process_method, force=argToBool(force),
                is_priority=argToBool(is_priority), delete_on=argToBool(delete_on), failed=argToBool(failed), proc_type=type
            )

            if quiet is not None and int(quiet) == 1:
                return result

            result = result.replace("\n", "<br>\n")
            return self._genericMessage("Postprocessing results", result)
