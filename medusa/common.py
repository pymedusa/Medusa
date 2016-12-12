# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.
"""Common interface for Quality and Status."""

import operator
import os
import platform
import re
import uuid

from collections import namedtuple
from os import path

from fake_useragent import UserAgent, settings as ua_settings

import knowit

from six import PY3
from six.moves import reduce

from .numdict import NumDict
from .recompiled import tags


if PY3:
    long = int

# If some provider has an issue with functionality of SR, other than user
# agents, it's best to come talk to us rather than block.  It is no different
# than us going to a provider if we have questions or issues.
# Be a team player here. This is disabled, and was only added for testing,
# it has no config.ini or web ui setting.
# To enable, set SPOOF_USER_AGENT = True
SPOOF_USER_AGENT = False
INSTANCE_ID = str(uuid.uuid1())
USER_AGENT = u'Medusa/{version}({system}; {release}; {instance})'.format(
    version=u'0.0.1', system=platform.system(), release=platform.release(),
    instance=INSTANCE_ID)
ua_settings.DB = path.abspath(path.join(path.dirname(__file__), '../lib/fake_useragent/ua.json'))
UA_POOL = UserAgent()
if SPOOF_USER_AGENT:
    USER_AGENT = UA_POOL.random

cpu_presets = {
    'HIGH': 5,
    'NORMAL': 2,
    'LOW': 1,
    'DISABLED': 0
}

privacy_levels = {
    'absurd': 9002,
    'stupid': 9001,  # it's over 9000!
    'max': 9000,
    'high': 30,
    'normal': 20,
    'low': 10,
    'disabled': 0
}

# Other constants
MULTI_EP_RESULT = -1
SEASON_RESULT = -2

# Notification Types
NOTIFY_SNATCH = 1
NOTIFY_DOWNLOAD = 2
NOTIFY_SUBTITLE_DOWNLOAD = 3
NOTIFY_GIT_UPDATE = 4
NOTIFY_GIT_UPDATE_TEXT = 5
NOTIFY_LOGIN = 6
NOTIFY_LOGIN_TEXT = 7
NOTIFY_SNATCH_PROPER = 8

notifyStrings = NumDict({
    NOTIFY_SNATCH: "Started Download",
    NOTIFY_DOWNLOAD: "Download Finished",
    NOTIFY_SUBTITLE_DOWNLOAD: "Subtitle Download Finished",
    NOTIFY_GIT_UPDATE: "Medusa Updated",
    NOTIFY_GIT_UPDATE_TEXT: "Medusa Updated To Commit#: ",
    NOTIFY_LOGIN: "Medusa new login",
    NOTIFY_LOGIN_TEXT: "New login from IP: {0}. http://geomaplookup.net/?ip={0}",
    NOTIFY_SNATCH_PROPER: "Started PROPER Download"
})

# Episode statuses
UNKNOWN = -1  # should never happen
UNAIRED = 1  # episodes that haven't aired yet
SNATCHED = 2  # qualified with quality
WANTED = 3  # episodes we don't have but want to get
DOWNLOADED = 4  # qualified with quality
SKIPPED = 5  # episodes we don't want
ARCHIVED = 6  # non-local episodes (counts toward download completion stats)
IGNORED = 7  # episodes that you don't want included in your download stats
SNATCHED_PROPER = 9  # qualified with quality
SUBTITLED = 10  # qualified with quality
FAILED = 11  # episode downloaded or snatched we don't want
SNATCHED_BEST = 12  # episode re-downloaded using best quality

NAMING_REPEAT = 1
NAMING_EXTEND = 2
NAMING_DUPLICATE = 4
NAMING_LIMITED_EXTEND = 8
NAMING_SEPARATED_REPEAT = 16
NAMING_LIMITED_EXTEND_E_PREFIXED = 32

MULTI_EP_STRINGS = NumDict({
    NAMING_REPEAT: "Repeat",
    NAMING_SEPARATED_REPEAT: "Repeat (Separated)",
    NAMING_DUPLICATE: "Duplicate",
    NAMING_EXTEND: "Extend",
    NAMING_LIMITED_EXTEND: "Extend (Limited)",
    NAMING_LIMITED_EXTEND_E_PREFIXED: "Extend (Limited, E-prefixed)"
})


class Quality(object):
    """Determine quality and set status codes."""

    NONE = 0  # 0
    SDTV = 1  # 1
    SDDVD = 1 << 1  # 2
    HDTV = 1 << 2  # 4
    RAWHDTV = 1 << 3  # 8  -- 720p/1080i mpeg2 (trollhd releases)
    FULLHDTV = 1 << 4  # 16 -- 1080p HDTV (QCF releases)
    HDWEBDL = 1 << 5  # 32
    FULLHDWEBDL = 1 << 6  # 64 -- 1080p web-dl
    HDBLURAY = 1 << 7  # 128
    FULLHDBLURAY = 1 << 8  # 256
    UHD_4K_TV = 1 << 9  # 512 -- 2160p aka 4K UHD aka UHD-1
    UHD_4K_WEBDL = 1 << 10  # 1024
    UHD_4K_BLURAY = 1 << 11  # 2048
    UHD_8K_TV = 1 << 12  # 4096 -- 4320p aka 8K UHD aka UHD-2
    UHD_8K_WEBDL = 1 << 13  # 8192
    UHD_8K_BLURAY = 1 << 14  # 16384
    ANYHDTV = HDTV | FULLHDTV  # 20
    ANYWEBDL = HDWEBDL | FULLHDWEBDL  # 96
    ANYBLURAY = HDBLURAY | FULLHDBLURAY  # 384

    # put these bits at the other end of the spectrum,
    # far enough out that they shouldn't interfere
    UNKNOWN = 1 << 15  # 32768

    qualityStrings = NumDict({
        None: "None",
        NONE: "N/A",
        UNKNOWN: "Unknown",
        SDTV: "SDTV",
        SDDVD: "SD DVD",
        HDTV: "720p HDTV",
        RAWHDTV: "RawHD",
        FULLHDTV: "1080p HDTV",
        HDWEBDL: "720p WEB-DL",
        FULLHDWEBDL: "1080p WEB-DL",
        HDBLURAY: "720p BluRay",
        FULLHDBLURAY: "1080p BluRay",
        UHD_4K_TV: "4K UHD TV",
        UHD_8K_TV: "8K UHD TV",
        UHD_4K_WEBDL: "4K UHD WEB-DL",
        UHD_8K_WEBDL: "8K UHD WEB-DL",
        UHD_4K_BLURAY: "4K UHD BluRay",
        UHD_8K_BLURAY: "8K UHD BluRay",
    })

    sceneQualityStrings = NumDict({
        None: "None",
        NONE: "N/A",
        UNKNOWN: "Unknown",
        SDTV: "",
        SDDVD: "",
        HDTV: "720p",
        RAWHDTV: "1080i",
        FULLHDTV: "1080p",
        HDWEBDL: "720p",
        FULLHDWEBDL: "1080p",
        HDBLURAY: "720p BluRay",
        FULLHDBLURAY: "1080p BluRay",
        UHD_4K_TV: "2160p",
        UHD_8K_TV: "4320p",
        UHD_4K_WEBDL: "2160p",
        UHD_8K_WEBDL: "4320p",
        UHD_4K_BLURAY: "2160p BluRay",
        UHD_8K_BLURAY: "4320p BluRay",
    })

    combinedQualityStrings = NumDict({
        ANYHDTV: "HDTV",
        ANYWEBDL: "WEB-DL",
        ANYBLURAY: "BluRay"
    })

    cssClassStrings = NumDict({
        None: "None",
        NONE: "N/A",
        UNKNOWN: "Unknown",
        SDTV: "SDTV",
        SDDVD: "SDDVD",
        HDTV: "HD720p",
        RAWHDTV: "RawHD",
        FULLHDTV: "HD1080p",
        HDWEBDL: "HD720p",
        FULLHDWEBDL: "HD1080p",
        HDBLURAY: "HD720p",
        FULLHDBLURAY: "HD1080p",
        UHD_4K_TV: "UHD-4K",
        UHD_8K_TV: "UHD-8K",
        UHD_4K_WEBDL: "UHD-4K",
        UHD_8K_WEBDL: "UHD-8K",
        UHD_4K_BLURAY: "UHD-4K",
        UHD_8K_BLURAY: "UHD-8K",
        ANYHDTV: "any-hd",
        ANYWEBDL: "any-hd",
        ANYBLURAY: "any-hd"
    })

    statusPrefixes = NumDict({
        DOWNLOADED: "Downloaded",
        SNATCHED: "Snatched",
        SNATCHED_PROPER: "Snatched (Proper)",
        FAILED: "Failed",
        SNATCHED_BEST: "Snatched (Best)",
        ARCHIVED: "Archived"
    })

    @staticmethod
    def _get_status_strings(status):
        """
        Return string values associated with Status prefix.

        :param status: Status prefix to resolve
        :return: Human readable status value
        """
        to_return = {}
        for quality in Quality.qualityStrings:
            if quality is not None:
                stat = Quality.statusPrefixes[status]
                qual = Quality.qualityStrings[quality]
                comp = Quality.composite_status(status, quality)
                to_return[comp] = '%s (%s)' % (stat, qual)
        return to_return

    @staticmethod
    def combine_qualities(allowed_qualities, preferred_qualities):
        any_quality = 0
        best_quality = 0
        if allowed_qualities:
            any_quality = reduce(operator.or_, allowed_qualities)
        if preferred_qualities:
            best_quality = reduce(operator.or_, preferred_qualities)
        return any_quality | (best_quality << 16)

    @staticmethod
    def split_quality(quality):
        if quality is None:
            quality = Quality.NONE
        allowed_qualities = []
        preferred_qualities = []
        for cur_qual in Quality.qualityStrings:
            if cur_qual is None:
                cur_qual = Quality.NONE
            if cur_qual & quality:
                allowed_qualities.append(cur_qual)
            if cur_qual << 16 & quality:
                preferred_qualities.append(cur_qual)

        return sorted(allowed_qualities), sorted(preferred_qualities)

    @staticmethod
    def name_quality(name, anime=False, extend=True):
        """
        Return The quality from an episode File renamed by the application.

        If no quality is achieved it will try scene_quality regex

        :param name: to parse
        :param anime: Boolean to indicate if the show we're resolving is Anime
        :param extend: boolean to extend methods to try
        :return: Quality prefix
        """
        # Try Scene names first
        quality = Quality.scene_quality(name, anime)
        if quality != Quality.UNKNOWN:
            return quality

        # Additional methods to get quality should be added here
        if extend:
            return Quality._extend_quality(name)

        return Quality.UNKNOWN

    @staticmethod
    def scene_quality(name, anime=False):
        """
        Return The quality from the Scene episode File.

        :param name: Episode filename to analyse
        :param anime: Boolean to indicate if the show we're resolving is Anime
        :return: Quality
        """
        from .tagger.episode import EpisodeTags
        if not name:
            return Quality.UNKNOWN
        else:
            name = path.basename(name)

        result = None
        ep = EpisodeTags(name)

        if anime:
            sd_options = tags.anime_sd.search(name)
            hd_options = tags.anime_hd.search(name)
            full_hd = tags.anime_fullhd.search(name)
            ep.rex[u'bluray'] = tags.anime_bluray

            # BluRay
            if ep.bluray and (full_hd or hd_options):
                result = Quality.FULLHDBLURAY if full_hd else Quality.HDBLURAY
            # HD TV
            elif not ep.bluray and (full_hd or hd_options):
                result = Quality.FULLHDTV if full_hd else Quality.HDTV
            # SD DVD
            elif ep.dvd:
                result = Quality.SDDVD
            # SD TV
            elif sd_options:
                result = Quality.SDTV

            return Quality.UNKNOWN if result is None else result

        # Is it UHD?
        if ep.vres in [2160, 4320] and ep.scan == u'p':
            # BluRay
            full_res = (ep.vres == 4320)
            if ep.avc and ep.bluray:
                result = Quality.UHD_4K_BLURAY if not full_res else Quality.UHD_8K_BLURAY
            # WEB-DL
            elif (ep.avc and ep.itunes) or ep.web:
                result = Quality.UHD_4K_WEBDL if not full_res else Quality.UHD_8K_WEBDL
            # HDTV
            elif ep.avc and ep.tv == u'hd':
                result = Quality.UHD_4K_TV if not full_res else Quality.UHD_8K_TV

        # Is it HD?
        elif ep.vres in [1080, 720]:
            if ep.scan == u'p':
                # BluRay
                full_res = (ep.vres == 1080)
                if ep.avc and (ep.bluray or ep.hddvd):
                    result = Quality.FULLHDBLURAY if full_res else Quality.HDBLURAY
                # WEB-DL
                elif (ep.avc and ep.itunes) or ep.web:
                    result = Quality.FULLHDWEBDL if full_res else Quality.HDWEBDL
                # HDTV
                elif ep.avc and ep.tv == u'hd':
                    result = Quality.FULLHDTV if full_res else Quality.HDTV
                elif all([ep.vres == 720, ep.tv == u'hd', ep.mpeg]):
                    result = Quality.RAWHDTV
            elif (ep.res == u'1080i') and ep.tv == u'hd':
                if ep.mpeg or (ep.raw and ep.avc_non_free):
                    result = Quality.RAWHDTV
        elif ep.hrws:
            result = Quality.HDTV

        # Is it SD?
        elif ep.xvid or ep.avc:
            # Is it aussie p2p?  If so its 720p
            if all([ep.tv == u'hd', ep.widescreen, ep.aussie]):
                result = Quality.HDTV
            # SD DVD
            elif ep.dvd or ep.bluray:
                result = Quality.SDDVD
            # SDTV
            elif ep.res == u'480p' or any([ep.tv, ep.sat, ep.web]):
                result = Quality.SDTV

        return Quality.UNKNOWN if result is None else result

    @staticmethod
    def _extend_quality(file_path):
        """
        Try other methods to get the file quality.

        :param file_path: File path of episode to analyse
        :return: Quality prefix
        """
        quality = Quality.quality_from_file_meta(file_path)
        if quality != Quality.UNKNOWN:
            return quality

        # This assumes that any .ts file is RAWHDTV (probably wrong)
        if file_path.lower().endswith('.ts'):
            return Quality.RAWHDTV

        return Quality.UNKNOWN

    @staticmethod
    def quality_from_file_meta(file_path):
        """
        Get quality file file metadata.

        :param file_path: File path to analyse
        :return: Quality prefix
        """
        if not os.path.isfile(file_path):
            return Quality.UNKNOWN

        knowledge = knowit.know(file_path)

        if not knowledge:
            return Quality.UNKNOWN

        height = None
        for track in knowledge.get('video') or []:
            height = track.get('height')
            if height:
                break

        if not height:
            return Quality.UNKNOWN

        # TODO: Use knowledge information like 'resolution'
        base_filename = path.basename(file_path)
        bluray = re.search(r"blue?-?ray|hddvd|b[rd](rip|mux)", base_filename, re.I) is not None
        webdl = re.search(r"web.?dl|web(rip|mux|hd)", base_filename, re.I) is not None

        ret = Quality.UNKNOWN
        if 3240 < height:
            ret = ((Quality.UHD_8K_TV, Quality.UHD_8K_BLURAY)[bluray], Quality.UHD_8K_WEBDL)[webdl]
        if 1620 < height <= 3240:
            ret = ((Quality.UHD_4K_TV, Quality.UHD_4K_BLURAY)[bluray], Quality.UHD_4K_WEBDL)[webdl]
        elif 800 < height <= 1620:
            ret = ((Quality.FULLHDTV, Quality.FULLHDBLURAY)[bluray], Quality.FULLHDWEBDL)[webdl]
        elif 680 < height <= 800:
            ret = ((Quality.HDTV, Quality.HDBLURAY)[bluray], Quality.HDWEBDL)[webdl]
        elif height <= 680:
            ret = (Quality.SDTV, Quality.SDDVD)[re.search(r'dvd|b[rd]rip|blue?-?ray', base_filename, re.I) is not None]

        return ret

    composite_status_quality = namedtuple('composite_status', ['status', 'quality'])

    @staticmethod
    def composite_status(status, quality):
        if quality is None:
            quality = Quality.NONE
        return status + 100 * quality

    @staticmethod
    def quality_downloaded(status):
        return (status - DOWNLOADED) / 100

    @staticmethod
    def split_composite_status(status):
        """
        Split a composite status code into a status and quality.

        :param status: to split
        :returns: a namedtuple containing (status, quality)
        """
        status = long(status)
        if status == UNKNOWN:
            return Quality.composite_status_quality(UNKNOWN, Quality.UNKNOWN)

        for q in sorted(Quality.qualityStrings.keys(), reverse=True):
            if status > q * 100:
                return Quality.composite_status_quality(status - q * 100, q)

        return Quality.composite_status_quality(status, Quality.NONE)

    @staticmethod
    def scene_quality_from_name(name, quality):
        """
        Get Scene naming parameters from filename and quality.

        :param name: filename to check
        :type name: text_type
        :param quality: int of quality to make sure we get the right release type
        :type quality: int
        :return: release type and/or encoder type for scene quality naming
        :rtype: text_type
        """
        rel_type = ''
        name = name.lower()
        codec = re.search(r'[xh].?26[45]', name) or ''

        if codec and codec.group(0).endswith('4') or 'avc' in name:
            if codec and codec.group(0).startswith('h'):
                codec = ' h264'
            else:
                codec = ' x264'
        elif codec and codec.group(0).endswith('5') or 'hevc' in name:
            if codec and codec.group(0).startswith('h'):
                codec = ' h265'
            else:
                codec = ' x265'
        elif 'xvid' in name:
            codec = ' XviD'
        elif 'divx' in name:
            codec = ' DivX'

        # If any HDTV type or SDTV
        if quality in (1, 4, 8, 16, 512, 4096):
            rel_type = ' HDTV'
            if 'ahdtv' in name:
                rel_type = ' AHDTV'
            elif 'hr.pdtv' in name:
                rel_type = ' HR.PDTV'
            elif 'pdtv' in name:
                rel_type = ' PDTV'
            elif 'satrip' in name:
                rel_type = ' SATRip'
            elif 'dsr' in name:
                rel_type = ' DSR'
            elif 'uhdtv' in name:
                rel_type = ' UHDTV'

        # If SDDVD
        if quality == 2:
            rel_type = ' BDRip'
            if re.search(r'br(-| |\.)?(rip|mux)', name):
                rel_type = ' BRRip'
            elif re.search(r'dvd(-| |\.)?(rip|mux)', name):
                rel_type = ' DVDRip'

        # If any WEB type
        if quality in (32, 64, 1024, 8192):
            rel_type = ' WEB'
            if re.search(r'web(-| |\.)?dl', name):
                rel_type = ' WEB-DL'
            elif re.search(r'web(-| |\.)?(rip|mux)', name):
                rel_type = ' WEBRip'

        return rel_type + codec

    @staticmethod
    def status_from_name(name, anime=False):
        """
        Get a status object from filename.

        :param name: Filename to check
        :param anime: boolean to enable anime parsing
        :return: Composite status/quality object
        """
        quality = Quality.name_quality(name, anime)
        return Quality.composite_status(DOWNLOADED, quality)

    guessit_map = {
        '720p': {
            'HDTV': HDTV,
            'WEB-DL': HDWEBDL,
            'WEBRip': HDWEBDL,
            'BluRay': HDBLURAY,
        },
        '1080i': RAWHDTV,
        '1080p': {
            'HDTV': FULLHDTV,
            'WEB-DL': FULLHDWEBDL,
            'WEBRip': FULLHDWEBDL,
            'BluRay': FULLHDBLURAY
        },
        '4K': {
            'HDTV': UHD_4K_TV,
            'WEB-DL': UHD_4K_WEBDL,
            'WEBRip': UHD_4K_WEBDL,
            'BluRay': UHD_4K_BLURAY
        }
    }

    to_guessit_format_list = [
        ANYHDTV, ANYWEBDL, ANYBLURAY, ANYHDTV | UHD_4K_TV, ANYWEBDL | UHD_4K_WEBDL, ANYBLURAY | UHD_4K_BLURAY
    ]

    to_guessit_screen_size_map = {
        HDTV | HDWEBDL | HDBLURAY: '720p',
        RAWHDTV: '1080i',
        FULLHDTV | FULLHDWEBDL | FULLHDBLURAY: '1080p',
        UHD_4K_TV | UHD_4K_WEBDL | UHD_4K_BLURAY: '4K',
    }

    @staticmethod
    def should_search(status, show_obj, manually_searched):
        """Return true if that episodes should be search for a better quality."""
        cur_status, cur_quality = Quality.split_composite_status(int(status) or UNKNOWN)
        allowed_qualities, preferred_qualities = show_obj.current_qualities

        if manually_searched:
            return False

        if cur_status not in (WANTED, DOWNLOADED, SNATCHED, SNATCHED_PROPER):
            return False

        if cur_status != WANTED:
            if preferred_qualities:
                if cur_quality in preferred_qualities:
                    return False
            elif cur_quality in allowed_qualities:
                return False
        return True

    @staticmethod
    def should_replace(ep_status, old_quality, new_quality, allowed_qualities, preferred_qualities,
                       download_current_quality=False, force=False, manually_searched=False):
        """Return true if the old quality should be replaced with new quality.

        If not preferred qualities, then any downloaded quality is final
        if preferred quality, then new quality should be higher than existing one AND not be in preferred
        If new quality is already in preferred then is already final quality.
        Force (forced search) bypass episode status only or unknown quality
        """
        if ep_status and ep_status not in Quality.DOWNLOADED + Quality.SNATCHED + Quality.SNATCHED_PROPER:
            if not force:
                return False, 'Episode status is not DOWNLOADED|SNATCHED|SNATCHED PROPER. Ignoring new quality'

        if old_quality == Quality.UNKNOWN:
            if not force:
                return False, 'Existing quality is UNKNOWN. Ignoring new quality'

        if manually_searched:
            if not force:
                # We only allow replace a manual searched episode if is a forced search
                return False, 'Existing episode quality was manually snatched. Ignoring all new qualities'

        if not Quality.wanted_quality(new_quality, allowed_qualities, preferred_qualities):
            return False, 'New quality is not in any wanted quality lists. Ignoring new quality'

        if old_quality not in allowed_qualities + preferred_qualities:
            # If old quality is no longer wanted quality and new quality is wanted, we should replace.
            return True, 'Existing quality is no longer in any wanted quality lists. Accepting new quality'

        if force and download_current_quality:
            # If we already downloaded quality, just redownload it as long is still part of the wanted qualities
            return new_quality == old_quality, 'Redownloading same quality'

        if preferred_qualities:
            # Don't replace because old quality is already best quality.
            if old_quality in preferred_qualities:
                return False, 'Existing quality is already a preferred quality. Ignoring new quality'

            # Old quality is not final. Check if we should replace:

            # Replace if preferred quality
            if new_quality in preferred_qualities:
                return True, 'New quality is preferred. Accepting new quality'

            # Commented for now as Labrys requests
            # if new_quality > old_quality:
            #    return True, 'New quality is higher quality (but not preferred). Accepting new quality'

            return False, 'New quality is same/lower quality (and not preferred). Ignoring new quality'

        else:
            # Allowed quality should never be replaced
            return False, 'Existing quality is already final (allowed only). Ignoring new quality'

    @staticmethod
    def is_higher_quality(current_quality, new_quality, allowed_qualities, preferred_qualities):
        """Check is new quality is better than current quality based on allowed and preferred qualities."""
        if new_quality in preferred_qualities:
            return new_quality > current_quality
        elif new_quality in allowed_qualities:
            if current_quality in preferred_qualities:
                return False
            return new_quality > current_quality

    @staticmethod
    def wanted_quality(new_quality, allowed_qualities, preferred_qualities):
        """Check if new quality is wanted."""
        return new_quality in allowed_qualities + preferred_qualities

    @staticmethod
    def from_guessit(guess):
        """
        Return a Quality from a guessit dict.

        :param guess: guessit dict
        :type guess: dict
        :return: quality
        :rtype: int
        """
        screen_size = guess.get('screen_size')
        fmt = guess.get('format')

        if not screen_size or isinstance(screen_size, list):
            return Quality.UNKNOWN

        format_map = Quality.guessit_map.get(screen_size)
        if not format_map:
            return Quality.UNKNOWN

        if isinstance(format_map, int):
            return format_map

        if not fmt or isinstance(fmt, list):
            return Quality.UNKNOWN

        quality = format_map.get(fmt)
        return quality if quality is not None else Quality.UNKNOWN

    @staticmethod
    def to_guessit(status):
        """Return a guessit dict containing 'screen_size and format' from a Quality (composite status).

        :param status: a quality composite status
        :type status: int
        :return: dict {'screen_size': <screen_size>, 'format': <format>}
        :rtype: dict (str, str)
        """
        _, quality = Quality.split_composite_status(status)
        screen_size = Quality.to_guessit_screen_size(quality)
        fmt = Quality.to_guessit_format(quality)
        result = dict()
        if screen_size:
            result['screen_size'] = screen_size
        if fmt:
            result['format'] = fmt

        return result

    @staticmethod
    def to_guessit_format(quality):
        """Return a guessit format from a Quality.

        :param quality: the quality
        :type quality: int
        :return: guessit format
        :rtype: str
        """
        for q in Quality.to_guessit_format_list:
            if quality & q:
                key = q & (512 - 1)  # 4k formats are bigger than 384 and are not part of ANY* bit set
                return Quality.combinedQualityStrings.get(key)

    @staticmethod
    def to_guessit_screen_size(quality):
        """Return a guessit screen_size from a Quality.

        :param quality: the quality
        :type quality: int
        :return: guessit screen_size
        :rtype: str
        """
        for key, value in Quality.to_guessit_screen_size_map.items():
            if quality & key:
                return value

    DOWNLOADED = None
    SNATCHED = None
    SNATCHED_PROPER = None
    FAILED = None
    SNATCHED_BEST = None
    ARCHIVED = None


Quality.DOWNLOADED = [Quality.composite_status(DOWNLOADED, x) for x in Quality.qualityStrings if x is not None]
Quality.SNATCHED = [Quality.composite_status(SNATCHED, x) for x in Quality.qualityStrings if x is not None]
Quality.SNATCHED_BEST = [Quality.composite_status(SNATCHED_BEST, x) for x in Quality.qualityStrings if x is not None]
Quality.SNATCHED_PROPER = [Quality.composite_status(SNATCHED_PROPER, x) for x in Quality.qualityStrings if x is not None]
Quality.FAILED = [Quality.composite_status(FAILED, x) for x in Quality.qualityStrings if x is not None]
Quality.ARCHIVED = [Quality.composite_status(ARCHIVED, x) for x in Quality.qualityStrings if x is not None]

Quality.DOWNLOADED.sort()
Quality.SNATCHED.sort()
Quality.SNATCHED_BEST.sort()
Quality.SNATCHED_PROPER.sort()
Quality.FAILED.sort()
Quality.ARCHIVED.sort()

HD720p = Quality.combine_qualities([Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY], [])
HD1080p = Quality.combine_qualities([Quality.FULLHDTV, Quality.FULLHDWEBDL, Quality.FULLHDBLURAY], [])
UHD_4K = Quality.combine_qualities([Quality.UHD_4K_TV, Quality.UHD_4K_WEBDL, Quality.UHD_4K_BLURAY], [])
UHD_8K = Quality.combine_qualities([Quality.UHD_8K_TV, Quality.UHD_8K_WEBDL, Quality.UHD_8K_BLURAY], [])

SD = Quality.combine_qualities([Quality.SDTV, Quality.SDDVD], [])
HD = Quality.combine_qualities([HD720p, HD1080p], [])
UHD = Quality.combine_qualities([UHD_4K, UHD_8K], [])
ANY = Quality.combine_qualities([SD, HD, UHD], [])

# legacy template, cant remove due to reference in main_db upgrade?
BEST = Quality.combine_qualities([Quality.SDTV, Quality.HDTV, Quality.HDWEBDL], [Quality.HDTV])

qualityPresets = (
    ANY,
    SD,
    HD, HD720p, HD1080p,
    UHD, UHD_4K, UHD_8K,
)

qualityPresetStrings = NumDict({
    SD: "SD",
    HD: "HD",
    HD720p: "HD720p",
    HD1080p: "HD1080p",
    UHD: "UHD",
    UHD_4K: "UHD-4K",
    UHD_8K: "UHD-8K",
    ANY: "Any",
})


class StatusStrings(NumDict):
    """Dictionary containing strings for status codes."""

    # todo: Make views return Qualities too
    qualities = Quality.DOWNLOADED + Quality.SNATCHED + Quality.SNATCHED_PROPER + Quality.SNATCHED_BEST + \
        Quality.ARCHIVED + Quality.FAILED

    def __missing__(self, key):
        """
        If the key is not found try to determine a status from Quality.

        :param key: A numeric key or None
        :raise KeyError: if the key is invalid and can't be determined from Quality
        """
        # convert key to number
        key = self.numeric(key)  # raises KeyError if it can't
        if key in self.qualities:  # if key isn't found check in qualities
            current = Quality.split_composite_status(key)
            return '{status} ({quality})'.format(
                status=self[current.status],
                quality=Quality.qualityStrings[current.quality]
            ) if current.quality else self[current.status]
        else:  # the key wasn't found in qualities either
            raise KeyError(key)  # ... so the key is invalid

    def __contains__(self, key):
        try:
            key = self.numeric(key)
            return key in self.data or key in self.qualities
        except KeyError:
            return False


# Assign strings to statuses
statusStrings = StatusStrings({
    UNKNOWN: "Unknown",
    UNAIRED: "Unaired",
    SNATCHED: "Snatched",
    DOWNLOADED: "Downloaded",
    SKIPPED: "Skipped",
    SNATCHED_PROPER: "Snatched (Proper)",
    WANTED: "Wanted",
    ARCHIVED: "Archived",
    IGNORED: "Ignored",
    SUBTITLED: "Subtitled",
    FAILED: "Failed",
    SNATCHED_BEST: "Snatched (Best)"
})


class Overview(object):
    UNAIRED = UNAIRED  # 1
    SNATCHED = SNATCHED  # 2
    WANTED = WANTED  # 3
    GOOD = DOWNLOADED  # 4
    SKIPPED = SKIPPED  # 5
    SNATCHED_PROPER = SNATCHED_PROPER  # 9
    SNATCHED_BEST = SNATCHED_BEST  # 12

    # Should suffice!
    QUAL = 50

    overviewStrings = NumDict({
        SKIPPED: "skipped",
        WANTED: "wanted",
        QUAL: "qual",
        GOOD: "good",
        UNAIRED: "unaired",
        SNATCHED: "snatched",
        # we can give these a different class later, otherwise
        # breaks checkboxes in displayShow for showing different statuses
        SNATCHED_BEST: "snatched",
        SNATCHED_PROPER: "snatched"
    })


countryList = {
    'Australia': 'AU',
    'Canada': 'CA',
    'USA': 'US'
}
