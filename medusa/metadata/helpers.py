# coding=utf-8

import logging

from medusa import app
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


def needs_metadata(episode):
    """Check if an episode needs metadata.

    :param episode: Episode object.
    :return: True if needed, None otherwise
    """
    if not episode.is_location_valid():
        return

    for provider in app.metadata_provider_dict.values():
        if provider.episode_metadata and not provider.has_episode_metadata(episode):
            return True

        if provider.episode_thumbnails and not provider.has_episode_thumb(episode):
            return True
