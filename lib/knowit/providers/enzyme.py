# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import logging

import enzyme

from .. import OrderedDict
from ..properties import (
    AudioChannelsRule, AudioCodec, HearingImpairedRule, Integer,
    Language, Property, ResolutionRule, VideoCodec, YesNo
)
from ..provider import MalformedFileError, Provider
from ..utils import todict


logger = logging.getLogger(__name__)


class EnzymeProvider(Provider):
    """Enzyme Provider."""

    def __init__(self):
        """Init method."""
        super(EnzymeProvider, self).__init__({
            'general': OrderedDict([
                ('title', Property('title')),
                ('duration', Property('duration')),
            ]),
            'video': OrderedDict([
                ('number', Property('number', Integer('video track number'))),
                ('name', Property('name')),
                ('language', Property('language', Language())),
                ('width', Property('width', Integer('width'))),
                ('height', Property('height', Integer('height'))),
                ('scan_type', Property('interlaced', YesNo('Interlaced', 'Progressive'), default='Progressive')),
                ('resolution', Property(handler=ResolutionRule())),
                # ('bit_depth', Property('bit_depth', Integer('video bit depth'))),
                ('codec', Property('codec_id', VideoCodec())),
                ('forced', Property('forced', YesNo(hide_value=False))),
                ('default', Property('default', YesNo(hide_value=False))),
                ('enabled', Property('enabled', YesNo(hide_value=True))),
            ]),
            'audio': OrderedDict([
                ('number', Property('number', Integer('audio track number'))),
                ('name', Property('name')),
                ('language', Property('language', Language())),
                ('codec', Property('codec_id', AudioCodec())),
                ('channels_count', Property('channels', Integer('audio channels'))),
                ('channels', Property(handler=AudioChannelsRule())),
                ('forced', Property('forced', YesNo(hide_value=False))),
                ('default', Property('default', YesNo(hide_value=False))),
                ('enabled', Property('enabled', YesNo(hide_value=True))),
            ]),
            'subtitle': OrderedDict([
                ('number', Property('number', Integer('subtitle track number'))),
                ('name', Property('name')),
                ('language', Property('language', Language())),
                ('hearing_impaired', Property(handler=HearingImpairedRule())),
                ('forced', Property('forced', YesNo(hide_value=False))),
                ('default', Property('default', YesNo(hide_value=False))),
                ('enabled', Property('enabled', YesNo(hide_value=True))),
            ]),
        })

    def accepts(self, video_path):
        """Accept only MKV files."""
        return video_path.lower().endswith('.mkv')

    def describe(self, video_path, options):
        """Return video metadata."""
        try:
            with open(video_path, 'rb') as f:
                data = todict(enzyme.MKV(f))
        except enzyme.MalformedMKVError:  # pragma: no cover
            logger.warning("Invalid file '%s'", video_path)
            if options.get('fail_on_error'):
                raise MalformedFileError
            return dict()

        if options.get('raw'):
            return data

        return self._describe_tracks(data.get('info'), data.get('video_tracks'),
                                     data.get('audio_tracks'), data.get('subtitle_tracks'))
