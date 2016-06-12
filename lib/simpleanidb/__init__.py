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

ANIME_LIST_URL = "http://anidb.net/api/anime-titles.xml.gz"

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

        self.anime_list_path = os.path.join(
            self._cache_dir, "anime-titles.xml.gz")
        self.auto_download = auto_download
        self._xml = None
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

    def search(self, term, autoload=False):
        if not self._xml:
            try:
                self._xml = self._read_file(self.anime_list_path)
            except IOError:
                if self.auto_download:
                    self.download_anime_list()
                    self._xml = self._read_file(self.anime_list_path)
                else:
                    raise

        term = term.lower()
        anime_ids = []
        for anime in self._xml.findall("anime"):
            for title in anime.findall("title"):
                if term in title.text.lower():
                    anime_ids.append((int(anime.get("aid")), anime))
                    break
        return [Anime(self, aid, autoload, xml_node) for aid, xml_node in anime_ids]

    def anime(self, aid):
        return Anime(self, aid)

    def _read_file(self, path):
        f = open(path, 'rb')
        return etree.ElementTree(file=f)

    def download_anime_list(self, force=False):
        if not force and os.path.exists(self.anime_list_path):
            modified_date = datetime.fromtimestamp(
                os.path.getmtime(self.anime_list_path))
            if modified_date + timedelta(1) > datetime.now():
                return False
        return download_file(self.anime_list_path, ANIME_LIST_URL)

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
