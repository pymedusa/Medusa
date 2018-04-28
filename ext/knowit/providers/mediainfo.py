# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import locale
import os
import sys

from ctypes import c_size_t, c_void_p, c_wchar_p
from logging import NullHandler, getLogger
from subprocess import check_output

from pymediainfo import MediaInfo
from pymediainfo import __version__ as pymediainfo_version

from .. import (
    OrderedDict,
    VIDEO_EXTENSIONS,
)
from ..properties import (
    AudioChannels,
    AudioCodec,
    AudioCompression,
    AudioProfile,
    Basic,
    BitRateMode,
    Duration,
    Language,
    Quantity,
    ScanType,
    SubtitleFormat,
    VideoCodec,
    VideoEncoder,
    VideoProfile,
    VideoProfileLevel,
    VideoProfileTier,
    YesNo,
)
from ..property import (
    MultiValue,
    Property,
)
from ..provider import (
    MalformedFileError,
    Provider,
)
from ..rules import (
    AudioChannelsRule,
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


WARN_MSG = '''
=========================================================================================
MediaInfo not found on your system or could not be loaded.
Visit https://mediaarea.net/ to download it.
If you still have problems, please check if the downloaded version matches your system.
To load MediaInfo from a specific location, please define the location as follow:
  knowit --mediainfo /usr/local/mediainfo/lib <video_path>
  knowit --mediainfo /usr/local/mediainfo/bin <video_path>
  knowit --mediainfo "C:\Program Files\MediaInfo" <video_path>
  knowit --mediainfo C:\Software\MediaInfo.dll <video_path>
  knowit --mediainfo C:\Software\MediaInfo.exe <video_path>
  knowit --mediainfo /opt/mediainfo/libmediainfo.so <video_path>
  knowit --mediainfo /opt/mediainfo/libmediainfo.dylib <video_path>
=========================================================================================
'''


class MediaInfoExecutor(object):
    """Media info executable knows how to execute media info: using ctypes or cli."""

    def __init__(self, location):
        """Constructor."""
        self.location = location

    def extract_info(self, filename):
        """Extract media info."""
        xml = self._execute(filename)
        return MediaInfo(xml)

    def _execute(self, filename):
        raise NotImplementedError

    @classmethod
    def get_executor_instance(cls, suggested_path):
        """Return the executor instance."""
        os_family = detect_os()
        logger.debug('Detected os: %s', os_family)
        for exec_cls in (MediaInfoCTypesExecutor, MediaInfoCliExecutor):
            executor = exec_cls.create(os_family, suggested_path)
            if executor:
                return executor


class MediaInfoCliExecutor(MediaInfoExecutor):
    """Media info using cli."""

    names = {
        'unix': ['mediainfo'],
        'windows': ['MediaInfo.exe'],
        'macos': ['mediainfo'],
    }

    locations = {
        'unix': ['/usr/local/mediainfo/bin', '__PATH__'],
        'windows': ['__PATH__'],
        'macos': ['__PATH__'],
    }

    def _execute(self, filename):
        return check_output([self.location, '--Output=XML', '--Full', filename])

    @classmethod
    def create(cls, os_family, suggested_path):
        """Create the executor instance."""
        for candidate in define_candidate(os_family, cls.locations, cls.names, suggested_path):
            try:
                check_output([candidate, '--version'])
                logger.debug('MediaInfo cli detected: %s', candidate)
                return MediaInfoCliExecutor(candidate)
            except OSError:
                pass


class MediaInfoCTypesExecutor(MediaInfoExecutor):
    """Media info ctypes."""

    names = {
        'unix': ['libmediainfo.so.0'],
        'windows': ['MediaInfo.dll'],
        'macos': ['libmediainfo.0.dylib', 'libmediainfo.dylib'],
    }

    locations = {
        'unix': ['/usr/local/mediainfo/lib', '__PATH__'],
        'windows': ['__PATH__'],  # 'C:\Program Files\MediaInfo', 'C:\Program Files (x86)\MediaInfo'],
        'macos': ['__PATH__'],
    }

    def __init__(self, location, lib):
        """Constructor."""
        super(MediaInfoCTypesExecutor, self).__init__(location)
        self.lib = lib

    def _execute(self, filename):
        # Create a MediaInfo handle
        handle = self.lib.MediaInfo_New()
        try:
            self.lib.MediaInfo_Option(handle, 'CharSet', 'UTF-8')
            # Fix for https://github.com/sbraz/pymediainfo/issues/22
            # Python 2 does not change LC_CTYPE
            # at startup: https://bugs.python.org/issue6203
            if sys.version_info < (3, ) and os.name == 'posix' and locale.getlocale() == (None, None):
                locale.setlocale(locale.LC_CTYPE, locale.getdefaultlocale())
            self.lib.MediaInfo_Option(None, 'Inform', 'XML')
            self.lib.MediaInfo_Option(None, 'Complete', '1')
            self.lib.MediaInfo_Open(handle, filename)
            return self.lib.MediaInfo_Inform(handle, 0)
        finally:
            # Delete the handle
            self.lib.MediaInfo_Close(handle)
            self.lib.MediaInfo_Delete(handle)

    @classmethod
    def create(cls, os_family, suggested_path):
        """Create the executor instance."""
        for candidate in define_candidate(os_family, cls.locations, cls.names, suggested_path):
            lib = cls._get_native_lib(os_family, candidate)
            if lib:
                logger.debug('MediaInfo library detected: %s', candidate)
                return MediaInfoCTypesExecutor(candidate, lib)

    @classmethod
    def _get_native_lib(cls, os_family, library_path):
        if os_family == 'windows':
            return cls._get_windows_lib(library_path)

        # works for unix and macos
        return cls._get_unix_lib(library_path)

    @classmethod
    def _get_windows_lib(cls, library_path):
        from ctypes import windll
        try:
            if sys.version_info[:3] == (2, 7, 13):
                # http://bugs.python.org/issue29082
                library_path = str(library_path)
            lib = windll.MediaInfo = windll.LoadLibrary(library_path)
            return cls._initialize_lib(lib)
        except OSError:
            pass

    @classmethod
    def _get_unix_lib(cls, library_path):
        from ctypes import CDLL
        try:
            return cls._initialize_lib(CDLL(library_path))
        except OSError:
            pass

    @classmethod
    def _initialize_lib(cls, lib):
        lib.MediaInfo_Inform.restype = c_wchar_p
        lib.MediaInfo_New.argtypes = []
        lib.MediaInfo_New.restype = c_void_p
        lib.MediaInfo_Option.argtypes = [c_void_p, c_wchar_p, c_wchar_p]
        lib.MediaInfo_Option.restype = c_wchar_p
        lib.MediaInfo_Inform.argtypes = [c_void_p, c_size_t]
        lib.MediaInfo_Inform.restype = c_wchar_p
        lib.MediaInfo_Open.argtypes = [c_void_p, c_wchar_p]
        lib.MediaInfo_Open.restype = c_size_t
        lib.MediaInfo_Delete.argtypes = [c_void_p]
        lib.MediaInfo_Delete.restype = None
        lib.MediaInfo_Close.argtypes = [c_void_p]
        lib.MediaInfo_Close.restype = None
        return lib


class MediaInfoProvider(Provider):
    """Media Info provider."""

    executor = None

    def __init__(self, config, suggested_path):
        """Init method."""
        super(MediaInfoProvider, self).__init__(config, {
            'general': OrderedDict([
                ('title', Property('title', description='media title')),
                ('path', Property('complete_name', description='media path')),
                ('duration', Duration('duration', description='media duration')),
                ('size', Quantity('file_size', units.byte, description='media size')),
                ('bit_rate', Quantity('overall_bit_rate', units.bps, description='media bit rate')),
            ]),
            'video': OrderedDict([
                ('id', Basic('track_id', int, allow_fallback=True, description='video track number')),
                ('name', Property('name', description='video track name')),
                ('language', Language('language', description='video language')),
                ('duration', Duration('duration', description='video duration')),
                ('size', Quantity('stream_size', units.byte, description='video stream size')),
                ('width', Quantity('width', units.pixel)),
                ('height', Quantity('height', units.pixel)),
                ('scan_type', ScanType(config, 'scan_type', default='Progressive', description='video scan type')),
                ('aspect_ratio', Basic('display_aspect_ratio', float, description='display aspect ratio')),
                ('pixel_aspect_ratio', Basic('pixel_aspect_ratio', float, description='pixel aspect ratio')),
                ('resolution', None),  # populated with ResolutionRule
                ('frame_rate', Quantity('frame_rate', units.FPS, float, description='video frame rate')),
                # frame_rate_mode
                ('bit_rate', Quantity('bit_rate', units.bps, description='video bit rate')),
                ('bit_depth', Quantity('bit_depth', units.bit, description='video bit depth')),
                ('codec', VideoCodec(config, 'codec', description='video codec')),
                ('profile', VideoProfile(config, 'codec_profile', description='video codec profile')),
                ('profile_level', VideoProfileLevel(config, 'codec_profile', description='video codec profile level')),
                ('profile_tier', VideoProfileTier(config, 'codec_profile', description='video codec profile tier')),
                ('encoder', VideoEncoder(config, 'encoded_library_name', description='video encoder')),
                ('media_type', Property('internet_media_type', description='video media type')),
                ('forced', YesNo('forced', hide_value=False, description='video track forced')),
                ('default', YesNo('default', hide_value=False, description='video track default')),
            ]),
            'audio': OrderedDict([
                ('id', Basic('track_id', int, allow_fallback=True, description='audio track number')),
                ('name', Property('title', description='audio track name')),
                ('language', Language('language', description='audio language')),
                ('duration', Duration('duration', description='audio duration')),
                ('size', Quantity('stream_size', units.byte, description='audio stream size')),
                ('codec', MultiValue(AudioCodec(config, 'codec', description='audio codec'))),
                ('profile', MultiValue(AudioProfile(config, 'format_profile', description='audio codec profile'),
                                       delimiter=' / ')),
                ('channels_count', MultiValue(AudioChannels('channel_s', description='audio channels count'))),
                ('channel_positions', MultiValue(name='other_channel_positions', handler=(lambda x, *args: x),
                                                 delimiter=' / ', private=True, description='audio channels position')),
                ('channels', None),  # populated with AudioChannelsRule
                ('bit_depth', Quantity('bit_depth', units.bit, description='audio bit depth')),
                ('bit_rate', MultiValue(Quantity('bit_rate', units.bps, description='audio bit rate'))),
                ('bit_rate_mode', MultiValue(BitRateMode(config, 'bit_rate_mode', description='audio bit rate mode'))),
                ('sampling_rate', MultiValue(Quantity('sampling_rate', units.Hz, description='audio sampling rate'))),
                ('compression', MultiValue(AudioCompression(config, 'compression_mode',
                                                            description='audio compression'))),
                ('forced', YesNo('forced', hide_value=False, description='audio track forced')),
                ('default', YesNo('default', hide_value=False, description='audio track default')),
            ]),
            'subtitle': OrderedDict([
                ('id', Basic('track_id', int, allow_fallback=True, description='subtitle track number')),
                ('name', Property('title', description='subtitle track name')),
                ('language', Language('language', description='subtitle language')),
                ('hearing_impaired', None),  # populated with HearingImpairedRule
                ('_closed_caption', Property('captionservicename', private=True)),
                ('closed_caption', None),  # populated with ClosedCaptionRule
                ('format', SubtitleFormat(config, 'codec_id', description='subtitle format')),
                ('forced', YesNo('forced', hide_value=False, description='subtitle track forced')),
                ('default', YesNo('default', hide_value=False, description='subtitle track default')),
            ]),
        }, {
            'video': OrderedDict([
                ('language', LanguageRule('video language')),
                ('resolution', ResolutionRule('video resolution')),
            ]),
            'audio': OrderedDict([
                ('language', LanguageRule('audio language')),
                ('channels', AudioChannelsRule('audio channels')),
            ]),
            'subtitle': OrderedDict([
                ('language', LanguageRule('subtitle language')),
                ('hearing_impaired', HearingImpairedRule('subtitle hearing impaired')),
                ('closed_caption', ClosedCaptionRule('closed caption'))
            ])
        })
        self.executor = MediaInfoExecutor.get_executor_instance(suggested_path)

    def accepts(self, video_path):
        """Accept any video when MediaInfo is available."""
        if self.executor is None:
            logger.warning(WARN_MSG)
            self.executor = False

        return self.executor and video_path.lower().endswith(VIDEO_EXTENSIONS)

    def describe(self, video_path, context):
        """Return video metadata."""
        data = self.executor.extract_info(video_path).to_data()
        if context.get('raw'):
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

        result = self._describe_tracks(video_path, general_tracks[0] if general_tracks else {},
                                       video_tracks, audio_tracks, subtitle_tracks, context)
        if not result:
            logger.warning('Invalid file %r', video_path)
            if context.get('fail_on_error'):
                raise MalformedFileError

        result['provider'] = self.executor.location
        return result

    @property
    def version(self):
        """Return mediainfo version information."""
        return pymediainfo_version, self.executor.location if self.executor else None
