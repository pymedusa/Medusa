from __future__ import absolute_import
import os
import xml.etree.cElementTree as etree
from datetime import datetime, timedelta
import tempfile
import getpass
from appdirs import user_cache_dir
import requests
from simpleanidb.helper import download_file
from simpleanidb.models import Anime
from simpleanidb.exceptions import GeneralError
import xml.etree.ElementTree as ET

__version__ = "0.1.0"
__author__ = "Dennis Lutter"

# Get this file directly from anidb batch import api
ANIME_TITLES_URL = "http://anidb.net/api/anime-titles.xml.gz"

# Get this file from ScudLee's managed anidb lists
ANIME_LIST_URL = "https://raw.githubusercontent.com/ScudLee/anime-lists/master/anime-list.xml"

# Url for the anidb http api
ANIDB_URL = \
    "http://api.anidb.net:9001/httpapi"

# Request list Types
REQUEST_CATEGORY_LIST = "categorylist"
REQUEST_RANDOM_RECOMMENDATION = "randomrecommendtion"
REQUEST_HOT = "hotanime"


class Anidb(object):
    def __init__(self, session=None, cache_dir=None, auto_download=True, lang=None):  # pylint: disable=too-many-arguments
        if not cache_dir:
            self._cache_dir = user_cache_dir("simpleanidb", appauthor="simpleanidb")  # appauthor is requered on windows
            if not os.path.isdir(self._cache_dir):
                os.makedirs(self._cache_dir)
        else:
            self._cache_dir = cache_dir
        if not os.path.isdir(self._cache_dir):
            raise ValueError("'%s' does not exist" % self._cache_dir)
        elif not os.access(self._cache_dir, os.W_OK):
            raise IOError("'%s' is not writable" % self._cache_dir)

        self.session = session or requests.Session()
        self.session.headers.setdefault('user-agent', 'simpleanidb/{0}.{1}.{2}'.format(*__version__))

        self.anime_titles_path = os.path.join(
            self._cache_dir, "anime-titles.xml.gz")
        self.anime_list_path = os.path.join(
            self._cache_dir, "anime-list.xml.gz")
        self.auto_download = auto_download
        self._xml_titles = self._xml = None
        self._xml_list = None
        self.lang = lang
        if not lang:
            self.lang = "en"

    def _get_temp_dir(self):
        """Returns the system temp dir"""
        if hasattr(os, 'getuid'):
            uid = "u%d" % (os.getuid())
            path = os.path.join(tempfile.gettempdir(), "simpleanidb-%s" % (uid))
        else:
            # For Windows
            try:
                uid = getpass.getuser()
                path = os.path.join(tempfile.gettempdir(), "simpleanidb-%s" % (uid))
            except ImportError:
                path = os.path.join(tempfile.gettempdir(), "simpleanidb")

        # Create the directory
        if not os.path.exists(path):
            os.makedirs(path)

        return path

    def _load_xml(self, url):
        local_file = os.path.join(self._cache_dir, url.split('/')[-1])
        xml = None
        try:
            xml = self._read_file(local_file)
        except IOError:
            if self.auto_download:
                self.download_anime_list(local_file, url)
                xml = self._read_file(local_file)
            else:
                raise
        return xml

    def search(self, term=None, autoload=False, aid=None, tvdbid=None):
        if not self._xml_list:
            self._xml_list = self._load_xml(ANIME_LIST_URL)

        if not self._xml_titles:
            self._xml_titles = self._load_xml(ANIME_TITLES_URL)

        anime_ids = []
        if term:
            for anime in self._xml_titles.findall("anime"):
                term = term.lower()
                for title in anime.findall("title"):
                    if term in title.text.lower():
                        anime_ids.append((int(anime.get("aid")), anime))
                        break
        else:
            if aid:
                for anime in self._xml_list.findall("anime"):
                    if aid == int(anime.attrib.get('anidbid')):
                        anime_ids.append((int(anime.attrib.get('anidbid')), anime))
                        break

            elif tvdbid:
                for anime in self._xml_list.findall("anime"):
                    try:
                        if tvdbid == int(anime.attrib.get('tvdbid')):
                            anime_ids.append((int(anime.attrib.get('anidbid')), anime))
                            break
                    except:
                        continue

        return [Anime(self, aid, autoload, xml_node) for aid, xml_node in anime_ids]

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
            "request": "anime",
            "client": "adbahttp",
            "clientver": 100,
            "protover": 1,
            "request": request_type
        }

        self._get_url(ANIDB_URL, params=params)

        anime_ids = []
        for anime in self._xml.findall("anime"):
            anime_ids.append((int(anime.get("id")), anime))

        return [Anime(self, aid, False, xml_node) for aid, xml_node in anime_ids]

    def _get_url(self, url, params=None):
        """Get the an anime or list of animes in XML, raise for status for an unexpected result"""
        if not params:
            params = {}

        r = self.session.get(url, params=params)

        r.raise_for_status()

        self._xml = ET.fromstring(r.text.encode("UTF-8"))
        if self._xml.tag == 'error':
            raise GeneralError(self._xml.text)

        return self._xml
