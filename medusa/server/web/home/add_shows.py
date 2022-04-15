# coding=utf-8

from __future__ import unicode_literals

import logging
from json.decoder import JSONDecodeError

from medusa import app, ui
from medusa.helpers import get_showname_from_indexer
from medusa.helpers.trakt import get_trakt_user
from medusa.indexers.config import INDEXER_TVDBV2
from medusa.logger.adapters.style import BraceAdapter
from medusa.server.web.core import PageTemplate
from medusa.server.web.home.handler import Home

from requests.exceptions import RequestException

from tornroutes import route

from trakt.errors import TraktException


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


@route('/addShows(/?.*)')
class HomeAddShows(Home):
    def __init__(self, *args, **kwargs):
        super(HomeAddShows, self).__init__(*args, **kwargs)

    def index(self):
        """
        Render the addShows page.

        [Converted to VueRouter]
        """
        return PageTemplate(rh=self, filename='index.mako').render()

    def newShow(self):
        """
        Render the newShow page.

        [Converted to VueRouter]
        """
        return PageTemplate(rh=self, filename='index.mako').render()

    def existingShows(self):
        """
        Render the add existing shows page.

        [Converted to VueRouter]
        """
        return PageTemplate(rh=self, filename='index.mako').render()

    def recommended(self):
        """
        Render template for route /home/addShows/recommended.

        [Converted to VueRouter]
        """
        return PageTemplate(rh=self, filename='index.mako').render()

    def addShowToBlacklist(self, seriesid):
        # URL parameters
        data = {'shows': [{'ids': {'tvdb': seriesid}}]}

        show_name = get_showname_from_indexer(INDEXER_TVDBV2, seriesid)
        try:
            trakt_user = get_trakt_user()
            blacklist = trakt_user.get_list(app.TRAKT_BLACKLIST_NAME)

            if not blacklist:
                ui.notifications.error(
                    'Warning',
                    'Could not find blacklist {blacklist} for user {user}.'.format(
                        blacklist=app.TRAKT_BLACKLIST_NAME, user=trakt_user.username
                    )
                )
                log.warning(
                    'Could not find blacklist {blacklist} for user {user}.',
                    {'blacklist': app.TRAKT_BLACKLIST_NAME, 'user': trakt_user.username}
                )

            # Add the show to the blacklist.
            blacklist.add_items(data)

            ui.notifications.message('Success!',
                                     "Added show '{0}' to blacklist".format(show_name))
        except (TraktException, RequestException, JSONDecodeError) as error:
            ui.notifications.error('Error!',
                                   "Unable to add show '{0}' to blacklist. Check logs.".format(show_name))
            log.warning("Error while adding show '{name}' to trakt blacklist: {error}",
                        {'name': show_name, 'error': error})

        except Exception as error:
            log.exception('Error trying to add show to blacklist, error: {error}', {'error': error})
