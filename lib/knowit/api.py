# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from . import OrderedDict
from .config import Config
from .providers import (
    EnzymeProvider,
    FFmpegProvider,
    MediaInfoProvider,
)

_provider_map = {
    'ffmpeg': FFmpegProvider,
    'mediainfo': MediaInfoProvider,
    'enzyme': EnzymeProvider,
}

available_providers = OrderedDict([])


def initialize(context=None):
    """Initialize knowit."""
    if not available_providers:
        context = context or {}
        config = Config.build(context.get('config'))
        for name, provider_cls in _provider_map.items():
            key = '{0}_path'.format(name)
            available_providers[name] = provider_cls(config, context.get(key) or config.general.get(key))


def know(video_path, context=None):
    """Return a dict containing the video metadata.

    :param video_path:
    :type video_path: string
    :param context:
    :type context: dict
    :return:
    :rtype: dict
    """
    context = context or {}
    context.setdefault('profile', 'default')
    initialize(context)

    for name, provider in available_providers.items():
        if name != (context.get('provider') or name):
            continue

        if provider.accepts(video_path):
            return provider.describe(video_path, context)

    return {}
