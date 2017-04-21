# coding=utf-8

import logging

from medusa import helpers
from medusa.logger.adapters.style import BraceAdapter


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

meta_session = helpers.make_session()


def getShowImage(url, imgNum=None):
    if url is None:
        return None

    # if they provided a fanart number try to use it instead
    if imgNum is not None:
        tempURL = url.split('-')[0] + '-' + str(imgNum) + '.jpg'
    else:
        tempURL = url

    log.debug(u'Fetching image from {url}', {'url': tempURL})

    image_data = helpers.get_url(tempURL, session=meta_session, returns='content')
    if image_data is None:
        log.warning(u'There was an error trying to retrieve the image, aborting')
        return

    return image_data
