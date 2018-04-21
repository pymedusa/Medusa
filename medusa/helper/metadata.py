# coding=utf-8

from __future__ import unicode_literals

import logging
from builtins import str

from medusa import app
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSafeSession

from six import itervalues

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

meta_session = MedusaSafeSession()


def get_image(url, img_no=None):
    if url is None:
        return None

    # if they provided a fanart number try to use it instead
    if img_no is not None:
        temp_url = url.split('-')[0] + '-' + str(img_no) + '.jpg'
    else:
        temp_url = url

    log.debug(u'Fetching image from {url}', {'url': temp_url})

    # TODO: SESSION: Check if this needs exception handling.
    image_data = meta_session.get(temp_url)
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

    for provider in itervalues(app.metadata_provider_dict):
        if provider.episode_metadata and not provider.has_episode_metadata(episode):
            return True

        if provider.episode_thumbnails and not provider.has_episode_thumb(episode):
            return True
