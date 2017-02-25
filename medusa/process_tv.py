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

import os
import shutil
import stat

import shutil_custom

from unrar2 import RarFile
from unrar2.rar_exceptions import (ArchiveHeaderBroken, FileOpenError, IncorrectRARPassword, InvalidRARArchive,
                                   InvalidRARArchiveUsage)
from . import app, db, failed_processor, helpers, logger, notifiers, post_processor
from .helper.common import is_sync_file, is_torrent_or_nzb_file, subtitle_extensions
from .helper.encoding import ss
from .helper.exceptions import EpisodePostProcessingFailedException, FailedPostProcessingFailedException, ex
from .name_parser.parser import InvalidNameException, InvalidShowException, NameParser
from .subtitles import accept_any, accept_unknown, get_embedded_subtitles

shutil.copyfile = shutil_custom.copyfile_custom


class ProcessResult(object):

    def __init__(self):
        self.result = True
        self.output = u''
        self.missedfiles = []
        self.succeeded = True

        self.video_files = []
        self.rar_content = []
        self.video_in_rar = []
        self.not_wanted_files = []

    def _log(self, message, level=logger.INFO):
        logger.log(message, level)
        self.output += message + u'\n'

    def process_dir(self, dir_name, nzb_name=None, process_method=None, force=False, is_priority=None,
                    delete_on=False, failed=False, proc_type=u'auto', ignore_subs=False):
        """
        Scan through the files in dir_name and process whatever media files are found.

        :param dir_name: The folder name to look in
        :param nzb_name: The NZB name which resulted in this folder being downloaded
        :param process_method: Process methodo: hardlink, move, softlink, etc.
        :param force: True to postprocess already postprocessed files
        :param is_priority: Boolean for whether or not is a priority download
        :param delete_on: Boolean for whether or not it should delete files
        :param failed: Boolean for whether or not the download failed
        :param proc_type: Type of postprocessing auto or manual
        :param ignore_subs: True to ignore setting 'postpone if no subs'
        """
        pp_dir = self._get_pp_dir(dir_name)
        if not pp_dir:
            return self.output

        path, dirs, files = self.get_path_dir_files(pp_dir, nzb_name, proc_type)

        files = [x for x in files if not is_torrent_or_nzb_file(x)]
        sync_files = [x for x in files if is_sync_file(x)]
        original_nzb_name = nzb_name

        # Don't post process if files are still being synced and option is activated
        postpone = sync_files and app.POSTPONE_IF_SYNC_FILES

        # Warn user if 'postpone if no subs' is enabled. Will debug possible user issues with PP
        if app.POSTPONE_IF_NO_SUBS:
            self._log(u"Feature 'postpone post-processing if no subtitle available' is enabled")

        if not postpone:
            self._log(u'PostProcessing Path: {0}'.format(path))
            self._log(u'PostProcessing Dirs: {0}'.format(dirs), logger.DEBUG)

            self.prepare_files(path, files, force)

            # If nzb_name is set and there is more than one videofile in the folder, files will be lost (overwritten).
            nzb_name = None if len(self.video_files) >= 2 else nzb_name

            process_method = process_method if process_method else app.PROCESS_METHOD

            self.result = True

            self.process_files(path, process_method, nzb_name=nzb_name, is_priority=is_priority,
                               ignore_subs=ignore_subs, force=force)

        else:
            self._log(u'Found temporary sync files: {0} in path: {1}'.format(sync_files, path))
            self._log(u'Skipping post processing for folder: {0}'.format(path))
            self.missedfiles.append(u'{0}: Sync files found'.format(path))

        # Process Video File in all TV Subdir
        for curDir in [x for x in dirs if self.validateDir(path, x, original_nzb_name, failed)]:
            self.result = True

            for processPath, _, file_list in os.walk(os.path.join(path, curDir), topdown=False):

                if not self.validateDir(path, processPath, original_nzb_name, failed):
                    continue

                sync_files = [x for x in file_list if is_sync_file(x)]

                # Don't post process if files are still being synced and option is activated
                postpone = sync_files and app.POSTPONE_IF_SYNC_FILES

                if not postpone:

                    self.prepare_files(processPath, file_list, force)

                    self.process_files(processPath, process_method, nzb_name=nzb_name, force=force,
                                       is_priority=is_priority, ignore_subs=ignore_subs)

                    # Delete all files not needed and avoid deleting files if Manual PostProcessing
                    if not (process_method == u'move' and self.result) or (proc_type == u'manual' and not delete_on):
                        continue

                    self.delete_folder(os.path.join(path, u'@eaDir'))
                    self.delete_files(path, self.not_wanted_files)

                    if all([not app.NO_DELETE or proc_type == u'manual', process_method == u'move',
                            os.path.normpath(path) != os.path.normpath(app.TV_DOWNLOAD_DIR)]):

                        if self.delete_folder(path, check_empty=True):
                            self._log(u'Deleted folder: {0}'.format(path), logger.DEBUG)

                else:
                    self._log(u'Found temporary sync files: {0} in path: {1}'.format(sync_files, processPath))
                    self._log(u'Skipping post processing for folder: {0}'.format(processPath))
                    self.missedfiles.append(u'{0}: Sync files found'.format(path))

        if self.succeeded:
            self._log(u'Successfully processed')

            # Clean library from KODI after PP ended
            if app.KODI_LIBRARY_CLEAN_PENDING and notifiers.kodi_notifier.clean_library():
                app.KODI_LIBRARY_CLEAN_PENDING = False

            if self.missedfiles:
                self._log(u'I did encounter some unprocessable items: ')
                for missedfile in self.missedfiles:
                    self._log(u'[{0}]'.format(missedfile))
        else:
            self._log(u'Problem(s) during processing, failed for the following files/folders: ', logger.WARNING)
            for missedfile in self.missedfiles:
                self._log(u'[{0}]'.format(missedfile), logger.WARNING)

        return self.output

    def _get_pp_dir(self, dir_name):

        # if they passed us a real dir then assume it's the one we want
        if os.path.isdir(dir_name):
            pp_dir = os.path.realpath(dir_name)
            self._log(u'Processing folder: {0}'.format(pp_dir), logger.DEBUG)
            return pp_dir

        # if the client and the application are not on the same machine,
        # translate the directory into a network directory
        elif all([app.TV_DOWNLOAD_DIR, os.path.isdir(app.TV_DOWNLOAD_DIR),
                  os.path.normpath(dir_name) == os.path.normpath(app.TV_DOWNLOAD_DIR)]):
            pp_dir = os.path.join(app.TV_DOWNLOAD_DIR, os.path.abspath(dir_name).split(os.path.sep)[-1])
            self._log(u'Trying to use folder: {0}'.format(pp_dir), logger.DEBUG)
            return pp_dir

        # if we didn't find a real dir then quit
        if not os.path.isdir(dir_name):
            self._log(u"Unable to figure out what folder to process. If your downloader and Medusa aren't on "
                      u"the same PC, make sure you fill out your TV download dir in the config.", logger.DEBUG)

    def prepare_files(self, path, files, force=False):
        allowed_extensions = app.ALLOWED_EXTENSIONS.split(',')
        video_files = [x for x in files if helpers.is_media_file(x)]
        rar_files = [x for x in files if helpers.is_rar_file(x)]
        rar_content = []

        if rar_files:
            # Unpack only if video file was not already extracted by 'postpone if no subs' feature
            rar_content = self.unRAR(path, rar_files, force)
            files += rar_content
            video_files += [x for x in rar_content if helpers.is_media_file(x)]

        video_in_rar = [x for x in rar_content if helpers.is_media_file(x)]
        not_wanted_files = [x for x in files if x not in video_files and helpers.get_extension(x)
                            not in allowed_extensions]

        self._log(u'\n')
        self._log(u'PostProcessing Files: {0}'.format(files), logger.DEBUG)
        self._log(u'PostProcessing VideoFiles: {0}'.format(video_files), logger.DEBUG)
        self._log(u'PostProcessing RarContent: {0}'.format(rar_content), logger.DEBUG)
        self._log(u'PostProcessing VideoInRar: {0}'.format(video_in_rar), logger.DEBUG)

        if not_wanted_files:
            self._log(u'Found unwanted files: {0}'.format(not_wanted_files), logger.DEBUG)

        self.video_files = video_files
        self.rar_content = rar_content
        self.video_in_rar = video_in_rar
        self.not_wanted_files = not_wanted_files

    def process_files(self, path, process_method, **kwargs):

        nzb_name = kwargs.get('nzb_name')
        force = kwargs.get('force')
        is_priority = kwargs.get('is_priority')
        ignore_subs = kwargs.get('ignore_subs')

        # Don't Link media when the media is extracted from a rar in the same path
        if process_method in (u'hardlink', u'symlink') and self.video_in_rar:
            self.process_media(path, self.video_in_rar, nzb_name, u'move', force, is_priority, ignore_subs)

            self.process_media(path, set(self.video_files) - set(self.video_in_rar), nzb_name, process_method,
                               force, is_priority, ignore_subs)

            self.delete_files(path, self.rar_content)

        elif app.DELRARCONTENTS and self.video_in_rar:
            self.process_media(path, self.video_in_rar, nzb_name, process_method, force, is_priority, ignore_subs)

            self.process_media(path, set(self.video_files) - set(self.video_in_rar), nzb_name, process_method,
                               force, is_priority, ignore_subs)

            self.delete_files(path, self.rar_content, force=True)

        else:
            self.process_media(path, self.video_files, nzb_name, process_method, force, is_priority, ignore_subs)

    @staticmethod
    def delete_folder(folder, check_empty=True):
        """
        Remove a folder from the filesystem.

        :param folder: Path to folder to remove
        :param check_empty: Boolean, check if the folder is empty before removing it, defaults to True
        :return: True on success, False on failure
        """
        # check if it's a folder
        if not os.path.isdir(folder):
            return False

        # check if it isn't TV_DOWNLOAD_DIR
        if app.TV_DOWNLOAD_DIR:
            if helpers.real_path(folder) == helpers.real_path(app.TV_DOWNLOAD_DIR):
                return False

        # check if it's empty folder when wanted checked
        if check_empty:
            check_files = os.listdir(folder)
            if check_files:
                logger.log(u'Not deleting folder {0} found the following files: {1}'.format
                           (folder, check_files), logger.INFO)
                return False

            try:
                logger.log(u"Deleting folder (if it's empty): {0}".format(folder))
                os.rmdir(folder)
            except (OSError, IOError) as e:
                logger.log(u'Unable to delete folder: {0}: {1}'.format(folder, ex(e)), logger.WARNING)
                return False
        else:
            try:
                logger.log(u'Deleting folder: {0}'.format(folder))
                shutil.rmtree(folder)
            except (OSError, IOError) as e:
                logger.log(u'Unable to delete folder: {0}: {1}'.format(folder, ex(e)), logger.WARNING)
                return False

        return True

    def delete_files(self, processPath, notwantedFiles, force=False):
        """
        Remove files from filesystem.

        :param processPath: path to process
        :param notwantedFiles: files we do not want
        :param result: Processor results
        :param force: Boolean, force deletion, defaults to false
        """
        if not notwantedFiles:
            return

        if not self.result and force:
            self._log(u'Forcing deletion of files, even though last result was not successful', logger.DEBUG)
        elif not self.result:
            return

        # Delete all file not needed
        for cur_file in notwantedFiles:

            cur_file_path = os.path.join(processPath, cur_file)

            if not os.path.isfile(cur_file_path):
                continue  # Prevent error when a notwantedfiles is an associated files

            self._log(u'Deleting file: {0}'.format(cur_file), logger.DEBUG)

            # check first the read-only attribute
            file_attribute = os.stat(cur_file_path)[0]
            if not file_attribute & stat.S_IWRITE:
                # File is read-only, so make it writeable
                self._log(u'Changing ReadOnly Flag for file: {0}'.format(cur_file), logger.DEBUG)
                try:
                    os.chmod(cur_file_path, stat.S_IWRITE)
                except OSError as e:
                    self._log(u'Cannot change permissions of {0}: {1}'.format(cur_file_path, ex(e)), logger.DEBUG)
            try:
                os.remove(cur_file_path)
            except OSError as e:
                self._log(u'Unable to delete file {0}: {1}'.format(cur_file, e.strerror), logger.DEBUG)

    def validateDir(self, path, dirName, nzbNameOriginal, failed):
        """
        Check if directory is valid for processing.

        :param path: Path to use
        :param dirName: Directory to check
        :param nzbNameOriginal: Original NZB name
        :param failed: Previously failed objects
        :param result: Previous results
        :return: True if dir is valid for processing, False if not
        """
        ignored_folders = [u'.AppleDouble', u'.@__thumb', u'@eaDir']
        folder_name = os.path.basename(dirName)
        if folder_name in ignored_folders:
            return False

        self._log(u'Processing folder {0}'.format(dirName), logger.DEBUG)

        if folder_name.startswith(u'_FAILED_'):
            self._log(u'The directory name indicates it failed to extract.', logger.DEBUG)
            failed = True
        elif folder_name.startswith(u'_UNDERSIZED_'):
            self._log(u'The directory name indicates that it was previously rejected for being undersized.',
                      logger.DEBUG)
            failed = True
        elif folder_name.upper().startswith(u'_UNPACK'):
            self._log(u'The directory name indicates that this release is in the process of being unpacked.',
                      logger.DEBUG)
            self.missedfiles.append(u'{0}: Being unpacked'.format(dirName))
            return False

        if failed:
            self.process_failed(os.path.join(path, dirName), nzbNameOriginal)
            self.missedfiles.append(u'{0}: Failed download'.format(dirName))
            return False

        if helpers.is_hidden_folder(os.path.join(path, dirName)):
            self._log(u'Ignoring hidden folder: {0}'.format(dirName), logger.DEBUG)
            self.missedfiles.append(u'{0}: Hidden folder'.format(dirName))
            return False

        for __, __, files in os.walk(os.path.join(path, dirName), topdown=False):
            for f in files:
                if helpers.is_media_file(f):
                    return True

        self._log(u'{0}: No processable items found in the folder'.format(dirName), logger.DEBUG)
        return False

    def unRAR(self, path, rarFiles, force):
        """
        Extract RAR files.

        :param path: Path to look for files in
        :param rarFiles: Names of RAR files
        :param force: process currently processing items
        :param result: Previous results
        :return: List of unpacked file names
        """
        unpacked_files = []

        if app.UNPACK and rarFiles:

            self._log(u"Packed releases detected: %s" % rarFiles, logger.DEBUG)

            for archive in rarFiles:

                self._log(u"Unpacking archive: %s" % archive, logger.DEBUG)

                failure = None
                try:
                    rar_handle = RarFile(os.path.join(path, archive))

                    # Skip extraction if any file in archive has previously been extracted
                    skip_file = False
                    for file_in_archive in [os.path.basename(x.filename) for x in rar_handle.infolist() if not x.isdir]:
                        if self.already_postprocessed(path, file_in_archive, force):
                            self._log(u'Archive file already post-processed, extraction skipped: %s' %
                                      file_in_archive, logger.DEBUG)
                            skip_file = True
                            break

                        if app.POSTPONE_IF_NO_SUBS and os.path.isfile(os.path.join(path, file_in_archive)):
                            self._log(u'Archive file already extracted, extraction skipped: %s' %
                                      file_in_archive, logger.DEBUG)

                            skip_file = True
                            # We need to return the media file inside the .RAR so we can move
                            # when method is hardlink/symlink
                            unpacked_files.append(file_in_archive)
                            break

                    if skip_file:
                        continue

                    rar_handle.extract(path=path, withSubpath=False, overwrite=False)
                    for x in rar_handle.infolist():
                        if not x.isdir:
                            basename = os.path.basename(x.filename)
                            if basename not in unpacked_files:
                                unpacked_files.append(basename)
                    del rar_handle

                except ArchiveHeaderBroken:
                    failure = (u'Archive Header Broken', u'Unpacking failed because the Archive Header is Broken')
                except IncorrectRARPassword:
                    failure = (u'Incorrect RAR Password', u'Unpacking failed because of an Incorrect Rar Password')
                except FileOpenError:
                    failure = (u'File Open Error, check the parent folder and destination file permissions.',
                               u'Unpacking failed with a File Open Error (file permissions?)')
                except InvalidRARArchiveUsage:
                    failure = (u'Invalid Rar Archive Usage', u'Unpacking Failed with Invalid Rar Archive Usage')
                except InvalidRARArchive:
                    failure = (u'Invalid Rar Archive', u'Unpacking Failed with an Invalid Rar Archive Error')
                except Exception as e:
                    failure = (ex(e), u'Unpacking failed for an unknown reason')

                if failure is not None:
                    self._log(u'Failed Unrar archive {}: {}'.format(archive, failure[0]), logger.WARNING)
                    self.missedfiles.append(u'{} : Unpacking failed: {}'.format(archive, failure[1]))
                    self.result = False
                    continue

            self._log(u"UnRar content: %s" % unpacked_files, logger.DEBUG)

        return unpacked_files

    def already_postprocessed(self, dir_name, video_file, force):
        """
        Check if we already post processed a file.

        :param dir_name: Directory a file resides in
        :param video_file: File name
        :param force: Force checking when already checking (currently unused)
        :param result: True if file is already postprocessed, False if not
        :return:
        """
        if force:
            return False

        main_db_con = db.DBConnection()
        history_result = main_db_con.select(
            'SELECT * FROM history '
            "WHERE action LIKE '%04' "
            'AND resource LIKE ?',
            ['%' + video_file])

        if history_result:
            self._log(u"You're trying to post-process a file that has already "
                      u"been processed, skipping: {0}".format(video_file), logger.DEBUG)
            return True

        return False

    def process_media(self, processPath, videoFiles, nzbName, process_method, force, is_priority, ignore_subs):
        """
        Postprocess mediafiles.

        :param processPath: Path to postprocess in
        :param videoFiles: Filenames to look for and postprocess
        :param nzbName: Name of NZB file related
        :param process_method: auto/manual
        :param force: Postprocess currently postprocessing file
        :param is_priority: Boolean, is this a priority download
        :param result: Previous results
        :param ignore_subs: True to ignore setting 'postpone if no subs'
        """
        processor = None
        for cur_video_file in videoFiles:
            cur_video_file_path = os.path.join(processPath, cur_video_file)

            if self.already_postprocessed(processPath, cur_video_file, force):
                self._log(u"Skipping already processed file: %s" % cur_video_file, logger.DEBUG)
                self._log(u"Skipping already processed dir: %s" % processPath, logger.DEBUG)
                continue

            try:
                processor = post_processor.PostProcessor(cur_video_file_path, nzbName, process_method, is_priority)

                # This feature prevents PP for files that do not have subtitle associated with the video file
                if app.POSTPONE_IF_NO_SUBS:
                    if not ignore_subs:
                        if self.subtitles_enabled(cur_video_file_path, nzbName):
                            embedded_subs = set() if app.IGNORE_EMBEDDED_SUBS else get_embedded_subtitles(cur_video_file_path)

                            # If user don't want to ignore embedded subtitles and video has at least one, don't postpone PP
                            if accept_unknown(embedded_subs):
                                self._log(u"Found embedded unknown subtitles and we don't want to ignore them. "
                                          u"Continuing the post-process of this file: %s" % cur_video_file)
                            elif accept_any(embedded_subs):
                                self._log(u"Found wanted embedded subtitles. "
                                          u"Continuing the post-process of this file: %s" % cur_video_file)
                            else:
                                associated_files = processor.list_associated_files(cur_video_file_path, subtitles_only=True)
                                if not [f for f in associated_files if helpers.get_extension(f) in subtitle_extensions]:
                                    self._log(u"No subtitles associated. Postponing the post-process of this file:"
                                              u" %s" % cur_video_file, logger.DEBUG)
                                    continue
                                else:
                                    self._log(u"Found subtitles associated. "
                                              u"Continuing the post-process of this file: %s" % cur_video_file)
                        else:
                            self._log(u"Subtitles disabled for this show. "
                                      u"Continuing the post-process of this file: %s" % cur_video_file)
                    else:
                        self._log(u"Subtitles check was disabled for this episode in Manual PP. "
                                  u"Continuing the post-process of this file: %s" % cur_video_file)

                self.result = processor.process()
                process_fail_message = u''
            except EpisodePostProcessingFailedException as e:
                self.result = False
                process_fail_message = ex(e)

            if processor:
                self.output += processor.log

            if self.result:
                self._log(u'Processing succeeded for %s' % cur_video_file_path)
            else:
                self._log(u'Processing failed for %s: %s' % (cur_video_file_path, process_fail_message), logger.WARNING)
                self.missedfiles.append(u'%s : Processing failed: %s' % (cur_video_file_path, process_fail_message))
                self.succeeded = False

    @staticmethod
    def get_path_dir_files(dirName, nzbName, proc_type):
        """
        Get files in a path.

        :param dirName: Directory to start in
        :param nzbName: NZB file, if present
        :param proc_type: auto/manual
        :return: a tuple of (path,dirs,files)
        """
        path = u''
        dirs = []
        files = []

        if dirName == app.TV_DOWNLOAD_DIR and not nzbName or proc_type == u'manual':  # Scheduled Post Processing Active
            # Get at first all the subdir in the dirName
            for path, dirs, files in os.walk(dirName):
                break
        else:
            path, dirs = os.path.split(dirName)  # Script Post Processing
            if not (nzbName is None or nzbName.endswith(u'.nzb')) and os.path.isfile(os.path.join(dirName, nzbName)):  # For single torrent file without Dir
                dirs = []
                files = [os.path.join(dirName, nzbName)]
            else:
                dirs = [dirs]
                files = []

        return path, dirs, files

    def process_failed(self, dirName, nzbName):
        """Process a download that did not complete correctly."""
        if app.USE_FAILED_DOWNLOADS:
            processor = None

            try:
                processor = failed_processor.FailedProcessor(dirName, nzbName)
                self.result = processor.process()
                process_fail_message = u""
            except FailedPostProcessingFailedException as e:
                self.result = False
                process_fail_message = ex(e)

            if processor:
                self.output += processor.log

            if app.DELETE_FAILED and self.result:
                if self.delete_folder(dirName, check_empty=False):
                    self._log(u"Deleted folder: %s" % dirName, logger.DEBUG)

            if self.result:
                self._log(u"Failed Download Processing succeeded: (%s, %s)" % (nzbName, dirName))
            else:
                self._log(u"Failed Download Processing failed: (%s, %s): %s" %
                          (nzbName, dirName, process_fail_message), logger.WARNING)

    @staticmethod
    def subtitles_enabled(*args):
        """Try to parse names to a show and check whether the show has subtitles enabled.

        :param args:
        :return:
        :rtype: bool
        """
        for name in args:
            if not name:
                continue

            try:
                parse_result = NameParser().parse(name, cache_result=True)
                if parse_result.show.indexerid:
                    main_db_con = db.DBConnection()
                    sql_results = main_db_con.select("SELECT subtitles FROM tv_shows WHERE indexer_id = ? LIMIT 1",
                                                     [parse_result.show.indexerid])
                    return bool(sql_results[0]['subtitles']) if sql_results else False

                logger.log(u'Empty indexer ID for: {name}'.format(name=name), logger.WARNING)
            except (InvalidNameException, InvalidShowException):
                logger.log(u'Not enough information to parse filename into a valid show. Consider adding scene '
                           u'exceptions or improve naming for: {name}'.format(name=name), logger.WARNING)
        return False
