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

import fnmatch
import os
import re
from collections import namedtuple

import medusa as app
from six import string_types
from . import common, logger
from .helper.encoding import ek
from .name_parser.parser import InvalidNameException, InvalidShowException, NameParser
from .scene_exceptions import get_scene_exceptions

resultFilters = [
    "(dir|sub|nfo)fix",
    "(?<!shomin.)sample",
    "(dvd)?extras",
]

if hasattr('General', 'ignore_und_subs') and app.IGNORE_UND_SUBS:
    resultFilters.append("sub(bed|ed|pack|s)")

if hasattr('General', 'ignored_subs_list') and app.IGNORED_SUBS_LIST:
    resultFilters.append("(" + app.IGNORED_SUBS_LIST.replace(",", "|") + ")sub(bed|ed|s)?")


def containsAtLeastOneWord(name, words):
    """
    Filters out results based on filter_words

    name: name to check
    words : string of words separated by a ',' or list of words

    Returns: False if the name doesn't contain any word of words list, or the found word from the list.
    """
    if not (name and words):
        return False

    if isinstance(words, string_types):
        words = words.split(',')
    items = [(re.compile(r'(^|[\W_])%s($|[\W_])' % word.strip(), re.I), word.strip()) for word in words]
    for regexp, word in items:
        if regexp.search(name):
            # subs_words = '.dub.' or '.dksub.' or else
            subs_word = regexp.search(name).group(0)
            # If word is a regex like "dub(bed)?" or "sub(bed|ed|pack|s)"
            # then return just the matched word: "dub" and not full regex
            if word in resultFilters:
                return subs_word.replace(".", "")
            else:
                return word

    return False


def filterBadReleases(name, parse=True):
    """
    Filters out non-english and just all-around stupid releases by comparing them
    to the resultFilters contents.

    name: the release name to check

    Returns: True if the release name is OK, False if it's bad.
    """

    try:
        if parse:
            NameParser().parse(name)
    except InvalidNameException as error:
        logger.log(u"{}".format(error), logger.DEBUG)
        return False
    except InvalidShowException:
        pass

    # if any of the bad strings are in the name then say no
    word = containsAtLeastOneWord(name, resultFilters)
    if word:
        logger.log(u"Unwanted scene release: {0}. Contains unwanted word: {1}. Ignoring it".format(name, word), logger.DEBUG)
        return False
    return True


def allPossibleShowNames(show, season=-1):
    """
    Figures out every possible variation of the name for a particular show. Includes TVDB name, TVRage name,
    country codes on the end, eg. "Show Name (AU)", and any scene exception names.

    show: a TVShow object that we should get the names of

    Returns: a list of all the possible show names
    """

    showNames = get_scene_exceptions(show.indexerid, season=season)
    if not showNames:  # if we dont have any season specific exceptions fallback to generic exceptions
        season = -1
        showNames = get_scene_exceptions(show.indexerid, season=season)

    showNames.append(show.name)

    if not show.is_anime:
        newShowNames = []
        country_list = common.countryList
        country_list.update(dict(zip(common.countryList.values(), common.countryList.keys())))
        for curName in set(showNames):
            if not curName:
                continue

            # if we have "Show Name Australia" or "Show Name (Australia)" this will add "Show Name (AU)" for
            # any countries defined in common.countryList
            # (and vice versa)
            for curCountry in country_list:
                if curName.endswith(' ' + curCountry):
                    newShowNames.append(curName.replace(' ' + curCountry, ' (' + country_list[curCountry] + ')'))
                elif curName.endswith(' (' + curCountry + ')'):
                    newShowNames.append(curName.replace(' (' + curCountry + ')', ' (' + country_list[curCountry] + ')'))

            # # if we have "Show Name (2013)" this will strip the (2013) show year from the show name
            # newShowNames.append(re.sub('\(\d{4}\)', '', curName))

        showNames += newShowNames

    return set(showNames)


def determineReleaseName(dir_name=None, nzb_name=None):
    """Determine a release name from an nzb and/or folder name"""

    if nzb_name is not None:
        logger.log(u"Using nzb_name for release name.")
        return nzb_name.rpartition('.')[0]

    if dir_name is None:
        return None

    # try to get the release name from nzb/nfo
    file_types = ["*.nzb", "*.nfo"]

    for search in file_types:

        reg_expr = re.compile(fnmatch.translate(search), re.IGNORECASE)
        files = [file_name for file_name in ek(os.listdir, dir_name) if
                 ek(os.path.isfile, ek(os.path.join, dir_name, file_name))]

        results = [f for f in files if reg_expr.search(f)]

        if len(results) == 1:
            found_file = ek(os.path.basename, results[0])
            found_file = found_file.rpartition('.')[0]
            if filterBadReleases(found_file):
                logger.log(u"Release name (" + found_file + ") found from file (" + results[0] + ")")
                return found_file.rpartition('.')[0]

    # If that fails, we try the folder
    folder = ek(os.path.basename, dir_name)
    if filterBadReleases(folder):
        # NOTE: Multiple failed downloads will change the folder name.
        # (e.g., appending #s)
        # Should we handle that?
        logger.log(u"Folder name (" + folder + ") appears to be a valid release name. Using it.", logger.DEBUG)
        return folder

    return None


def show_words(showObj):
    """
    Returns all related words to show: preferred, undesired, ignore, require.
    """

    ShowWords = namedtuple('show_words', ['preferred_words', 'undesired_words', 'ignore_words', 'require_words'])

    preferred_words = ",".join(app.PREFERRED_WORDS.split(',')) if app.PREFERRED_WORDS.split(',') else ''
    undesired_words = ",".join(app.UNDESIRED_WORDS.split(',')) if app.UNDESIRED_WORDS.split(',') else ''

    global_ignore = app.IGNORE_WORDS.split(',') if app.IGNORE_WORDS else []
    global_require = app.REQUIRE_WORDS.split(',') if app.REQUIRE_WORDS else []
    show_ignore = showObj.rls_ignore_words.split(',') if showObj.rls_ignore_words else []
    show_require = showObj.rls_require_words.split(',') if showObj.rls_require_words else []

    # If word is in global ignore and also in show require, then remove it from global ignore
    # Join new global ignore with show ignore
    final_ignore = show_ignore + [i for i in global_ignore if i.lower() not in [r.lower() for r in show_require]]
    # If word is in global require and also in show ignore, then remove it from global require
    # Join new global required with show require
    final_require = show_require + [i for i in global_require if i.lower() not in [r.lower() for r in show_ignore]]

    ignore_words = ",".join(final_ignore)
    require_words = ",".join(final_require)

    return ShowWords(preferred_words, undesired_words, ignore_words, require_words)
