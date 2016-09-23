# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
#

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
"""Browser module."""
from __future__ import unicode_literals

import os
import string

from . import logger


# adapted from http://stackoverflow.com/questions/827371/is-there-a-way-to-list-all-the-available-drive-letters-in-python/827490
def get_win_drives():
    """Return list of detected drives."""
    assert os.name == 'nt'
    from ctypes import windll

    drives = []
    bitmask = windll.kernel32.GetLogicalDrives()  # @UndefinedVariable
    for letter in string.uppercase:
        if bitmask & 1:
            drives.append(letter)
        bitmask >>= 1

    return drives


def get_file_list(path, include_files):
    """Return file list for the given path."""
    # prune out directories to protect the user from doing stupid things (already lower case the dir to reduce calls)
    hide_list = ['boot', 'bootmgr', 'cache', 'config.msi', 'msocache', 'recovery', '$recycle.bin',
                 'recycler', 'system volume information', 'temporary internet files']  # windows specific
    hide_list += ['.fseventd', '.spotlight', '.trashes', '.vol', 'cachedmessages', 'caches', 'trash']  # osx specific
    hide_list += ['.git']

    file_list = []
    for filename in os.listdir(path):
        if filename.lower() in hide_list:
            continue

        full_filename = os.path.join(path, filename)
        is_dir = os.path.isdir(full_filename)

        if not include_files and not is_dir:
            continue

        entry = {
            'name': filename,
            'path': full_filename
        }
        if not is_dir:
            entry['isFile'] = True
        file_list.append(entry)

    return file_list


def list_folders(path, include_parent=False, include_files=False):
    """Return a list of dictionaries with the folders contained at the given path.

    Give the empty string as the path to list the contents of the root path
    (under Unix this means "/", on Windows this will be a list of drive letters)

    :param path: to list contents
    :param include_parent: boolean, include parent dir in list as well
    :param include_files: boolean, include files or only directories
    :return: list of folders/files
    """
    # walk up the tree until we find a valid path
    while path and not os.path.isdir(path):
        if path == os.path.dirname(path):
            path = ''
            break
        else:
            path = os.path.dirname(path)

    if path == '':
        if os.name == 'nt':
            entries = [{'currentPath': 'Root'}]
            for letter in get_win_drives():
                letter_path = letter + ':\\'
                entries.append({'name': letter_path, 'path': letter_path})
            return entries
        else:
            path = '/'

    # fix up the path and find the parent
    path = os.path.abspath(os.path.normpath(path))
    parent_path = os.path.dirname(path)

    # if we're at the root then the next step is the meta-node showing our drive letters
    if path == parent_path and os.name == 'nt':
        parent_path = ''

    try:
        file_list = get_file_list(path, include_files)
    except OSError as e:
        logger.log('Unable to open %s: %s / %s' % (path, repr(e), str(e)), logger.WARNING)
        file_list = get_file_list(parent_path, include_files)

    file_list = sorted(file_list,
                       lambda x, y: cmp(os.path.basename(x['name']).lower(), os.path.basename(y['path']).lower()))

    entries = [{'currentPath': path}]
    if include_parent and parent_path != path:
        entries.append({'name': '..', 'path': parent_path})
    entries.extend(file_list)

    return entries
