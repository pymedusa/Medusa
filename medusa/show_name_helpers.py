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

from six import string_types
from . import app, common, logger
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
    Figures out every possible variation of the name for a particular show.

    Includes indexer name, and any scene exception names, and country code
    at the end of the name (e.g. "Show Name (AU)".

    show: a TVShow object that we should get the names of
    Returns: all possible show names
    """

    show_names = {show.name}
    show_names.update(
        get_scene_exceptions(show.indexerid, show.indexer, season)
    )
    new_show_names = set()

    if not show.is_anime:
        country_list = {}
        # add the country list
        country_list.update(common.countryList)
        # add the reversed mapping of the country list
        country_list.update({v: k for k, v in common.countryList.items()})

        for name in show_names:
            if not name:
                continue

            # if we have "Show Name Australia" or "Show Name (Australia)"
            # this will add "Show Name (AU)" for any countries defined in
            # common.countryList (and vice versa)
            for country in country_list:
                pattern_1 = ' {0}'.format(country)
                pattern_2 = ' ({0})'.format(country)
                replacement = ' ({0})'.format(country_list[country])
                if name.endswith(pattern_1):
                    new_show_names.add(name.replace(pattern_1, replacement))
                elif name.endswith(pattern_2):
                    new_show_names.add(name.replace(pattern_2, replacement))

    return show_names.union(new_show_names)


def determineReleaseName(dir_name=None, nzb_name=None):
    """Determine a release name from an nzb and/or folder name."""

    if nzb_name is not None:
        logger.log(u"Using nzb_name for release name.")
        return nzb_name.rpartition('.')[0]

    if dir_name is None:
        return None

    # try to get the release name from nzb/nfo
    file_types = ["*.nzb", "*.nfo"]

    for search in file_types:

        reg_expr = re.compile(fnmatch.translate(search), re.IGNORECASE)
        files = [file_name for file_name in os.listdir(dir_name) if
                 os.path.isfile(os.path.join(dir_name, file_name))]

        results = [f for f in files if reg_expr.search(f)]

        if len(results) == 1:
            found_file = os.path.basename(results[0])
            found_file = found_file.rpartition('.')[0]
            if filterBadReleases(found_file):
                logger.log(u"Release name (" + found_file + ") found from file (" + results[0] + ")")
                return found_file.rpartition('.')[0]

    # If that fails, we try the folder
    folder = os.path.basename(dir_name)
    if filterBadReleases(folder):
        # NOTE: Multiple failed downloads will change the folder name.
        # (e.g., appending #s)
        # Should we handle that?
        logger.log(u"Folder name (" + folder + ") appears to be a valid release name. Using it.", logger.DEBUG)
        return folder

    return None
