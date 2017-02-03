# -*- coding: utf-8 -*-
"""TVEpisode refiner."""
from __future__ import unicode_literals

import logging
import re

from subliminal.video import Episode
from ..common import Quality

logger = logging.getLogger(__name__)

SHOW_MAPPING = {
    'series_tvdb_id': 'tvdb_id',
    'series_imdb_id': 'imdb_id',
    'year': 'start_year'
}

EPISODE_MAPPING = {
    'tvdb_id': 'tvdb_id',
    'size': 'file_size',
    'title': 'name',
}

ADDITIONAL_MAPPING = {
    'season': 'season',
    'episode': 'episode',
    'release_group': 'release_group',
}

series_re = re.compile(r'^(?P<series>.*?)(?: \((?:(?P<year>\d{4})|(?P<country>[A-Z]{2}))\))?$')


def refine(video, tv_episode=None, **kwargs):
    """Refine a video by using TVEpisode information.

    :param video: the video to refine.
    :type video: Episode
    :param tv_episode: the TVEpisode to be used.
    :type tv_episode: medusa.tv.TVEpisode
    :param kwargs:
    """
    if video.series_tvdb_id and video.tvdb_id:
        logger.debug('No need to refine with TVEpisode')
        return

    if not tv_episode:
        logger.debug('No TVEpisode to be used to refine')
        return

    if not isinstance(video, Episode):
        logger.debug('Video {name} is not an episode. Skipping refiner...', name=video.name)
        return

    if tv_episode.show:
        logger.debug('Refining using Series information.')
        series, year, _ = series_re.match(tv_episode.show.name).groups()
        enrich({'series': series, 'year': int(year) if year else None}, video)
        enrich(SHOW_MAPPING, video, tv_episode.show)

    logger.debug('Refining using TVEpisode information.')
    enrich(EPISODE_MAPPING, video, tv_episode)
    enrich(ADDITIONAL_MAPPING, video, tv_episode, overwrite=False)
    guess = Quality.to_guessit(tv_episode.status)
    enrich({'resolution': guess.get('screen_size'), 'format': guess.get('format')}, video, overwrite=False)


def enrich(attributes, target, source=None, overwrite=True):
    """Copy attributes from source to target.

    :param attributes: the attributes mapping
    :type attributes: dict(str -> str)
    :param target: the target object
    :param source: the source object. If None, the value in attributes dict will be used as new_value
    :param overwrite: if source field should be overwritten if not already set
    :type overwrite: bool
    """
    for key, value in attributes.items():
        old_value = getattr(target, key)
        if old_value and old_value != '' and not overwrite:
            continue

        new_value = getattr(source, value) if source else value

        if new_value and old_value != new_value:
            setattr(target, key, new_value)
            logger.debug('Attribute {key} changed from {old} to {new}', key=key, old=old_value, new=new_value)
