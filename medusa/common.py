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
from __future__ import division
from __future__ import unicode_literals

import logging
import operator
import os
import platform
import re
import uuid
from functools import reduce

import knowit

from medusa.logger.adapters.style import BraceAdapter
from medusa.recompiled import tags
from medusa.search import PROPER_SEARCH

from six import text_type, viewitems

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

INSTANCE_ID = text_type(uuid.uuid1())
VERSION = '0.4.6'
USER_AGENT = 'Medusa/{version} ({system}; {release}; {instance})'.format(
    version=VERSION, system=platform.system(), release=platform.release(),
    instance=INSTANCE_ID)

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

notifyStrings = {
    NOTIFY_SNATCH: 'Started Download',
    NOTIFY_DOWNLOAD: 'Download Finished',
    NOTIFY_SUBTITLE_DOWNLOAD: 'Subtitle Download Finished',
    NOTIFY_GIT_UPDATE: 'Medusa Updated',
    NOTIFY_GIT_UPDATE_TEXT: 'Medusa Updated To Commit#: ',
    NOTIFY_LOGIN: 'Medusa new login',
    NOTIFY_LOGIN_TEXT: 'New login from IP: {0}. http://geomaplookup.net/?ip={0}',
    NOTIFY_SNATCH_PROPER: 'Started Proper Download'
}

# Episode statuses
UNSET = -1  # default episode status
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
NAMING_LIMITED_EXTEND_E_UPPER_PREFIXED = 32
NAMING_LIMITED_EXTEND_E_LOWER_PREFIXED = 64

MULTI_EP_STRINGS = {
    NAMING_REPEAT: 'Repeat',
    NAMING_SEPARATED_REPEAT: 'Repeat (Separated)',
    NAMING_DUPLICATE: 'Duplicate',
    NAMING_EXTEND: 'Extend',
    NAMING_LIMITED_EXTEND: 'Extend (Limited)',
    NAMING_LIMITED_EXTEND_E_UPPER_PREFIXED: 'Extend (Limited, E-prefixed)',
    NAMING_LIMITED_EXTEND_E_LOWER_PREFIXED: 'Extend (Limited, e-prefixed)'
}


statusStrings = {
    ARCHIVED: 'Archived',
    DOWNLOADED: 'Downloaded',
    FAILED: 'Failed',
    IGNORED: 'Ignored',
    SKIPPED: 'Skipped',
    SNATCHED: 'Snatched',
    SNATCHED_BEST: 'Snatched (Best)',
    SNATCHED_PROPER: 'Snatched (Proper)',
    SUBTITLED: 'Subtitled',
    UNAIRED: 'Unaired',
    UNSET: 'Unset',
    WANTED: 'Wanted'
}


class Quality(object):

    NA = 0  # 0
    UNKNOWN = 1  # 1
    SDTV = 1 << 1  # 2
    SDDVD = 1 << 2  # 4
    HDTV = 1 << 3  # 8
    RAWHDTV = 1 << 4  # 16 -- 720p/1080i mpeg2
    FULLHDTV = 1 << 5  # 32 -- 1080p HDTV
    HDWEBDL = 1 << 6  # 64
    FULLHDWEBDL = 1 << 7  # 128 -- 1080p web-dl
    HDBLURAY = 1 << 8  # 256
    FULLHDBLURAY = 1 << 9  # 512
    UHD_4K_TV = 1 << 10  # 1024 -- 2160p aka 4K UHD aka UHD-1
    UHD_4K_WEBDL = 1 << 11  # 2048
    UHD_4K_BLURAY = 1 << 12  # 4096
    UHD_8K_TV = 1 << 13  # 8192 -- 4320p aka 8K UHD aka UHD-2
    UHD_8K_WEBDL = 1 << 14  # 16384
    UHD_8K_BLURAY = 1 << 15  # 32768
    ANYHDTV = HDTV | FULLHDTV  # 40
    ANYWEBDL = HDWEBDL | FULLHDWEBDL  # 192
    ANYBLURAY = HDBLURAY | FULLHDBLURAY  # 768

    qualityStrings = {
        NA: 'N/A',
        UNKNOWN: 'Unknown',
        SDTV: 'SDTV',
        SDDVD: 'SD DVD',
        HDTV: '720p HDTV',
        RAWHDTV: 'RawHD',
        FULLHDTV: '1080p HDTV',
        HDWEBDL: '720p WEB-DL',
        FULLHDWEBDL: '1080p WEB-DL',
        HDBLURAY: '720p BluRay',
        FULLHDBLURAY: '1080p BluRay',
        UHD_4K_TV: '4K UHD TV',
        UHD_8K_TV: '8K UHD TV',
        UHD_4K_WEBDL: '4K UHD WEB-DL',
        UHD_8K_WEBDL: '8K UHD WEB-DL',
        UHD_4K_BLURAY: '4K UHD BluRay',
        UHD_8K_BLURAY: '8K UHD BluRay',
    }

    scene_quality_strings = {
        NA: 'N/A',
        UNKNOWN: 'Unknown',
        SDTV: '',
        SDDVD: '',
        HDTV: '720p',
        RAWHDTV: '1080i',
        FULLHDTV: '1080p',
        HDWEBDL: '720p',
        FULLHDWEBDL: '1080p',
        HDBLURAY: '720p BluRay',
        FULLHDBLURAY: '1080p BluRay',
        UHD_4K_TV: '2160p',
        UHD_8K_TV: '4320p',
        UHD_4K_WEBDL: '2160p',
        UHD_8K_WEBDL: '4320p',
        UHD_4K_BLURAY: '2160p BluRay',
        UHD_8K_BLURAY: '4320p BluRay',
    }

    combined_quality_strings = {
        ANYHDTV: 'HDTV',
        ANYWEBDL: 'WEB-DL',
        ANYBLURAY: 'BluRay',
    }

    # A reverse map from quality values and any-sets to "keys"
    quality_keys = {
        NA: 'na',
        UNKNOWN: 'unknown',
        SDTV: 'sdtv',
        SDDVD: 'sddvd',
        HDTV: 'hdtv',
        RAWHDTV: 'rawhdtv',
        FULLHDTV: 'fullhdtv',
        HDWEBDL: 'hdwebdl',
        FULLHDWEBDL: 'fullhdwebdl',
        HDBLURAY: 'hdbluray',
        FULLHDBLURAY: 'fullhdbluray',
        UHD_4K_TV: 'uhd4ktv',
        UHD_4K_WEBDL: 'uhd4kwebdl',
        UHD_4K_BLURAY: 'uhd4kbluray',
        UHD_8K_TV: 'uhd8ktv',
        UHD_8K_WEBDL: 'uhd8kwebdl',
        UHD_8K_BLURAY: 'uhd8kbluray',
        ANYHDTV: 'anyhdtv',
        ANYWEBDL: 'anywebdl',
        ANYBLURAY: 'anybluray',
    }

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
        allowed_qualities = []
        preferred_qualities = []
        for cur_qual in Quality.qualityStrings:
            if cur_qual & quality:
                allowed_qualities.append(cur_qual)
            if cur_qual << 16 & quality:
                preferred_qualities.append(cur_qual)

        return sorted(allowed_qualities), sorted(preferred_qualities)

    @staticmethod
    def is_valid_combined_quality(quality):
        """
        Check quality value to make sure it is a valid combined quality.

        :param quality: Quality to check
        :type quality: int
        :return: True if valid, False if not
        """
        for cur_qual in Quality.qualityStrings:
            if cur_qual & quality:
                quality -= cur_qual
            if cur_qual << 16 & quality:
                quality -= cur_qual << 16
        return quality == 0

    @staticmethod
    def name_quality(name, anime=False, extend=True):
        """
        Return the quality from an episode filename.

        :param name: to parse
        :param anime: Boolean to indicate if the show we're resolving is anime
        :param extend: boolean to extend methods to try
        :return: Quality
        """
        # Try getting the quality from the filename
        quality = Quality.quality_from_name(name, anime)
        if quality != Quality.UNKNOWN:
            return quality

        # Additional methods to get quality should be added here
        if extend:
            return Quality._extend_quality(name)

        return Quality.UNKNOWN

    @staticmethod
    def quality_from_name(path, anime=False):
        """
        Return the quality from the episode filename or its parent folder.

        :param path: Episode filename or its parent folder
        :param anime: Boolean to indicate if the show we're resolving is anime
        :return: Quality
        """
        from medusa.tagger.episode import EpisodeTags

        if not path:
            return Quality.UNKNOWN

        result = None
        name = os.path.basename(path)
        ep = EpisodeTags(name)

        if anime:
            sd_options = tags.anime_sd.search(name)
            hd_options = tags.anime_hd.search(name)
            full_hd = tags.anime_fullhd.search(name)
            ep.rex['bluray'] = tags.anime_bluray

            # BluRay
            if ep.bluray and (full_hd or hd_options):
                result = Quality.FULLHDBLURAY if full_hd else Quality.HDBLURAY
            # HDTV
            elif full_hd or hd_options:
                result = Quality.FULLHDTV if full_hd else Quality.HDTV
            # SDDVD
            elif ep.dvd:
                result = Quality.SDDVD
            # SDTV
            elif sd_options:
                result = Quality.SDTV

            return Quality.UNKNOWN if result is None else result

        # Is it UHD?
        if ep.vres in [2160, 4320]:
            is_4320 = ep.vres == 4320
            if ep.scan == 'p':
                # BluRay
                if ep.bluray:
                    result = Quality.UHD_8K_BLURAY if is_4320 else Quality.UHD_4K_BLURAY
                # WEB-DL
                elif ep.web:
                    result = Quality.UHD_8K_WEBDL if is_4320 else Quality.UHD_4K_WEBDL
                # HDTV
                else:
                    result = Quality.UHD_8K_TV if is_4320 else Quality.UHD_4K_TV

        # Is it HD?
        elif ep.vres in [1080, 720]:
            is_1080 = ep.vres == 1080
            if ep.scan == 'p':
                # BluRay
                if ep.bluray or ep.hddvd:
                    result = Quality.FULLHDBLURAY if is_1080 else Quality.HDBLURAY
                # WEB-DL
                elif ep.web:
                    result = Quality.FULLHDWEBDL if is_1080 else Quality.HDWEBDL
                # HDTV and MPEG2 encoded
                elif ep.tv == 'hd' and ep.mpeg:
                    result = Quality.RAWHDTV
                # HDTV
                else:
                    result = Quality.FULLHDTV if is_1080 else Quality.HDTV
            elif ep.scan == 'i' and ep.tv == 'hd' and (ep.mpeg or (ep.raw and ep.avc_non_free)):
                result = Quality.RAWHDTV
        elif ep.hrws:
            result = Quality.HDTV

        # Is it SD?
        elif ep.dvd or ep.bluray:
            # SD DVD
            result = Quality.SDDVD
        elif ep.web and not ep.web.lower().endswith('hd'):
            # This should be Quality.WEB in the future
            result = Quality.SDTV
        elif ep.tv or any([ep.res == '480p', ep.sat]):
            # SDTV/HDTV
            result = Quality.SDTV

        if result is not None:
            return result

        # Try to get the quality from the parent folder
        parent_folder = os.path.basename(os.path.dirname(path))
        if parent_folder:
            return Quality.quality_from_name(parent_folder, anime)

        return Quality.UNKNOWN

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
        Get quality from file metadata.

        :param file_path: File path to analyse
        :return: Quality prefix
        """
        if not os.path.isfile(file_path):
            return Quality.UNKNOWN

        try:
            knowledge = knowit.know(file_path)
        except knowit.KnowitException as error:
            log.warning(
                'An error occurred while parsing: {path}\n'
                'KnowIt reported:\n{report}', {
                    'path': file_path,
                    'report': error,
                })
            return Quality.UNKNOWN

        if not knowledge:
            return Quality.UNKNOWN

        height = None
        for track in knowledge.get('video') or []:
            height = track.get('height')
            if height:
                break

        if not height:
            return Quality.UNKNOWN

        height = int(height.magnitude)

        # TODO: Use knowledge information like 'resolution'
        base_filename = os.path.basename(file_path)
        bluray = re.search(r'blue?-?ray|hddvd|b[rd](rip|mux)', base_filename, re.I) is not None
        webdl = re.search(r'web.?dl|web(rip|mux|hd)', base_filename, re.I) is not None

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
        if quality in (Quality.SDTV, Quality.HDTV, Quality.RAWHDTV, Quality.FULLHDTV,
                       Quality.UHD_4K_TV, Quality.UHD_8K_TV):
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

        if quality == Quality.SDDVD:
            rel_type = ' BDRip'
            if re.search(r'br(-| |\.)?(rip|mux)', name):
                rel_type = ' BRRip'
            elif re.search(r'dvd(-| |\.)?(rip|mux)', name):
                rel_type = ' DVDRip'

        # If any WEB type
        if quality in (Quality.HDWEBDL, Quality.FULLHDWEBDL, Quality.UHD_4K_WEBDL,
                       Quality.UHD_8K_WEBDL):
            rel_type = ' WEB'
            if re.search(r'web(-| |\.)?dl', name):
                rel_type = ' WEB-DL'
            elif re.search(r'web(-| |\.)?(rip|mux)', name):
                rel_type = ' WEBRip'

        return rel_type + codec

    @staticmethod
    def should_search(cur_status, cur_quality, show_obj, manually_searched):
        """Return true if that episodes should be search for a better quality.

        :param cur_status: current status of the episode
        :param cur_quality: current quality of the episode
        :param show_obj: Series object of the episode we will check if we should search or not
        :param manually_searched: if episode was manually searched by user
        :return: True if need to run a search for given episode
        """
        allowed_qualities, preferred_qualities = show_obj.current_qualities

        # When user manually searched, we should consider this as final quality.
        if manually_searched:
            return False, 'Episode was manually searched. Skipping episode'

        #  Can't be SNATCHED_BEST because the quality is already final (unless user changes qualities).
        #  All other status will return false: IGNORED, SKIPPED, FAILED.
        if cur_status not in (WANTED, DOWNLOADED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST):
            return False, 'Status is not allowed: {0}. Skipping episode'.format(statusStrings[cur_status])

        # If current status is WANTED, we must always search
        if cur_status != WANTED:
            if cur_quality not in allowed_qualities + preferred_qualities:
                return True, 'Quality is not in Allowed|Preferred. Searching episode'
            elif preferred_qualities:
                if cur_quality in preferred_qualities:
                    return False, 'Quality is already Preferred. Skipping episode'
                else:
                    return True, 'Quality is not Preferred. Searching episode'
            elif cur_quality in allowed_qualities:
                return False, 'Quality is already Allowed. Skipping episode'
        else:
            return True, 'Status is WANTED. Searching episode'

        return False, 'No rule set to allow the search'

    @staticmethod
    def should_replace(ep_status, old_quality, new_quality, allowed_qualities, preferred_qualities,
                       download_current_quality=False, force=False, manually_searched=False, search_type=None):
        """Return true if the old quality should be replaced with new quality.

        If not preferred qualities, then any downloaded quality is final
        If preferred quality, then new quality should be higher than existing one AND not be in preferred
        If new quality is already in preferred then is already final quality
        Force (forced search) bypass episode status only or unknown quality

        :param ep_status: current status of the episode
        :param old_quality: current quality of the episode
        :param new_quality: quality of the episode we found
        :param allowed_qualities: List of selected allowed qualities of the show we are checking
        :param preferred_qualities: List of selected preferred qualities of the show we are checking
        :param download_current_quality: True if user wants the same existing quality to be snatched
        :param force: True if user did a forced search for that episode
        :param manually_searched: True if episode was manually searched
        :param search_type: The search type, that started this method
        :return: True if the old quality should be replaced with new quality
        """
        if not ep_status or ep_status not in (DOWNLOADED, SNATCHED, SNATCHED_PROPER):
            if not force:
                return False, 'Episode status is not Downloaded, Snatched or Snatched Proper. Ignoring new quality'

        if manually_searched:
            if not force:
                # We only allow replace a manual searched episode if is a forced search
                return False, 'Existing episode quality was manually snatched. Ignoring all new qualities'

        if not Quality.wanted_quality(new_quality, allowed_qualities, preferred_qualities):
            return False, 'New quality is not in any wanted quality lists. Ignoring new quality'

        if search_type == PROPER_SEARCH:
            if new_quality == old_quality:
                return True, 'New quality is the same as the existing quality. Accepting PROPER'
            return False, 'New quality is different from the existing quality.' \
                          'Ignoring PROPER, as we only PROPER the same release.'

        if old_quality not in allowed_qualities + preferred_qualities:
            # If old quality is no longer wanted quality and new quality is wanted, we should replace.
            return True, 'Existing quality is no longer in any wanted quality lists. Accepting new quality'

        if download_current_quality and force and new_quality == old_quality:
            # If we already downloaded quality, just redownload it as long is still part of the wanted qualities
            return True, 'Re-downloading same quality'

        if preferred_qualities:
            # Don't replace because old quality is already best quality.
            if old_quality in preferred_qualities:
                return False, 'Existing quality is already a preferred quality. Ignoring new quality'

            # Replace if preferred quality
            if new_quality in preferred_qualities:
                return True, 'New quality is preferred. Accepting new quality'

            if new_quality > old_quality:
                return True, 'New quality is higher quality (and allowed). Accepting new quality'
            else:
                return False, 'New quality is same/lower quality (and not preferred). Ignoring new quality'

        else:
            # Allowed quality should never be replaced
            return False, 'Existing quality is already final (allowed only). Ignoring new quality'

    @staticmethod
    def is_higher_quality(current_quality, new_quality, allowed_qualities, preferred_qualities):
        """Check is new quality is better than current quality based on allowed and preferred qualities."""
        if new_quality in preferred_qualities:
            if current_quality in preferred_qualities:
                return new_quality > current_quality
            return True
        elif new_quality in allowed_qualities:
            if current_quality in preferred_qualities:
                return False
            elif current_quality in allowed_qualities:
                return new_quality > current_quality
            return True

    @staticmethod
    def wanted_quality(new_quality, allowed_qualities, preferred_qualities):
        """Check if new quality is wanted."""
        return new_quality in allowed_qualities + preferred_qualities

    # Map guessit screen sizes and sources to our Quality values
    guessit_map = {
        '720p': {
            'HDTV': HDTV,
            'Web': HDWEBDL,
            'Blu-ray': HDBLURAY,
        },
        '1080i': RAWHDTV,
        '1080p': {
            'HDTV': FULLHDTV,
            'Web': FULLHDWEBDL,
            'Blu-ray': FULLHDBLURAY
        },
        '2160p': {
            'HDTV': UHD_4K_TV,
            'Web': UHD_4K_WEBDL,
            'Blu-ray': UHD_4K_BLURAY
        },
        '4320p': {
            'HDTV': UHD_8K_TV,
            'Web': UHD_8K_WEBDL,
            'Blu-ray': UHD_8K_BLURAY
        }
    }

    # Consolidate the guessit-supported screen sizes of each source
    to_guessit_source_map = {
        ANYHDTV | UHD_4K_TV | UHD_8K_TV: 'HDTV',
        ANYWEBDL | UHD_4K_WEBDL | UHD_8K_WEBDL: 'Web',
        ANYBLURAY | UHD_4K_BLURAY | UHD_8K_BLURAY: 'Blu-ray'
    }

    # Consolidate the sources of each guessit-supported screen size
    to_guessit_screen_size_map = {
        HDTV | HDWEBDL | HDBLURAY: '720p',
        RAWHDTV: '1080i',
        FULLHDTV | FULLHDWEBDL | FULLHDBLURAY: '1080p',
        UHD_4K_TV | UHD_4K_WEBDL | UHD_4K_BLURAY: '2160p',
        UHD_8K_TV | UHD_8K_WEBDL | UHD_8K_BLURAY: '4320p',
    }

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
        source = guess.get('source')

        if not screen_size or isinstance(screen_size, list):
            return Quality.UNKNOWN

        source_map = Quality.guessit_map.get(screen_size)
        if not source_map:
            return Quality.UNKNOWN

        if isinstance(source_map, int):
            return source_map

        if not source or isinstance(source, list):
            return Quality.UNKNOWN

        quality = source_map.get(source)
        return quality if quality is not None else Quality.UNKNOWN

    @staticmethod
    def to_guessit(quality):
        """
        Return a guessit dict containing 'screen_size and source' from a Quality.

        :param quality: a quality
        :type quality: int
        :return: dict {'screen_size': <screen_size>, 'source': <source>}
        :rtype: dict (str, str)
        """
        if quality not in Quality.qualityStrings:
            quality = Quality.UNKNOWN

        screen_size = Quality.to_guessit_screen_size(quality)
        source = Quality.to_guessit_source(quality)
        result = dict()
        if screen_size:
            result['screen_size'] = screen_size
        if source:
            result['source'] = source

        return result

    @staticmethod
    def to_guessit_source(quality):
        """
        Return a guessit source from a Quality.

        :param quality: the quality
        :type quality: int
        :return: guessit source
        :rtype: str
        """
        for quality_set, source in viewitems(Quality.to_guessit_source_map):
            if quality_set & quality:
                return source

    @staticmethod
    def to_guessit_screen_size(quality):
        """
        Return a guessit screen_size from a Quality.

        :param quality: the quality
        :type quality: int
        :return: guessit screen_size
        :rtype: str
        """
        for quality_set, screen_size in viewitems(Quality.to_guessit_screen_size_map):
            if quality_set & quality:
                return screen_size


HD720p = Quality.combine_qualities([Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY], [])
HD1080p = Quality.combine_qualities([Quality.FULLHDTV, Quality.FULLHDWEBDL, Quality.FULLHDBLURAY], [])
UHD_4K = Quality.combine_qualities([Quality.UHD_4K_TV, Quality.UHD_4K_WEBDL, Quality.UHD_4K_BLURAY], [])
UHD_8K = Quality.combine_qualities([Quality.UHD_8K_TV, Quality.UHD_8K_WEBDL, Quality.UHD_8K_BLURAY], [])

SD = Quality.combine_qualities([Quality.SDTV, Quality.SDDVD], [])
HD = Quality.combine_qualities([HD720p, HD1080p], [])
UHD = Quality.combine_qualities([UHD_4K, UHD_8K], [])
ANY = Quality.combine_qualities([SD, HD, UHD], [])

qualityPresets = (
    ANY,
    SD,
    HD, HD720p, HD1080p,
    UHD, UHD_4K, UHD_8K,
)

qualityPresetStrings = {
    SD: 'SD',
    HD: 'HD',
    HD720p: 'HD720p',
    HD1080p: 'HD1080p',
    UHD: 'UHD',
    UHD_4K: 'UHD-4K',
    UHD_8K: 'UHD-8K',
    ANY: 'Any',
}


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

    overviewStrings = {
        SKIPPED: 'skipped',
        WANTED: 'wanted',
        QUAL: 'allowed',
        GOOD: 'preferred',
        UNAIRED: 'unaired',
        SNATCHED: 'snatched',
        # we can give these a different class later, otherwise
        # breaks checkboxes in displayShow for showing different statuses
        SNATCHED_BEST: 'snatched',
        SNATCHED_PROPER: 'snatched'
    }


countryList = {
    'Australia': 'AU',
    'Canada': 'CA',
    'USA': 'US'
}
