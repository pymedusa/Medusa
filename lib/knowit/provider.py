# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from logging import NullHandler, getLogger

from . import OrderedDict
from .units import units

logger = getLogger(__name__)
logger.addHandler(NullHandler())


class Provider(object):
    """Base class for all providers."""

    min_fps = 1. * units.FPS
    max_fps = 100 * units.FPS

    def __init__(self, config, mapping, rules=None):
        """Init method."""
        self.config = config
        self.mapping = mapping
        self.rules = rules or {}

    def accepts(self, target):
        """Whether or not the video is supported by this provider."""
        raise NotImplementedError

    def describe(self, target, context):
        """Read video metadata information."""
        raise NotImplementedError

    def _describe_tracks(self, general_track, video_tracks, audio_tracks, subtitle_tracks, context):
        logger.debug('Handling general track')
        props = self._describe_track(general_track, 'general', context)

        for track_type, tracks, in (('video', video_tracks),
                                    ('audio', audio_tracks),
                                    ('subtitle', subtitle_tracks)):
            results = []
            for track in tracks or []:
                logger.debug('Handling %s track', track_type)
                t = self._validate_track(track_type, self._describe_track(track, track_type, context))
                if t:
                    results.append(t)

            if results:
                props[track_type] = results

        return props

    @classmethod
    def _validate_track(cls, track_type, track):
        if track_type != 'video' or 'frame_rate' not in track or cls.min_fps < track['frame_rate'] < cls.max_fps:
            return track

    def _describe_track(self, track, track_type, context):
        """Describe track to a dict.

        :param track:
        :param track_type:
        :rtype: dict
        """
        props = OrderedDict()
        pv_props = {}
        for name, prop in self.mapping[track_type].items():
            if not prop:
                # placeholder to be populated by rules. It keeps the order
                props[name] = None
                continue

            value = prop.extract_value(track, context)
            if value is not None:
                if not prop.private:
                    which = props
                else:
                    which = pv_props
                which[name] = value

        for name, rule in self.rules.get(track_type, {}).items():
            if props.get(name) is not None and not rule.override:
                logger.debug('Skipping rule %s since property is already present', name)
                continue

            value = rule.execute(props, pv_props, context)
            if value is not None:
                props[name] = value
            elif name in props and not rule.override:
                del props[name]

        return props

    @property
    def version(self):
        """Return provider version information."""
        raise NotImplementedError


class ProviderError(Exception):
    """Base class for provider exceptions."""

    pass


class MalformedFileError(ProviderError):
    """Malformed File error."""

    pass


class UnsupportedFileFormatError(ProviderError):
    """Unsupported File Format error."""

    pass
