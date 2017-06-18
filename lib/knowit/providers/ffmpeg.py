# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from logging import NullHandler, getLogger
from subprocess import check_output

from .. import (
    OrderedDict,
    VIDEO_EXTENSIONS,
)
from ..properties import (
    AudioChannels,
    AudioCodec,
    AudioProfile,
    Basic,
    Duration,
    Language,
    Quantity,
    Ratio,
    ScanType,
    SubtitleFormat,
    VideoCodec,
    VideoProfile,
    VideoProfileLevel,
    YesNo,
)
from ..property import (
    Property,
)
from ..provider import (
    MalformedFileError,
    Provider,
)
from ..rules import (
    AudioChannelsRule,
    AudioCodecRule,
    ClosedCaptionRule,
    HearingImpairedRule,
    LanguageRule,
    ResolutionRule,
)
from ..units import units
from ..utils import (
    define_candidate,
    detect_os,
)

logger = getLogger(__name__)
logger.addHandler(NullHandler())


WARN_MSG = r'''
=========================================================================================
FFmpeg (ffprobe) not found on your system or could not be loaded.
Visit https://ffmpeg.org/download.html to download it.
If you still have problems, please check if the downloaded version matches your system.
To load FFmpeg (ffprobe) from a specific location, please define the location as follow:
  knowit --ffmpeg /usr/local/ffmpeg/bin <video_path>
  knowit --ffmpeg /usr/local/ffmpeg/bin/ffprobe <video_path>
  knowit --ffmpeg "C:\Program Files\FFmpeg" <video_path>
  knowit --ffmpeg C:\Software\ffprobe.exe <video_path>
=========================================================================================
'''


class FFmpegExecutor(object):
    """Executor that knows how to execute media info: using ctypes or cli."""

    def __init__(self, location):
        """Constructor."""
        self.location = location

    def extract_info(self, filename):
        """Extract media info."""
        json_dump = self._execute(filename)
        return json.loads(json_dump)

    def _execute(self, filename):
        raise NotImplementedError

    @classmethod
    def get_executor_instance(cls, suggested_path):
        """Return executor instance."""
        os_family = detect_os()
        logger.debug('Detected os: %s', os_family)
        for exec_cls in (FFmpegCliExecutor, ):
            executor = exec_cls.create(os_family, suggested_path)
            if executor:
                return executor


class FFmpegCliExecutor(FFmpegExecutor):
    """Executor that uses FFmpeg (ffprobe) cli."""

    names = {
        'unix': ['ffprobe'],
        'windows': ['ffprobe.exe'],
        'macos': ['ffprobe'],
    }

    locations = {
        'unix': ['/usr/local/ffmpeg/bin', '__PATH__'],
        'windows': ['__PATH__'],
        'macos': ['__PATH__'],
    }

    def _execute(self, filename):
        return check_output([self.location, '-v', 'quiet', '-print_format', 'json',
                             '-show_format', '-show_streams', '-sexagesimal', filename])

    @classmethod
    def create(cls, os_family, suggested_path):
        """Create the executor instance."""
        for candidate in define_candidate(os_family, cls.locations, cls.names, suggested_path):
            try:
                check_output([candidate, '-version'])
                logger.debug('FFmpeg cli detected: %s', candidate)
                return FFmpegCliExecutor(candidate)
            except OSError:
                pass


class FFmpegProvider(Provider):
    """FFmpeg provider."""

    def __init__(self, config, suggested_path):
        """Init method."""
        super(FFmpegProvider, self).__init__(config, {
            'general': OrderedDict([
                ('title', Property('tags.title', description='media title')),
                ('path', Property('filename', description='media path')),
                ('duration', Duration('duration', description='media duration')),
                ('size', Quantity('size', units.byte, description='media size')),
                ('bit_rate', Quantity('bit_rate', units.bps, description='media bit rate')),
            ]),
            'video': OrderedDict([
                ('id', Basic('index', int, allow_fallback=True, description='video track number')),
                ('name', Property('tags.title', description='video track name')),
                ('language', Language('tags.language', description='video language')),
                ('duration', Duration('duration', description='video duration')),
                ('width', Quantity('width', units.pixel)),
                ('height', Quantity('height', units.pixel)),
                ('scan_type', ScanType(config, 'field_order', default='Progressive', description='video scan type')),
                ('aspect_ratio', Ratio('display_aspect_ratio', description='display aspect ratio')),
                ('pixel_aspect_ratio', Ratio('sample_aspect_ratio', description='pixel aspect ratio')),
                ('resolution', None),  # populated with ResolutionRule
                ('frame_rate', Ratio('r_frame_rate', unit=units.FPS, description='video frame rate')),
                # frame_rate_mode
                ('bit_rate', Quantity('bit_rate', units.bps, description='video bit rate')),
                ('bit_depth', Quantity('bits_per_raw_sample', units.bit, description='video bit depth')),
                ('codec', VideoCodec(config, 'codec_name', description='video codec')),
                ('profile', VideoProfile(config, 'profile', description='video codec profile')),
                ('profile_level', VideoProfileLevel(config, 'level', description='video codec profile level')),
                # ('profile_tier', VideoProfileTier(config, 'codec_profile', description='video codec profile tier')),
                ('forced', YesNo('disposition.forced', hide_value=False, description='video track forced')),
                ('default', YesNo('disposition.default', hide_value=False, description='video track default')),
            ]),
            'audio': OrderedDict([
                ('id', Basic('index', int, allow_fallback=True, description='audio track number')),
                ('name', Property('tags.title', description='audio track name')),
                ('language', Language('tags.language', description='audio language')),
                ('duration', Duration('duration', description='audio duration')),
                ('codec', AudioCodec(config, 'codec_name', description='audio codec')),
                ('_codec', AudioCodec(config, 'profile', description='audio codec', private=True, reportable=False)),
                ('profile', AudioProfile(config, 'profile', description='audio codec profile')),
                ('channels_count', AudioChannels('channels', description='audio channels count')),
                ('channels', None),  # populated with AudioChannelsRule
                ('bit_depth', Quantity('bits_per_raw_sample', units.bit, description='audio bit depth')),
                ('bit_rate', Quantity('bit_rate', units.bps, description='audio bit rate')),
                ('sampling_rate', Quantity('sample_rate', units.Hz, description='audio sampling rate')),
                ('forced', YesNo('disposition.forced', hide_value=False, description='audio track forced')),
                ('default', YesNo('disposition.default', hide_value=False, description='audio track default')),
            ]),
            'subtitle': OrderedDict([
                ('id', Basic('index', int, allow_fallback=True, description='subtitle track number')),
                ('name', Property('tags.title', description='subtitle track name')),
                ('language', Language('tags.language', description='subtitle language')),
                ('hearing_impaired', YesNo('disposition.hearing_impaired',
                                           hide_value=False, description='subtitle hearing impaired')),
                ('closed_caption', None),  # populated with ClosedCaptionRule
                ('format', SubtitleFormat(config, 'codec_name', description='subtitle format')),
                ('forced', YesNo('disposition.forced', hide_value=False, description='subtitle track forced')),
                ('default', YesNo('disposition.default', hide_value=False, description='subtitle track default')),
            ]),
        }, {
            'video': OrderedDict([
                ('language', LanguageRule('video language')),
                ('resolution', ResolutionRule('video resolution')),
            ]),
            'audio': OrderedDict([
                ('language', LanguageRule('audio language')),
                ('channels', AudioChannelsRule('audio channels')),
                ('codec', AudioCodecRule('audio codec', override=True)),
            ]),
            'subtitle': OrderedDict([
                ('language', LanguageRule('subtitle language')),
                ('hearing_impaired', HearingImpairedRule('subtitle hearing impaired')),
                ('closed_caption', ClosedCaptionRule('closed caption'))
            ])
        })
        self.executor = FFmpegExecutor.get_executor_instance(suggested_path)

    def accepts(self, video_path):
        """Accept any video when FFprobe is available."""
        if self.executor is None:
            logger.warning(WARN_MSG)
            self.executor = False

        return self.executor and video_path.lower().endswith(VIDEO_EXTENSIONS)

    def describe(self, video_path, context):
        """Return video metadata."""
        data = self.executor.extract_info(video_path)
        if context.get('raw'):
            return data

        general_track = data.get('format') or {}
        video_tracks = []
        audio_tracks = []
        subtitle_tracks = []
        for track in data.get('streams'):
            track_type = track.get('codec_type')
            if track_type == 'video':
                video_tracks.append(track)
            elif track_type == 'audio':
                audio_tracks.append(track)
            elif track_type == 'subtitle':
                subtitle_tracks.append(track)

        result = self._describe_tracks(general_track, video_tracks, audio_tracks, subtitle_tracks, context)
        if not result:
            logger.warning('Invalid file %r', video_path)
            if context.get('fail_on_error'):
                raise MalformedFileError

        result['provider'] = self.executor.location
        return result

    @property
    def version(self):
        """Return ffmpeg version information."""
        return None, self.executor.location if self.executor else None
