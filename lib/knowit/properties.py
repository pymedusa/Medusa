# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import logging
import re

from babelfish import Error as BabelfishError, Language as BabelfishLanguage
from six import PY3, text_type

logger = logging.getLogger(__name__)


def is_unknown(value):
    return isinstance(value, text_type) and (not value or value.lower() == 'unknown')


def split(value, delimiter='/'):
    if value is None:
        return

    v = text_type(value)
    result = map(text_type.strip, v.split(delimiter))
    if PY3:
        result = list(result)
    return result


class Property(object):
    """Property class."""

    def __init__(self, name=None, handler=None, default=None, private=False):
        """Init method."""
        self.name = name
        self.handler = handler
        self.default = default
        self.private = private


class Handler(object):
    """Property Handler abstract class."""

    def handle(self, value, context):
        """How to handle property value."""
        raise NotImplementedError

    @staticmethod
    def _handle(name, value, key, mapping):
        result = mapping.get(key)
        if result is not None:
            return result

        logger.info('Invalid %s: %r', name, value)


class MultiHandler(Handler):
    """Property Handler for properties with multiple values."""

    def __init__(self, handler, delimiter='/'):
        """Init method."""
        self.handler = handler
        self.delimiter = delimiter

    def handle(self, value, context):
        """Handle properties with multiple values."""
        values = (split(value[0], self.delimiter)
                  if len(value) == 1 else value) if isinstance(value, list) else split(value, self.delimiter)
        call = self.handler if callable(self.handler) else self.handler.handle
        if len(values) > 1:
            return [call(item, context) if not is_unknown(item) else None for item in values]

        return call(values[0], context)


class Duration(Handler):
    """Duration handler."""

    duration_re = re.compile(r'(?P<hours>\d{1,2}):'
                             r'(?P<minutes>\d{1,2}):'
                             r'(?P<seconds>\d{1,2})(?:\.'
                             r'(?P<millis>\d{3})'
                             r'(?P<micro>\d{3})?\d*)?')

    def handle(self, value, context):
        """Return duration as timedelta."""
        if isinstance(value, int):
            return datetime.timedelta(milliseconds=value)
        try:
            return datetime.timedelta(milliseconds=int(float(value)))
        except ValueError:
            pass

        try:
            h, m, s, ms, mc = self.duration_re.match(text_type(value)).groups('0')
            return datetime.timedelta(hours=int(h), minutes=int(m), seconds=int(s),
                                      milliseconds=int(ms), microseconds=int(mc))
        except ValueError:
            pass

        logger.info('Invalid duration: %r', value)


class ScanType(Handler):
    """Scan Type handler."""

    scan_types = {
        'progressive': 'Progressive',
        'interlaced': 'Interlaced',
        'mbaff': 'Interlaced',
    }

    def handle(self, value, context):
        """Return Progressive or Interlaced."""
        return self._handle('scan type', value, value.lower(), self.scan_types)


class AudioCompression(Handler):
    """Audio Compression handler."""

    mapping = {
        'lossy': 'Lossy',
        'lossless': 'Lossless',
    }

    def handle(self, value, context):
        """Return Lossy or Lossless."""
        return self._handle('audio compression', value, value.lower(), self.mapping)


class BitRateMode(Handler):
    """Bit Rate mode handler."""

    mapping = {
        'VBR': 'Variable',
        'CBR': 'Constant',
    }

    def handle(self, value, context):
        """Return Lossy or Lossless."""
        return self._handle('audio bit rate mode', value, value.upper(), self.mapping)


class VideoCodec(Handler):
    """Video Codec handler."""

    video_codecs = {
        'AVC': 'h264',
        'H264': 'h264',
        'HEVC': 'h265',
        'MPEG-1V': 'Mpeg1',
        'MPEG2': 'Mpeg2',
        'MPEG-2V': 'Mpeg2',
        'MP42': 'MsMpeg4v2',
        'MP43': 'MsMpeg4v3',
        # https://en.wikipedia.org/wiki/MPEG-4_Part_2
        'MPEG-4V': 'Mpeg4',
        'XVID': 'XviD',  # Mpeg4
        'DIVX': 'DivX',  # Mpeg4
        'DX50': 'DivX',  # Mpeg4
        'DIV3': 'DivX',  # Mpeg4
        'ASP': 'DivX',  # Mpeg4
        'JPEG': 'Jpeg',
        'WMV1': 'Wmv1',
        'WMV2': 'Wmv2',
        'WMV3': 'Wmv3',
        'WVC1': 'Wmv3',
        # https://en.wikipedia.org/wiki/VC-1
        'VC-1': 'VC1',
        'QUICKTIME': 'QuickTime',
        # https://en.wikipedia.org/wiki/Sorenson_Media#Sorenson_Spark
        'SORENSON H263': 'h263',
        # https://en.wikipedia.org/wiki/VP6
        'ON2 VP6': 'VP6',
        'VP70': 'VP7',
        # https://en.wikipedia.org/wiki/VP9
        'VP9': 'VP9',
    }

    def handle(self, value, context):
        """Handle video codecs values."""
        key = value.upper().split('/')[-1]
        if key.startswith('V_'):
            key = key[2:]

        return self._handle('video codec', value, key, self.video_codecs)


class AudioCodec(Handler):
    """Audio codec handler."""

    audio_codecs = {
        'AC3': 'AC3',
        'AC3/BSID9': 'AC3',
        'AC3/BSID10': 'AC3',
        'BSID9': 'AC3',
        'BSID10': 'AC3',
        '2000': 'AC3',
        'EAC3': 'EAC3',
        'AC3+': 'EAC3',
        'TRUEHD': 'TrueHD',
        'ATMOS': 'DolbyAtmos',
        'DTS': 'DTS',
        'DTS-HD': 'DTS-HD',
        'AAC': 'AAC',
        'AAC MAIN': 'AAC',
        'AAC LC': 'AAC',
        'AAC LC-SBR': 'AAC',
        'AAC LC-SBR-PS': 'AAC',
        'FLAC': 'FLAC',
        'PCM': 'PCM',
        # https://en.wikipedia.org/wiki/MPEG-1_Audio_Layer_II
        'MPA1L2': 'MP2',
        'MPEG/L2': 'MP2',
        # https://en.wikipedia.org/wiki/MP3
        'MPA1L3': 'MP3',
        'MPA2L3': 'MP3',
        'MPEG/L3': 'MP3',
        '50': 'MP3',
        '55': 'MP3',
        'VORBIS': 'Vorbis',
        'OPUS': 'Opus',
        # https://wiki.multimedia.cx/index.php?title=Windows_Media_Audio_9
        '160': 'WMAv1',
        '161': 'WMAv2',
        '162': 'WMAPro',
    }

    def handle(self, value, context):
        """Handle audio codec."""
        key = text_type(value).upper()
        if key.startswith('A_'):
            key = key[2:]

        return self._handle('audio codec', value, key, self.audio_codecs)


class AudioProfile(Handler):
    """Audio profile handler."""

    audio_profiles = {
        'AAC MAIN': 'Main',
        'AAC LC': 'LC',
        'AAC LC-SBR': 'LC',
        'AAC LC-SBR-PS': 'LC',
    }

    def handle(self, value, context):
        """Handle profiles."""
        key = text_type(value).upper()
        return self.audio_profiles.get(key)


class SubtitleFormat(Handler):
    """Subtitle Format handler."""

    formats = {
        'S_HDMV/PGS': 'PGS',
        '144': 'PGS',
        'S_VOBSUB': 'VobSub',
        'E0': 'VobSub',
        'S_TEXT/UTF8': 'SubRip',
        'S_TEXT/SSA': 'SubStationAlpha',
        # https://en.wikipedia.org/wiki/SubStation_Alpha
        'S_TEXT/ASS': 'AdvancedSubStationAlpha',
        'TX3G': 'Tx3g',
    }

    def handle(self, value, context):
        """Handle subtitle format values."""
        key = value.upper()
        return self._handle('subtitle format', value, key, self.formats)


class SubtitleEncoding(Handler):
    """Subtitle Encoding handler."""

    encoding = {
        'S_TEXT/UTF8': 'utf-8'
    }

    def handle(self, value, context):
        """Handle subtitle encoding values."""
        key = value.upper()
        return self.encoding.get(key)


class Language(Handler):
    """Language handler."""

    def handle(self, value, context):
        """Handle languages."""
        try:
            if len(value) == 3:
                return BabelfishLanguage.fromalpha3b(value)

            return BabelfishLanguage.fromietf(value)
        except (BabelfishError, ValueError):
            pass

        try:
            return BabelfishLanguage.fromname(value)
        except BabelfishError:
            pass

        logger.info('Invalid language: %r', value)
        return BabelfishLanguage('und')


class YesNo(Handler):
    """Yes or No handler."""

    mapping = {'yes', 'true', '1'}

    def __init__(self, yes=True, no=False, hide_value=None):
        """Init method."""
        self.yes = yes
        self.no = no
        self.hide_value = hide_value

    def handle(self, value, context):
        """Handle boolean values."""
        v = text_type(value).lower()
        result = self.yes if v in self.mapping else self.no
        return result if result != self.hide_value else None


class AudioChannels(Handler):
    """Audio Channels handler."""

    ignored = {
        'object based',  # Dolby Atmos
    }

    def handle(self, value, context):
        """Handle audio channels."""
        if isinstance(value, int):
            return value

        v = text_type(value).lower()
        if v not in self.ignored:
            try:
                return int(v)
            except ValueError:
                logger.info('Invalid %s: %r', self.name, value)


class Integer(Handler):
    """Integer handler."""

    def __init__(self, name):
        """Init method."""
        self.name = name

    def handle(self, value, context):
        """Handle integer values."""
        if isinstance(value, int):
            return value

        try:
            return int(text_type(value))
        except ValueError:
            logger.info('Invalid %s: %r', self.name, value)


class Float(Handler):
    """Float handler."""

    def __init__(self, name):
        """Init method."""
        self.name = name

    def handle(self, value, context):
        """Handle float values."""
        if isinstance(value, float):
            return value

        try:
            return float(text_type(value))
        except ValueError:
            logger.info('Invalid %s: %r', self.name, value)


class ResolutionRule(Handler):
    """Resolution rule."""

    standard_resolutions = (
        480, 720, 1080, 2160, 4320,
    )
    uncommon_resolutions = (
        240, 288, 360, 576,
    )
    resolutions = list(sorted(standard_resolutions + uncommon_resolutions))
    square = 4. / 3
    wide = 16. / 9

    def handle(self, props, context):
        """Return the resolution for the video.

        The resolution is based on a widescreen TV (16:9)
        1920x800 will be considered 1080p since the TV will use 1920x1080 with vertical black bars
        1426x1080 is considered 1080p since the TV will use 1920x1080 with horizontal black bars

        The calculation considers the display aspect ratio and the pixel aspect ratio (not only width and height).
        The upper resolution is selected if there's no perfect match with the following list of resolutions:
            240, 288, 360, 480, 576, 720, 1080, 2160, 4320
        If no interlaced information is available, resolution will be considered Progressive.
        """
        width = props.get('width')
        height = props.get('height')
        dar = props.get('aspect_ratio', float(width) / height)
        par = props.get('pixel_aspect_ratio', 1)
        scan_type = props.get('scan_type', 'p')[0].lower()

        if width and height:
            # selected DAR must be between 4:3 and 16:9
            selected_dar = max(min(dar, self.wide), self.square)
            stretched_width = int(round(width * par / 16)) * 16  # mod-16
            calculated_height = int(round(stretched_width / selected_dar / 8)) * 8  # mod-8

            selected_resolution = None
            for r in reversed(self.resolutions):
                if r < calculated_height:
                    break

                selected_resolution = r

            if selected_resolution:
                return '{0}{1}'.format(selected_resolution, scan_type)

            logger.info('''# Unable to detect resolution
  - width: {0}
    height: {1}
    scan_type: {2}
    aspect_ratio: {3}
    pixel_aspect_ratio: {4}'''.format(width, height, scan_type, dar, par))


class AudioChannelsRule(Handler):
    """Audio Channel rule."""

    mapping = {
        1: '1.0',
        2: '2.0',
        6: '5.1',
        8: '7.1',
    }

    def handle(self, props, context):
        """Execute the rule against properties."""
        count = props.get('channels_count')
        if count is not None:
            channels = self.mapping.get(count) if isinstance(count, int) else None
            positions = context.get('channel_positions') or []
            positions = positions if isinstance(positions, list) else [positions]
            candidate = 0
            for position in positions:
                if not position:
                    continue
                c = sum([float(i) for i in position.split('/')])
                c_count = int(c) + int(round((c - int(c)) * 10))
                if c_count == count:
                    return text_type(c)

                candidate = max(candidate, c)

            if channels:
                return channels

            if candidate:
                return text_type(candidate)

            logger.info('Invalid channels: %d', count)


class HearingImpairedRule(Handler):
    """Hearing Impaired rule."""

    hi_re = re.compile(r'(\bcc\d\b)|(\bsdh\b)', re.IGNORECASE)

    def handle(self, props, context):
        """Hearing Impaired."""
        name = props.get('name')
        if name and self.hi_re.search(name):
            return True
