#!/usr/bin/env python
# coding=utf-8
#
# This file is part of aDBa.
#
# aDBa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# aDBa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with aDBa.  If not, see <http://www.gnu.org/licenses/>.


import hashlib
import logging
import os
import pickle
import requests
import sys
import time
import xml.etree.cElementTree as etree


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# http://www.radicand.org/blog/orz/2010/2/21/edonkey2000-hash-in-python/
def get_ED2K(filePath, forceHash=False, cacheLocation=os.path.normpath(sys.path[0] + os.sep + "ED2KCache.pickle")):
    """ Returns the ed2k hash of a given file."""
    if not filePath:
        return None
    md4 = hashlib.new('md4').copy
    ed2k_chunk_size = 9728000
    try:
        get_ED2K.ED2KCache
    except:
        if os.path.isfile(cacheLocation):
            with open(cacheLocation, 'rb') as f:
                get_ED2K.ED2KCache = pickle.load(f)
        else:
            get_ED2K.ED2KCache = {}

    def gen(f):
        while True:
            x = f.read(ed2k_chunk_size)
            if x:
                yield x
            else:
                return

    def md4_hash(data):
        m = md4()
        m.update(data)
        return m

    def writeCacheToDisk():
        try:
            if len(get_ED2K.ED2KCache) != 0:
                with open(cacheLocation, 'wb') as f:
                    pickle.dump(get_ED2K.ED2KCache, f, pickle.HIGHEST_PROTOCOL)
        except:
            logger.error("Error occurred while writing back to disk")
        return

    file_modified_time = os.path.getmtime(filePath)
    file_name = os.path.basename(filePath)
    try:
        cached_file_modified_time = get_ED2K.ED2KCache[file_name][1]
    except:
        # if not existing in cache it will be caught by other test
        cached_file_modified_time = file_modified_time

    if forceHash or file_modified_time > cached_file_modified_time or file_name not in get_ED2K.ED2KCache:
        with open(filePath, 'rb') as f:
            file_size = os.path.getsize(filePath)
            # if file size is small enough the ed2k hash is the same as the md4 hash
            if file_size <= ed2k_chunk_size:
                full_file = f.read()
                new_hash = md4_hash(full_file).hexdigest()
            else:
                a = gen(f)
                hashes = [md4_hash(data).digest() for data in a]
                combinedhash = bytearray()
                for hash in hashes:
                    combinedhash.extend(hash)
                new_hash = md4_hash(combinedhash).hexdigest()
            get_ED2K.ED2KCache[file_name] = (new_hash, file_modified_time)
            writeCacheToDisk()
            return new_hash
    else:
        return get_ED2K.ED2KCache[file_name][0]


def get_file_size(path):
    size = os.path.getsize(path)
    return size


def read_anidb_xml(file_path=None):
    if not file_path:
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "animetitles.xml")
    elif not file_path.endswith("xml"):
        file_path = os.path.join(file_path, "animetitles.xml")
    return read_xml_into_etree(file_path)


def read_tvdb_map_xml(file_path=None):
    if not file_path:
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "anime-list.xml")
    elif not file_path.endswith(".xml"):
        file_path = os.path.join(file_path, "anime-list.xml")
    return read_xml_into_etree(file_path)


def read_xml_into_etree(filePath):
    if not filePath:
        return None

    if not os.path.isfile(filePath):
        if not get_anime_titles_xml(filePath):
            return
    else:
        mtime = os.path.getmtime(filePath)
        if time.time() > mtime + 24 * 60 * 60:
            if not get_anime_titles_xml(filePath):
                return

    xml_a_setree = etree.ElementTree().parse(filePath)
    return xml_a_setree


def _remove_file_failed(file):
    try:
        os.remove(file)
    except OSError:
        logger.warning("Error occurred while trying to remove file %s", file)


def download_file(url, filename):
    try:
        r = requests.get(url, stream=True, verify=False)
        r.raise_for_status()
        with open(filename, 'wb') as fp:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    fp.write(chunk)
                    fp.flush()

    except (requests.HTTPError, requests.exceptions.RequestException):
        _remove_file_failed(filename)
        return False
    except (requests.ConnectionError, requests.Timeout):
        return False

    return True


def get_anime_titles_xml(path):
    return download_file("https://raw.githubusercontent.com/ScudLee/anime-lists/master/animetitles.xml", path)


def get_anime_list_xml(path):
    return download_file("https://raw.githubusercontent.com/ScudLee/anime-lists/master/anime-list.xml", path)
