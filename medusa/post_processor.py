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
import fnmatch
import os
import re
import stat
import subprocess

import adba

from six import text_type

from . import app, common, db, failed_history, helpers, history, logger, notifiers, show_name_helpers
from .helper.common import episode_num, remove_extension
from .helper.exceptions import (EpisodeNotFoundException, EpisodePostProcessingFailedException,
                                ShowDirectoryNotFoundException)
from .helpers import is_subtitle, verify_freespace
from .name_parser.parser import InvalidNameException, InvalidShowException, NameParser
from .subtitles import from_code, from_ietf_code


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

        # name of the NZB that resulted in this folder
        self.nzb_name = nzb_name

        self.process_method = process_method if process_method else app.PROCESS_METHOD

        self.in_history = False

        self.release_group = None

        self.release_name = None

        self.is_proper = False

        self.is_priority = is_priority

        self.log = ''

        self.version = None

        self.anidbEpisode = None

        self.manually_searched = False

    def _log(self, message, level=logger.INFO):
        """
        A wrapper for the internal logger which also keeps track of messages and saves them to a string for later.

        :param message: The string to log (unicode)
        :param level: The log level to use (optional)
        """
        logger.log(message, level)
        self.log += message + '\n'

    def _get_rel_path(self):
        """Return the relative path to the file if possible, else the parent dir.

        :return: relative path to file or parent dir to file
        :rtype: text_type
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

    def _check_for_existing_file(self, existing_file):
        """
        Check if a file exists already.

        If it does whether it's bigger or smaller than the file we are post processing.

        :param existing_file: The file to compare to
        :return:
            DOESNT_EXIST if the file doesn't exist
            EXISTS_LARGER if the file exists and is larger than the file we are post processing
            EXISTS_SMALLER if the file exists and is smaller than the file we are post processing
            EXISTS_SAME if the file exists and is the same size as the file we are post processing
        """
        if not existing_file:
            self._log(u"There is no existing file so there's no worries about replacing it", logger.DEBUG)
            return PostProcessor.DOESNT_EXIST

        # if the new file exists, return the appropriate code depending on the size
        if os.path.isfile(existing_file):

            # see if it's bigger than our old file
            if os.path.getsize(existing_file) > os.path.getsize(self.file_path):
                self._log(u'File {0} is larger than {1}'.format(existing_file, self.file_path), logger.DEBUG)
                return PostProcessor.EXISTS_LARGER

            elif os.path.getsize(existing_file) == os.path.getsize(self.file_path):
                self._log(u'File {0} is same size as {1}'.format(existing_file, self.file_path), logger.DEBUG)
                return PostProcessor.EXISTS_SAME

            else:
                self._log(u'File {0} is smaller than {1}'.format(existing_file, self.file_path), logger.DEBUG)
                return PostProcessor.EXISTS_SMALLER

        else:
            self._log(u"File {0} doesn't exist so there's no worries about replacing it".format
                      (existing_file), logger.DEBUG)
            return PostProcessor.DOESNT_EXIST

    @staticmethod
    def _search_files(path, pattern='*', subfolders=None, base_name_only=None, sort=False):
        """
        Search for files in a given path.

        :param path: path to file or folder (folder paths must end with slashes)
        :type path: text_type
        :param pattern: pattern used to match the files
        :type pattern: text_type
        :param subfolders: search for files in subfolders
        :type subfolders: bool
        :param base_name_only: only match files with the same name
        :type base_name_only: bool
        :param sort: return files sorted by size
        :type sort: bool
        :return: list with found files or empty list
        :rtype: list
        """
        directory = os.path.dirname(path)

        if base_name_only:
            if os.path.isfile(path):
                new_pattern = os.path.basename(path).rpartition('.')[0]
            elif os.path.isdir(path):
                new_pattern = os.path.split(directory)[1]
            else:
                return []

            if any(char in new_pattern for char in ['[', '?', '*']):
                # Escaping is done by wrapping any of "*?[" between square brackets.
                # Modified from: https://hg.python.org/cpython/file/tip/Lib/glob.py#l161
                if isinstance(new_pattern, bytes):
                    new_pattern = re.compile(b'([*?[])').sub(br'[\1]', new_pattern)
                else:
                    new_pattern = re.compile('([*?[])').sub(r'[\1]', new_pattern)

            pattern = new_pattern + pattern

        found_files = []
        for root, __, filenames in os.walk(directory):
            for filename in fnmatch.filter(filenames, pattern):
                found_files.append(os.path.join(root, filename))
            if not subfolders:
                break

        if sort:
            found_files = sorted(found_files, key=os.path.getsize, reverse=True)

        return found_files

    def list_associated_files(self, file_path, base_name_only=False, subtitles_only=False, subfolders=False):
        """
        For a given file path search for files in the same directory and return their absolute paths.

        :param file_path: The file to check for associated files
        :param base_name_only: False add extra '.' (conservative search) to file_path minus extension
        :param subtitles_only: list only subtitles
        :param subfolders: check subfolders while listing files
        :return: A list containing all files which are associated to the given file
        """
        # file path to the video file that is being processed (without extension)
        processed_file_name = os.path.basename(file_path).rpartition('.')[0].lower()

        file_list = self._search_files(file_path, subfolders=subfolders, base_name_only=base_name_only)

        # loop through all the files in the folder, and check if they are the same name
        # even when the cases don't match
        filelist = []
        for found_file in file_list:

            file_name = os.path.basename(found_file).lower()

            if file_name.startswith(processed_file_name):

                # only add subtitles with valid languages to the list
                if is_subtitle(found_file):
                    code = file_name.rsplit('.', 2)[1].replace('_', '-')
                    language = from_code(code, unknown='') or from_ietf_code(code, unknown='und')
                    if not language:
                        continue

                filelist.append(found_file)

        file_path_list = []
        extensions_to_delete = []
        for associated_file_path in filelist:
            # Exclude the video file we are post-processing
            if associated_file_path == file_path:
                continue

            # Exlude non-subtitle files with the 'only subtitles' option
            if subtitles_only and not is_subtitle(associated_file_path):
                continue

            # Exclude .rar files from associated list
            if re.search(r'(^.+\.(rar|r\d+)$)', associated_file_path):
                continue

            # Add the extensions that the user doesn't allow to the 'extensions_to_delete' list
            if app.MOVE_ASSOCIATED_FILES:
                allowed_extensions = app.ALLOWED_EXTENSIONS.split(',')
                found_extension = associated_file_path.rpartition('.')[2]
                if found_extension and found_extension not in allowed_extensions:
                    self._log(u'Associated file extension not found in allowed extensions: .{0}'.format
                              (found_extension.upper()), logger.DEBUG)
                    if os.path.isfile(associated_file_path):
                        extensions_to_delete.append(associated_file_path)

            if os.path.isfile(associated_file_path):
                file_path_list.append(associated_file_path)

        if file_path_list:
            self._log(u'Found the following associated files for {0}: {1}'.format
                      (file_path, file_path_list), logger.DEBUG)
            if extensions_to_delete:
                # Rebuild the 'file_path_list' list only with the extensions the user allows
                file_path_list = [associated_file for associated_file in file_path_list
                                  if associated_file not in extensions_to_delete]
                self._delete(extensions_to_delete)
        else:
            self._log(u'No associated files for {0} were found during this pass'.format(file_path), logger.DEBUG)

        return file_path_list

    def _delete(self, file_path, associated_files=False):
        """
        Delete the file and optionally all associated files.

        :param file_path: The file to delete
        :param associated_files: True to delete all files which differ only by extension, False to leave them
        """
        if not file_path:
            return

        # Check if file_path is a list, if not, make it one
        if not isinstance(file_path, list):
            file_list = [file_path]
        else:
            file_list = file_path

        # figure out which files we want to delete
        if associated_files:
            file_list += self.list_associated_files(file_path, base_name_only=True, subfolders=True)

        if not file_list:
            self._log(u'There were no files associated with {0}, not deleting anything'.format
                      (file_path), logger.DEBUG)
            return

        # delete the file and any other files which we want to delete
        for cur_file in file_list:
            if os.path.isfile(cur_file):
                self._log(u'Deleting file {0}'.format(cur_file), logger.DEBUG)
                # check first the read-only attribute
                file_attribute = os.stat(cur_file)[0]
                if not file_attribute & stat.S_IWRITE:
                    # File is read-only, so make it writeable
                    self._log(u'Read only mode on file {0}. Will try to make it writeable'.format
                              (cur_file), logger.DEBUG)
                    try:
                        os.chmod(cur_file, stat.S_IWRITE)
                    except Exception:
                        self._log(u'Cannot change permissions of {0}'.format(cur_file), logger.WARNING)

                os.remove(cur_file)

                # do the library update for synoindex
                notifiers.synoindex_notifier.deleteFile(cur_file)

    def _combined_file_operation(self, file_path, new_path, new_base_name, associated_files=False,
                                 action=None, subtitles=False):
        """
        Perform a generic operation (move or copy) on a file.

        Can rename the file as well as change its location, and optionally move associated files too.

        :param file_path: The full path of the media file to act on
        :param new_path: Destination path where we want to move/copy the file to
        :param new_base_name: The base filename (no extension) to use during the copy. Use None to keep the same name.
        :param associated_files: Boolean, whether we should copy similarly-named files too
        :param action: function that takes an old path and new path and does an operation with them (move/copy)
        :param subtitles: Boolean, whether we should process subtitles too
        """
        if not action:
            self._log(u'Must provide an action for the combined file operation', logger.ERROR)
            return

        file_list = [file_path]
        if associated_files:
            file_list += self.list_associated_files(file_path)
        elif subtitles:
            file_list += self.list_associated_files(file_path, subtitles_only=True)

        if not file_list:
            self._log(u'There were no files associated with {0}, not moving anything'.format
                      (file_path), logger.DEBUG)
            return

        # base name with file path (without extension and ending dot)
        old_base_name = file_path.rpartition('.')[0]
        old_base_name_length = len(old_base_name)

        for cur_file_path in file_list:
            # remember if the extension changed
            changed_extension = None
            # file extension without leading dot (for example: de.srt)
            extension = cur_file_path[old_base_name_length + 1:]
            # initally set current extension as new extension
            new_extension = extension

            # split the extension in two parts. E.g.: ('de', '.srt')
            split_extension = os.path.splitext(extension)
            # check if it's a subtitle and also has a subtitle language
            if is_subtitle(cur_file_path) and all(split_extension):
                sub_lang = split_extension[0].lower()
                if sub_lang == 'pt-br':
                    sub_lang = 'pt-BR'
                new_extension = sub_lang + split_extension[1]
                changed_extension = True

            # replace nfo with nfo-orig to avoid conflicts
            if extension == 'nfo' and app.NFO_RENAME:
                new_extension = 'nfo-orig'
                changed_extension = True

            # rename file with new base name
            if new_base_name:
                new_file_name = new_base_name + '.' + new_extension
            else:
                # current file name including extension
                new_file_name = os.path.basename(cur_file_path)
                # if we're not renaming we still need to change the extension sometimes
                if changed_extension:
                    new_file_name = new_file_name.replace(extension, new_extension)

            if app.SUBTITLES_DIR and is_subtitle(cur_file_path):
                subs_new_path = os.path.join(new_path, app.SUBTITLES_DIR)
                dir_exists = helpers.make_dir(subs_new_path)
                if not dir_exists:
                    logger.log(u'Unable to create subtitles folder {0}'.format(subs_new_path), logger.ERROR)
                else:
                    helpers.chmod_as_parent(subs_new_path)
                new_file_path = os.path.join(subs_new_path, new_file_name)
            else:
                new_file_path = os.path.join(new_path, new_file_name)

            action(cur_file_path, new_file_path)

    def _move(self, file_path, new_path, new_base_name, associated_files=False, subtitles=False):
        """
        Move file and set proper permissions.

        :param file_path: The full path of the media file to move
        :param new_path: Destination path where we want to move the file to
        :param new_base_name: The base filename (no extension) to use during the move. Use None to keep the same name.
        :param associated_files: Boolean, whether we should move similarly-named files too
        """
        def _int_move(cur_file_path, new_file_path):

            self._log(u'Moving file from {0} to {1} '.format(cur_file_path, new_file_path), logger.DEBUG)
            try:
                helpers.move_file(cur_file_path, new_file_path)
                helpers.chmod_as_parent(new_file_path)
            except (IOError, OSError) as e:
                self._log(u'Unable to move file {0} to {1}: {2!r}'.format
                          (cur_file_path, new_file_path, e), logger.ERROR)
                raise

        self._combined_file_operation(file_path, new_path, new_base_name, associated_files, action=_int_move,
                                      subtitles=subtitles)

    def _copy(self, file_path, new_path, new_base_name, associated_files=False, subtitles=False):
        """
        Copy file and set proper permissions.

        :param file_path: The full path of the media file to copy
        :param new_path: Destination path where we want to copy the file to
        :param new_base_name: The base filename (no extension) to use during the copy. Use None to keep the same name.
        :param associated_files: Boolean, whether we should copy similarly-named files too
        """
        def _int_copy(cur_file_path, new_file_path):

            self._log(u'Copying file from {0} to {1}'.format(cur_file_path, new_file_path), logger.DEBUG)
            try:
                helpers.copy_file(cur_file_path, new_file_path)
                helpers.chmod_as_parent(new_file_path)
            except (IOError, OSError) as e:
                self._log(u'Unable to copy file {0} to {1}: {2!r}'.format
                          (cur_file_path, new_file_path, e), logger.ERROR)
                raise

        self._combined_file_operation(file_path, new_path, new_base_name, associated_files, action=_int_copy,
                                      subtitles=subtitles)

    def _hardlink(self, file_path, new_path, new_base_name, associated_files=False, subtitles=False):
        """
        Hardlink file and set proper permissions.

        :param file_path: The full path of the media file to move
        :param new_path: Destination path where we want to create a hard linked file
        :param new_base_name: The base filename (no extension) to use during the link. Use None to keep the same name.
        :param associated_files: Boolean, whether we should move similarly-named files too
        """
        def _int_hard_link(cur_file_path, new_file_path):

            self._log(u'Hard linking file from {0} to {1}'.format(cur_file_path, new_file_path), logger.DEBUG)
            try:
                helpers.hardlink_file(cur_file_path, new_file_path)
                helpers.chmod_as_parent(new_file_path)
            except (IOError, OSError) as e:
                self._log(u'Unable to link file {0} to {1}: {2!r}'.format
                          (cur_file_path, new_file_path, e), logger.ERROR)
                raise

        self._combined_file_operation(file_path, new_path, new_base_name, associated_files,
                                      action=_int_hard_link, subtitles=subtitles)

    def _move_and_symlink(self, file_path, new_path, new_base_name, associated_files=False, subtitles=False):
        """
        Move file, symlink source location back to destination, and set proper permissions.

        :param file_path: The full path of the media file to move
        :param new_path: Destination path where we want to move the file to create a symbolic link to
        :param new_base_name: The base filename (no extension) to use during the link. Use None to keep the same name.
        :param associated_files: Boolean, whether we should move similarly-named files too
        """
        def _int_move_and_sym_link(cur_file_path, new_file_path):

            self._log(u'Moving then symbolic linking file from {0} to {1}'.format
                      (cur_file_path, new_file_path), logger.DEBUG)
            try:
                helpers.move_and_symlink_file(cur_file_path, new_file_path)
                helpers.chmod_as_parent(new_file_path)
            except (IOError, OSError) as e:
                self._log(u'Unable to link file {0} to {1}: {2!r}'.format
                          (cur_file_path, new_file_path, e), logger.ERROR)
                raise

        self._combined_file_operation(file_path, new_path, new_base_name, associated_files,
                                      action=_int_move_and_sym_link, subtitles=subtitles)

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
        if helpers.set_up_anidb_connection():
            if not self.anidbEpisode:  # seems like we could parse the name before, now lets build the anidb object
                self.anidbEpisode = self._build_anidb_episode(app.ADBA_CONNECTION, file_path)

            self._log(u'Adding the file to the anidb mylist', logger.DEBUG)
            try:
                self.anidbEpisode.add_to_mylist(status=1)  # status = 1 sets the status of the file to "internal HDD"
            except Exception as e:
                self._log(u'Exception message: {0!r}'.format(e))

    def _find_info(self):
        """
        For a given file try to find the show, season, epsiodes, version and quality.

        :return: A (show, season, episodes, version, quality) tuple
        """
        show = season = version = airdate = quality = None
        episodes = []
        name_list = [self.nzb_name, self.file_name, self.rel_path]

        for counter, name in enumerate(name_list):

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
                self._log(u'Looks like this is an air-by-date or sports show, '
                          u'attempting to convert the date to season and episode', logger.DEBUG)

                try:
                    airdate = episodes[0].toordinal()
                except AttributeError:
                    self._log(u"Couldn't convert to a valid airdate: {0}".format(episodes[0]), logger.DEBUG)
                    continue

            if counter < (len(name_list) - 1):
                if common.Quality.qualityStrings[cur_quality] == 'Unknown':
                    continue
            quality = cur_quality

            # We have all the information we need
            break

        if airdate and show:
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
                [show.indexerid, show.indexer, airdate])

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
                    [show.indexerid, show.indexer, airdate])

                if sql_result:
                    season = int(sql_result[0]['season'])
                    episodes = [int(sql_result[0]['episode'])]
                else:
                    self._log(u'Unable to find episode with date {0} for show {1}, skipping'.format
                              (episodes[0], show.indexerid), logger.DEBUG)
                    # we don't want to leave dates in the episode list
                    # if we couldn't convert them to real episode numbers
                    episodes = []

        # If there's no season, we assume it's the first season
        elif season is None and show:
            main_db_con = db.DBConnection()
            numseasons_result = main_db_con.select(
                'SELECT COUNT(DISTINCT season) '
                'FROM tv_episodes '
                'WHERE showid = ? '
                'AND indexer = ? '
                'AND season != 0',
                [show.indexerid, show.indexer])

            if int(numseasons_result[0][0]) == 1:
                self._log(u"Episode doesn't have a season number, but this show appears "
                          u"to have only 1 season, setting season number to 1...", logger.DEBUG)
                season = 1

        return show, season, episodes, quality, version

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
            self._log(u'{0}'.format(error), logger.DEBUG)
            return to_return

        if parse_result.show and all([parse_result.show.air_by_date, parse_result.is_air_by_date]):
            season = -1
            episodes = [parse_result.air_date]
        else:
            season = parse_result.season_number
            episodes = parse_result.episode_numbers

        to_return = (parse_result.show, season, episodes, parse_result.quality, parse_result.version)

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

    def _get_ep_obj(self, show, season, episodes):
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
            self._log(u'Retrieving episode object for {0} {1}'.format
                      (show.name, episode_num(season, cur_episode)), logger.DEBUG)

            # now that we've figured out which episode this file is just load it manually
            try:
                cur_ep = show.get_episode(season, cur_episode)
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

    def _get_quality(self, ep_obj):
        """
        Determine the quality of the file that is being post processed.

        First by checking if it is directly available in the Episode's status or
        otherwise by parsing through the data available.

        :param ep_obj: The Episode object related to the file we are post processing
        :return: A quality value found in common.Quality
        """
        ep_quality = common.Quality.UNKNOWN

        # Try getting quality from the episode (snatched) status first
        if ep_obj.status in common.Quality.SNATCHED + common.Quality.SNATCHED_PROPER + common.Quality.SNATCHED_BEST:
            _, ep_quality = common.Quality.split_composite_status(ep_obj.status)
            if ep_quality != common.Quality.UNKNOWN:
                self._log(u'The snatched status has a quality in it, using that: {0}'.format
                          (common.Quality.qualityStrings[ep_quality]), logger.DEBUG)
                return ep_quality

        # NZB name is the most reliable if it exists, followed by file name and lastly folder name
        name_list = [self.nzb_name, self.file_name, self.rel_path]

        for cur_name in name_list:

            # Skip names that are falsey
            if not cur_name:
                continue

            ep_quality = common.Quality.name_quality(cur_name, ep_obj.show.is_anime, extend=False)
            self._log(u"Looking up quality for '{0}', got {1}".format
                      (cur_name, common.Quality.qualityStrings[ep_quality]), logger.DEBUG)
            if ep_quality != common.Quality.UNKNOWN:
                self._log(u"Looks like '{0}' has quality {1}, using that".format
                          (cur_name, common.Quality.qualityStrings[ep_quality]), logger.DEBUG)
                return ep_quality

        # Try using other methods to get the file quality
        ep_quality = common.Quality.name_quality(self.file_path, ep_obj.show.is_anime)
        self._log(u"Trying other methods to get quality for '{0}', got {1}".format
                  (self.file_name, common.Quality.qualityStrings[ep_quality]), logger.DEBUG)
        if ep_quality != common.Quality.UNKNOWN:
            self._log(u"Looks like '{0}' has quality {1}, using that".format
                      (self.file_name, common.Quality.qualityStrings[ep_quality]), logger.DEBUG)
            return ep_quality

        return ep_quality

    def _priority_from_history(self, show_id, season, episodes, quality):
        """Evaluate if the file should be marked as priority."""
        main_db_con = db.DBConnection()
        for episode in episodes:
            # First: check if the episode status is snatched
            tv_episodes_result = main_db_con.select(
                'SELECT status '
                'FROM tv_episodes '
                'WHERE showid = ? '
                'AND season = ? '
                'AND episode = ? '
                "AND (status LIKE '%02' "
                "OR status LIKE '%09' "
                "OR status LIKE '%12')",
                [show_id, season, episode])

            if tv_episodes_result:
                # Second: get the quality of the last snatched epsiode
                # and compare it to the quality we are post-processing
                history_result = main_db_con.select(
                    'SELECT quality, manually_searched '
                    'FROM history '
                    'WHERE showid = ? '
                    'AND season = ? '
                    'AND episode = ? '
                    "AND (action LIKE '%02' "
                    "OR action LIKE '%09' "
                    "OR action LIKE '%12') "
                    'ORDER BY date DESC',
                    [show_id, season, episode])

                if history_result and history_result[0]['quality'] == quality:
                    # Third: make sure the file we are post-processing hasn't been
                    # previously processed, as we wouldn't want it in that case

                    # Check if the last snatch was a manual snatch
                    if history_result[0]['manually_searched']:
                        self.manually_searched = True

                    download_result = main_db_con.select(
                        'SELECT resource '
                        'FROM history '
                        'WHERE showid = ? '
                        'AND season = ? '
                        'AND episode = ? '
                        'AND quality = ? '
                        "AND action LIKE '%04' "
                        'ORDER BY date DESC',
                        [show_id, season, episode, quality])

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
            self._log(u'Snatch in history: {0}'.format(self.in_history), level)
            self._log(u'Manually snatched: {0}'.format(self.manually_searched), level)
            self._log(u'Current quality: {0}'.format(common.Quality.qualityStrings[old_ep_quality]), level)
            self._log(u'New quality: {0}'.format(common.Quality.qualityStrings[new_ep_quality]), level)
            self._log(u'Proper: {0}'.format(self.is_proper), level)

            # If in_history is True it must be a priority download
            return bool(self.in_history or self.is_priority)

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
        if current_quality is common.Quality.NONE:
            return False, 'There is no current quality. Skipping as we can only replace existing qualities'
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
                return True, 'New quality is Allowed and we don\'t have a current Preferred. Accepting quality'
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

        file_path = self.file_path
        if isinstance(file_path, text_type):
            try:
                file_path = file_path.encode(app.SYS_ENCODING)
            except UnicodeEncodeError:
                # ignore it
                pass

        ep_location = ep_obj.location
        if isinstance(ep_location, text_type):
            try:
                ep_location = ep_location.encode(app.SYS_ENCODING)
            except UnicodeEncodeError:
                # ignore it
                pass

        for cur_script_name in app.EXTRA_SCRIPTS:
            if isinstance(cur_script_name, text_type):
                try:
                    cur_script_name = cur_script_name.encode(app.SYS_ENCODING)
                except UnicodeEncodeError:
                    # ignore it
                    pass

            # generate a safe command line string to execute the script and provide all the parameters
            script_cmd = [piece for piece in re.split(r'(\'.*?\'|".*?"| )', cur_script_name) if piece.strip()]
            script_cmd[0] = os.path.abspath(script_cmd[0])
            self._log(u'Absolute path to script: {0}'.format(script_cmd[0]), logger.DEBUG)

            script_cmd += [
                ep_location, file_path, str(ep_obj.show.indexerid),
                str(ep_obj.season), str(ep_obj.episode), str(ep_obj.airdate)
            ]

            # use subprocess to run the command and capture output
            self._log(u'Executing command: {0}'.format(script_cmd))
            try:
                p = subprocess.Popen(
                    script_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, cwd=app.PROG_DIR
                )
                out, _ = p.communicate()

                self._log(u'Script result: {0}'.format(out), logger.DEBUG)

            except Exception as e:
                self._log(u'Unable to run extra_script: {0!r}'.format(e))

    def flag_kodi_clean_library(self):
        """Set flag to clean Kodi's library if Kodi is enabled."""
        if app.USE_KODI:
            self._log(u'Setting to clean Kodi library as we are going to replace the file')
            app.KODI_LIBRARY_CLEAN_PENDING = True

    def process(self):
        """
        Post-process a given file.

        :return: True on success, False on failure
        """
        self._log(u'Processing {0}'.format(self.file_path))

        if os.path.isdir(self.file_path):
            self._log(u'File {0} seems to be a directory'.format(self.file_path))
            return False

        if not os.path.exists(self.file_path):
            raise EpisodePostProcessingFailedException(u"File {0} doesn't exist, did unrar fail?".format
                                                       (self.file_path))

        for ignore_file in self.IGNORED_FILESTRINGS:
            if ignore_file in self.file_path:
                self._log(u'File {0} is ignored type, skipping'.format(self.file_path))
                return False

        # reset in_history
        self.in_history = False

        # reset the anidb episode object
        self.anidbEpisode = None

        # try to find the file info
        (show, season, episodes, quality, version) = self._find_info()
        if not show:
            raise EpisodePostProcessingFailedException(u"This show isn't in your list, you need to add it "
                                                       u"before post-processing an episode")
        elif season is None or not episodes:
            raise EpisodePostProcessingFailedException(u'Not enough information to determine what episode this is')

        # retrieve/create the corresponding Episode objects
        ep_obj = self._get_ep_obj(show, season, episodes)
        old_ep_status, old_ep_quality = common.Quality.split_composite_status(ep_obj.status)

        # get the quality of the episode we're processing
        if quality and common.Quality.qualityStrings[quality] != 'Unknown':
            self._log(u'The episode file has a quality in it, using that: {0}'.format
                      (common.Quality.qualityStrings[quality]), logger.DEBUG)
            new_ep_quality = quality
        else:
            new_ep_quality = self._get_quality(ep_obj)

        logger.log(u'Quality of the episode we are processing: {0}'.format
                   (common.Quality.qualityStrings[new_ep_quality]), logger.DEBUG)

        # check snatched history to see if we should set the download as priority
        self._priority_from_history(show.indexerid, season, episodes, new_ep_quality)
        if self.in_history:
            self._log(u'This episode was found in history as SNATCHED.', logger.DEBUG)

        # see if this is a priority download (is it snatched, in history, PROPER, or BEST)
        priority_download = self._is_priority(old_ep_quality, new_ep_quality)
        self._log(u'This episode is a priority download: {0}'.format(priority_download), logger.DEBUG)

        # get the version of the episode we're processing (default is -1)
        if version != -1:
            self._log(u'Episode has a version in it, using that: v{0}'.format(version), logger.DEBUG)
        new_ep_version = version

        # check for an existing file
        existing_file_status = self._check_for_existing_file(ep_obj.location)

        if not priority_download:
            if existing_file_status == PostProcessor.EXISTS_SAME:
                self._log(u'File exists and the new file has the same size, aborting post-processing')
                return True

            if existing_file_status != PostProcessor.DOESNT_EXIST:
                if self.is_proper and new_ep_quality == old_ep_quality:
                    self._log(u'New file is a PROPER, marking it safe to replace')
                    self.flag_kodi_clean_library()
                else:
                    allowed_qualities, preferred_qualities = show.current_qualities
                    self._log(u'Checking if new quality {0} should replace current quality: {1}'.format
                              (common.Quality.qualityStrings[new_ep_quality],
                               common.Quality.qualityStrings[old_ep_quality]))
                    should_process, should_process_reason = self._should_process(old_ep_quality, new_ep_quality,
                                                                                 allowed_qualities, preferred_qualities)
                    if not should_process:
                        raise EpisodePostProcessingFailedException(
                            u'File exists. Marking it unsafe to replace. Reason: {0}'.format(should_process_reason))
                    else:
                        self._log(u'File exists. Marking it safe to replace. Reason: {0}'.format(should_process_reason))
                        self.flag_kodi_clean_library()

            # Check if the processed file season is already in our indexer. If not,
            # the file is most probably mislabled/fake and will be skipped.
            # Only proceed if the file season is > 0
            if int(ep_obj.season) > 0:
                main_db_con = db.DBConnection()
                max_season = main_db_con.select(
                    "SELECT MAX(season) FROM tv_episodes WHERE showid = ? and indexer = ?",
                    [show.indexerid, show.indexer])

                # If the file season (ep_obj.season) is bigger than
                # the indexer season (max_season[0][0]), skip the file
                if int(ep_obj.season) > int(max_season[0][0]):
                    self._log(u'File has season {0}, while the indexer is on season {1}. '
                              u'The file may be incorrectly labeled or fake, aborting.'.format
                              (ep_obj.season, max_season[0][0]))
                    return False

        # if the file is priority then we're going to replace it even if it exists
        else:
            # Set to clean Kodi if file exists and it is priority_download
            if existing_file_status != PostProcessor.DOESNT_EXIST:
                self.flag_kodi_clean_library()
            self._log(u"This download is marked a priority download so I'm going to replace "
                      u"an existing file if I find one")

        # try to find out if we have enough space to perform the copy or move action.
        if not helpers.is_file_locked(self.file_path, False):
            if not verify_freespace(self.file_path, ep_obj.show._location, [ep_obj] + ep_obj.related_episodes):
                self._log(u'Not enough space to continue post-processing, exiting', logger.WARNING)
                return False
        else:
            self._log(u'Unable to determine needed filespace as the source file is locked for access')

        # delete the existing file (and company)
        for cur_ep in [ep_obj] + ep_obj.related_episodes:
            try:
                self._delete(cur_ep.location, associated_files=True)
                # clean up any left over folders
                if cur_ep.location:
                    helpers.delete_empty_folders(os.path.dirname(cur_ep.location), keep_dir=ep_obj.show._location)
            except (OSError, IOError):
                raise EpisodePostProcessingFailedException(u'Unable to delete the existing files')

            # set the status of the episodes
            # for cur_ep in [ep_obj] + ep_obj.related_episodes:
            #    cur_ep.status = common.Quality.composite_status(common.SNATCHED, new_ep_quality)

        # if the show directory doesn't exist then make it if desired
        if not os.path.isdir(ep_obj.show._location) and app.CREATE_MISSING_SHOW_DIRS:
            self._log(u"Show directory doesn't exist, creating it", logger.DEBUG)
            try:
                os.mkdir(ep_obj.show._location)
                helpers.chmod_as_parent(ep_obj.show._location)

                # do the library update for synoindex
                notifiers.synoindex_notifier.addFolder(ep_obj.show._location)
            except (OSError, IOError):
                raise EpisodePostProcessingFailedException(u'Unable to create the show directory: {0}'.format
                                                           (ep_obj.show._location))

            # get metadata for the show (but not episode because it hasn't been fully processed)
            ep_obj.show.write_metadata(True)

        # update the ep info before we rename so the quality & release name go into the name properly
        sql_l = []

        for cur_ep in [ep_obj] + ep_obj.related_episodes:
            with cur_ep.lock:

                if self.release_name:
                    self._log(u'Found release name {0}'.format(self.release_name), logger.DEBUG)
                    cur_ep.release_name = self.release_name
                elif self.file_name:
                    # If we can't get the release name we expect, save the original release name instead
                    self._log(u'Using original release name {0}'.format(self.file_name), logger.DEBUG)
                    cur_ep.release_name = self.file_name
                else:
                    cur_ep.release_name = u''

                cur_ep.status = common.Quality.composite_status(common.DOWNLOADED, new_ep_quality)

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
        release_name = show_name_helpers.determineReleaseName(self.folder_path, self.nzb_name)
        if release_name is not None:
            failed_history.log_success(release_name)
        else:
            self._log(u"Couldn't determine release name, aborting", logger.WARNING)

        # find the destination folder
        try:
            proper_path = ep_obj.proper_path()
            proper_absolute_path = os.path.join(ep_obj.show.location, proper_path)
            dest_path = os.path.dirname(proper_absolute_path)
        except ShowDirectoryNotFoundException:
            raise EpisodePostProcessingFailedException(u"Unable to post-process an episode if the show dir '{0}' "
                                                       u"doesn't exist, quitting".format(ep_obj.show.raw_location))

        self._log(u'Destination folder for this episode: {0}'.format(dest_path), logger.DEBUG)

        # create any folders we need
        helpers.make_dirs(dest_path)

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
        if ep_obj.show.is_anime and app.ANIDB_USE_MYLIST:
            self._add_to_anidb_mylist(self.file_path)

        try:
            # move the episode and associated files to the show dir
            if self.process_method == 'copy':
                if helpers.is_file_locked(self.file_path, False):
                    raise EpisodePostProcessingFailedException('File is locked for reading')
                self._copy(self.file_path, dest_path, new_base_name, app.MOVE_ASSOCIATED_FILES,
                           app.USE_SUBTITLES and ep_obj.show.subtitles)
            elif self.process_method == 'move':
                if helpers.is_file_locked(self.file_path, True):
                    raise EpisodePostProcessingFailedException('File is locked for reading/writing')
                self._move(self.file_path, dest_path, new_base_name, app.MOVE_ASSOCIATED_FILES,
                           app.USE_SUBTITLES and ep_obj.show.subtitles)
            elif self.process_method == "hardlink":
                self._hardlink(self.file_path, dest_path, new_base_name, app.MOVE_ASSOCIATED_FILES,
                               app.USE_SUBTITLES and ep_obj.show.subtitles)
            elif self.process_method == "symlink":
                if helpers.is_file_locked(self.file_path, True):
                    raise EpisodePostProcessingFailedException('File is locked for reading/writing')
                self._move_and_symlink(self.file_path, dest_path, new_base_name, app.MOVE_ASSOCIATED_FILES,
                                       app.USE_SUBTITLES and ep_obj.show.subtitles)
            else:
                logger.log(u"'{0}' is an unknown file processing method. "
                           u"Please correct your app's usage of the API.".format(self.process_method), logger.WARNING)
                raise EpisodePostProcessingFailedException('Unable to move the files to their new home')
        except (OSError, IOError):
            raise EpisodePostProcessingFailedException('Unable to move the files to their new home')

        # download subtitles
        if app.USE_SUBTITLES and ep_obj.show.subtitles:
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

        # log it to history
        history.logDownload(ep_obj, self.file_path, new_ep_quality, self.release_group, new_ep_version)

        # If any notification fails, don't stop post_processor
        try:
            # send notifications
            notifiers.notify_download(ep_obj._format_pattern('%SN - %Sx%0E - %EN - %QN'))

            # do the library update for KODI
            notifiers.kodi_notifier.update_library(ep_obj.show.name)

            # do the library update for Plex
            notifiers.plex_notifier.update_library(ep_obj)

            # do the library update for EMBY
            notifiers.emby_notifier.update_library(ep_obj.show)

            # do the library update for NMJ
            # nmj_notifier kicks off its library update when the notify_download is issued (inside notifiers)

            # do the library update for Synology Indexer
            notifiers.synoindex_notifier.addFile(ep_obj.location)

            # do the library update for pyTivo
            notifiers.pytivo_notifier.update_library(ep_obj)

            # do the library update for Trakt
            notifiers.trakt_notifier.update_library(ep_obj)
        except Exception as e:
            logger.log(u'Some notifications could not be sent. Error: {0!r}. '
                       u'Continuing with post-processing...'.format(e))

        self._run_extra_scripts(ep_obj)

        return True
