# -*- coding: utf-8 -*-
"""Release refiner."""
from __future__ import unicode_literals

import logging
import os

from guessit import guessit

from medusa.logger.adapters.style import BraceAdapter

from six import viewitems

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

MOVIE_ATTRIBUTES = {
    'title': 'title',
    'year': 'year',
    'source': 'source',
    'release_group': 'release_group',
    'resolution': 'screen_size',
    'video_codec': 'video_codec',
    'audio_codec': 'audio_codec',
}
EPISODE_ATTRIBUTES = {
    'series': 'title',
    'season': 'season',
    'episode': 'episode',
    'title': 'episode_title',
    'year': 'year',
    'source': 'source',
    'release_group': 'release_group',
    'resolution': 'screen_size',
    'video_codec': 'video_codec',
    'audio_codec': 'audio_codec',
}


def refine(video, release_name=None, release_file=None, extension='release', **kwargs):
    """Refine a video by using the original release name.

    The refiner will first try:
    - Read the file video_name.<extension> seeking for a release name
    - If no release name, it will read the release_file seeking for a release name
    - If no release name, it will use the release_name passed as an argument
    - If no release name, then no change in the video object is made

    When a release name is found, the video object will be enhanced using the guessit properties extracted from it.

    Several :class:`~subliminal.video.Video` attributes can be found:

      * :attr:`~subliminal.video.Video.title`
      * :attr:`~subliminal.video.Video.series`
      * :attr:`~subliminal.video.Video.season`
      * :attr:`~subliminal.video.Video.episode`
      * :attr:`~subliminal.video.Video.year`
      * :attr:`~subliminal.video.Video.source`
      * :attr:`~subliminal.video.Video.release_group`
      * :attr:`~subliminal.video.Video.resolution`
      * :attr:`~subliminal.video.Video.video_codec`
      * :attr:`~subliminal.video.Video.audio_codec`

    :param video: the video to refine.
    :type video: subliminal.video.Video
    :param str release_name: the release name to be used.
    :param str release_file: the release file to be used
    :param str extension: the release file extension.
    """
    log.debug('Starting release refiner [extension={extension}, release_name={name}, release_file={file}]',
              {'extension': extension, 'name': release_name, 'file': release_file})
    dirpath, filename = os.path.split(video.name)
    dirpath = dirpath or '.'
    fileroot, fileext = os.path.splitext(filename)
    release_file = get_release_file(dirpath, fileroot, extension) or release_file
    release_name = get_release_name(release_file) or release_name

    if not release_name:
        log.debug('No release name for {video!r}', {'video': video.name})
        return

    release_path = os.path.join(dirpath, release_name + fileext)
    log.debug('Guessing using {path}', {'path': release_path})

    guess = guessit(release_path)
    attributes = MOVIE_ATTRIBUTES if guess.get('type') == 'movie' else EPISODE_ATTRIBUTES
    for key, value in viewitems(attributes):
        old_value = getattr(video, key)
        new_value = guess.get(value)

        if new_value and old_value != new_value:
            setattr(video, key, new_value)
            log.debug('Attribute {key} changed from {old!r} to {new!r}',
                      {'key': key, 'old': old_value, 'new': new_value})


def get_release_file(dirpath, filename, extension):
    """Return the release file that should contain the release name for a given a `dirpath`, `filename` and `extension`.

    :param dirpath: the file base folder
    :type dirpath: str
    :param filename: the file name without extension
    :type filename: str
    :param extension:
    :type extension: the file extension
    :return: the release file if the file exists
    :rtype: str
    """
    release_file = os.path.join(dirpath, filename + '.' + extension)

    # skip if info file doesn't exist
    if os.path.isfile(release_file):
        log.debug('Found release file {file}', {'file': release_file})
        return release_file


def get_release_name(release_file):
    """Given a `release_file` it will return the release name.

    :param release_file: the text file that contains the release name
    :type release_file: str
    :return: the release name
    :rtype: str
    """
    if not release_file or not os.path.isfile(release_file):
        return

    with open(release_file, 'r') as f:
        release_name = f.read().strip()

    # skip if no release name was found
    if not release_name:
        log.warning('Release file {file} does not contain a release name',
                    {'file': release_file})

    return release_name
