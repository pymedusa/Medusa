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
# pylint:disable=too-many-lines
"""Various helper methods."""

import base64
import ctypes
import datetime
import errno
import hashlib
import imghdr
import io
import logging
import os
import platform
import random
import re
import shutil
import socket
import ssl
import stat
import struct
import time
import traceback
import uuid
import warnings
import xml.etree.ElementTree as ET
import zipfile
from itertools import cycle, izip

import adba

from cachecontrol import CacheControlAdapter
from cachecontrol.cache import DictCache

import certifi

import cfscrape

from contextlib2 import closing, suppress

import guessit

import requests
from requests.compat import urlparse

from six import binary_type, string_types, text_type
from six.moves import http_client

from . import app
from .common import USER_AGENT
from .helper.common import episode_num, http_code_description, media_extensions, pretty_file_size, subtitle_extensions
from .helper.exceptions import ex
from .show.show import Show

logger = logging.getLogger(__name__)


try:
    from urllib.parse import splittype
except ImportError:
    from urllib2 import splittype


def indent_xml(elem, level=0):
    """Do our pretty printing and make Matt very happy."""
    i = "\n" + level * "  "
    if elem:
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent_xml(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def is_media_file(filename):
    """Check if named file may contain media.

    :param filename: Filename to check
    :type filename: str
    :return: True if this is a known media file, False if not
    :rtype: bool
    """
    # ignore samples
    try:
        if re.search(r'(^|[\W_])(?<!shomin.)(sample\d*)[\W_]', filename, re.I):
            return False

        # ignore RARBG release intro
        if re.search(r'^RARBG(\.(com|to))?\.(txt|avi|mp4)$', filename, re.I):
            return False

        # ignore MAC OS's retarded "resource fork" files
        if filename.startswith('._'):
            return False

        sep_file = filename.rpartition(".")

        if re.search('extras?$', sep_file[0], re.I):
            return False

        return sep_file[2].lower() in media_extensions
    except TypeError as error:  # Not a string
        logger.debug('Invalid filename. Filename must be a string. {error}', error=error)
        return False


def is_rar_file(filename):
    """Check if file is a RAR file, or part of a RAR set.

    :param filename: Filename to check
    :type filename: str
    :return: True if this is RAR/Part file, False if not
    :rtype: bool
    """
    archive_regex = r'(?P<file>^(?P<base>(?:(?!\.part\d+\.rar$).)*)\.(?:(?:part0*1\.)?rar)$)'

    return bool(re.search(archive_regex, filename))


def is_subtitle(file_path):
    """Return whether the file is a subtitle or not.

    :param file_path: path to the file
    :type file_path: text_type
    :return: True if it is a subtitle, else False
    :rtype: bool
    """
    return get_extension(file_path) in subtitle_extensions


def get_extension(file_path):
    """Return the file extension without leading dot.

    :param file_path: path to the file
    :type file_path: text_type
    :return: extension or empty string
    :rtype: text_type
    """
    return os.path.splitext(file_path)[1][1:]


def remove_file_failed(failed_file):
    """Remove file from filesystem.

    :param failed_file: File to remove
    :type failed_file: str
    """
    try:
        os.remove(failed_file)
    except Exception:
        pass


def make_dir(path):
    """Make a directory on the filesystem.

    :param path: directory to make
    :type path: str
    :return: True if success, False if failure
    :rtype: bool
    """
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
            # do the library update for synoindex
            from . import notifiers
            notifiers.synoindex_notifier.addFolder(path)
        except OSError:
            return False
    return True


def search_indexer_for_show_id(show_name, indexer=None, indexer_id=None, ui=None):
    """Contact indexer to check for information on shows by showid.

    :param show_name: Name of show
    :type show_name: str
    :param indexer: Which indexer to use
    :type indexer: int
    :param indexer_id: Which indexer ID to look for
    :type indexer_id: int
    :param ui: Custom UI for indexer use
    :return:
    """
    from .indexers.indexer_api import indexerApi
    show_names = [re.sub('[. -]', ' ', show_name)]

    # Query Indexers for each search term and build the list of results
    for i in indexerApi().indexers if not indexer else int(indexer or []):
        # Query Indexers for each search term and build the list of results
        indexer_api = indexerApi(i)
        indexer_api_params = indexer_api.api_params.copy()
        if ui is not None:
            indexer_api_params['custom_ui'] = ui
        t = indexer_api.indexer(**indexer_api_params)

        for name in show_names:
            logger.debug(u'Trying to find {name} on {api_name}', name=name, api_name=indexer_api.name)

            try:
                search = t[indexer_id] if indexer_id else t[name]
            except Exception:
                continue

            try:
                seriesname = search[0]['seriesname']
            except Exception:
                seriesname = None

            try:
                series_id = search[0]['id']
            except Exception:
                series_id = None

            if not (seriesname and series_id):
                continue
            show = Show.find(app.showList, int(series_id))
            # Check if we can find the show in our list (if not, it's not the right show)
            if (indexer_id is None) and (show is not None) and (show.indexerid == int(series_id)):
                return seriesname, i, int(series_id)
            elif (indexer_id is not None) and (int(indexer_id) == int(series_id)):
                return seriesname, i, int(indexer_id)

        if indexer:
            break

    return None, None, None


def list_media_files(path):
    """Get a list of files possibly containing media in a path.

    :param path: Path to check for files
    :type path: str
    :return: list of files
    :rtype: list of str
    """
    if not dir or not os.path.isdir(path):
        return []

    files = []
    for cur_file in os.listdir(path):
        full_cur_file = os.path.join(path, cur_file)

        # if it's a folder do it recursively
        if os.path.isdir(full_cur_file) and not cur_file.startswith('.') and not cur_file == 'Extras':
            files += list_media_files(full_cur_file)

        elif is_media_file(cur_file):
            files.append(full_cur_file)

    return files


def copy_file(src_file, dest_file):
    """Copy a file from source to destination.

    :param src_file: Path of source file
    :type src_file: str
    :param dest_file: Path of destination file
    :type dest_file: str
    """
    try:
        from shutil import SpecialFileError, Error
    except ImportError:
        from shutil import Error
        SpecialFileError = Error

    try:
        shutil.copyfile(src_file, dest_file)
    except (SpecialFileError, Error) as error:
        logger.warning(u'{error}', error=error)
    except OSError as error:
        if 'No space left on device' in error:
            logger.warning(u'{error}', error=error)
        else:
            logger.error(u'{error}', error=error)
    else:
        try:
            shutil.copymode(src_file, dest_file)
        except OSError:
            pass


def move_file(src_file, dest_file):
    """Move a file from source to destination.

    :param src_file: Path of source file
    :type src_file: str
    :param dest_file: Path of destination file
    :type dest_file: str
    """
    try:
        shutil.move(src_file, dest_file)
        fix_set_group_id(dest_file)
    except OSError:
        copy_file(src_file, dest_file)
        os.unlink(src_file)


def link(src, dst):
    """Create a file link from source to destination.

    TODO: Make this unicode proof

    :param src: Source file
    :type src: str
    :param dst: Destination file
    :type dst: str
    """
    if os.name == 'nt':
        if ctypes.windll.kernel32.CreateHardLinkW(text_type(dst), text_type(src), 0) == 0:
            raise ctypes.WinError()
    else:
        os.link(src, dst)


def hardlink_file(src_file, dest_file):
    """Create a hard-link (inside filesystem link) between source and destination.

    :param src_file: Source file
    :type src_file: str
    :param dest_file: Destination file
    :type dest_file: str
    """
    try:
        link(src_file, dest_file)
        fix_set_group_id(dest_file)
    except OSError as e:
        if hasattr(e, 'errno') and e.errno == 17:  # File exists. Don't fallback to copy
            logger.warning(u'Failed to create hardlink of {source} at {dest}. Error: {error!r}',
                           source=src_file, dest=dest_file, error=e)
        else:
            logger.warning(u'Failed to create hardlink of {source} at {dest}. Error: {error!r}. Copying instead',
                           source=src_file, dest=dest_file, error=e)
            copy_file(src_file, dest_file)


def symlink(src, dst):
    """Create a soft/symlink between source and destination.

    :param src: Source file
    :type src: str
    :param dst: Destination file
    :type dst: str
    """
    if os.name == 'nt':
        if ctypes.windll.kernel32.CreateSymbolicLinkW(text_type(dst), text_type(src),
                                                      1 if os.path.isdir(src) else 0) in [0, 1280]:
            raise ctypes.WinError()
    else:
        os.symlink(src, dst)


def move_and_symlink_file(src_file, dest_file):
    """Move a file from source to destination, then create a symlink back from destination from source.

    If this fails, copy the file from source to destination.

    :param src_file: Source file
    :type src_file: str
    :param dest_file: Destination file
    :type dest_file: str
    """
    try:
        shutil.move(src_file, dest_file)
        fix_set_group_id(dest_file)
        symlink(dest_file, src_file)
    except OSError as e:
        if hasattr(e, 'errno') and e.errno == 17:  # File exists. Don't fallback to copy
            logger.warning(u'Failed to create symlink of {source} at {dest}. Error: {error!r}',
                           source=src_file, dest=dest_file, error=e)
        else:
            logger.warning(u'Failed to create symlink of {source} at {dest}. Error: {error!r}. Copying instead',
                           source=src_file, dest=dest_file, error=e)
            copy_file(src_file, dest_file)


def make_dirs(path):
    """Create any folders that are missing and assigns them the permissions of their parents.

    :param path:
    :rtype path: str
    """
    logger.debug(u'Checking if the path {path} already exists', path=path)

    if not os.path.isdir(path):
        # Windows, create all missing folders
        if os.name == 'nt' or os.name == 'ce':
            try:
                logger.debug(u"Folder {path} didn't exist, creating it", path=path)
                os.makedirs(path)
            except (OSError, IOError) as e:
                logger.error(u"Failed creating {path} : {error!r}", path=path, error=e)
                return False

        # not Windows, create all missing folders and set permissions
        else:
            sofar = ''
            folder_list = path.split(os.path.sep)

            # look through each subfolder and make sure they all exist
            for cur_folder in folder_list:
                sofar += cur_folder + os.path.sep

                # if it exists then just keep walking down the line
                if os.path.isdir(sofar):
                    continue

                try:
                    logger.debug(u"Folder {path} didn't exist, creating it", path=sofar)
                    os.mkdir(sofar)
                    # use normpath to remove end separator, otherwise checks permissions against itself
                    chmod_as_parent(os.path.normpath(sofar))
                    # do the library update for synoindex
                    from . import notifiers
                    notifiers.synoindex_notifier.addFolder(sofar)
                except (OSError, IOError) as e:
                    logger.error(u'Failed creating {path} : {error!r}', path=sofar, error=e)
                    return False

    return True


def rename_ep_file(cur_path, new_path, old_path_length=0):
    """Create all folders needed to move a file to its new location.

    Rename it and then cleans up any folders left that are now empty.

    :param  cur_path: The absolute path to the file you want to move/rename
    :type cur_path: str
    :param new_path: The absolute path to the destination for the file WITHOUT THE EXTENSION
    :type new_path: str
    :param old_path_length: The length of media file path (old name) WITHOUT THE EXTENSION
    :type old_path_length: int
    """
    from . import subtitles
    if old_path_length == 0 or old_path_length > len(cur_path):
        # approach from the right
        cur_file_name, cur_file_ext = os.path.splitext(cur_path)
    else:
        # approach from the left
        cur_file_ext = cur_path[old_path_length:]
        cur_file_name = cur_path[:old_path_length]

    if cur_file_ext[1:] in subtitle_extensions:
        # Extract subtitle language from filename
        sublang = os.path.splitext(cur_file_name)[1][1:]

        # Check if the language extracted from filename is a valid language
        if sublang in subtitles.subtitle_code_filter():
            cur_file_ext = '.' + sublang + cur_file_ext

    # put the extension on the incoming file
    new_path += cur_file_ext

    # Only rename if something has changed in the new name
    if cur_path == new_path:
        return True

    make_dirs(os.path.dirname(new_path))

    # move the file
    try:
        logger.info(u"Renaming file from '{old}' to '{new}'", old=cur_path, new=new_path)
        shutil.move(cur_path, new_path)
    except (OSError, IOError) as e:
        logger.error(u"Failed renaming '{old}' to '{new}' : {error!r}", old=cur_path, new=new_path, error=e)
        return False

    # clean up any old folders that are empty
    delete_empty_folders(os.path.dirname(cur_path))

    return True


def delete_empty_folders(check_empty_dir, keep_dir=None):
    """Walk backwards up the path and deletes any empty folders found.

    :param check_empty_dir: The path to clean (absolute path to a folder)
    :type check_empty_dir: str
    :param keep_dir: Clean until this path is reached
    :type keep_dir: str
    """
    # treat check_empty_dir as empty when it only contains these items
    ignore_items = []

    logger.info(u'Trying to clean any empty folders under {path}', path=check_empty_dir)

    # as long as the folder exists and doesn't contain any files, delete it
    while os.path.isdir(check_empty_dir) and check_empty_dir != keep_dir:
        check_files = os.listdir(check_empty_dir)

        if not check_files or (len(check_files) <= len(ignore_items) and all(
                [check_file in ignore_items for check_file in check_files])):
            # directory is empty or contains only ignore_items
            try:
                logger.info(u'Deleting empty folder: {folder}', folder=check_empty_dir)
                # need shutil.rmtree when ignore_items is really implemented
                os.rmdir(check_empty_dir)
                # do the library update for synoindex
                from . import notifiers
                notifiers.synoindex_notifier.deleteFolder(check_empty_dir)
            except OSError as e:
                logger.warning(u'Unable to delete {folder}. Error: {error!r}', folder=check_empty_dir, error=e)
                break
            check_empty_dir = os.path.dirname(check_empty_dir)
        else:
            break


def file_bit_filter(mode):
    """Strip special filesystem bits from file.

    :param mode: mode to check and strip
    :return: required mode for media file
    """
    for bit in [stat.S_IXUSR, stat.S_IXGRP, stat.S_IXOTH, stat.S_ISUID, stat.S_ISGID]:
        if mode & bit:
            mode -= bit

    return mode


def chmod_as_parent(child_path):
    """Retain permissions of parent for childs.

    (Does not work for Windows hosts)
    :param child_path: Child Path to change permissions to sync from parent
    :type child_path: str
    """
    if os.name == 'nt' or os.name == 'ce':
        return

    parent_path = os.path.dirname(child_path)

    if not parent_path:
        logger.debug(u'No parent path provided in {path}, unable to get permissions from it', path=child_path)
        return

    child_path = os.path.join(parent_path, os.path.basename(child_path))

    if not os.path.exists(child_path):
        return

    parent_path_stat = os.stat(parent_path)
    parent_mode = stat.S_IMODE(parent_path_stat[stat.ST_MODE])

    child_path_stat = os.stat(child_path.encode(app.SYS_ENCODING))
    child_path_mode = stat.S_IMODE(child_path_stat[stat.ST_MODE])

    if os.path.isfile(child_path):
        child_mode = file_bit_filter(parent_mode)
    else:
        child_mode = parent_mode

    if child_path_mode == child_mode:
        return

    child_path_owner = child_path_stat.st_uid
    user_id = os.geteuid()

    if user_id not in (0, child_path_owner):
        logger.debug(u'Not running as root or owner of {path}, not trying to set permissions', path=child_path)
        return

    try:
        os.chmod(child_path, child_mode)
        logger.debug(u'Setting permissions for {path} to {mode} as parent directory has {parent_mode}',
                     path=child_path, mode=child_mode, parent_mode=parent_mode)
    except OSError:
        logger.debug(u'Failed to set permission for {path} to {mode}', path=child_path, mode=child_mode)


def fix_set_group_id(child_path):
    """Inherid SGID from parent.

    (does not work on Windows hosts)

    :param child_path: Path to inherit SGID permissions from parent
    :type child_path: str
    """
    if os.name == 'nt' or os.name == 'ce':
        return

    parent_path = os.path.dirname(child_path)
    parent_stat = os.stat(parent_path)
    parent_mode = stat.S_IMODE(parent_stat[stat.ST_MODE])

    child_path = os.path.join(parent_path, os.path.basename(child_path))

    if parent_mode & stat.S_ISGID:
        parent_gid = parent_stat[stat.ST_GID]
        child_stat = os.stat(child_path.encode(app.SYS_ENCODING))
        child_gid = child_stat[stat.ST_GID]

        if child_gid == parent_gid:
            return

        child_path_owner = child_stat.st_uid
        user_id = os.geteuid()

        if user_id not in (0, child_path_owner):
            logger.debug(u'Not running as root or owner of {path}, not trying to set the set-group-ID', path=child_path)
            return

        try:
            os.chown(child_path, -1, parent_gid)
            logger.debug(u'Respecting the set-group-ID bit on the parent directory for {path}', path=child_path)
        except OSError:
            logger.error(
                u'Failed to respect the set-group-ID bit on the parent directory for {path} (setting group ID {gid})',
                path=child_path, gid=parent_gid)


def is_anime_in_show_list():
    """Check if any shows in list contain anime.

    :return: True if global showlist contains Anime, False if not
    """
    for show in app.showList:
        if show.is_anime:
            return True
    return False


def update_anime_support():
    """Check if we need to support anime, and if we do, enable the feature."""
    app.ANIMESUPPORT = is_anime_in_show_list()


def get_absolute_number_from_season_and_episode(show, season, episode):
    """Find the absolute number for a show episode.

    :param show: Show object
    :param season: Season number
    :param episode: Episode number
    :return: The absolute number
    """
    from . import db
    absolute_number = None

    if season and episode:
        main_db_con = db.DBConnection()
        sql = b'SELECT * FROM tv_episodes WHERE showid = ? and season = ? and episode = ?'
        sql_results = main_db_con.select(sql, [show.indexerid, season, episode])

        if len(sql_results) == 1:
            absolute_number = int(sql_results[0][b'absolute_number'])
            logger.debug(u'Found absolute number {absolute} for show {show} {ep}',
                         absolute=absolute_number, show=show.name, ep=episode_num(season, episode))
        else:
            logger.debug(u'No entries for absolute number for show {show} {ep}',
                         show=show.name, ep=episode_num(season, episode))

    return absolute_number


def get_all_episodes_from_absolute_number(show, absolute_numbers, indexer_id=None):
    episodes = []
    season = None

    if absolute_numbers:
        if not show and indexer_id:
            show = Show.find(app.showList, indexer_id)

        for absolute_number in absolute_numbers if show else []:
            ep = show.get_episode(None, None, absolute_number=absolute_number)
            if ep:
                episodes.append(ep.episode)
                # this will always take the last found season so eps that cross the season border are not handeled well
                season = ep.season

    return season, episodes


def sanitize_scene_name(name, anime=False):
    """Take a show name and returns the "scenified" version of it.

    :param name: Show name to be sanitized.
    :param anime: Some show have a ' in their name(Kuroko's Basketball) and is needed for search.
    :return: A string containing the scene version of the show name given.
    """
    if not name:
        return ''

    bad_chars = u',:()!?\u2019'
    if not anime:
        bad_chars += u"'"

    # strip out any bad chars
    for x in bad_chars:
        name = name.replace(x, '')

    # tidy up stuff that doesn't belong in scene names
    name = name.replace('- ', '.').replace(' ', '.').replace('&', 'and').replace('/', '.')
    name = re.sub(r'\.\.*', '.', name)

    if name.endswith('.'):
        name = name[:-1]

    return name


def create_https_certificates(ssl_cert, ssl_key):
    """Create self-signed HTTPS certificares and store in paths 'ssl_cert' and 'ssl_key'.

    :param ssl_cert: Path of SSL certificate file to write
    :param ssl_key: Path of SSL keyfile to write
    :return: True on success, False on failure
    :rtype: bool
    """
    try:
        from OpenSSL import crypto
        from certgen import createKeyPair, createCertRequest, createCertificate, TYPE_RSA, serial
    except Exception:
        logger.warning(u'pyopenssl module missing, please install for https access')
        return False

    # Create the CA Certificate
    cakey = createKeyPair(TYPE_RSA, 1024)
    careq = createCertRequest(cakey, CN='Certificate Authority')
    cacert = createCertificate(careq, (careq, cakey), serial, (0, 60 * 60 * 24 * 365 * 10))  # ten years

    cname = 'Medusa'
    pkey = createKeyPair(TYPE_RSA, 1024)
    req = createCertRequest(pkey, CN=cname)
    cert = createCertificate(req, (cacert, cakey), serial, (0, 60 * 60 * 24 * 365 * 10))  # ten years

    # Save the key and certificate to disk
    try:
        io.open(ssl_key, 'wb').write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey))
        io.open(ssl_cert, 'wb').write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    except Exception:
        logger.error(u'Error creating SSL key and certificate')
        return False

    return True


def backup_versioned_file(old_file, version):
    """Back up an old version of a file.

    :param old_file: Original file, to take a backup from
    :param version: Version of file to store in backup
    :return: True if success, False if failure
    """
    num_tries = 0

    with suppress(TypeError):
        version = u'.'.join([str(i) for i in version]) if not isinstance(version, str) else version

    new_file = u'{old_file}.v{version}'.format(old_file=old_file, version=version)

    while not os.path.isfile(new_file):
        if not os.path.isfile(old_file):
            logger.debug(u"Not creating backup, {old_file} doesn't exist", old_file=old_file)
            break

        try:
            logger.debug(u'Trying to back up {old} to new', old=old_file, new=new_file)
            shutil.copy(old_file, new_file)
            logger.debug(u"Backup done")
            break
        except Exception as e:
            logger.warning(u'Error while trying to back up {old} to {new} : {error!r}',
                           old=old_file, new=new_file, error=e)
            num_tries += 1
            time.sleep(1)
            logger.debug(u'Trying again.')

        if num_tries >= 10:
            logger.error(u'Unable to back up {old} to {new} please do it manually.',
                         old=old_file, new=new_file)
            return False

    return True


def restore_versioned_file(backup_file, version):
    """Restore a file version to original state.

    For example sickbeard.db.v41 passed with version int(41), will translate back to sickbeard.db.
    sickbeard.db.v41. passed with version tuple(41,2), will translate back to sickbeard.db.

    :param backup_file: File to restore
    :param version: Version of file to restore
    :return: True on success, False on failure
    """
    num_tries = 0

    with suppress(TypeError):
        version = '.'.join([str(i) for i in version]) if not isinstance(version, str) else version

    new_file, _ = backup_file[0:backup_file.find(u'v{version}'.format(version=version))]
    restore_file = backup_file

    if not os.path.isfile(new_file):
        logger.debug(u"Not restoring, %s doesn't exist" % new_file)
        return False

    try:
        logger.debug(u"Trying to backup %s to %s.r%s before restoring backup" % (new_file, new_file, version))

        shutil.move(new_file, new_file + '.' + 'r' + str(version))
    except Exception as e:
        logger.warning(u"Error while trying to backup DB file %s before proceeding with restore: %r" %
                       (restore_file, ex(e)))
        return False

    while not os.path.isfile(new_file):
        if not os.path.isfile(restore_file):
            logger.debug(u"Not restoring, %s doesn't exist" % restore_file)
            break

        try:
            logger.debug(u"Trying to restore file %s to %s" % (restore_file, new_file))
            shutil.copy(restore_file, new_file)
            logger.debug(u"Restore done")
            break
        except Exception as e:
            logger.warning(u"Error while trying to restore file %s. Error: %r" % (restore_file, ex(e)))
            num_tries += 1
            time.sleep(1)
            logger.debug(u"Trying again. Attempt #: %s" % num_tries)

        if num_tries >= 10:
            logger.warning(u"Unable to restore file %s to %s" % (restore_file, new_file))
            return False

    return True


def get_lan_ip():
    """Return IP of system."""
    try:
        return [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][0]
    except Exception:
        return socket.gethostname()


def check_url(url):
    """Check if a URL exists without downloading the whole file.

    We only check the URL header.
    """
    # see also http://stackoverflow.com/questions/2924422
    # http://stackoverflow.com/questions/1140661
    good_codes = [http_client.OK, http_client.FOUND, http_client.MOVED_PERMANENTLY]

    host, path = urlparse(url)[1:3]  # elems [1] and [2]
    try:
        conn = http_client.HTTPConnection(host)
        conn.request('HEAD', path)
        return conn.getresponse().status in good_codes
    except StandardError:
        return None


def anon_url(*url):
    """Return a URL string consisting of the Anonymous redirect URL and an arbitrary number of values appended."""
    # normalize to byte
    url = [u.encode('utf-8') if isinstance(u, text_type) else binary_type(u) for u in url]
    return '' if None in url else '{0}{1}'.format(app.ANON_REDIRECT, ''.join(url)).decode('utf-8')

# Encryption
# ==========
# By Pedro Jose Pereira Vieito <pvieito@gmail.com> (@pvieito)
#
# * If encryption_version==0 then return data without encryption
# * The keys should be unique for each device
#
# To add a new encryption_version:
#   1) Code your new encryption_version
#   2) Update the last encryption_version available in server/web/config/general.py
#   3) Remember to maintain old encryption versions and key generators for retro-compatibility


# Key Generators
unique_key1 = hex(uuid.getnode() ** 2)  # Used in encryption v1

# Encryption Functions


def encrypt(data, encryption_version=0, _decrypt=False):
    # Version 1: Simple XOR encryption (this is not very secure, but works)
    if encryption_version == 1:
        if _decrypt:
            return ''.join(chr(ord(x) ^ ord(y)) for (x, y) in izip(base64.decodestring(data), cycle(unique_key1)))
        else:
            return base64.encodestring(
                ''.join(chr(ord(x) ^ ord(y)) for (x, y) in izip(data, cycle(unique_key1)))).strip()
    # Version 2: Simple XOR encryption (this is not very secure, but works)
    elif encryption_version == 2:
        if _decrypt:
            return ''.join(chr(ord(x) ^ ord(y)) for (x, y) in izip(base64.decodestring(data),
                                                                   cycle(app.ENCRYPTION_SECRET)))
        else:
            return base64.encodestring(
                ''.join(chr(ord(x) ^ ord(y)) for (x, y) in izip(data, cycle(app.ENCRYPTION_SECRET)))).strip()
    # Version 0: Plain text
    else:
        return data


def decrypt(data, encryption_version=0):
    return encrypt(data, encryption_version, _decrypt=True)


def full_sanitize_scene_name(name):
    return re.sub('[. -]', ' ', sanitize_scene_name(name)).lower().lstrip()


def get_show(name, try_indexers=False):
    from . import classes, name_cache, scene_exceptions
    if not app.showList:
        return

    show = None
    from_cache = False

    if not name:
        return show

    try:
        # check cache for show
        cache = name_cache.retrieveNameFromCache(name)
        if cache:
            from_cache = True
            show = Show.find(app.showList, int(cache))

        # try indexers
        if not show and try_indexers:
            show = Show.find(
                app.showList, search_indexer_for_show_id(full_sanitize_scene_name(name), ui=classes.ShowListUI)[2])

        # try scene exceptions
        if not show:
            show_id = scene_exceptions.get_scene_exception_by_name(name)[0]
            if show_id:
                show = Show.find(app.showList, int(show_id))

        # add show to cache
        if show and not from_cache:
            name_cache.addNameToCache(name, show.indexerid)
    except Exception as e:
        logger.debug(u"Error when attempting to find show: %s. Error: %r " % (name, repr(e)))

    return show


def is_hidden_folder(folder):
    """Return True if folder is hidden.

    On Linux based systems hidden folders start with . (dot)
    :param folder: Full path of folder to check
    """
    def is_hidden(filepath):
        name = os.path.basename(os.path.abspath(filepath))
        return name.startswith('.') or has_hidden_attribute(filepath)

    def has_hidden_attribute(filepath):
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(text_type(filepath))
            assert attrs != -1
            result = bool(attrs & 2)
        except (AttributeError, AssertionError):
            result = False
        return result

    if os.path.isdir(folder):
        if is_hidden(folder):
            return True

    return False


def real_path(path):
    """Return the canonicalized absolute pathname.

    The resulting path will have no symbolic link, '/./' or '/../' components.
    """
    return os.path.normpath(os.path.normpath(os.path.realpath(path)))


def validate_show(show, season=None, episode=None):
    """Reindex show from originating indexer, and return indexer information for the passed episode."""
    from .indexers.indexer_api import indexerApi
    from .indexers.indexer_exceptions import IndexerEpisodeNotFound, IndexerSeasonNotFound
    indexer_lang = show.lang

    try:
        indexer_api_params = indexerApi(show.indexer).api_params.copy()

        if indexer_lang and not indexer_lang == app.INDEXER_DEFAULT_LANGUAGE:
            indexer_api_params['language'] = indexer_lang

        if show.dvdorder != 0:
            indexer_api_params['dvdorder'] = True

        t = indexerApi(show.indexer).indexer(**indexer_api_params)
        if season is None and episode is None:
            return t

        return t[show.indexerid][season][episode]
    except (IndexerEpisodeNotFound, IndexerSeasonNotFound):
        pass


def set_up_anidb_connection():
    """Connect to anidb."""
    if not app.USE_ANIDB:
        logger.debug(u"Usage of anidb disabled. Skiping")
        return False

    if not app.ANIDB_USERNAME and not app.ANIDB_PASSWORD:
        logger.debug(u"anidb username and/or password are not set. Aborting anidb lookup.")
        return False

    if not app.ADBA_CONNECTION:
        def anidb_logger(msg):
            return logger.debug(u"anidb: %s " % msg)

        try:
            app.ADBA_CONNECTION = adba.Connection(keepAlive=True, log=anidb_logger)
        except Exception as e:
            logger.warning(u"anidb exception msg: %r " % repr(e))
            return False

    try:
        if not app.ADBA_CONNECTION.authed():
            app.ADBA_CONNECTION.auth(app.ANIDB_USERNAME, app.ANIDB_PASSWORD)
        else:
            return True
    except Exception as e:
        logger.warning(u"anidb exception msg: %r " % repr(e))
        return False

    return app.ADBA_CONNECTION.authed()


def backup_config_zip(file_list, archive, arcname=None):
    """Store the config file as a ZIP.

    :param file_list: List of files to store
    :param archive: ZIP file name
    :param arcname: Archive path
    :return: True on success, False on failure
    """
    try:
        a = zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, allowZip64=True)
        for f in file_list:
            a.write(f, os.path.relpath(f, arcname))
        a.close()
        return True
    except Exception as e:
        logger.error(u'Zip creation error: {error!r} ', error=e)
        return False


def restore_config_zip(archive, target_dir):
    """Restore a Config ZIP file back in place.

    :param archive: ZIP filename
    :param target_dir: Directory to restore to
    :return: True on success, False on failure
    """
    try:
        if not os.path.exists(target_dir):
            os.mkdir(target_dir)
        else:
            def path_leaf(path):
                head, tail = os.path.split(path)
                return tail or os.path.basename(head)
            bak_filename = '{0}-{1}'.format(path_leaf(target_dir), datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
            shutil.move(target_dir, os.path.join(os.path.dirname(target_dir), bak_filename))

        zip_file = zipfile.ZipFile(archive, 'r', allowZip64=True)
        for member in zip_file.namelist():
            zip_file.extract(member, target_dir)
        zip_file.close()
        return True
    except Exception as e:
        logger.error(u'Zip extraction error: {error!r}', error=e)
        shutil.rmtree(target_dir)
        return False


def touch_file(fname, atime=None):
    """Touch a file (change modification date).

    :param fname: Filename to touch
    :param atime: Specific access time (defaults to None)
    :return: True on success, False on failure
    """
    if atime and fname and os.path.isfile(fname):
        os.utime(fname, (atime, atime))
        return True

    return False


def make_session(cache_etags=True, serializer=None, heuristic=None):
    session = requests.Session()

    adapter = CacheControlAdapter(
        DictCache(),
        cache_etags=cache_etags,
        serializer=serializer,
        heuristic=heuristic,
    )

    session.mount('http://', adapter)
    session.mount('https://', adapter)

    session.cache_controller = adapter.controller

    session.headers.update({'User-Agent': USER_AGENT, 'Accept-Encoding': 'gzip,deflate'})

    return session


def request_defaults(kwargs):
    hooks = kwargs.pop(u'hooks', None)
    cookies = kwargs.pop(u'cookies', None)
    verify = certifi.old_where() if all([app.SSL_VERIFY, kwargs.pop(u'verify', True)]) else False

    # request session proxies
    if app.PROXY_SETTING:
        logger.debug(u"Using global proxy: " + app.PROXY_SETTING)
        scheme, address = splittype(app.PROXY_SETTING)
        address = app.PROXY_SETTING if scheme else 'http://' + app.PROXY_SETTING
        proxies = {
            "http": address,
            "https": address,
        }
    else:
        proxies = None

    return hooks, cookies, verify, proxies


def prepare_cf_req(session, request):
    logger.debug(u'CloudFlare protection detected, trying to bypass it')

    try:
        tokens, user_agent = cfscrape.get_tokens(request.url)
        if request.cookies:
            request.cookies.update(tokens)
        else:
            request.cookies = tokens
        if request.headers:
            request.headers.update({u'User-Agent': user_agent})
        else:
            request.headers = {u'User-Agent': user_agent}
        logger.debug(u'CloudFlare protection successfully bypassed.')
        return session.prepare_request(request)
    except (ValueError, AttributeError) as error:
        logger.warning(u"Couldn't bypass CloudFlare's anti-bot protection. Error: {err_msg}", err_msg=error)


def get_url(url, post_data=None, params=None, headers=None, timeout=30, session=None, **kwargs):
    """Return data retrieved from the url provider."""
    response_type = kwargs.pop(u'returns', u'response')
    stream = kwargs.pop(u'stream', False)
    hooks, cookies, verify, proxies = request_defaults(kwargs)
    method = u'POST' if post_data else u'GET'

    try:
        req = requests.Request(method, url, data=post_data, params=params, hooks=hooks,
                               headers=headers, cookies=cookies)
        prepped = session.prepare_request(req)
        resp = session.send(prepped, stream=stream, verify=verify, proxies=proxies, timeout=timeout,
                            allow_redirects=True)

        if not resp.ok:
            # Try to bypass CloudFlare's anti-bot protection
            if resp.status_code == 503 and resp.headers.get('server') == u'cloudflare-nginx':
                cf_prepped = prepare_cf_req(session, req)
                if cf_prepped:
                    cf_resp = session.send(cf_prepped, stream=stream, verify=verify, proxies=proxies,
                                           timeout=timeout, allow_redirects=True)
                    if cf_resp.ok:
                        return cf_resp

            logger.debug(u'Requested url {url} returned status code {status}: {desc}'.format
                         (url=resp.url, status=resp.status_code, desc=http_code_description(resp.status_code)))

            if response_type and response_type != u'response':
                return None

    except requests.exceptions.RequestException as e:
        logger.debug(u'Error requesting url {url}. Error: {err_msg}', url=url, err_msg=e)
        return None
    except Exception as e:
        if u'ECONNRESET' in e or (hasattr(e, u'errno') and e.errno == errno.ECONNRESET):
            logger.warning(u'Connection reset by peer accessing url {url}. Error: {err_msg}'.format(url=url, err_msg=e))
        else:
            logger.info(u'Unknown exception in url {url}. Error: {err_msg}', url=url, err_msg=e)
            logger.debug(traceback.format_exc())
        return None

    if not response_type or response_type == u'response':
        return resp
    else:
        warnings.warn(u'Returning {0} instead of {1} will be deprecated in the near future!'.format
                      (response_type, 'response'), PendingDeprecationWarning)
        if response_type == u'json':
            try:
                return resp.json()
            except ValueError:
                return {}
        else:
            return getattr(resp, response_type, None)


def download_file(url, filename, session=None, headers=None, **kwargs):
    """Download a file specified.

    :param url: Source URL
    :param filename: Target file on filesystem
    :param session: request session to use
    :param headers: override existing headers in request session
    :return: True on success, False on failure
    """
    try:
        hooks, cookies, verify, proxies = request_defaults(kwargs)

        with closing(session.get(url, allow_redirects=True, stream=True,
                                 verify=verify, headers=headers, cookies=cookies,
                                 hooks=hooks, proxies=proxies)) as resp:

            if not resp.ok:
                logger.debug(u'Requested download URL {url} returned status code is {code}: {description}'.format
                             (url=url, code=resp.status_code, description=http_code_description(resp.status_code)))
                return False

            try:
                with io.open(filename, 'wb') as fp:
                    for chunk in resp.iter_content(chunk_size=1024):
                        if chunk:
                            fp.write(chunk)
                            fp.flush()

                chmod_as_parent(filename)
            except OSError as e:
                remove_file_failed(filename)
                logger.warning(u'Problem setting permissions or writing file to: {location}. Error: {error}'.format
                               (location=filename, error=e))
                return False

    except requests.exceptions.RequestException as e:
        remove_file_failed(filename)
        logger.warning(u'Error requesting download URL: {url}. Error: {error}'.format(url=url, error=e))
        return False
    except EnvironmentError as e:
        remove_file_failed(filename)
        logger.warning(u'Unable to save the file: {name}. Error: {error}'.format(name=filename, error=e))
        return False
    except Exception as e:
        remove_file_failed(filename)
        logger.error(u'Unknown exception while downloading file {name} from URL: {url}. Error: {error}'.format
                     (name=filename, url=url, error=e))
        logger.debug(traceback.format_exc())
        return False

    return True


def handle_requests_exception(requests_exception):
    default = "Request failed: {0}"
    try:
        raise requests_exception
    except requests.exceptions.SSLError as error:
        if ssl.OPENSSL_VERSION_INFO < (1, 0, 1, 5):
            logger.info("SSL Error requesting url: '{0}' You have {1}, try upgrading OpenSSL to 1.0.1e+".format(
                error.request.url, ssl.OPENSSL_VERSION))
        if app.SSL_VERIFY:
            logger.info(
                "SSL Error requesting url: '{0}'. Disable Cert Verification on the advanced tab of /config/general")
        logger.debug(default.format(error))
        logger.debug(traceback.format_exc())

    except requests.exceptions.RequestException as error:
        logger.info(default.format(error))
    except Exception as error:
        logger.error(default.format(error))
        logger.debug(traceback.format_exc())


def get_size(start_path='.'):
    """Find the total dir and filesize of a path.

    :param start_path: Path to recursively count size
    :return: total filesize
    """
    if not os.path.isdir(start_path):
        return -1

    total_size = 0
    for dirpath, _, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total_size += os.path.getsize(fp)
            except OSError as e:
                logger.error(u"Unable to get size for file %s Error: %r" % (fp, ex(e)))
                logger.debug(traceback.format_exc())
    return total_size


def generate_api_key():
    """Return a new randomized API_KEY."""
    logger.info(u"Generating New API key")
    secure_hash = hashlib.sha512(str(time.time()))
    secure_hash.update(str(random.SystemRandom().getrandbits(4096)))
    return secure_hash.hexdigest()[:32]


def remove_article(text=''):
    """Remove the english articles from a text string."""
    return re.sub(r'(?i)^(?:(?:A(?!\s+to)n?)|The)\s(\w)', r'\1', text)


def generate_cookie_secret():
    """Generate a new cookie secret."""
    return base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)


def verify_freespace(src, dest, oldfile=None):
    """Check if the target system has enough free space to copy or move a file.

    :param src: Source filename
    :param dest: Destination path
    :param oldfile: File to be replaced (defaults to None)
    :return: True if there is enough space for the file,
             False if there isn't. Also returns True if the OS doesn't support this option
    """
    if not isinstance(oldfile, list):
        oldfile = [oldfile]

    logger.debug(u"Trying to determine free space on destination drive")

    if not os.path.isfile(src):
        logger.warning("A path to a file is required for the source. {0} is not a file.".format(src))
        return True

    try:
        diskfree = get_disk_space_usage(dest, None)
        if not diskfree:
            logger.warning(u"Unable to determine the free space on your OS.")
            return True
    except Exception:
        logger.warning(u"Unable to determine free space, so I will assume there is enough.")
        return True

    try:
        neededspace = os.path.getsize(src)
    except OSError as e:
        logger.warning(u'Unable to determine needed space. Aborting. Error: {error_msg}'.format(error_msg=e))
        return False

    if oldfile:
        for f in oldfile:
            if os.path.isfile(f.location):
                diskfree += os.path.getsize(f.location)

    if diskfree > neededspace:
        return True
    else:
        logger.warning(u"Not enough free space. Needed: {0} bytes ({1}), found: {2} bytes ({3})".format
                       (neededspace, pretty_file_size(neededspace), diskfree, pretty_file_size(diskfree)))
        return False


# https://gist.github.com/thatalextaylor/7408395
def pretty_time_delta(seconds):
    sign_string = '-' if seconds < 0 else ''
    seconds = abs(int(seconds))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    time_delta = sign_string

    if days > 0:
        time_delta += ' %dd' % days
    if hours > 0:
        time_delta += ' %dh' % hours
    if minutes > 0:
        time_delta += ' %dm' % minutes
    if seconds > 0:
        time_delta += ' %ds' % seconds

    return time_delta


def is_file_locked(check_file, write_lock_check=False):
    """Check if a file is locked.

    Performs three checks:
        1. Checks if the file even exists
        2. Attempts to open the file for reading. This will determine if the file has a write lock.
            Write locks occur when the file is being edited or copied to, e.g. a file copy destination
        3. If the readLockCheck parameter is True, attempts to rename the file. If this fails the
            file is open by some other process for reading. The file can be read, but not written to
            or deleted.
    :param check_file: the file being checked
    :param write_lock_check: when true will check if the file is locked for writing (prevents move operations)
    """
    check_file = os.path.abspath(check_file)

    if not os.path.exists(check_file):
        return True
    try:
        f = io.open(check_file, 'rb')
        f.close()  # pylint: disable=no-member
    except IOError:
        return True

    if write_lock_check:
        lock_file = check_file + ".lckchk"
        if os.path.exists(lock_file):
            os.remove(lock_file)
        try:
            os.rename(check_file, lock_file)
            time.sleep(1)
            os.rename(lock_file, check_file)
        except (OSError, IOError):
            return True

    return False


def get_disk_space_usage(disk_path=None, pretty=True):
    """Return the free space in human readable bytes for a given path or False if no path given.

    :param disk_path: the filesystem path being checked
    :param pretty: return as bytes if None
    """
    if disk_path and os.path.exists(disk_path):
        if platform.system() == 'Windows':
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(disk_path), None, None, ctypes.pointer(free_bytes))
            return pretty_file_size(free_bytes.value) if pretty else free_bytes.value
        else:
            st = os.statvfs(disk_path)
            file_size = st.f_bavail * st.f_frsize
            return pretty_file_size(file_size) if pretty else file_size
    else:
        return False


def get_tvdb_from_id(indexer_id, indexer):

    session = make_session()
    tvdb_id = ''
    if indexer == 'IMDB':
        url = "http://www.thetvdb.com/api/GetSeriesByRemoteID.php?imdbid=%s" % indexer_id
        data = get_url(url, session=session, returns='content')
        if data is None:
            return tvdb_id

        with suppress(SyntaxError):
            tree = ET.fromstring(data)
            for show in tree.iter("Series"):
                tvdb_id = show.findtext("seriesid")

        if tvdb_id:
            return tvdb_id

    elif indexer == 'ZAP2IT':
        url = "http://www.thetvdb.com/api/GetSeriesByRemoteID.php?zap2it=%s" % indexer_id
        data = get_url(url, session=session, returns='content')
        if data is None:
            return tvdb_id

        with suppress(SyntaxError):
            tree = ET.fromstring(data)
            for show in tree.iter("Series"):
                tvdb_id = show.findtext("seriesid")

        return tvdb_id

    elif indexer == 'TVMAZE':
        url = "http://api.tvmaze.com/shows/%s" % indexer_id
        data = get_url(url, session=session, returns='json')
        if data is None:
            return tvdb_id
        tvdb_id = data['externals']['thetvdb']
        return tvdb_id

    # If indexer is IMDB and we've still not returned a tvdb_id, let's try to use tvmaze's api, to get the tvdbid
    if indexer == 'IMDB':
        url = 'http://api.tvmaze.com/lookup/shows?imdb={indexer_id}'.format(indexer_id=indexer_id)
        data = get_url(url, session=session, returns='json')
        if not data:
            return tvdb_id
        tvdb_id = data['externals'].get('thetvdb', '')
        return tvdb_id
    else:
        return tvdb_id


def get_showname_from_indexer(indexer, indexer_id, lang='en'):
    from .indexers.indexer_api import indexerApi
    indexer_api_params = indexerApi(indexer).api_params.copy()
    if lang:
        indexer_api_params['language'] = lang

    logger.info(u"" + str(indexerApi(indexer).name) + ": " + repr(indexer_api_params))

    t = indexerApi(indexer).indexer(**indexer_api_params)
    s = t[int(indexer_id)]

    if hasattr(s, 'data'):
        return s.data.get('seriesname')

    return None


# http://stackoverflow.com/a/20380514
def get_image_size(image_path):
    """Determine the image type of image_path and return its size.."""
    with open(image_path, 'rb') as f:
        head = f.read(24)
        if len(head) != 24:
            return
        if imghdr.what(image_path) == 'png':
            check = struct.unpack('>i', head[4:8])[0]
            if check != 0x0d0a1a0a:
                return
            return struct.unpack('>ii', head[16:24])
        elif imghdr.what(image_path) == 'gif':
            return struct.unpack('<HH', head[6:10])
        elif imghdr.what(image_path) == 'jpeg':
            f.seek(0)  # Read 0xff next
            size = 2
            ftype = 0
            while not 0xc0 <= ftype <= 0xcf:
                f.seek(size, 1)
                byte = f.read(1)
                while ord(byte) == 0xff:
                    byte = f.read(1)
                ftype = ord(byte)
                size = struct.unpack('>H', f.read(2))[0] - 2
            # We are at a SOFn block
            f.seek(1, 1)  # Skip `precision' byte.
            return struct.unpack('>HH', f.read(4))


def remove_folder(folder_path, level=logging.WARNING):
    """Recursively delete a directory tree.

    :param folder_path:
    :type folder_path: string
    :param level:
    :type level: int
    """
    if os.path.exists(folder_path):
        try:
            shutil.rmtree(folder_path)
        except OSError as e:
            logger.log(level, u'Unable to remove directory {folder}: {cause!r}', folder=folder_path, cause=e)


def is_ip_private(ip):
    """Return whether the ip is a private ip address.

    :param ip:
    :type ip: str
    :return:
    :rtype: bool
    """
    priv_lo = re.compile(r"^127\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    priv_24 = re.compile(r"^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    priv_20 = re.compile(r"^192\.168\.\d{1,3}.\d{1,3}$")
    priv_16 = re.compile(r"^172.(1[6-9]|2[0-9]|3[0-1]).[0-9]{1,3}.[0-9]{1,3}$")
    return bool(priv_lo.match(ip) or priv_24.match(ip) or priv_20.match(ip) or priv_16.match(ip))


def unicodify(value):
    """Return the value as unicode.

    :param value:
    :type value: str
    :return:
    :rtype: str
    """
    if isinstance(value, string_types) and not isinstance(value, text_type):
        return text_type(value, 'utf-8', 'replace')

    return value


def single_or_list(value, allow_multi=False):
    """Return a single value or a list.

    If value is a list with more than one element and allow_multi is False then it returns None.
    :param value:
    :type value: list
    :param allow_multi: if False, multiple values will return None
    :type allow_multi: bool
    :rtype: list or str or int
    """
    if not isinstance(value, list):
        return value

    if len(value) == 1:
        return value[0]

    if allow_multi:
        return sorted(value)


def ensure_list(value):
    """Return a list.

    When value is not a list, return a list containing the single value.
    :param value:
    :rtype: list
    """
    return sorted(value) if isinstance(value, list) else [value] if value is not None else []


def canonical_name(obj, fmt=u'{key}:{value}', separator=u'|', ignore_list=frozenset()):
    """Create a canonical name from a release name or a guessed dictionary.

    The return value is always unicode.

    :param obj:
    :type obj: str or dict
    :param fmt:
    :type fmt: str or unicode
    :param separator:
    :type separator: str or unicode
    :param ignore_list:
    :type ignore_list: set
    :return:
    :rtype: text_type
    """
    guess = obj if isinstance(obj, dict) else guessit.guessit(obj)
    return text_type(
        text_type(separator).join(
            [text_type(fmt).format(key=unicodify(k), value=unicodify(v))
             for k, v in guess.items() if k not in ignore_list]))


def get_broken_providers():
    """Get broken providers from cdn.pymedusa.com."""
    # Check if last broken providers update happened less than 60 minutes ago
    if app.BROKEN_PROVIDERS_UPDATE and isinstance(app.BROKEN_PROVIDERS_UPDATE, datetime.datetime) and \
            (datetime.datetime.now() - app.BROKEN_PROVIDERS_UPDATE).seconds < 3600:
        logger.debug('Broken providers already updated in the last hour')
        return

    # Update last broken providers update-timestamp to avoid updating again in less than 60 minutes
    app.BROKEN_PROVIDERS_UPDATE = datetime.datetime.now()

    url = 'https://cdn.pymedusa.com/providers/broken_providers.json'
    response = get_url(url, session=make_session(), returns='json')
    if not response:
        logger.warning('Unable to update the list with broken providers. '
                       'This list is used to disable broken providers. '
                       'You may encounter errors in the logfiles if you are using a broken provider.')
        return []

    logger.info('Broken providers found: {0}'.format(response))
    return ','.join(response)
