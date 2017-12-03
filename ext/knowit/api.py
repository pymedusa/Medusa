# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from . import OrderedDict
from .config import Config
from .providers import (
    EnzymeProvider,
    FFmpegProvider,
    MediaInfoProvider,
)

_provider_map = OrderedDict([
    ('mediainfo', MediaInfoProvider),
    ('ffmpeg', FFmpegProvider),
    ('enzyme', EnzymeProvider),
])

available_providers = OrderedDict([])


def initialize(context=None):
    """Initialize knowit."""
    if not available_providers:
        context = context or {}
        config = Config.build(context.get('config'))
        for name, provider_cls in _provider_map.items():
            available_providers[name] = provider_cls(config, context.get(name) or config.general.get(name))


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


def dependencies(context=None):
    """Return all dependencies detected by knowit."""
    initialize(context)
    deps = OrderedDict([])
    for name, provider_cls in _provider_map.items():
        if name in available_providers:
            deps[name] = available_providers[name].version
        else:
            deps[name] = None, None

    return deps
