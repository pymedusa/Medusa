# coding=utf-8

"""Episode tagger to extract information from episodes."""

from __future__ import unicode_literals

import re

from ..helper.common import try_int
from ..recompiled import tags


class EpisodeTags(object):
    """
    Quality tags
    """
    def __init__(self, name):
        self.name = name
        self.rex = {
            'res': tags.resolution,
            'bluray': tags.bluray,
            'web': tags.web,
            'itunes': tags.itunes,
            'dvd': tags.dvd,
            'sat': tags.sat,
            'tv': tags.tv,
            'avc': tags.avc,
            'mpeg': tags.mpeg,
            'xvid': tags.xvid,
            'wide': tags.widescreen,
            'aussie': tags.aussie,
            'netflix': tags.netflix,
        }

    def _get_match_obj(self, attr, regex=None, flags=0):
        match_obj = '%s_match' % attr
        try:
            return getattr(self, match_obj)
        except (KeyError, AttributeError):
            regex = regex or self.rex[attr]
            result = regex.search(self.name, flags)
            setattr(self, match_obj, result)
            return result

    # RESOLUTION
    @property
    def res(self):
        """
        The resolution tag found in the name

        :returns: an empty string if not found
        """
        attr = 'res'
        match = self._get_match_obj(attr)
        return '' if not match else match.group().lower()

    @property
    def vres(self):
        """
        The vertical found in the name

        :returns: an empty string if not found
        """
        attr = 'res'
        match = self._get_match_obj(attr)
        return None if not match else try_int(match.group('vres'))

    @property
    def scan(self):
        """
        The type of scan found in the name

        e.g. `i` for Interlaced, `p` for Progressive Scan

        :returns: an empty string if not found
        """
        attr = 'res'
        match = self._get_match_obj(attr)
        return '' if not match else match.group('scan').lower()

    @property
    def widescreen(self):
        """
        The wide screen tag found in the name

        :return: an empty string if not found
        """
        attr = 'wide'
        match = self._get_match_obj(attr)
        return '' if not match else match.group()

    # SOURCES
    @property
    def bluray(self):
        """
        The bluray tag found in the name

        :returns: an empty string if not found
        """
        attr = 'bluray'
        match = self._get_match_obj(attr)
        return '' if not match else match.group()

    @property
    def hddvd(self):
        """
        The hddvd tag found in the name

        :returns: an empty string if not found
        """
        attr = 'dvd'
        match = self._get_match_obj(attr)
        return None if not match else match.group('hd')

    @property
    def itunes(self):
        """
        The iTunes tag found in the name

        :returns: an empty string if not found
        """
        attr = 'itunes'
        match = self._get_match_obj(attr)
        return '' if not match else match.group()

    @property
    def web(self):
        """
        The web tag found in the name

        :returns: an empty string if not found
        """
        if 'dlmux' in self.name.lower():
            return 'dlmux'

        if self.netflix:
            return self.netflix

        else:
            attr = 'web'
            match = self._get_match_obj(attr)
            return '' if not match else match.group('type') or match.group(0)

    @property
    def sat(self):
        """
        The sat tag found in the name

        :returns: an empty string if not found
        """
        attr = 'sat'
        match = self._get_match_obj(attr)
        return None if not match else match.group()

    @property
    def dvdrip(self):
        """
        The dvd tag found in the name

        :returns: an empty string if not found
        """
        attr = 'dvd'
        match = self._get_match_obj(attr)
        return '' if not match else match.group('rip')

    @property
    def dvd(self):
        """
        The dvd tag found in the name

        :returns: an empty string if not found
        """
        attr = 'dvd'
        match = self._get_match_obj(attr)
        return '' if not (match or self.hddvd) else match.group()

    @property
    def tv(self):
        attr = 'tv'
        match = self._get_match_obj(attr)
        return '' if not match else (match.group(1) or match.group(2)).lower()

    # CODECS
    @property
    def hevc(self):
        """
        The hevc tag found in the name

        :returns: an empty string if not found
        """
        return '' if not (self.avc[:-1] == '5') else self.avc

    @property
    def avc(self):
        """
        The avc tag found in the name

        :returns: an empty string if not found
        """
        attr = 'avc'
        match = self._get_match_obj(attr)
        return '' if not match else match.group()

    @property
    def avc_free(self):
        """
        The free avc codec found in the name
        e.g.: x.265 or X264

        :returns: an empty string if not found
        """
        return '' if self.avc_non_free else self.avc

    @property
    def avc_non_free(self):
        """
        The non-free avc codec found in the name
        e.g.: h.265 or H264

        :returns: an empty string if not found
        """
        return '' if not self.avc.lower().startswith('h') else self.avc

    @property
    def mpeg(self):
        """
        The mpeg tag found in the name

        :returns: an empty string if not found
        """
        attr = 'mpeg'
        match = self._get_match_obj(attr)
        return '' if not match else match.group()

    @property
    def xvid(self):
        """
        The xvid tag found in the name

        :returns: an empty string if not found
        """
        attr = 'xvid'
        match = self._get_match_obj(attr)
        return '' if not match else match.group()

    # MISCELLANEOUS
    @property
    def hrws(self):
        """
        The hrws tag found in the name

        HR = High Resolution
        WS = Wide Screen
        PD TV = Pure Digital Television

        :returns: an empty string if not found
        """
        attr = 'hrws'
        match = None
        if self.avc and self.tv == 'pd':
            regex = re.compile(r'(hr.ws.pdtv).%s' % self.avc, re.IGNORECASE)
            match = self._get_match_obj(attr, regex)
        return '' if not match else match.group()

    @property
    def raw(self):
        """
        The raw tag found in the name

        :return: an empty string if not found
        """
        attr = 'raw'
        match = None
        if self.res and self.tv == 'hd':
            regex = re.compile(r'(%s.hdtv)' % self.res, re.IGNORECASE)
            match = self._get_match_obj(attr, regex)
        return '' if not match else match.group()

    @property
    def aussie(self):
        """
        Aussie p2p release groups

        :return: the aussie p2p release group
        """
        attr = 'aussie'
        match = self._get_match_obj(attr)
        return '' if not match else match.group()

    @property
    def netflix(self):
        """
        Netflix tag found in name

        :return: an empty string if not found
        """
        attr = 'netflix'
        match = self._get_match_obj(attr)
        return '' if not match else match.group()
