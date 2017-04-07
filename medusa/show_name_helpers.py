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

import re

from six import string_types

from . import app, logger

from .name_parser.parser import InvalidNameException, InvalidShowException, NameParser


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
