# coding=utf-8

from __future__ import unicode_literals

import logging
import os
from builtins import object

from medusa import app
from medusa.logger.adapters.style import BraceAdapter

import requests
from requests.exceptions import RequestException

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    def notify_snatch(self, title, message):
        pass

    def notify_download(self, ep_obj):
        pass

    def notify_subtitle_download(self, ep_obj, lang):
        pass

    def notify_git_update(self, new_version):
        pass

    def notify_login(self, ipaddress=''):
        pass

    def update_library(self, ep_obj):

        # Values from config

        if not app.USE_PYTIVO:
            return False

        host = app.PYTIVO_HOST
        shareName = app.PYTIVO_SHARE_NAME
        tsn = app.PYTIVO_TIVO_NAME

        # There are two more values required, the container and file.
        #
        # container: The share name, show name and season
        #
        # file: The file name
        #
        # Some slicing and dicing of variables is required to get at these values.
        #
        # There might be better ways to arrive at the values, but this is the best I have been able to
        # come up with.
        #

        # Calculated values
        showPath = ep_obj.series.location
        showName = ep_obj.series.name
        rootShowAndSeason = os.path.dirname(ep_obj.location)
        absPath = ep_obj.location

        # Some show names have colons in them which are illegal in a path location, so strip them out.
        # (Are there other characters?)
        showName = showName.replace(':', '')

        root = showPath.replace(showName, '')
        showAndSeason = rootShowAndSeason.replace(root, '')

        container = shareName + '/' + showAndSeason
        filename = '/' + absPath.replace(root, '')

        # Finally create the url and make request
        request_url = 'http://{host}/TiVoConnect'.format(host=host)
        params = {'Command': 'Push', 'Container': container, 'File': filename, 'tsn': tsn}

        log.debug(u'pyTivo notification: Requesting {0}', request_url)

        try:
            r = requests.get(request_url, params=params)
            r.raise_for_status()
        except RequestException as error:
            if hasattr(error, 'response'):
                if hasattr(error.response, 'reason'):
                    log.error(u'pyTivo notification: Error, failed to reach a server - {0}', error.response.reason)
                elif hasattr(error.response, 'status_code'):
                    log.error(u'pyTivo notification: Error, the server could not fulfill the request - {0}', error.response.status_code)
                return False
        except Exception as error:
            log.error(u'PYTIVO: Unknown exception: {0!r}', error)
            return False
        else:
            log.info(u'pyTivo notification: Successfully requested transfer of file')
            return True
