# coding=utf-8

import logging

from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSafeSession


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

meta_session = MedusaSafeSession()


def getShowImage(url, imgNum=None):
    if url is None:
        return None

    # if they provided a fanart number try to use it instead
    if imgNum is not None:
        tempURL = url.split('-')[0] + '-' + str(imgNum) + '.jpg'
    else:
        tempURL = url

    log.debug(u'Fetching image from {url}', {'url': tempURL})

    # TODO: SESSION: Check if this needs exception handling.
    image_data = meta_session.get(tempURL)
    if not image_data:
        log.warning(u'There was an error trying to retrieve the image, aborting')
        return

    return image_data.content
