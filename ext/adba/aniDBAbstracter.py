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

import logging
import os
import re
from six import string_types
import string

from . import aniDBfileInfo as fileInfo
from .aniDBerrors import *
from .aniDBmaper import AniDBMaper
from .aniDBtvDBmaper import TvDBMap
from .aniDBfileInfo import read_anidb_xml

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class aniDBabstractObject(object):
    def __init__(self, aniDB, load=False):
        self.laoded = False
        self.set_connection(aniDB)
        if load:
            self.load_data()

    def set_connection(self, aniDB):
        self.aniDB = aniDB

    def _fill(self, dataline):
        for key in dataline:
            try:
                tmp_list = dataline[key].split("'")
                if len(tmp_list) > 1:
                    new_list = []
                    for i in tmp_list:
                        try:
                            new_list.append(int(i))
                        except:
                            new_list.append(i)
                    self.__dict__[key] = new_list
                    continue
            except:
                pass
            try:
                self.__dict__[key] = int(dataline[key])
            except:
                # self.__dict__[key] = text_type(dataline[key], "utf-8")
                self.__dict__[key] = dataline[key]
            key = property(lambda x: dataline[key])

    def __getattr__(self, name):
        try:
            return object.__getattribute__(self, name)
        except:
            return None

    def _build_names(self):
        names = []
        names = self._easy_extend(names, self.english_name)
        names = self._easy_extend(names, self.short_name_list)
        names = self._easy_extend(names, self.synonym_list)
        names = self._easy_extend(names, self.other_name)

        self.allNames = names

    @staticmethod
    def _easy_extend(initialList, item):
        if item:
            if isinstance(item, list):
                initialList.extend(item)
            elif isinstance(item, string_types):
                initialList.append(item)

        return initialList

    def load_data(self):
        return False

    def add_notification(self):
        """
        type - Type of notification: type=>  0=all, 1=new, 2=group, 3=complete
        priority - low = 0, medium = 1, high = 2 (unconfirmed)

        """
        if self.aid:
            self.aniDB.notifyadd(aid=self.aid, type=1, priority=1)


class Anime(aniDBabstractObject):
    def __init__(self, aniDB, name=None, aid=None, tvdbid=None, paramsA=None, autoCorrectName=False, load=False, cache_path=None):

        self.maper = AniDBMaper()

        if cache_path and not os.path.exists(cache_path):
            os.makedirs(cache_path)

        self.tvDBMap = TvDBMap(cache_path)
        self.allAnimeXML = None

        self.name = name
        self.aid = aid
        self.tvdb_id = tvdbid
        self.cache_path = cache_path

        if self.tvdb_id and not self.aid:
            self.aid = self.tvDBMap.get_anidb_for_tvdb(self.tvdb_id)

        if not (self.name or self.aid):
            raise AniDBIncorrectParameterError("No aid or name available")

        if not self.aid:
            self.aid = self._get_aid_from_xml(self.name)
        # if not self.name or autoCorrectName:
        #    self.name = self._get_name_from_xml(self.aid)

        if not (self.name or self.aid):
            raise ValueError

        if not self.tvdb_id:
            self.tvdb_id = self.tvDBMap.get_tvdb_for_anidb(self.aid)

        if not paramsA:
            self.bitCode = "b2f0e0fc000000"
            self.params = self.maper.getAnimeCodesA(self.bitCode)
        else:
            self.paramsA = paramsA
            self.bitCode = self.maper.getAnimeBitsA(self.paramsA)

        super(Anime, self).__init__(aniDB, load)

    def load_data(self):
        """load the data from anidb"""

        if not (self.name or self.aid):
            raise ValueError

        self.rawData = self.aniDB.anime(aid=self.aid, aname=self.name, amask=self.bitCode)
        if self.rawData.datalines:
            self._fill(self.rawData.datalines[0])
            self._builPreSequal()
            self.laoded = True

    def return_raw_data(self):
        """Returns all raw data from request"""
        return self.rawData

    def get_groups(self):
        if not self.aid:
            return []
        self.rawData = self.aniDB.groupstatus(aid=self.aid)
        self.release_groups = []
        for line in self.rawData.datalines:
            self.release_groups.append({"name": line["name"],
                                        "rating": line["rating"],
                                        "range": line["episode_range"]
                                        })
        return self.release_groups

    # TODO: refactor and use the new functions in anidbFileinfo
    def _get_aid_from_xml(self, name):
        if not self.allAnimeXML:
            self.allAnimeXML = read_anidb_xml(self.cache_path)

        regex = re.compile('( \(\d{4}\))|[%s]' % re.escape(string.punctuation))  # remove any punctuation and e.g. ' (2011)'
        # regex = re.compile('[%s]'  % re.escape(string.punctuation)) # remove any punctuation and e.g. ' (2011)'
        name = regex.sub('', name.lower())
        last_aid = 0
        for element in self.allAnimeXML.iter():
            if element.get("aid", False):
                last_aid = int(element.get("aid"))
            if element.text:
                testname = regex.sub('', element.text.lower())

                if testname == name:
                    return last_aid
        return 0

    # TODO: refactor and use the new functions in anidbFileinfo
    def _get_name_from_xml(self, aid, onlyMain=True):
        if not self.allAnimeXML:
            self.allAnimeXML = read_anidb_xml(self.cache_path)

        for anime in self.allAnimeXML.findall("anime"):
            if int(anime.get("aid", False)) == aid:
                for title in anime.getiterator():
                    current_lang = title.get("{http://www.w3.org/XML/1998/namespace}lang", False)
                    current_type = title.get("type", False)
                    if (current_lang == "en" and not onlyMain) or current_type == "main":
                        return title.text
        return ""

    def _builPreSequal(self):
        if self.related_aid_list and self.related_aid_type:
            try:
                for i in range(len(self.related_aid_list)):
                    if self.related_aid_type[i] == 2:
                        self.__dict__["prequal"] = self.related_aid_list[i]
                    elif self.related_aid_type[i] == 1:
                        self.__dict__["sequal"] = self.related_aid_list[i]
            except:
                if self.related_aid_type == 2:
                    self.__dict__["prequal"] = self.related_aid_list
                elif self.str_related_aid_type == 1:
                    self.__dict__["sequal"] = self.related_aid_list


class Episode(aniDBabstractObject):
    def __init__(self, aniDB, number=None, epid=None, filePath=None, fid=None, epno=None, paramsA=None, paramsF=None, load=False, calculate=False):
        if not aniDB and not number and not epid and not filePath and not fid:
            return None

        self.maper = AniDBMaper()
        self.epid = epid
        self.filePath = filePath
        self.fid = fid
        self.epno = epno
        if calculate:
            (self.ed2k, self.size) = self._calculate_file_stuff(self.filePath)

        if not paramsA:
            self.bitCodeA = "C000F0C0"
            self.paramsA = self.maper.getFileCodesA(self.bitCodeA)
        else:
            self.paramsA = paramsA
            self.bitCodeA = self.maper.getFileBitsA(self.paramsA)

        if not paramsF:
            self.bitCodeF = "7FF8FEF8"
            self.paramsF = self.maper.getFileCodesF(self.bitCodeF)
        else:
            self.paramsF = paramsF
            self.bitCodeF = self.maper.getFileBitsF(self.paramsF)

        super(Episode, self).__init__(aniDB, load)

    def load_data(self):
        """load the data from anidb"""
        if self.filePath and not (self.ed2k or self.size):
            (self.ed2k, self.size) = self._calculate_file_stuff(self.filePath)

        self.rawData = self.aniDB.file(fid=self.fid, size=self.size, ed2k=self.ed2k, aid=self.aid, aname=None, gid=None, gname=None, epno=self.epno, fmask=self.bitCodeF, amask=self.bitCodeA)
        self._fill(self.rawData.datalines[0])
        self._build_names()
        self.laoded = True

    def add_to_mylist(self, state=None, viewed=None, source=None, storage=None, other=None):
        """
        state    - the location of the file
                viewed    - whether you have watched the file (0=unwatched,1=watched)
                source    - where you got the file (bittorrent,dc++,ed2k,...)
                storage    - for example the title of the cd you have this on
                other    - other data regarding this file

        structure of state:
                value    meaning
                0    unknown    - state is unknown or the user doesn't want to provide this information
                1    on hdd    - the file is stored on hdd
                2    on cd    - the file is stored on cd
                3    deleted    - the file has been deleted or is not available for other reasons (i.e. reencoded)
        """
        if self.filePath and not (self.ed2k or self.size):
            (self.ed2k, self.size) = self._calculate_file_stuff(self.filePath)
        try:
            self.aniDB.mylistadd(size=self.size, ed2k=self.ed2k, state=state, viewed=viewed, source=source, storage=storage, other=other)
        except Exception as e:
            logger.exception("Exception: %s", e)
        else:
            # TODO: add the name or something
            logger.info("Added the episode to anidb")

    def edit_to_mylist(self, state=None, viewed=None, source=None, storage=None, other=None):
        """
        state    - the location of the file
                viewed    - whether you have watched the file (0=unwatched,1=watched)
                source    - where you got the file (bittorrent,dc++,ed2k,...)
                storage    - for example the title of the cd you have this on
                other    - other data regarding this file

        structure of state:
                value    meaning
                0    unknown    - state is unknown or the user doesn't want to provide this information
                1    on hdd    - the file is stored on hdd
                2    on cd    - the file is stored on cd
                3    deleted    - the file has been deleted or is not available for other reasons (i.e. reencoded)
        """
        if self.filePath and not (self.ed2k or self.size):
            (self.ed2k, self.size) = self._calculate_file_stuff(self.filePath)
        try:
            edit_response = self.aniDB.mylistadd(size=self.size, ed2k=self.ed2k, edit=1, state=state, viewed=viewed, source=source, storage=storage, other=other)
        except Exception as e:
            logger.exception("Exception: %s", e)
        # handling the case that the entry is not in anidb yet, non ideal to check the string but isinstance is having issue
        # currently raises an exception for less changes in the code, unsure if this is the ideal way to do so
        if edit_response.codestr == "NO_SUCH_MYLIST_ENTRY":
            logger.info("attempted an edit before add")
            raise AniDBError("Attempted to edit file without adding")
        else:
            logger.info("Edited the episode in anidb")

    def delete_from_mylist(self):
        if self.filePath and not (self.ed2k or self.size):
            (self.ed2k, self.size) = self._calculate_file_stuff(self.filePath)
        try:
            self.aniDB.mylistdel(size=self.size, ed2k=self.ed2k)
        except Exception as e:
            logger.exception("Exception: %s", e)
        else:
            logger.info("Deleted the episode from anidb")

    @staticmethod
    def _calculate_file_stuff(filePath):
        if not filePath:
            return None, None
        logger.info("Calculating the ed2k. Please wait...")
        ed2k = fileInfo.get_ED2K(filePath)
        size = fileInfo.get_file_size(filePath)
        return ed2k, size
