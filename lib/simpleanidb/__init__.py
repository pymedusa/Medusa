from __future__ import absolute_import, unicode_literals

import os
from os import makedirs, path
import xml.etree.cElementTree as etree
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import tempfile
import getpass
from appdirs import user_cache_dir
from simpleanidb.helper import download_file
from simpleanidb.models import Anime
from simpleanidb.exceptions import GeneralError

import requests

__version__ = '0.1.0'
__author__ = 'Dennis Lutter'

# Get this file directly from anidb batch import api
ANIME_TITLES_URL = 'http://anidb.net/api/anime-titles.xml.gz'

# Get this file from ScudLee's managed anidb lists
ANIME_LIST_URL = 'https://raw.githubusercontent.com/ScudLee/anime-lists/master/anime-list.xml'

# Url for the anidb http api
ANIDB_URL = 'http://api.anidb.net:9001/httpapi'

# Request list Types
REQUEST_CATEGORY_LIST = 'categorylist'
REQUEST_RANDOM_RECOMMENDATION = 'randomrecommendtion'
REQUEST_HOT = 'hotanime'


class Anidb(object):
    def __init__(self, session=None, cache_dir=None, auto_download=True, lang=None):  # pylint: disable=too-many-arguments
        self._init_cache(cache_dir)

        self.session = session or requests.Session()
        self.session.headers.setdefault('user-agent', 'simpleanidb/{0}.{1}.{2}'.format(*__version__))

        self.auto_download = auto_download
        self._xml_titles = self._xml = None
        self._xml_list = None
        self.lang = lang
        if not lang:
            self.lang = 'en'

    @staticmethod
    def _get_temp_dir():
        """Returns the system temp dir"""
        if hasattr(os, 'getuid'):
            uid = 'u{0}'.format(os.getuid())
            path = os.path.join(tempfile.gettempdir(), 'simpleanidb-{0}'.format(uid))
        else:
            # For Windows
            try:
                uid = getpass.getuser()
                path = os.path.join(tempfile.gettempdir(), 'simpleanidb-{0}'.format(uid))
            except ImportError:
                path = os.path.join(tempfile.gettempdir(), 'simpleanidb')

        # Create the directory
        if not os.path.exists(path):
            os.makedirs(path)

        return path

    def _load_xml(self, url, force=False):
        local_file = os.path.join(self._cache_dir, url.split('/')[-1])
        xml = None

        if self.auto_download:
            self.download_anime_list(local_file, url, force)
        xml = self._read_file(local_file)

        return xml

    def _init_cache(self, cache_dir, refresh=False):
        if not cache_dir:
            self._cache_dir = user_cache_dir('simpleanidb', appauthor='simpleanidb')  # appauthor is requered on windows
            if not os.path.isdir(self._cache_dir):
                os.makedirs(self._cache_dir)
        else:
            if not path.exists(cache_dir):
                makedirs(cache_dir)

            self._cache_dir = cache_dir
        if not os.path.isdir(self._cache_dir):
            raise ValueError('{0} does not exist'.format(self._cache_dir))
        elif not os.access(self._cache_dir, os.W_OK):
            raise IOError('{0} is not writable'.format(self._cache_dir))

    def refresh(self):
        """Refresh the xml_lists."""
        self._xml_list = self._load_xml(ANIME_LIST_URL, force=True)
        self._xml_titles = self._load_xml(ANIME_TITLES_URL, force=True)

    def search(self, term=None, autoload=False, aid=None, tvdbid=None):
        anime_ids = []

        if not self._xml_titles:
            self._xml_titles = self._load_xml(ANIME_TITLES_URL)

        if term:
            for anime in self._xml_titles.findall('anime'):
                term = term.lower()
                for title in anime.findall('title'):
                    if term in title.text.lower():
                        anime_ids.append((int(anime.get('aid')), anime))
                        break

        elif aid:
            anime = self._xml_titles.find(".//anime[@aid='{aid}']".format(aid=aid))
            anime_ids.append((aid, anime))

        elif tvdbid:
            list_aids = self.tvdb_id_to_aid(tvdbid)
            for aid in list_aids:
                anime_ids.append((aid, self._xml_titles.find(".//anime[@aid='{aid}']".format(aid=aid))))

        return [Anime(self, aid, autoload, xml_node) for aid, xml_node in anime_ids]

    def aid_to_tvdb_id(self, aid):
        """
        Tranlates an aid (anidb.info anime id) to tvdbid (thetvdb.com).
        :param aid: The aid in int or string
        :return: One tvdbid as string, or None.
        """
        if not self._xml_list:
            self._xml_list = self._load_xml(ANIME_LIST_URL)

        anime = self._xml_list.find(".//anime[@anidbid='{aid}']".format(aid=aid))
        return anime.attrib.get('tvdbid') if anime else None

    def tvdb_id_to_aid(self, tvdbid):
        """
        Tranlates a tvdbid to aid (anidb.info anime id)
        :param tvdbid: The tvdbid in int or string
        :return: A list of matched aid's, as one show on tvdb can be matched to multiple on anidb.info, due to season mappings.
        """
        if not self._xml_list:
            self._xml_list = self._load_xml(ANIME_LIST_URL)

        return [anime_xml.get('anidbid') for anime_xml in
                self._xml_list.findall(".//anime[@tvdbid='{tvdbid}']".
                                       format(tvdbid=tvdbid))]

    def anime(self, aid):
        return Anime(self, aid)

    def _read_file(self, path):
        f = open(path, 'rb')
        return etree.ElementTree(file=f)

    def download_anime_list(self, anime_list_path, anidb_archive_url, force=False):
        if not force and os.path.exists(anime_list_path):
            modified_date = datetime.fromtimestamp(
                os.path.getmtime(anime_list_path))
            if modified_date + timedelta(1) > datetime.now():
                return False
        return download_file(anime_list_path, anidb_archive_url)

    def get_list(self, request_type):
        """Retrieve a lists of animes from anidb.info
        @param request_type: type of list, options are:
        REQUEST_CATEGORY_LIST, REQUEST_RANDOM_RECOMMENDATION, REQUEST_HOST

        @return: A list of Anime objects.
        """
        params = {
            'request': 'anime',
            'client': 'adbahttp',
            'clientver': 100,
            'protover': 1,
            'request': request_type
        }

        self._get_url(ANIDB_URL, params=params)

        anime_ids = []
        for anime in self._xml.findall('anime'):
            anime_ids.append((int(anime.get('id')), anime))

        return [Anime(self, aid, False, xml_node) for aid, xml_node in anime_ids]

    def _get_url(self, url, params=None):
        """Get the an anime or list of animes in XML, raise for status for an unexpected result"""
        if not params:
            params = {}

        r = self.session.get(url, params=params)

        r.raise_for_status()

        self._xml = ET.fromstring(r.content)
        if self._xml.tag == 'error':
            raise GeneralError(self._xml.text)

        return self._xml
