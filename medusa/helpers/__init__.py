# coding=utf-8

"""Various helper methods."""
from __future__ import unicode_literals

import base64
import ctypes
import datetime
import errno
import hashlib
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
import zipfile
from builtins import chr
from builtins import str
from itertools import cycle
from xml.etree import ElementTree

from cachecontrol import CacheControlAdapter
from cachecontrol.cache import DictCache

import certifi

from contextlib2 import suppress

import guessit

from medusa import app, db
from medusa.common import DOWNLOADED, USER_AGENT
from medusa.helper.common import (http_code_description, media_extensions,
                                  pretty_file_size, subtitle_extensions)
from medusa.helpers.utils import generate
from medusa.imdb import Imdb
from medusa.indexers.exceptions import IndexerException
from medusa.logger.adapters.style import BraceAdapter, BraceMessage
from medusa.session.core import MedusaSafeSession
from medusa.show.show import Show

import requests
from requests.compat import urlparse

from six import binary_type, ensure_binary, ensure_text, string_types, text_type, viewitems
from six.moves import http_client

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

try:
    import reflink
except ImportError:
    reflink = None

try:
    from psutil import Process
    memory_usage_tool = 'psutil'
except ImportError:
    try:
        import resource  # resource module is unix only
        memory_usage_tool = 'resource'
    except ImportError:
        memory_usage_tool = None


def indent_xml(elem, level=0):
    """Do our pretty printing and make Matt very happy."""
    i = '\n' + level * '  '
    if elem:
        if not elem.text or not elem.text.strip():
            elem.text = i + '  '
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

        sep_file = filename.rpartition('.')

        if re.search('extras?$', sep_file[0], re.I):
            return False

        return sep_file[2].lower() in media_extensions
    except TypeError as error:  # Not a string
        log.debug(u'Invalid filename. Filename must be a string. {error}',
                  {'error': error})
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
            from medusa import notifiers
            notifiers.synoindex_notifier.addFolder(path)
        except OSError:
            return False
    return True


def search_indexer_for_show_id(show_name, indexer=None, series_id=None, ui=None):
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
    from medusa.indexers.api import indexerApi
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
            log.debug(u'Trying to find {name} on {indexer}',
                      {'name': name, 'indexer': indexer_api.name})

            try:
                search = t[series_id] if series_id else t[name]
            except Exception:
                continue

            try:
                searched_series_name = search[0]['seriesname']
            except Exception:
                searched_series_name = None

            try:
                searched_series_id = search[0]['id']
            except Exception:
                searched_series_id = None

            if not (searched_series_name and searched_series_id):
                continue
            series = Show.find_by_id(app.showList, i, searched_series_id)
            # Check if we can find the show in our list
            # if not, it's not the right show
            if (series_id is None) and (series is not None) and (series.indexerid == int(searched_series_id)):
                return searched_series_name, i, int(searched_series_id)
            elif (series_id is not None) and (int(series_id) == int(searched_series_id)):
                return searched_series_name, i, int(series_id)

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
        log.warning('Error copying file: {error}', {'error': error})
    except OSError as error:
        msg = BraceMessage('OSError: {0!r}', error)
        if error.errno == errno.ENOSPC:
            # Only warn if device is out of space
            log.warning(msg)
        else:
            # Error for any other OSError
            log.error(msg)
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
    except OSError as msg:
        log.warning(
            u'Failed to create hardlink of {source} at {destination}.'
            u' Error: {error!r}.', {
                'source': src_file,
                'destination': dest_file,
                'error': msg,
            }
        )


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
    except OSError as msg:
        if msg.errno == errno.EEXIST:
            # File exists. Don't fallback to copy
            log.warning(
                u'Failed to create symlink of {source} at {destination}.'
                u' Error: {error!r}', {
                    'source': src_file,
                    'destination': dest_file,
                    'error': msg,
                }
            )
        else:
            log.warning(
                u'Failed to create symlink of {source} at {destination}.'
                u' Error: {error!r}. Copying instead', {
                    'source': src_file,
                    'destination': dest_file,
                    'error': msg,
                }
            )
            copy_file(src_file, dest_file)


def reflink_file(src_file, dest_file):
    """Copy a file from source to destination with a reference link.

    :param src_file: Source file
    :type src_file: str
    :param dest_file: Destination file
    :type dest_file: str
    """
    try:
        if reflink is None:
            raise NotImplementedError()
        reflink.reflink(src_file, dest_file)
    except (reflink.ReflinkImpossibleError, IOError) as msg:
        if msg.args and msg.args[0] == 'EOPNOTSUPP':
            log.warning(
                u'Failed to create reference link of {source} at {destination}.'
                u' Error: Filesystem or OS has not implemented reflink. Copying instead', {
                    'source': src_file,
                    'destination': dest_file,
                }
            )
            copy_file(src_file, dest_file)
        elif msg.args and msg.args[0] == 'EXDEV':
            log.warning(
                u'Failed to create reference link of {source} at {destination}.'
                u' Error: Can not reflink between two devices. Copying instead', {
                    'source': src_file,
                    'destination': dest_file,
                }
            )
            copy_file(src_file, dest_file)
        else:
            log.warning(
                u'Failed to create reflink of {source} at {destination}.'
                u' Error: {error!r}. Copying instead', {
                    'source': src_file,
                    'destination': dest_file,
                    'error': msg,
                }
            )
            copy_file(src_file, dest_file)
    except NotImplementedError:
        log.warning(
            u'Failed to create reference link of {source} at {destination}.'
            u' Error: Filesystem does not support reflink or reflink is not installed. Copying instead', {
                'source': src_file,
                'destination': dest_file,
            }
        )
        copy_file(src_file, dest_file)


def make_dirs(path):
    """Create any folders that are missing and assigns them the permissions of their parents.

    :param path:
    :rtype path: str
    """
    log.debug(u'Checking if the path {path} already exists', {'path': path})

    if not os.path.isdir(path):
        # Windows, create all missing folders
        if os.name == 'nt' or os.name == 'ce':
            try:
                log.debug(u"Folder {path} didn't exist, creating it",
                          {'path': path})
                os.makedirs(path)
            except (OSError, IOError) as msg:
                log.error(u'Failed creating {path} : {error!r}',
                          {'path': path, 'error': msg})
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
                    log.debug(u"Folder {path} didn't exist, creating it",
                              {'path': sofar})
                    os.mkdir(sofar)
                    # use normpath to remove end separator,
                    # otherwise checks permissions against itself
                    chmod_as_parent(os.path.normpath(sofar))

                    # do the library update for synoindex
                    from medusa import notifiers
                    notifiers.synoindex_notifier.addFolder(sofar)
                except (OSError, IOError) as msg:
                    log.error(u'Failed creating {path} : {error!r}',
                              {'path': sofar, 'error': msg})
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
    from medusa import subtitles
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
        log.info(u"Renaming file from '{old}' to '{new}'",
                 {'old': cur_path, 'new': new_path})
        shutil.move(cur_path, new_path)
    except (OSError, IOError) as msg:
        log.error(u"Failed renaming '{old}' to '{new}' : {error!r}",
                  {'old': cur_path, 'new': new_path, 'error': msg})
        return False

    # clean up any old folders that are empty
    delete_empty_folders(os.path.dirname(cur_path))

    return True


def delete_empty_folders(top_dir, keep_dir=None):
    """Walk backwards up the path and deletes any empty folders found.

    :param top_dir: Clean until this directory is reached (absolute path to a folder)
    :type top_dir: str
    :param keep_dir: Don't delete this directory, even if it's empty
    :type keep_dir: str
    """
    if not top_dir or not os.path.isdir(top_dir):
        return

    log.info(u'Trying to clean any empty folder under {path}',
             {'path': top_dir})

    for directory in os.walk(top_dir, topdown=False):
        dirpath = directory[0]

        if dirpath == top_dir:
            return

        if dirpath != keep_dir and not os.listdir(dirpath):
            try:
                log.info(u'Deleting empty folder: {folder}',
                         {'folder': dirpath})
                os.rmdir(dirpath)

                # Do the library update for synoindex
                from medusa import notifiers
                notifiers.synoindex_notifier.deleteFolder(dirpath)
            except OSError as msg:
                log.warning(u'Unable to delete {folder}. Error: {error!r}',
                            {'folder': dirpath, 'error': msg})
        else:
            log.debug(u'Not deleting {folder}. The folder is not empty'
                      u' or should be kept.', {'folder': dirpath})


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
        log.debug(u'No parent path provided in {path}, unable to get'
                  u' permissions from it', {'path': child_path})
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
        log.debug(u'Not running as root or owner of {path}, not trying to set'
                  u' permissions', {'path': child_path})
        return

    try:
        os.chmod(child_path, child_mode)
        log.debug(
            u'Setting permissions for {path} to {mode} as parent directory'
            u' has {parent_mode}', {
                'path': child_path,
                'mode': child_mode,
                'parent_mode': parent_mode
            }
        )
    except OSError:
        log.debug(u'Failed to set permission for {path} to {mode}',
                  {'path': child_path, 'mode': child_mode})


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
            log.debug(u'Not running as root or owner of {path}, not trying to'
                      u' set the set-group-ID', {'path': child_path})
            return

        try:
            os.chown(child_path, -1, parent_gid)
            log.debug(u'Respecting the set-group-ID bit on the parent'
                      u' directory for {path}', {'path': child_path})
        except OSError:
            log.error(
                u'Failed to respect the set-group-ID bit on the parent'
                u' directory for {path} (setting group ID {gid})',
                {'path': child_path, 'gid': parent_gid})


def get_all_episodes_from_absolute_number(show, absolute_numbers, indexer_id=None, indexer=None):
    episodes = []
    season = None

    if absolute_numbers:
        if not show and (indexer_id and indexer):
            show = Show.find_by_id(app.showList, indexer, indexer_id)

        for absolute_number in absolute_numbers if show else []:
            ep = show.get_episode(None, None, absolute_number=absolute_number)
            if ep:
                episodes.append(ep.episode)
                # this will always take the last found season so eps that cross
                # the season border are not handled well
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
    name = name.replace('- ', '.').replace(' ', '.').replace('&', 'and').replace('/', '.').replace(': ', ' ')
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
        from medusa.helpers.certgen import create_key_pair, create_cert_request, create_certificate, TYPE_RSA
    except Exception:
        log.warning('pyopenssl module missing, please install for https access')
        return False

    # Serial number for the certificate
    serial = int(time.time())

    # Create the CA Certificate
    cakey = create_key_pair(TYPE_RSA, 2048)
    careq = create_cert_request(cakey, CN='Certificate Authority')
    cacert = create_certificate(careq, (careq, cakey), serial, (0, 60 * 60 * 24 * 365 * 10))  # ten years

    cname = 'Medusa'
    pkey = create_key_pair(TYPE_RSA, 2048)
    req = create_cert_request(pkey, CN=cname)
    cert = create_certificate(req, (cacert, cakey), serial, (0, 60 * 60 * 24 * 365 * 10))  # ten years

    # Save the key and certificate to disk
    try:
        io.open(ssl_key, 'wb').write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey))
        io.open(ssl_cert, 'wb').write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    except Exception:
        log.error(u'Error creating SSL key and certificate')
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
            log.debug(u"Not creating backup, {old_file} doesn't exist",
                      {'old_file': old_file})
            break

        try:
            log.debug(u'Trying to back up {old} to new',
                      {'old': old_file, 'new': new_file})
            shutil.copy(old_file, new_file)
            log.debug(u'Backup done')
            break
        except OSError as error:
            log.warning(u'Error while trying to back up {old} to {new}:'
                        u' {error!r}',
                        {'old': old_file, 'new': new_file, 'error': error})
            num_tries += 1
            time.sleep(1)
            log.debug(u'Trying again.')

        if num_tries >= 10:
            log.error(u'Unable to back up {old} to {new}, please do it'
                      u' manually.', {'old': old_file, 'new': new_file})
            return False

    return True


def get_lan_ip():
    """Return IP of system."""
    try:
        return [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith('127.')][0]
    except Exception:
        return socket.gethostname()


def check_url(url):
    """Check if a URL exists without downloading the whole file.

    We only check the URL header.
    """
    # see also https://stackoverflow.com/questions/2924422
    # https://stackoverflow.com/questions/1140661
    good_codes = [http_client.OK, http_client.FOUND, http_client.MOVED_PERMANENTLY]

    host, path = urlparse(url)[1:3]  # elems [1] and [2]
    try:
        conn = http_client.HTTPConnection(host)
        conn.request('HEAD', path)
        return conn.getresponse().status in good_codes
    except Exception:
        return None


def encrypt(data, encryption_version=0, _decrypt=False):
    # Version 0: Plain text
    if encryption_version == 0:
        return data

    # Simple XOR encryption, Base64 encoded
    # Version 2: app.ENCRYPTION_SECRET
    key = app.ENCRYPTION_SECRET
    if _decrypt:
        data = ensure_text(base64.decodebytes(ensure_binary(data)))
        return ''.join(chr(ord(x) ^ ord(y)) for (x, y) in zip(data, cycle(key)))
    else:
        data = ''.join(chr(ord(x) ^ ord(y)) for (x, y) in zip(data, cycle(key)))
        return ensure_text(base64.encodebytes(ensure_binary(data))).strip()


def decrypt(data, encryption_version=0):
    return encrypt(data, encryption_version, _decrypt=True)


def full_sanitize_scene_name(name):
    return re.sub('[. -]', ' ', sanitize_scene_name(name)).lower().lstrip()


def get_show(name, try_indexers=False):
    """
    Retrieve a series object using the series name.

    :param name: A series name or a list of series names, when the parsed series result, returned multiple.
    :param try_indexers: Toggle the lookup of the series using the series name and one or more indexers.

    :return: The found series object or None.
    """
    from medusa import classes, name_cache, scene_exceptions
    if not app.showList:
        return

    series = None
    from_cache = False

    if not name:
        return series

    for series_name in generate(name):
        # check cache for series
        indexer_id, series_id = name_cache.retrieveNameFromCache(series_name)
        if series_id:
            from_cache = True
            series = Show.find_by_id(app.showList, indexer_id, series_id)

        # try indexers
        if not series and try_indexers:
            _, found_indexer_id, found_series_id = search_indexer_for_show_id(full_sanitize_scene_name(series_name),
                                                                              ui=classes.ShowListUI)
            series = Show.find_by_id(app.showList, found_indexer_id, found_series_id)

        # try scene exceptions
        if not series:
            found_exception = scene_exceptions.get_scene_exception_by_name(series_name)
            if found_exception:
                series = Show.find_by_id(app.showList, found_exception.indexer, found_exception.series_id)

        if not series:
            match_name_only = (s.name for s in app.showList if text_type(s.imdb_year) in s.name and
                               series_name.lower() == s.name.lower().replace(' ({year})'.format(year=s.imdb_year), ''))
            for found_series in match_name_only:
                log.info("Consider adding '{name}' in scene exceptions for series '{series}'".format
                         (name=series_name, series=found_series))

        # add show to cache
        if series and not from_cache:
            name_cache.addNameToCache(series_name, series.indexer, series.indexerid)

        return series


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
    if path is None:
        return ''

    return os.path.normpath(os.path.normcase(os.path.realpath(path)))


def validate_show(show, season=None, episode=None):
    """Reindex show from originating indexer, and return indexer information for the passed episode."""
    from medusa.indexers.api import indexerApi
    from medusa.indexers.exceptions import IndexerEpisodeNotFound, IndexerSeasonNotFound, IndexerShowNotFound
    indexer_lang = show.lang

    try:
        indexer_api_params = indexerApi(show.indexer).api_params.copy()

        if indexer_lang and not indexer_lang == app.INDEXER_DEFAULT_LANGUAGE:
            indexer_api_params['language'] = indexer_lang

        if show.dvd_order != 0:
            indexer_api_params['dvdorder'] = True

        if season is None and episode is None:
            return show.indexer_api

        return show.indexer_api[show.indexerid][season][episode]
    except (IndexerEpisodeNotFound, IndexerSeasonNotFound, IndexerShowNotFound) as error:
        log.debug(u'Unable to validate show. Reason: {0!r}', error)
        pass


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
    except OSError as error:
        log.warning(u'Zip creation error: {0!r} ', error)
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
    except OSError as error:
        log.warning(u'Zip extraction error: {0!r}', error)
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


def request_defaults(**kwargs):
    hooks = kwargs.pop(u'hooks', None)
    cookies = kwargs.pop(u'cookies', None)
    verify = certifi.where() if all([app.SSL_VERIFY, kwargs.pop(u'verify', True)]) else False

    return hooks, cookies, verify


def download_file(url, filename, session, method='GET', data=None, headers=None, **kwargs):
    """Download a file specified.

    :param url: Source URL
    :param filename: Target file on filesystem
    :param method: Specity the http method. Currently only GET and POST supported
    :param data: sessions post data
    :param session: request session to use
    :param headers: override existing headers in request session
    :return: True on success, False on failure
    """
    try:
        hooks, cookies, verify = request_defaults(**kwargs)

        with session as s:
            resp = s.request(method, url, data=data, allow_redirects=True, stream=True,
                             verify=verify, headers=headers, cookies=cookies, hooks=hooks)

            if not resp:
                log.debug(
                    u"Requested download URL {url} couldn't be reached.",
                    {'url': url}
                )
                return False

            if not resp.ok:
                log.debug(
                    u'Requested download URL {url} returned'
                    u' status code {code}: {description}', {
                        'url': url,
                        'code': resp.status_code,
                        'description': http_code_description(resp.status_code),
                    }
                )
                return False

            try:
                with io.open(filename, 'wb') as fp:
                    for chunk in resp.iter_content(chunk_size=1024):
                        if chunk:
                            fp.write(chunk)
                            fp.flush()

                chmod_as_parent(filename)
            except OSError as msg:
                remove_file_failed(filename)
                log.warning(
                    u'Problem setting permissions or writing file'
                    u' to: {location}. Error: {msg}', {
                        'location': filename,
                        'msg': msg,
                    }
                )
                return False

    except requests.exceptions.RequestException as msg:
        remove_file_failed(filename)
        log.warning(u'Error requesting download URL: {url}. Error: {error}',
                    {'url': url, 'error': msg})
        return False
    except EnvironmentError as msg:
        remove_file_failed(filename)
        log.warning(u'Unable to save the file: {name}. Error: {error}',
                    {'name': filename, 'error': msg})
        return False
    except Exception as msg:
        remove_file_failed(filename)
        log.error(u'Unknown exception while downloading file {name}'
                  u' from URL: {url}. Error: {error}',
                  {'name': filename, 'url': url, 'error': msg})
        log.debug(traceback.format_exc())
        return False

    return True


def handle_requests_exception(requests_exception):
    default = 'Request failed: {0}'
    try:
        raise requests_exception
    except requests.exceptions.SSLError as error:
        if ssl.OPENSSL_VERSION_INFO < (1, 0, 1, 5):
            log.info(
                u'SSL Error requesting: {url} You have {version},'
                u' try upgrading OpenSSL to 1.0.1e+',
                {'url': error.request.url, 'version': ssl.OPENSSL_VERSION})
        if app.SSL_VERIFY:
            log.info(
                u'SSL Error requesting url: {url}. Disable Cert Verification'
                u' on the advanced tab of /config/general',
                {'url': error.request.url}
            )
        log.debug(default.format(error))
        log.debug(traceback.format_exc())

    except requests.exceptions.RequestException as error:
        log.info(default.format(error))
    except Exception as error:
        log.error(default.format(error))
        log.debug(traceback.format_exc())


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
            except OSError as error:
                log.warning(u'Unable to get size for file {name} Error: {msg!r}',
                            {'name': fp, 'msg': error})
    return total_size


def generate_api_key():
    """Return a new randomized API_KEY."""
    log.info(u'Generating New API key')
    secure_hash = hashlib.sha512(str(time.time()).encode('utf-8'))
    secure_hash.update(str(random.SystemRandom().getrandbits(4096)).encode('utf-8'))
    return secure_hash.hexdigest()[:32]


def remove_article(text=''):
    """Remove the english articles from a text string."""
    return re.sub(r'(?i)^(?:(?:A(?!\s+to)n?)|The)\s(\w)', r'\1', text)


def generate_cookie_secret():
    """Generate a new cookie secret."""
    return base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes).decode('utf-8')


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

    log.debug(u'Trying to determine free space on destination drive')

    if not os.path.isfile(src):
        log.warning(u'A path to a file is required for the source.'
                    u' {source} is not a file.', {'source': src})
        return True

    try:
        diskfree = get_disk_space_usage(dest, None)
        if not diskfree:
            log.warning(u'Unable to determine the free space on your OS.')
            return True
    except Exception:
        log.warning(u'Unable to determine free space, assuming there is '
                    u'enough.')
        return True

    try:
        neededspace = os.path.getsize(src)
    except OSError as error:
        log.warning(u'Unable to determine needed space. Aborting.'
                    u' Error: {msg}', {'msg': error})
        return False

    if oldfile:
        for f in oldfile:
            if os.path.isfile(f.location):
                diskfree += os.path.getsize(f.location)

    if diskfree > neededspace:
        return True
    else:
        log.warning(
            u'Not enough free space.'
            u' Needed: {0} bytes ({1}),'
            u' found: {2} bytes ({3})',
            neededspace, pretty_file_size(neededspace),
            diskfree, pretty_file_size(diskfree)
        )
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
        lock_file = check_file + '.lckchk'
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
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(disk_path), None, None,
                                                       ctypes.pointer(free_bytes))
            return pretty_file_size(free_bytes.value) if pretty else free_bytes.value
        else:
            st = os.statvfs(disk_path)
            file_size = st.f_bavail * st.f_frsize
            return pretty_file_size(file_size) if pretty else file_size
    else:
        return False


def memory_usage(pretty=True):
    """
    Get the current memory usage (if possible).

    :param pretty: True for human readable size, False for bytes

    :return: Current memory usage
    """
    usage = ''
    if memory_usage_tool == 'resource':
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if platform.system() == 'Linux':
            # resource.RUSAGE_SELF is in KB on Linux
            usage *= 1024
    elif memory_usage_tool == 'psutil':
        usage = Process(os.getpid()).memory_info().rss
    else:
        return ''

    if pretty:
        usage = pretty_file_size(usage)

    return usage


def get_tvdb_from_id(indexer_id, indexer):

    session = MedusaSafeSession()
    tvdb_id = ''

    if indexer == 'IMDB':
        url = 'https://www.thetvdb.com/api/GetSeriesByRemoteID.php?imdbid=%s' % indexer_id
        data = session.get_content(url)
        if data is None:
            return tvdb_id

        with suppress(SyntaxError):
            tree = ElementTree.fromstring(data)
            for show in tree.iter('Series'):
                tvdb_id = show.findtext('seriesid')

        if tvdb_id:
            return tvdb_id

    elif indexer == 'ZAP2IT':
        url = 'https://www.thetvdb.com/api/GetSeriesByRemoteID.php?zap2it=%s' % indexer_id
        data = session.get_content(url)
        if data is None:
            return tvdb_id

        with suppress(SyntaxError):
            tree = ElementTree.fromstring(data)
            for show in tree.iter('Series'):
                tvdb_id = show.findtext('seriesid')

        return tvdb_id

    elif indexer == 'TVMAZE':
        url = 'https://api.tvmaze.com/shows/%s' % indexer_id
        data = session.get_json(url)
        if data is None:
            return tvdb_id
        tvdb_id = data['externals']['thetvdb']
        return tvdb_id

    # If indexer is IMDB and we've still not returned a tvdb_id,
    # let's try to use tvmaze's api, to get the tvdbid
    if indexer == 'IMDB':
        url = 'https://api.tvmaze.com/lookup/shows?imdb={indexer_id}'.format(indexer_id=indexer_id)
        data = session.get_json(url)
        if not data:
            return tvdb_id
        tvdb_id = data['externals'].get('thetvdb', '')
        return tvdb_id
    else:
        return tvdb_id


def get_showname_from_indexer(indexer, indexer_id, lang='en'):
    from medusa.indexers.api import indexerApi
    indexer_api_params = indexerApi(indexer).api_params.copy()
    if lang:
        indexer_api_params['language'] = lang

    log.info(u'{0}: {1!r}', indexerApi(indexer).name, indexer_api_params)

    s = None
    try:
        indexer_api = indexerApi(indexer).indexer(**indexer_api_params)
        s = indexer_api[int(indexer_id)]
    except IndexerException as msg:
        log.warning(
            'Show name unavailable for {name} id {id} in {language}:'
            ' {reason}', {
                'name': indexerApi(indexer).name,
                'id': indexer_id,
                'language': lang,
                'reason': msg,
            }
        )

    data = getattr(s, 'data', {})
    return data.get('seriesname')


# https://stackoverflow.com/a/20380514
def get_image_size(image_path):
    """Determine the image type of image_path and return its (width, height)."""
    img_ext = os.path.splitext(image_path)[1].lower().strip('.')
    with open(image_path, 'rb') as f:
        head = f.read(24)
        if len(head) != 24:
            return None  # file too small
        # PNG check
        if head.startswith(b'\x89PNG\r\n\x1a\n'):
            # Verify PNG signature
            check = struct.unpack('>i', head[4:8])[0]
            if check != 0x0d0a1a0a:
                return None
            width, height = struct.unpack('>ii', head[16:24])
            return width, height
        # GIF check
        elif head[:6] in (b'GIF87a', b'GIF89a'):
            width, height = struct.unpack('<HH', head[6:10])
            return width, height
        # JPEG check
        elif head.startswith(b'\xff\xd8') or img_ext in ('jpg', 'jpeg'):
            f.seek(0)
            size = 2
            ftype = 0
            while True:
                f.seek(size, 1)
                byte = f.read(1)
                if not byte:
                    return None  # EOF reached unexpectedly
                while ord(byte) == 0xff:
                    byte = f.read(1)
                ftype = ord(byte)
                if 0xc0 <= ftype <= 0xcf and ftype != 0xc4 and ftype != 0xc8 and ftype != 0xcc:
                    break # Found SOF marker
                size_bytes = f.read(2)
                if len(size_bytes) != 2:
                    return None
                size = struct.unpack('>H', size_bytes)[0] - 2
            # Cursor is positioned after the SOF marker.
            # Need to skip 3 bytes: segment length (2 bytes) + sample precision (1 byte)
            f.seek(3, 1)
            # Read Image Height (2 bytes) and Image Width (2 bytes)
            height, width = struct.unpack('>HH', f.read(4))
            return width, height
        else:
            # Unknown or unsupported format
            return None


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
        except OSError as error:
            log.log(level, u'Unable to remove directory {folder}: {reason!r}',
                    {'folder': folder_path, 'reason': error})


def is_ip_private(ip):
    """Return whether the ip is a private ip address.

    :param ip:
    :type ip: str
    :return:
    :rtype: bool
    """
    priv_lo = re.compile(r'^127\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
    priv_24 = re.compile(r'^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
    priv_20 = re.compile(r'^192\.168\.\d{1,3}.\d{1,3}$')
    priv_16 = re.compile(r'^172.(1[6-9]|2[0-9]|3[0-1]).[0-9]{1,3}.[0-9]{1,3}$')
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


def to_text(s, encoding='utf-8', errors='strict'):
    """Coerce *s* to six.text_type.

    This code is part of the six library.
    For Python 2:
      - `unicode` -> `unicode`
      - `str` -> `unicode`
    For Python 3:
      - `str` -> `str`
      - `bytes` -> decoded to `str`
    """
    if isinstance(s, binary_type):
        return s.decode(encoding, errors)
    elif isinstance(s, text_type):
        return s
    else:
        raise TypeError("not expecting type '%s'" % type(s))


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
    try:
        return sorted(value) if isinstance(value, list) else [value] if value is not None else []
    except TypeError:
        log.debug('Could not sort list with values: {value}', {'value': value})
        return []


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
             for k, v in viewitems(guess) if k not in ignore_list]))


def get_broken_providers():
    """Get broken providers from cdn.pymedusa.com."""
    # Check if last broken providers update happened less than 60 minutes ago
    if app.BROKEN_PROVIDERS_UPDATE and isinstance(app.BROKEN_PROVIDERS_UPDATE, datetime.datetime) and \
            (datetime.datetime.now() - app.BROKEN_PROVIDERS_UPDATE).seconds < 3600:
        log.debug('Broken providers already updated in the last hour')
        return

    # Update last broken providers update-timestamp to avoid updating again in less than 60 minutes
    app.BROKEN_PROVIDERS_UPDATE = datetime.datetime.now()

    url = '{base_url}/providers/broken_providers.json'.format(base_url=app.BASE_PYMEDUSA_URL)

    response = MedusaSafeSession().get_json(url)
    if response is None:
        log.info('Unable to update the list with broken providers.'
                 ' This list is used to disable broken providers.'
                 ' You may encounter errors in the log files if you are'
                 ' using a broken provider.')
        return []

    log.info('Broken providers found: {0}', response)
    return response


def is_already_processed_media(full_filename):
    """Check if resource was already processed."""
    main_db_con = db.DBConnection()
    history_result = main_db_con.select('SELECT action FROM history '
                                        'WHERE action = ? '
                                        'AND resource LIKE ?',
                                        [DOWNLOADED, '%' + full_filename])
    return bool(history_result)


def is_info_hash_in_history(info_hash):
    """Check if info hash is in history."""
    main_db_con = db.DBConnection()
    history_result = main_db_con.select('SELECT info_hash FROM history '
                                        'WHERE info_hash=?',
                                        [info_hash])
    return bool(history_result)


def is_info_hash_processed(info_hash):
    """Check if info hash was already processed (downloaded status)."""
    main_db_con = db.DBConnection()
    history_result = main_db_con.select('SELECT info_hash FROM (SELECT showid, season, episode, quality '
                                        'FROM history WHERE info_hash=?) s '
                                        'JOIN history d ON '
                                        'd.showid = s.showid AND '
                                        'd.season = s.season AND '
                                        'd.episode = s.episode AND '
                                        'd.quality = s.quality '
                                        'WHERE d.action = ?',
                                        [info_hash, DOWNLOADED])
    return bool(history_result)


def title_to_imdb(title, start_year, imdb_api=None):
    """Get the IMDb ID from a show title and its start year."""
    if imdb_api is None:
        imdb_api = Imdb()

    titles = imdb_api.search_for_title(title)

    # ImdbPie returns the year as string
    start_year = str(start_year)
    title = title.lower()

    for candidate in titles:
        # Only return matches by year
        if candidate['title'].lower() == title and candidate['year'] == start_year:
            return candidate['imdb_id']


def get_title_without_year(title, title_year):
    """Get title without year."""
    if not title_year:
        return title
    year = ' ({year})'.format(year=title_year)
    if year in title:
        title = title.replace(year, '')
    return title
