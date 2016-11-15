# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from six import binary_type, text_type

from . import OrderedDict
from .properties import is_unknown


logger = logging.getLogger(__name__)

visible_chars_table = dict.fromkeys(range(32))


class Provider(object):
    """Base class for all providers."""

    def __init__(self, mapping):
        """Init method."""
        self.mapping = mapping

    def accepts(self, target):
        """Whether or not the video is supported by this provider."""
        raise NotImplementedError

    def describe(self, target, options):
        """Read video metadata information."""
        raise NotImplementedError

    def _describe_tracks(self, general_track, video_tracks, audio_tracks, subtitle_tracks):
        props = self._describe_general(general_track)

        video = []
        for track in video_tracks:
            t = self._describe_video_track(track)
            if t:
                video.append(t)

        audio = []
        for track in audio_tracks:
            t = self._describe_audio_track(track)
            if t:
                audio.append(t)

        subtitle = []
        for track in subtitle_tracks:
            t = self._describe_subtitle_track(track)
            if t:
                subtitle.append(t)

        if video:
            props['video'] = video
        if audio:
            props['audio'] = audio
        if subtitle:
            props['subtitle'] = subtitle

        return props

    def _describe_general(self, track):
        """Describe general media info to a dict.

        :param track:
        :return:
        :rtype: dict
        """
        logger.debug('Handling general track')
        return self._describe_track(track, self.mapping['general'])

    def _describe_video_track(self, track):
        """Describe video track to a dict.

        :param track:
        :return:
        :rtype: dict
        """
        logger.debug('Handling video track')
        return self._describe_track(track, self.mapping['video'])

    def _describe_audio_track(self, track):
        """Describe audio track to a dict.

        :param track:
        :return:
        :rtype: dict
        """
        logger.debug('Handling audio track')
        return self._describe_track(track, self.mapping['audio'])

    def _describe_subtitle_track(self, track):
        """Describe subtitle track to a dict.

        :param track:
        :return:
        :rtype: dict
        """
        logger.debug('Handling subtitle track')
        return self._describe_track(track, self.mapping['subtitle'])

    def _describe_track(self, track, mapping):
        """Describe track to a dict.

        :param track:
        :param mapping:
        :type mapping: dict(str, str)
        :return:
        :rtype: dict
        """
        props = OrderedDict()
        context = dict()
        for name, prop in mapping.items():
            self._enrich(props, name, track, prop, context)

        return props

    @staticmethod
    def _enrich(props, name, source, prop, context):
        if source is not None:
            is_rule = prop.name is None
            value = source.get(prop.name) or prop.default if not is_rule else props
            if value is not None:
                logger.debug('Adding %s with value %r', name, value)
                if isinstance(value, binary_type):
                    value = text_type(value)
                if isinstance(value, text_type):
                    value = value.translate(visible_chars_table).strip()
                    if is_unknown(value):
                        return

                result = prop.handler.handle(value, context) if prop.handler else value
                if result is not None and not is_unknown(result):
                    if not prop.private:
                        if name.startswith('_'):
                            name = name[1:]
                        props[name] = result
                    context[name] = result


class ProviderError(Exception):
    """Base class for provider exceptions."""

    pass


class MalformedFileError(ProviderError):
    """Malformed File error."""

    pass


class UnsupportedFileFormatError(ProviderError):
    """Unsupported File Format error."""

    pass
