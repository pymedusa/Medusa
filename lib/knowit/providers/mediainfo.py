# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os
import sys

from pymediainfo import MediaInfo

from .. import OrderedDict, VIDEO_EXTENSIONS
from ..properties import (
    AudioChannels, AudioChannelsRule, AudioCodec, AudioCompression, AudioProfile, BitRateMode,
    Duration, Float, HearingImpairedRule, Integer, Language, MultiHandler, Property,
    ResolutionRule, ScanType, SubtitleEncoding, SubtitleFormat, VideoCodec, YesNo
)
from ..provider import MalformedFileError, Provider


logger = logging.getLogger(__name__)

MEDIA_INFO_AVAILABLE = False
INITIALIZED = False


def load_native():
    global MEDIA_INFO_AVAILABLE, INITIALIZED
    if INITIALIZED:
        return MEDIA_INFO_AVAILABLE

    os_family = 'windows' if (
        os.name in ('nt', 'dos', 'os2', 'ce')
    ) else (
        'macos' if sys.platform == "darwin" else 'unix'
    )
    logger.debug('Detected os family: %s', os_family)
    try:
        if os_family == 'unix':
            from ctypes import CDLL
            logger.debug('Loading native mediainfo library')
            so_name = 'libmediainfo.so.0'
            for location in ('/usr/local/mediainfo/lib', ):
                candidate = os.path.join(location, so_name)
                if os.path.isfile(candidate):
                    so_name = candidate
                    break
            CDLL(so_name)
            MEDIA_INFO_AVAILABLE = True
        else:  # pragma: no cover
            os_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '../native', os_family))
            if os_family == 'macos':
                from ctypes import CDLL
                logger.debug('Loading native mediainfo library from %s', os_folder)
                CDLL(os.path.join(os_folder, 'libmediainfo.0.dylib'))
                MEDIA_INFO_AVAILABLE = True
            else:
                from ctypes import windll
                is_64bits = sys.maxsize > 2 ** 32
                arch = 'x86_64' if is_64bits else 'i386'
                lib = os.path.join(os_folder, arch)
                logger.debug('Loading native mediainfo library from %s', lib)
                windll.MediaInfo = windll.LoadLibrary(os.path.join(lib, 'MediaInfo.dll'))
                MEDIA_INFO_AVAILABLE = True
        logger.debug('MediaInfo loaded')
    except OSError:
        logger.warning('Unable to load native mediainfo library')
    finally:
        INITIALIZED = True
    return MEDIA_INFO_AVAILABLE


class MediaInfoProvider(Provider):
    """Media Info provider."""

    def __init__(self):
        """Init method."""
        super(MediaInfoProvider, self).__init__({
            'general': OrderedDict([
                ('title', Property('title')),
                ('duration', Property('duration', Duration())),
                ('overall_bit_rate', Property('overall_bit_rate', Integer('overall bit rate'))),
            ]),
            'video': OrderedDict([
                ('number', Property('track_id', Integer('video track number'))),
                ('name', Property('name')),
                ('language', Property('language', Language())),
                ('duration', Property('duration', Duration())),
                ('size', Property('stream_size', Integer('video stream size'))),
                ('width', Property('width', Integer('width'))),
                ('height', Property('height', Integer('height'))),
                ('scan_type', Property('scan_type', ScanType(), default='Progressive')),
                ('aspect_ratio', Property('display_aspect_ratio', Float('aspect ratio'))),
                ('pixel_aspect_ratio', Property('pixel_aspect_ratio', Float('pixel aspect ratio'))),
                ('resolution', Property(handler=ResolutionRule())),
                ('frame_rate', Property('frame_rate', Float('frame rate'))),
                # frame_rate_mode
                ('bit_rate', Property('bit_rate', Integer('video bit rate'))),
                ('bit_depth', Property('bit_depth', Integer('video bit depth'))),
                ('codec', Property('codec', VideoCodec())),
                ('profile', Property('codec_profile')),
                ('encoder', Property('encoded_library_name')),
                ('media_type', Property('internet_media_type')),
                ('forced', Property('forced', YesNo(hide_value=False))),
                ('default', Property('default', YesNo(hide_value=False))),
            ]),
            'audio': OrderedDict([
                ('number', Property('track_id', Integer('audio track number'))),
                ('name', Property('title')),
                ('language', Property('language', Language())),
                ('duration', Property('duration', Duration())),
                ('size', Property('stream_size', Integer('audio stream size'))),
                ('codec', Property('codec', MultiHandler(AudioCodec()))),
                ('profile', Property('codec', MultiHandler(AudioProfile()))),
                ('channels_count', Property('channel_s', MultiHandler(AudioChannels()))),
                ('channel_positions', Property('other_channel_positions',
                                               MultiHandler(lambda x, *args: x, delimiter=' / '), private=True)),
                ('channels', Property(handler=AudioChannelsRule())),
                ('bit_depth', Property('bit_depth', Integer('audio bit depth'))),
                ('bit_rate', Property('bit_rate', MultiHandler(Integer('audio bit rate')))),
                ('bit_rate_mode', Property('bit_rate_mode', MultiHandler(BitRateMode()))),
                ('sampling_rate', Property('sampling_rate', MultiHandler(Integer('audio sampling rate')))),
                ('compression', Property('compression_mode', MultiHandler(AudioCompression()))),
                ('forced', Property('forced', YesNo(hide_value=False))),
                ('default', Property('default', YesNo(hide_value=False))),
            ]),
            'subtitle': OrderedDict([
                ('number', Property('track_id', Integer('subtitle track number'))),
                ('name', Property('title')),
                ('language', Property('language', Language())),
                ('hearing_impaired', Property(handler=HearingImpairedRule())),
                ('format', Property('codec_id', SubtitleFormat())),
                ('encoding', Property('codec_id', SubtitleEncoding())),
                ('forced', Property('forced', YesNo(hide_value=False))),
                ('default', Property('default', YesNo(hide_value=False))),
            ]),
        })

    def accepts(self, video_path):
        """Accept any video when MediaInfo is available."""
        return load_native() and video_path.lower().endswith(VIDEO_EXTENSIONS)

    def describe(self, video_path, options):
        """Return video metadata."""
        data = MediaInfo.parse(video_path).to_data()
        if options.get('raw'):
            return data

        general_tracks = []
        video_tracks = []
        audio_tracks = []
        subtitle_tracks = []
        for track in data.get('tracks'):
            track_type = track.get('track_type')
            if track_type == 'General':
                general_tracks.append(track)
            elif track_type == 'Video':
                video_tracks.append(track)
            elif track_type == 'Audio':
                audio_tracks.append(track)
            elif track_type == 'Text':
                subtitle_tracks.append(track)

        result = self._describe_tracks(general_tracks[0] if general_tracks else [],
                                       video_tracks, audio_tracks, subtitle_tracks)
        if not result:
            logger.warning("Invalid file '%s'", video_path)
            if options.get('fail_on_error'):
                raise MalformedFileError

        return result
