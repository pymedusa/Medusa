# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from . import OrderedDict
from .providers.enzyme import EnzymeProvider
from .providers.mediainfo import MediaInfoProvider


available_providers = OrderedDict([
    ('mediainfo', MediaInfoProvider()),
    ('enzyme', EnzymeProvider()),
])


def know(video_path, options=None):
    """Return a dict containing the video metadata.

    :param video_path:
    :type video_path: string
    :param options:
    :type options: dict
    :return:
    :rtype: dict
    """
    options = options or dict()
    for name, provider in available_providers.items():
        if name != (options.get('provider') or name):
            continue

        if provider.accepts(video_path):
            return provider.describe(video_path, options)

    return dict()
