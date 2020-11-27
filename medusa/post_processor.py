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
"""Post processor module."""
from __future__ import unicode_literals

import fnmatch
import os
import re
import stat
import subprocess
import sys
from builtins import object
from builtins import str
from collections import OrderedDict

import adba

from medusa import (
    app,
    db,
    failed_history,
    helpers,
    history,
    logger,
    notifiers,
)
from medusa.common import (
    DOWNLOADED,
    Quality,
    SNATCHED,
    SNATCHED_BEST,
    SNATCHED_PROPER,
)
from medusa.helper.common import (
    episode_num,
    pretty_file_size,
    remove_extension,
)
from medusa.helper.exceptions import (
    EpisodeNotFoundException,
    EpisodePostProcessingFailedException,
    ShowDirectoryNotFoundException,
)
from medusa.helpers import is_subtitle, verify_freespace
from medusa.helpers.anidb import set_up_anidb_connection
from medusa.helpers.utils import generate
from medusa.name_parser.parser import (
    InvalidNameException,
    InvalidShowException,
    NameParser,
)
from medusa.show import naming
from medusa.subtitles import from_code, from_ietf_code, get_subtitles_dir

import rarfile
from rarfile import Error as RarError, NeedFirstVolume

from six import viewitems

# Most common language tags from IETF
# https://datahub.io/core/language-codes#resource-ietf-language-tags
LANGUAGE_TAGS = {
    'en-us': 'en-US',
    'en-gb': 'en-GB',
    'en-au': 'en-AU',
    'pt-br': 'pt-BR',
    'pt-pt': 'pt-PT',
    'es-mx': 'es-MX',
    'zh-cn': 'zh-CN',
    'zh-tw': 'zh-TW',
}


class PostProcessor(object):
    """A class which will process a media file according to the post processing settings in the config."""

    EXISTS_LARGER = 1
    EXISTS_SAME = 2
    EXISTS_SMALLER = 3
    DOESNT_EXIST = 4
    IGNORED_FILESTRINGS = ['.AppleDouble', '.DS_Store']

    def __init__(self, file_path, nzb_name=None, process_method=None, is_priority=None):
        """
        Create a new post processor with the given file path and optionally an NZB name.

        file_path: The path to the file to be processed
        nzb_name: The name of the NZB which resulted in this file being downloaded (optional)
        """
        # absolute path to the folder that is being processed
        self.folder_path = os.path.dirname(os.path.abspath(file_path))
        # full path to file
        self.file_path = file_path
        # file name only
        self.file_name = os.path.basename(file_path)
        # relative path to the file that is being processed
        self.rel_path = self._get_rel_path()
        self.nzb_name = nzb_name
        self.process_method = process_method or app.PROCESS_METHOD
        self.in_history = False
        self.release_group = None
        self.release_name = None
        self.is_proper = False
        self.is_priority = is_priority
        self._output = []
        self.version = None
        self.anidbEpisode = None
        self.manually_searched = False
        self.info_hash = None
        self.item_resources = OrderedDict([('file name', self.file_name),
                                           ('relative path', self.rel_path),
                                           ('nzb name', self.nzb_name)])

    def log(self, message, level=logger.INFO):
        """
        Wrap the internal logger which also keeps track of messages and saves them to a string for later.

        :param message: The string to log (unicode)
        :param level: The log level to use (optional)
        """
        logger.log(message, level)
        self._output.append(message)

    @property
    def output(self):
        """Return the concatenated log messages."""
        return '\n'.join(self._output)

    def _get_rel_path(self):
        """
        Return the relative path to the file if possible, else the parent dir.

        :return: relative path to file or parent dir to file
        """
        if app.TV_DOWNLOAD_DIR:
            try:
                rel_path = os.path.relpath(self.file_path, app.TV_DOWNLOAD_DIR)
                # check if we really found the relative path
                if not rel_path.startswith('..'):
                    return rel_path
            except ValueError:
                pass

        return self.file_path

    def _compare_file_size(self, existing_file):
        """
        Compare size to existing file.

        :param existing_file: file to compare
        :return:
            DOESNT_EXIST if file doesn't exist
            EXISTS_LARGER if existing file is larger
            EXISTS_SMALLER if existing file is smaller
            EXISTS_SAME  if existing file is the same size
        """
        new_size = os.path.getsize(self.file_path)

        try:
            old_size = os.path.getsize(existing_file)
        except OSError:
            self.log(u'New file: {}'.format(self.file_path))
            self.log(u'New size: {}'.format(pretty_file_size(new_size)))
            self.log(u"There is no existing file so there's no worries about replacing it", logger.DEBUG)
            return self.DOESNT_EXIST

        delta_size = new_size - old_size

        self.log(u'Old file: {}'.format(existing_file))
        self.log(u'New file: {}'.format(self.file_path))
        self.log(u'Old size: {}'.format(pretty_file_size(old_size)))
        self.log(u'New size: {}'.format(pretty_file_size(new_size)))

        if not delta_size:
            self.log(u'New file is the same size.')
            return self.EXISTS_SAME
        else:
            self.log(u'New file is {size} {difference}'.format(
                size=pretty_file_size(abs(delta_size)),
                difference=u'smaller' if new_size < old_size else u'larger',
            ))
            return self.EXISTS_LARGER if new_size < old_size else self.EXISTS_SMALLER

    def list_associated_files(self, file_path, subfolders=False, subtitles_only=False, refine=False):
        """
        For a given file path search for associated files and return their absolute paths.

        :param file_path: path of the file to check for associated files
        :param subfolders: also check subfolders while searching files
        :param subtitles_only: list only associated subtitles
        :param refine: refine the associated files with additional options
        :return: A list containing all files which are associated to the given file
        """
        files = self._search_files(file_path, subfolders=subfolders)

        # file path to the video file that is being processed (without extension)
        processed_file_name = os.path.splitext(os.path.basename(file_path))[0].lower() + '.'

        processed_names = (processed_file_name,)
        processed_names += tuple((_f for _f in (self._rar_basename(file_path, files),) if _f))

        associated_files = set()
        for found_file in files:

            # Exclude the video file we are post-processing
            if found_file == file_path:
                continue

            # Exclude non-subtitle files with the 'only subtitles' option
            if subtitles_only and not is_subtitle(found_file):
                continue

            # Exclude .rar files
            if re.search(r'(^.+\.(rar|r\d+)$)', found_file):
                continue

            file_name = os.path.basename(found_file).lower()
            if file_name.startswith(processed_names):
                associated_files.add(found_file)

        if associated_files:
            self.log(u'Found the following associated files for {0}: {1}'.format
                     (file_path, associated_files), logger.DEBUG)
            if refine:
                associated_files = self._refine_associated_files(associated_files)
        else:
            self.log(u'No associated files were found for {0}'.format(file_path), logger.DEBUG)

        return list(associated_files)

    def _refine_associated_files(self, files):
        """
        Refine associated files with additional options.

        :param files: set of associated files
        :return: set containing the associated files left
        """
        files_to_delete = set()

        # "Delete associated files" setting
        if app.MOVE_ASSOCIATED_FILES:
            # "Keep associated file extensions" input box
            if app.ALLOWED_EXTENSIONS:
                allowed_extensions = app.ALLOWED_EXTENSIONS
                for associated_file in files:
                    found_extension = helpers.get_extension(associated_file)
                    if found_extension and found_extension.lower() not in allowed_extensions:
                        files_to_delete.add(associated_file)
            else:
                files_to_delete = files

        if files_to_delete:
            self.log(u'Deleting following associated files: {0}'.format(files_to_delete), logger.DEBUG)
            self._delete(list(files_to_delete))

        return files - files_to_delete

    @staticmethod
    def _search_files(path, pattern='*', subfolders=False, basename_only=False, sort=False):
        """
        Search for files in a given path.

        :param path: path to file or folder (folder paths must end with slashes)
        :param pattern: pattern used to match the files
        :param subfolders: search for files in subfolders
        :param basename_only: only match files with the same name
        :param sort: return files sorted by size
        :return: list with found files or empty list
        """
        directory = os.path.dirname(path)

        if basename_only:
            if os.path.isfile(path):
                new_pattern = os.path.splitext(os.path.basename(path))[0]
            elif os.path.isdir(path):
                new_pattern = os.path.split(directory)[1]
            else:
                logger.log(u'Basename match requires either a file or a directory. '
                           u'{name} is not allowed.'.format(name=path), logger.ERROR)
                return []

            if any(char in new_pattern for char in ['[', '?', '*']):
                # Escaping is done by wrapping any of "*?[" between square brackets.
                # Modified from: https://hg.python.org/cpython/file/tip/Lib/glob.py#l161
                if isinstance(new_pattern, bytes):
                    new_pattern = re.compile(b'([*?[])').sub(br'[\1]', new_pattern)
                else:
                    new_pattern = re.compile('([*?[])').sub(r'[\1]', new_pattern)

            pattern = new_pattern + pattern

        files = []
        for root, _, filenames in os.walk(directory):
            for filename in fnmatch.filter(filenames, pattern):
                files.append(os.path.join(root, filename))
            if not subfolders:
                break

        if sort:
            files = sorted(files, key=os.path.getsize, reverse=True)

        return files

    @staticmethod
    def _rar_basename(file_path, files):
        """Return the lowercase basename of the source rar archive if found."""
        videofile = os.path.basename(file_path)
        rars = (x for x in files if os.path.isfile(x) and rarfile.is_rarfile(x))

        for rar in rars:
            try:
                content = rarfile.RarFile(rar).namelist()
            except NeedFirstVolume:
                continue
            except RarError as error:
                logger.log(u'An error occurred while reading the following RAR file: {name}. '
                           u'Error: {message}'.format(name=rar, message=error), logger.WARNING)
                continue
            if videofile in content:
                return os.path.splitext(os.path.basename(rar))[0].lower() + '.'

    def _delete(self, files, associated_files=False):
        """
        Delete the file(s) and optionally all associated files.

        :param files: path(s) to file(s) that should be deleted
        :param associated_files: True to delete all files which differ only by extension, False to leave them
        """
        gen_files = generate(files or [])
        files = list(gen_files)

        # also delete associated files, works only for 1 file
        if associated_files and len(files) == 1:
            files += self.list_associated_files(files[0], subfolders=True)

        for filename in files:
            if os.path.isfile(filename):
                self.log(u'Deleting file: {0}'.format(filename), logger.DEBUG)
                # check first the read-only attribute
                file_attribute = os.stat(filename)[0]
                if not file_attribute & stat.S_IWRITE:
                    # File is read-only, so make it writeable
                    self.log(u'Read only mode on file {0}. '
                             u'Will try to make it writeable'.format(filename),
                             logger.DEBUG)
                    try:
                        os.chmod(filename, stat.S_IWRITE)
                    except OSError as error:
                        self.log(
                            u'Cannot change permissions for {path}. '
                            u'Error: {msg}'.format(path=filename, msg=error),
                            logger.WARNING
                        )

                os.remove(filename)

                # do the library update for synoindex
                notifiers.synoindex_notifier.deleteFile(filename)

    @staticmethod
    def rename_associated_file(new_path, new_basename, filepath):
        """Rename associated file using media basename.

        :param new_path: full show folder path where the file will be moved|copied|linked to
        :param new_basename: the media base filename (no extension) to use during the rename
        :param filepath: full path of the associated file
        :return: renamed full file path
        """
        # file extension without leading dot
        extension = helpers.get_extension(filepath)
        # initially set current extension as new extension
        new_extension = extension

        # replace nfo with nfo-orig to avoid conflicts
        if extension == 'nfo' and app.NFO_RENAME:
            new_extension = 'nfo-orig'

        elif is_subtitle(filepath):
            split_path = filepath.rsplit('.', 2)
            # len != 3 means we have a subtitle without language
            if len(split_path) == 3:
                sub_code = split_path[1]
                code = sub_code.lower().replace('_', '-')
                if from_code(code, unknown='') or from_ietf_code(code, unknown=''):
                    code = LANGUAGE_TAGS.get(code, code)
                    new_extension = code + '.' + extension
                    extension = sub_code + '.' + extension

        # rename file with new basename
        if new_basename:
            new_filename = new_basename + '.' + new_extension
        else:
            # current file name including extension
            new_filename = os.path.basename(filepath)
            # if we're not renaming we still want to change the extension sometimes
            if extension != new_extension:
                new_filename = new_filename.replace(extension, new_extension)

        new_filepath = os.path.join(new_path, new_filename)
        if is_subtitle(new_filepath):
            new_filepath = os.path.join(get_subtitles_dir(new_filepath), new_filename)

        return new_filepath

    def _combined_file_operation(self, file_path, new_path, new_basename, associated_files=False,
                                 action=None, subtitles=False, subtitle_action=None):
        """
        Perform a generic operation (move or copy) on a file.

        Can rename the file as well as change its location, and optionally move associated files too.

        :param file_path: The full path of the file to act on
        :param new_path: full show folder path where the file will be moved|copied|linked to
        :param new_basename: The base filename (no extension) to use during the action. Use None to keep the same name
        :param associated_files: Boolean, whether we should copy similarly-named files too
        :param action: function that takes an old path and new path and does an operation with them (move/copy/link)
        :param subtitles: Boolean, whether we should process subtitles too
        """
        if not action:
            self.log(u'Must provide an action for the combined file operation', logger.ERROR)
            return

        other_files = []
        if associated_files:
            other_files += self.list_associated_files(file_path, refine=True)
        if subtitles:
            other_files += self.list_associated_files(file_path, subfolders=True, subtitles_only=True, refine=True)
            # Remove possible duplicates
            if associated_files:
                other_files = list(set(other_files))

        file_list = [file_path] + other_files
        if not file_list:
            self.log(u'There were no files associated with {0}, not moving anything'.format
                     (file_path), logger.DEBUG)
            return

        for cur_associated_file in file_list:
            new_file_path = self.rename_associated_file(new_path, new_basename, cur_associated_file)

            # If subtitle was downloaded from Medusa it can't be in the torrent folder, so we move it.
            # Otherwise when torrent+data gets removed, the folder won't be deleted because of subtitle
            if app.POSTPONE_IF_NO_SUBS and is_subtitle(cur_associated_file):
                # subtitle_action = move
                action = subtitle_action or action

            action(cur_associated_file, new_file_path)

    def post_process_action(self, file_path, new_path, new_basename, associated_files=False, subtitles=False):
        """
        Run the given action on file and set proper permissions.

        :param file_path: The full path of the file to act on
        :param new_path: full show folder path where the file will be moved|copied|linked to
        :param new_basename: The base filename (no extension) to use. Use None to keep the same name
        :param associated_files: Boolean, whether we should run the action in similarly-named files too
        :param subtitles: Boolean, whether we should process subtitles too
        """
        def move(cur_file_path, new_file_path):
            self.log(u'Moving file from {0} to {1} '.format(cur_file_path, new_file_path), logger.DEBUG)
            try:
                helpers.move_file(cur_file_path, new_file_path)
                helpers.chmod_as_parent(new_file_path)
            except (IOError, OSError) as e:
                self.log(u'Unable to move file {0} to {1}: {2!r}'.format
                         (cur_file_path, new_file_path, e), logger.ERROR)
                raise EpisodePostProcessingFailedException('Unable to move the files to their new home')

        def copy(cur_file_path, new_file_path):
            self.log(u'Copying file from {0} to {1}'.format(cur_file_path, new_file_path), logger.DEBUG)
            try:
                helpers.copy_file(cur_file_path, new_file_path)
                helpers.chmod_as_parent(new_file_path)
            except (IOError, OSError) as e:
                self.log(u'Unable to copy file {0} to {1}: {2!r}'.format
                         (cur_file_path, new_file_path, e), logger.ERROR)
                raise EpisodePostProcessingFailedException('Unable to copy the files to their new home')

        def hardlink(cur_file_path, new_file_path):
            self.log(u'Hard linking file from {0} to {1}'.format(cur_file_path, new_file_path), logger.DEBUG)
            try:
                helpers.hardlink_file(cur_file_path, new_file_path)
                helpers.chmod_as_parent(new_file_path)
            except (IOError, OSError) as e:
                self.log(u'Unable to link file {0} to {1}: {2!r}'.format
                         (cur_file_path, new_file_path, e), logger.ERROR)
                raise EpisodePostProcessingFailedException('Unable to hard link the files to their new home')

        def symlink(cur_file_path, new_file_path):
            self.log(u'Moving then symbolic linking file from {0} to {1}'.format
                     (cur_file_path, new_file_path), logger.DEBUG)
            try:
                helpers.move_and_symlink_file(cur_file_path, new_file_path)
                helpers.chmod_as_parent(new_file_path)
            except (IOError, OSError) as e:
                self.log(u'Unable to link file {0} to {1}: {2!r}'.format
                         (cur_file_path, new_file_path, e), logger.ERROR)
                raise EpisodePostProcessingFailedException('Unable to move and link the files to their new home')

        def keeplink(cur_file_path, new_file_path):
            self.log(u'Symbolic linking file from {0} to {1}'.format
                     (cur_file_path, new_file_path), logger.DEBUG)
            try:
                helpers.symlink(cur_file_path, new_file_path)
                helpers.chmod_as_parent(new_file_path)
            except (IOError, OSError) as e:
                self.log(u'Unable to link file {0} to {1}: {2!r}'.format
                         (cur_file_path, new_file_path, e), logger.ERROR)
                raise EpisodePostProcessingFailedException('Unable to move and link the files to their new home')

        def reflink(cur_file_path, new_file_path):
            self.log(u'Reflink file from {0} to {1}'.format(cur_file_path, new_basename), logger.DEBUG)
            try:
                helpers.reflink_file(cur_file_path, new_file_path)
                helpers.chmod_as_parent(new_file_path)
            except (IOError, OSError) as e:
                self.log(u'Unable to reflink file {0} to {1}: {2!r}'.format
                         (cur_file_path, new_file_path, e), logger.ERROR)
                raise EpisodePostProcessingFailedException('Unable to copy the files to their new home')

        action = {'copy': copy, 'move': move, 'hardlink': hardlink, 'symlink': symlink, 'reflink': reflink, 'keeplink': keeplink}.get(self.process_method)
        # Subtitle action should be move in case of hardlink|symlink|reflink as downloaded subtitle is not part of torrent
        subtitle_action = {'copy': copy, 'move': move, 'hardlink': move, 'symlink': move, 'reflink': move}.get(self.process_method)
        self._combined_file_operation(file_path, new_path, new_basename, associated_files=associated_files,
                                      action=action, subtitles=subtitles, subtitle_action=subtitle_action)

    @staticmethod
    def _build_anidb_episode(connection, file_path):
        """
        Look up anidb properties for an episode.

        :param connection: anidb connection handler
        :param file_path: file to check
        :return: episode object
        """
        ep = adba.Episode(connection, filePath=file_path,
                          paramsF=['quality', 'anidb_file_name', 'crc32'],
                          paramsA=['epno', 'english_name', 'short_name_list', 'other_name', 'synonym_list'])

        return ep

    def _add_to_anidb_mylist(self, file_path):
        """
        Add an episode to anidb mylist.

        :param file_path: file to add to mylist
        """
        if set_up_anidb_connection():
            if not self.anidbEpisode:  # seems like we could parse the name before, now lets build the anidb object
                self.anidbEpisode = self._build_anidb_episode(app.ADBA_CONNECTION, file_path)

            self.log(u'Adding the file to the anidb mylist', logger.DEBUG)
            try:
                self.anidbEpisode.add_to_mylist(state=1)  # state = 1 sets the state of the file to "internal HDD"
            except Exception as e:
                self.log(u'Exception message: {0!r}'.format(e))

    def _parse_info(self):
        """
        For a given file try to find the show, season, epsiodes, version and quality.

        :return: A (show, season, episodes, version, quality) tuple
        """
        show = season = version = airdate = quality = None
        episodes = []

        for counter, (resource, name) in enumerate(self.item_resources.items()):

            cur_show, cur_season, cur_episodes, cur_quality, cur_version = self._analyze_name(name)

            if not cur_show:
                continue
            show = cur_show

            if cur_season is not None:
                season = cur_season

            if cur_episodes:
                episodes = cur_episodes

            # we only get current version from anime
            if cur_version is not None:
                version = cur_version

            # for air-by-date shows we need to look up the season/episode from database
            if cur_season == -1 and show and cur_episodes:
                self.log(u'Looks like this is an air-by-date or sports show, '
                         u'attempting to convert the date to season and episode', logger.DEBUG)

                try:
                    airdate = episodes[0].toordinal()
                except AttributeError:
                    self.log(u"Couldn't convert to a valid airdate: {0}".format(episodes[0]), logger.DEBUG)
                    continue

            if counter < (len(self.item_resources) - 1):
                if Quality.qualityStrings[cur_quality] == 'Unknown':
                    continue
            quality = cur_quality

            # We have all the information we need
            self.log(u'Show information parsed from {0}'.format(resource), logger.DEBUG)
            break

        return show, season, episodes, quality, version, airdate

    def _find_info(self):
        series_obj, season, episodes, quality, version, airdate = self._parse_info()
        # TODO: Move logic below to a single place -> NameParser

        if airdate and series_obj:
            # Ignore season 0 when searching for episode
            # (conflict between special and regular episode, same air date)
            main_db_con = db.DBConnection()
            sql_result = main_db_con.select(
                'SELECT season, episode '
                'FROM tv_episodes '
                'WHERE showid = ? '
                'AND indexer = ? '
                'AND airdate = ? '
                'AND season != 0',
                [series_obj.series_id, series_obj.indexer, airdate])

            if sql_result:
                season = int(sql_result[0]['season'])
                episodes = [int(sql_result[0]['episode'])]
            else:
                # Found no result, trying with season 0
                sql_result = main_db_con.select(
                    'SELECT season, episode '
                    'FROM tv_episodes '
                    'WHERE showid = ? '
                    'AND indexer = ? '
                    'AND airdate = ?',
                    [series_obj.series_id, series_obj.indexer, airdate])

                if sql_result:
                    season = int(sql_result[0]['season'])
                    episodes = [int(sql_result[0]['episode'])]
                else:
                    self.log(u'Unable to find episode with date {0} for show {1}, skipping'.format
                             (episodes[0], series_obj.indexerid), logger.DEBUG)
                    # we don't want to leave dates in the episode list
                    # if we couldn't convert them to real episode numbers
                    episodes = []

        # If there's no season, we assume it's the first season
        elif season is None and series_obj:
            main_db_con = db.DBConnection()
            numseasons_result = main_db_con.select(
                'SELECT COUNT(DISTINCT season) as count '
                'FROM tv_episodes '
                'WHERE showid = ? '
                'AND indexer = ? '
                'AND season != 0',
                [series_obj.series_id, series_obj.indexer])

            if int(numseasons_result[0]['count']) == 1:
                self.log(u"Episode doesn't have a season number, but this show appears "
                         u'to have only 1 season, setting season number to 1...', logger.DEBUG)
                season = 1

        return series_obj, season, episodes, quality, version

    def _analyze_name(self, name):
        """
        Take a name and try to figure out a show, season, episodes, version and quality from it.

        :param name: A string which we want to analyze to determine show info from (unicode)
        :return: A (show, season, episodes, version, quality) tuple
        """
        to_return = (None, None, [], None, None)

        if not name:
            return to_return

        logger.log(u'Analyzing name: {0}'.format(name), logger.DEBUG)

        # parse the name to break it into show, season, episodes, quality and version
        try:
            parse_result = NameParser().parse(name)
        except (InvalidNameException, InvalidShowException) as error:
            self.log(u'{0}'.format(error), logger.DEBUG)
            return to_return

        if parse_result.series and all([parse_result.series.air_by_date or parse_result.series.is_sports,
                                        parse_result.is_air_by_date]):
            season = -1
            episodes = [parse_result.air_date]
        else:
            season = parse_result.season_number
            episodes = parse_result.episode_numbers

        to_return = (parse_result.series, season, episodes, parse_result.quality, parse_result.version)

        self._finalize(parse_result)
        return to_return

    def _finalize(self, parse_result):
        """
        Store release name of result if it is complete and final.

        :param parse_result: Result of parser
        """
        self.release_group = parse_result.release_group

        # remember whether it's a proper
        self.is_proper = bool(parse_result.proper_tags)

        # if the result is complete set release name
        if parse_result.series_name and ((parse_result.season_number is not None and parse_result.episode_numbers) or
                                         parse_result.air_date) and parse_result.release_group:

            if not self.release_name:
                self.release_name = remove_extension(os.path.basename(parse_result.original_name))

        else:
            logger.log(u"Parse result not sufficient (all following have to be set). Won't save release name",
                       logger.DEBUG)
            logger.log(u'Parse result (series_name): {0}'.format(parse_result.series_name), logger.DEBUG)
            logger.log(u'Parse result (season_number): {0}'.format(parse_result.season_number), logger.DEBUG)
            logger.log(u'Parse result (episode_numbers): {0}'.format(parse_result.episode_numbers), logger.DEBUG)
            logger.log(u'Parse result (ab_episode_numbers): {0}'.format(parse_result.ab_episode_numbers), logger.DEBUG)
            logger.log(u'Parse result (air_date): {0}'.format(parse_result.air_date), logger.DEBUG)
            logger.log(u'Parse result (release_group): {0}'.format(parse_result.release_group), logger.DEBUG)

    def _get_ep_obj(self, series_obj, season, episodes):
        """
        Retrieve the Episode object requested.

        :param show: The show object belonging to the show we want to process
        :param season: The season of the episode (int)
        :param episodes: A list of episodes to find (list of ints)
        :return: If the episode(s) can be found then a Episode object with the correct related eps will
        be instantiated and returned. If the episode can't be found then None will be returned.
        """
        root_ep = None
        for cur_episode in episodes:
            self.log(u'Retrieving episode object for {0} {1}'.format
                     (series_obj.name, episode_num(season, cur_episode)), logger.DEBUG)

            # now that we've figured out which episode this file is just load it manually
            try:
                cur_ep = series_obj.get_episode(season, cur_episode)
                if not cur_ep:
                    raise EpisodeNotFoundException()
            except EpisodeNotFoundException as e:
                raise EpisodePostProcessingFailedException(u'Unable to create episode: {0!r}'.format(e))

            # associate all the episodes together under a single root episode
            if root_ep is None:
                root_ep = cur_ep
                root_ep.related_episodes = []
            elif cur_ep not in root_ep.related_episodes:
                root_ep.related_episodes.append(cur_ep)

        return root_ep

    # def _quality_from_status(self, ep_obj):
    #     """
    #     Determine the quality of the file that is being post processed with its status.
    #
    #     :param ep_obj: episode object.
    #     :return: A quality value found in common.Quality
    #     """
    #
    #     if ep_obj.status in (common.SNATCHED, common.SNATCHED_PROPER, common.SNATCHED_BEST):
    #         if ep_obj.quality != common.Quality.UNKNOWN:
    #             self.log(u'The snatched status has a quality in it, using that: {0}'.format
    #                      (common.Quality.qualityStrings[ep_obj.quality]), logger.DEBUG)
    #             return ep_obj.quality
    #
    #     return common.UNKNOWN

    def _get_quality(self, ep_obj):
        """
        Determine the quality of the file that is being post processed with alternative methods.

        :param ep_obj: The Episode object related to the file we are post processing
        :return: A quality value found in common.Quality
        """
        for resource_name, cur_name in viewitems(self.item_resources):

            # Skip names that are falsey
            if not cur_name:
                continue

            ep_quality = Quality.name_quality(cur_name, ep_obj.series.is_anime, extend=False)
            self.log(u"Looking up quality for '{0}', got {1}".format
                     (cur_name, Quality.qualityStrings[ep_quality]), logger.DEBUG)
            if ep_quality != Quality.UNKNOWN:
                self.log(u"Looks like {0} '{1}' has quality {2}, using that".format
                         (resource_name, cur_name, Quality.qualityStrings[ep_quality]), logger.DEBUG)
                return ep_quality

        # Try using other methods to get the file quality
        ep_quality = Quality.name_quality(self.file_path, ep_obj.series.is_anime)
        self.log(u"Trying other methods to get quality for '{0}', got {1}".format
                 (self.file_name, Quality.qualityStrings[ep_quality]), logger.DEBUG)
        if ep_quality != Quality.UNKNOWN:
            self.log(u"Looks like '{0}' has quality {1}, using that".format
                     (self.file_name, Quality.qualityStrings[ep_quality]), logger.DEBUG)
            return ep_quality

        return ep_quality

    def _priority_from_history(self, series_obj, season, episodes, quality):
        """Evaluate if the file should be marked as priority."""
        main_db_con = db.DBConnection()
        snatched_statuses = [SNATCHED, SNATCHED_PROPER, SNATCHED_BEST]

        for episode in episodes:
            # First: check if the episode status is snatched
            tv_episodes_result = main_db_con.select(
                'SELECT quality, manually_searched '
                'FROM tv_episodes '
                'WHERE indexer = ? '
                'AND showid = ? '
                'AND season = ? '
                'AND episode = ? '
                'AND status IN (?, ?, ?) ',
                [series_obj.indexer, series_obj.series_id,
                 season, episode] + snatched_statuses
            )

            if tv_episodes_result and tv_episodes_result[0]['quality'] == quality:
                # Check if the snatch is a manual snatch
                if tv_episodes_result[0]['manually_searched'] == 1:
                    self.manually_searched = True

                # Second: get the quality of the last snatched epsiode
                # and compare it to the quality we are post-processing
                history_result = main_db_con.select(
                    'SELECT quality, info_hash '
                    'FROM history '
                    'WHERE indexer_id = ? '
                    'AND showid = ? '
                    'AND season = ? '
                    'AND episode = ? '
                    'AND action IN (?, ?, ?) '
                    'ORDER BY date DESC',
                    [series_obj.indexer, series_obj.series_id,
                     season, episode] + snatched_statuses
                )

                if history_result and history_result[0]['quality'] == quality:
                    # Third: make sure the file we are post-processing hasn't been
                    # previously processed, as we wouldn't want it in that case

                    # Get info hash so we can move torrent if setting is enabled
                    self.info_hash = history_result[0]['info_hash'] or None

                    download_result = main_db_con.select(
                        'SELECT resource '
                        'FROM history '
                        'WHERE indexer_id = ? '
                        'AND showid = ? '
                        'AND season = ? '
                        'AND episode = ? '
                        'AND quality = ? '
                        'AND action = ? '
                        'ORDER BY date DESC',
                        [series_obj.indexer, series_obj.series_id,
                         season, episode, quality, DOWNLOADED]
                    )

                    if download_result:
                        download_name = os.path.basename(download_result[0]['resource'])
                        # If the file name we are processing differs from the file
                        # that was previously processed, we want this file
                        if self.file_name != download_name:
                            self.in_history = True
                            return

                    else:
                        # There aren't any other files processed before for this
                        # episode and quality, we can safely say we want this file
                        self.in_history = True
                        return

    def _is_priority(self, old_ep_quality, new_ep_quality):
        """
        Determine if the episode is a priority download or not (if it is expected).

        Episodes which are expected (snatched) are priority, others are not.

        :param old_ep_quality: The old quality of the episode that is being processed
        :param new_ep_quality: The new quality of the episode that is being processed
        :return: True if the episode is priority, False otherwise.
        """
        level = logger.DEBUG
        self.log(u'Snatch in history: {0}'.format(self.in_history), level)
        self.log(u'Manually snatched: {0}'.format(self.manually_searched), level)
        self.log(u'Info hash: {0}'.format(self.info_hash), level)
        self.log(u'NZB: {0}'.format(bool(self.nzb_name)), level)
        self.log(u'Current quality: {0}'.format(Quality.qualityStrings[old_ep_quality]), level)
        self.log(u'New quality: {0}'.format(Quality.qualityStrings[new_ep_quality]), level)
        self.log(u'Proper: {0}'.format(self.is_proper), level)

        # If in_history is True it must be a priority download
        return any([self.in_history, self.is_priority, self.manually_searched])

    @staticmethod
    def _should_process(current_quality, new_quality, allowed, preferred):
        """
        Determine if a quality should be processed according to the quality system.

        This method is used only for replace existing files
        Despite quality system rules (should_search method), in should_process method:
         - New higher Allowed replaces current Allowed (overrrides rule where Allowed is final quality)
         - New higher Preferred replaces current Preferred (overrides rule where Preffered is final quality)

        :param current_quality: The current quality of the episode that is being processed
        :param new_quality: The new quality of the episode that is being processed
        :param allowed: Qualities that are allowed
        :param preferred: Qualities that are preferred
        :return: Tuple with Boolean if the quality should be processed and String with reason if should process or not
        """
        if new_quality in preferred:
            if current_quality in preferred:
                if new_quality > current_quality:
                    return True, 'New quality is higher than current Preferred. Accepting quality'
                elif new_quality < current_quality:
                    return False, 'New quality is lower than current Preferred. Ignoring quality'
                else:
                    return False, 'New quality is equal than current Preferred. Ignoring quality'
            return True, 'New quality is Preferred'
        elif new_quality in allowed:
            if current_quality in preferred:
                return False, 'Current quality is Allowed but we already have a current Preferred. Ignoring quality'
            elif current_quality not in allowed:
                return True, "New quality is Allowed and we don't have a current Preferred. Accepting quality"
            elif new_quality > current_quality:
                return True, 'New quality is higher than current Allowed. Accepting quality'
            elif new_quality < current_quality:
                return False, 'New quality is lower than current Allowed. Ignoring quality'
            else:
                return False, 'New quality is equal to current Allowed. Ignoring quality'
        else:
            return False, 'New quality is not in Allowed|Preferred. Ignoring quality'

    def _run_extra_scripts(self, ep_obj):
        """
        Execute any extra scripts defined in the config.

        :param ep_obj: The object to use when calling the extra script
        """
        if not app.EXTRA_SCRIPTS:
            return

        ep_location = ep_obj.location
        file_path = self.file_path
        indexer_id = str(ep_obj.series.indexerid)
        season = str(ep_obj.season)
        episode = str(ep_obj.episode)
        airdate = str(ep_obj.airdate)

        for script_path in app.EXTRA_SCRIPTS:

            if not os.path.isfile(script_path):
                self.log(u'Extra script {0} is not a file.'.format(script_path), logger.WARNING)
                continue

            if not script_path.endswith('.py'):
                self.log(u'Extra script {0} is not a Python file.'.format(script_path), logger.WARNING)
                continue

            self.log(u'Running extra script: {0}'.format(script_path), logger.INFO)
            script_cmd = [sys.executable, script_path, ep_location, file_path, indexer_id, season, episode, airdate]

            # use subprocess to run the command and capture output
            self.log(u'Executing command: {0}'.format(script_cmd))
            try:
                process = subprocess.Popen(
                    script_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=app.PROG_DIR
                )
                out, _ = process.communicate()

                self.log(u'Script result: {0}'.format(out), logger.DEBUG)

            except Exception as error:
                self.log(u'Unable to run extra script: {0!r}'.format(error))

    def flag_kodi_clean_library(self):
        """Set flag to clean Kodi's library if Kodi is enabled."""
        if app.USE_KODI:
            self.log(u'Setting to clean Kodi library as we are going to replace the file')
            app.KODI_LIBRARY_CLEAN_PENDING = True

    def process(self):
        """
        Post-process a given file.

        :return: True on success, False on failure
        """
        self.log(u'Processing {0}'.format(self.file_path))

        if os.path.isdir(self.file_path):
            self.log(u'File {0} seems to be a directory'.format(self.file_path))
            return False

        if not os.path.exists(self.file_path):
            raise EpisodePostProcessingFailedException(u"File {0} doesn't exist, did unrar fail?".format
                                                       (self.file_path))

        for ignore_file in self.IGNORED_FILESTRINGS:
            if ignore_file in self.file_path:
                self.log(u'File {0} is ignored type, skipping'.format(self.file_path))
                return False

        # reset in_history
        self.in_history = False

        # reset the anidb episode object
        self.anidbEpisode = None

        # try to find the file info
        (series_obj, season, episodes, quality, version) = self._find_info()
        if not series_obj:
            raise EpisodePostProcessingFailedException(u"This show isn't in your list, you need to add it "
                                                       u'before post-processing an episode')
        elif season is None or not episodes:
            raise EpisodePostProcessingFailedException(u'Not enough information to determine what episode this is')

        # retrieve/create the corresponding Episode objects
        ep_obj = self._get_ep_obj(series_obj, season, episodes)
        old_ep_quality = ep_obj.quality

        # get the quality of the episode we're processing
        if quality and quality != Quality.UNKNOWN:
            self.log(u'The episode file has a quality in it, using that: {0}'.format
                     (Quality.qualityStrings[quality]), logger.DEBUG)
            new_ep_quality = quality
        else:
            # Fall back to the episode object's quality
            new_ep_quality = ep_obj.quality

        # check snatched history to see if we should set the download as priority
        self._priority_from_history(series_obj, season, episodes, new_ep_quality)
        if self.in_history:
            self.log(u'This episode was found in history as SNATCHED.', logger.DEBUG)

        if new_ep_quality == Quality.UNKNOWN:
            new_ep_quality = self._get_quality(ep_obj)

        logger.log(u'Quality of the episode we are processing: {0}'.format
                   (Quality.qualityStrings[new_ep_quality]), logger.DEBUG)

        # see if this is a priority download
        priority_download = self._is_priority(old_ep_quality, new_ep_quality)
        self.log(u'This episode is a priority download: {0}'.format(priority_download), logger.DEBUG)

        # get the version of the episode we're processing (default is -1)
        if version != -1:
            self.log(u'Episode has a version in it, using that: v{0}'.format(version), logger.DEBUG)
        new_ep_version = version

        # check for an existing file
        existing_file_status = self._compare_file_size(ep_obj.location)

        if not priority_download:
            if existing_file_status == PostProcessor.EXISTS_SAME:
                self.log(u'File exists and the new file has the same size, aborting post-processing')
                return True

            if existing_file_status != PostProcessor.DOESNT_EXIST:
                if self.is_proper and new_ep_quality == old_ep_quality:
                    self.log(u'New file is a PROPER, marking it safe to replace')
                    self.flag_kodi_clean_library()
                else:
                    allowed_qualities, preferred_qualities = series_obj.current_qualities
                    self.log(u'Checking if new quality {0} should replace current quality: {1}'.format
                             (Quality.qualityStrings[new_ep_quality],
                              Quality.qualityStrings[old_ep_quality]))
                    should_process, should_process_reason = self._should_process(old_ep_quality, new_ep_quality,
                                                                                 allowed_qualities, preferred_qualities)
                    if not should_process:
                        raise EpisodePostProcessingFailedException(
                            u'File exists. Marking it unsafe to replace. Reason: {0}'.format(should_process_reason))
                    else:
                        self.log(u'File exists. Marking it safe to replace. Reason: {0}'.format(should_process_reason))
                        self.flag_kodi_clean_library()

            # Check if the processed file season is already in our indexer. If not,
            # the file is most probably mislabled/fake and will be skipped.
            # Only proceed if the file season is > 0
            if int(ep_obj.season) > 0:
                main_db_con = db.DBConnection()
                max_season = main_db_con.select(
                    'SELECT MAX(season) as max FROM tv_episodes WHERE showid = ? and indexer = ?',
                    [series_obj.series_id, series_obj.indexer])

                # If the file season (ep_obj.season) is bigger than
                # the indexer season (max_season[0]['max']), skip the file
                if max_season[0]['max'] and int(ep_obj.season) > int(max_season[0]['max']):
                    self.log(u'File has season {0}, while the indexer is on season {1}. '
                             u'The file may be incorrectly labeled or fake, aborting.'.format
                             (ep_obj.season, max_season[0]['max']))
                    return False

        # if the file is priority then we're going to replace it even if it exists
        else:
            # Set to clean Kodi if file exists and it is priority_download
            if existing_file_status != PostProcessor.DOESNT_EXIST:
                self.flag_kodi_clean_library()
            self.log(u"This download is marked a priority download so I'm going to replace "
                     u'an existing file if I find one')

        # try to find out if we have enough space to perform the copy or move action.
        if not helpers.is_file_locked(self.file_path, False):
            if not verify_freespace(self.file_path, ep_obj.series._location, [ep_obj] + ep_obj.related_episodes):
                self.log(u'Not enough space to continue post-processing, exiting', logger.WARNING)
                return False
        else:
            self.log(u'Unable to determine needed filespace as the source file is locked for access')

        # delete the existing file (and company)
        for cur_ep in [ep_obj] + ep_obj.related_episodes:
            try:
                self._delete(cur_ep.location, associated_files=True)
                # clean up any left over folders
                if cur_ep.location:
                    helpers.delete_empty_folders(os.path.dirname(cur_ep.location), keep_dir=ep_obj.series._location)
            except (OSError, IOError) as error:
                raise EpisodePostProcessingFailedException(u'Unable to delete the existing files. '
                                                           u'Error: {msg}'.format(msg=error))

            # set the status of the episodes
            # for cur_ep in [ep_obj] + ep_obj.related_episodes:
            #    cur_ep.status = common.Quality.composite_status(common.SNATCHED, new_ep_quality)

        # if the show directory doesn't exist then make it if desired
        if not os.path.isdir(ep_obj.series._location) and app.CREATE_MISSING_SHOW_DIRS:
            self.log(u"Show directory doesn't exist, creating it", logger.DEBUG)
            try:
                os.mkdir(ep_obj.series._location)
                helpers.chmod_as_parent(ep_obj.series._location)

                # do the library update for synoindex
                notifiers.synoindex_notifier.addFolder(ep_obj.series._location)
            except (OSError, IOError) as error:
                raise EpisodePostProcessingFailedException(u'Unable to create the show directory: {location}. '
                                                           u'Error: {msg}'.format(location=ep_obj.series._location,
                                                                                  msg=error))

            # get metadata for the show (but not episode because it hasn't been fully processed)
            ep_obj.series.write_metadata(True)

        # update the ep info before we rename so the quality & release name go into the name properly
        sql_l = []

        for cur_ep in [ep_obj] + ep_obj.related_episodes:
            with cur_ep.lock:

                if self.release_name:
                    self.log(u'Found release name {0}'.format(self.release_name), logger.DEBUG)
                    cur_ep.release_name = self.release_name
                elif self.file_name:
                    # If we can't get the release name we expect, save the original release name instead
                    self.log(u'Using original release name {0}'.format(self.file_name), logger.DEBUG)
                    cur_ep.release_name = self.file_name
                else:
                    cur_ep.release_name = u''

                cur_ep.status = DOWNLOADED
                cur_ep.quality = new_ep_quality

                cur_ep.subtitles = u''

                cur_ep.subtitles_searchcount = 0

                cur_ep.subtitles_lastsearch = u'0001-01-01 00:00:00'

                cur_ep.is_proper = self.is_proper

                cur_ep.version = new_ep_version

                if self.release_group:
                    cur_ep.release_group = self.release_group
                else:
                    cur_ep.release_group = u''

                sql_l.append(cur_ep.get_sql())

        # Just want to keep this consistent for failed handling right now
        nzb_release_name = naming.determine_release_name(self.folder_path, self.nzb_name)
        if nzb_release_name is not None:
            failed_history.log_success(nzb_release_name)
        else:
            self.log(u"Couldn't determine NZB release name, aborting", logger.WARNING)

        # find the destination folder
        try:
            proper_path = ep_obj.proper_path()
            proper_absolute_path = os.path.join(ep_obj.series.validate_location, proper_path)
            dest_path = os.path.dirname(proper_absolute_path)
        except ShowDirectoryNotFoundException:
            raise EpisodePostProcessingFailedException(u"Unable to post-process an episode if the show dir '{0}' "
                                                       u"doesn't exist, quitting".format(ep_obj.series.location))

        self.log(u'Destination folder for this episode: {0}'.format(dest_path), logger.DEBUG)

        # create any folders we need
        if not helpers.make_dirs(dest_path):
            raise EpisodePostProcessingFailedException('Unable to create destination folder to the files')

        # figure out the base name of the resulting episode file
        if app.RENAME_EPISODES:
            orig_extension = self.file_name.rpartition('.')[-1]
            new_base_name = os.path.basename(proper_path)
            new_file_name = new_base_name + '.' + orig_extension

        else:
            # if we're not renaming then there's no new base name, we'll just use the existing name
            new_base_name = None
            new_file_name = self.file_name

        # add to anidb
        if ep_obj.series.is_anime and app.ANIDB_USE_MYLIST:
            self._add_to_anidb_mylist(self.file_path)

        try:
            # do the action to the episode and associated files to the show dir
            if self.process_method in ['copy', 'hardlink', 'move', 'symlink', 'reflink', 'keeplink']:
                if not self.process_method == 'hardlink':
                    if helpers.is_file_locked(self.file_path, False):
                        raise EpisodePostProcessingFailedException('File is locked for reading')

                self.post_process_action(self.file_path, dest_path, new_base_name, bool(app.MOVE_ASSOCIATED_FILES),
                                         app.USE_SUBTITLES and bool(ep_obj.series.subtitles))
            else:
                logger.log(u"'{0}' is an unknown file processing method. "
                           u"Please correct your app's usage of the API.".format(self.process_method), logger.WARNING)
                raise EpisodePostProcessingFailedException('Unable to move the files to their new home')
        except (OSError, IOError) as error:
            self.log(u'Unable to move file {0} to {1}: {2!r}'.format
                     (self.file_path, dest_path, error), logger.ERROR)
            raise EpisodePostProcessingFailedException('Unable to move the files to their new home')

        # download subtitles
        if app.USE_SUBTITLES and ep_obj.series.subtitles:
            for cur_ep in [ep_obj] + ep_obj.related_episodes:
                with cur_ep.lock:
                    cur_ep.location = os.path.join(dest_path, new_file_name)
                    cur_ep.refresh_subtitles()
                    cur_ep.download_subtitles()

        # now that processing has finished, we can put the info in the DB.
        # If we do it earlier, then when processing fails, it won't try again.
        if sql_l:
            main_db_con = db.DBConnection()
            main_db_con.mass_action(sql_l)

        # put the new location in the database
        sql_l = []
        for cur_ep in [ep_obj] + ep_obj.related_episodes:
            with cur_ep.lock:
                cur_ep.location = os.path.join(dest_path, new_file_name)
                sql_l.append(cur_ep.get_sql())

        if sql_l:
            main_db_con = db.DBConnection()
            main_db_con.mass_action(sql_l)

        cur_ep.airdate_modify_stamp()

        # generate nfo/tbn
        try:
            ep_obj.create_meta_files()
        except Exception:
            logger.log(u'Could not create/update meta files. Continuing with post-processing...')

        # log it to history episode and related episodes (multi-episode for example)
        for cur_ep in [ep_obj] + ep_obj.related_episodes:
            history.log_download(cur_ep, self.file_path, new_ep_quality, self.release_group, new_ep_version)

        # send notifications
        notifiers.notify_download(ep_obj)
        # do the library update for KODI
        notifiers.kodi_notifier.update_library(ep_obj.series.name)
        # do the library update for Plex
        notifiers.plex_notifier.update_library(ep_obj)
        # do the library update for EMBY
        notifiers.emby_notifier.update_library(ep_obj.series)
        # do the library update for NMJ
        # nmj_notifier kicks off its library update when the notify_download is issued (inside notifiers)
        # do the library update for Synology Indexer
        notifiers.synoindex_notifier.addFile(ep_obj.location)
        # do the library update for pyTivo
        notifiers.pytivo_notifier.update_library(ep_obj)
        # do the library update for Trakt
        notifiers.trakt_notifier.update_library(ep_obj)

        self._run_extra_scripts(ep_obj)

        if not self.nzb_name and all([app.USE_TORRENTS, app.TORRENT_SEED_LOCATION,
                                      self.process_method in ('hardlink', 'symlink', 'reflink', 'keeplink')]):
            # Store self.info_hash and self.release_name so later we can remove from client if setting is enabled
            if self.info_hash:
                existing_release_names = app.RECENTLY_POSTPROCESSED.get(self.info_hash, [])
                existing_release_names.append(self.release_name or 'N/A')
                app.RECENTLY_POSTPROCESSED[self.info_hash] = existing_release_names
            else:
                if not self.in_history:
                    logger.log(u"Please consider manually move torrent to seed folder as it wasn't snatched from "
                               u"Medusa or we couldn't find it in history: {0}".format(self.file_path), logger.WARNING)
                else:
                    logger.log(u'Please consider manually move torrent to seed folder as there is no info hash in '
                               u'snatch history: {0}'.format(self.file_path), logger.WARNING)
        return True
