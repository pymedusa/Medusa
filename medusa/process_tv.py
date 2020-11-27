# coding=utf-8

"""Process TV module."""

from __future__ import unicode_literals

import logging
import os
import shutil
import stat
from builtins import object

from medusa import app, db, failed_processor, helpers, notifiers, post_processor
from medusa.clients import torrent
from medusa.common import DOWNLOADED, SNATCHED, SNATCHED_BEST, SNATCHED_PROPER
from medusa.helper.common import is_sync_file
from medusa.helper.exceptions import EpisodePostProcessingFailedException, FailedPostProcessingFailedException, ex
from medusa.logger.adapters.style import CustomBraceAdapter
from medusa.name_parser.parser import InvalidNameException, InvalidShowException, NameParser
from medusa.subtitles import accept_any, accept_unknown, get_embedded_subtitles

from rarfile import BadRarFile, Error, NotRarFile, RarCannotExec, RarFile

from six import iteritems


log = CustomBraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class PostProcessorRunner(object):
    """Post Processor Scheduler Action."""

    def __init__(self):
        """Init method."""
        self.amActive = False

    def run(self, force=False, **kwargs):
        """Run the postprocessor."""
        path = kwargs.pop('path', app.TV_DOWNLOAD_DIR)
        process_method = kwargs.pop('process_method', app.PROCESS_METHOD)

        if not os.path.isdir(path):
            result = "Post-processing attempted but directory doesn't exist: {path}"
            log.warning(result, {'path': path})
            return result.format(path=path)

        if not os.path.isabs(path):
            result = 'Post-processing attempted but directory is relative '
            '(and probably not what you really want to process): {path}'
            log.warning(result, {'path': path})
            return result.format(path=path)

        if app.post_processor_scheduler.action.amActive:
            result = 'Post-processor is already running.'
            log.info(result)
            return result

        try:
            self.amActive = True
            return ProcessResult(path, process_method).process(force=force, **kwargs)
        finally:
            self.amActive = False


class ProcessResult(object):

    IGNORED_FOLDERS = ('@eaDir', '#recycle', '.@__thumb',)

    def __init__(self, path, process_method=None):

        self._output = []
        self.directory = path
        self.process_method = process_method or app.PROCESS_METHOD
        self.resource_name = None
        self.result = True
        self.succeeded = True
        self.missedfiles = []
        self.unwanted_files = []
        self.allowed_extensions = app.ALLOWED_EXTENSIONS

    @property
    def directory(self):
        """Return the root directory we are going to process."""
        return getattr(self, '_directory')

    @directory.setter
    def directory(self, path):
        directory = None
        if os.path.isdir(path):
            self.log_and_output('Processing path: {path}', **{'path': path})
            directory = os.path.realpath(path)

        # If the client and the application are not on the same machine,
        # translate the directory into a network directory
        elif all([app.TV_DOWNLOAD_DIR, os.path.isdir(app.TV_DOWNLOAD_DIR),
                  os.path.normpath(path) == os.path.normpath(app.TV_DOWNLOAD_DIR)]):
            directory = os.path.join(
                app.TV_DOWNLOAD_DIR,
                os.path.abspath(path).split(os.path.sep)[-1]
            )
            self.log_and_output('Trying to use folder: {directory}', level=logging.DEBUG, **{'directory': directory})
        else:
            self.log_and_output(
                'Unable to figure out what folder to process.'
                " If your download client and Medusa aren't on the same"
                ' machine, make sure to fill out the Post Processing Dir'
                ' field in the config.', level=logging.WARNING
            )
        setattr(self, '_directory', directory)

    @property
    def paths(self):
        """Return the paths we are going to try to process."""
        if self.directory:
            yield self.directory
            if self.resource_name:
                return
            for root, dirs, files in os.walk(self.directory):
                del files  # unused variable
                for folder in dirs:
                    path = os.path.join(root, folder)
                    yield path
                break

    @property
    def video_files(self):
        """Return attribute _video_files."""
        return getattr(self, '_video_files', [])

    @video_files.setter
    def video_files(self, value):
        """Set attribute _video_files."""
        setattr(self, '_video_files', value)

    @property
    def output(self):
        """Join self.output into string."""
        return '\n'.join(self._output)

    def log_and_output(self, message, level=logging.INFO, **kwargs):
        """Log helper for logging through CustomBraceAdapter and adding the output to self._output."""
        log.log(level, message, kwargs)
        self._output.append(message.format(**kwargs))

    def process(self, resource_name=None, force=False, is_priority=None, delete_on=False, failed=False,
                proc_type='auto', ignore_subs=False):
        """
        Scan through the files in the root directory and process whatever media files are found.

        :param resource_name: The resource that will be processed directly
        :param force: True to postprocess already postprocessed files
        :param is_priority: Boolean for whether or not is a priority download
        :param delete_on: Boolean for whether or not it should delete files
        :param failed: Boolean for whether or not the download failed
        :param proc_type: Type of postprocessing auto or manual
        :param ignore_subs: True to ignore setting 'postpone if no subs'
        """
        if not self.directory:
            return self.output

        if resource_name:
            self.resource_name = resource_name

        if app.POSTPONE_IF_NO_SUBS:
            self.log_and_output("Feature 'postpone post-processing if no subtitle available' is enabled.")

        for path in self.paths:

            if not self.should_process(path, failed):
                continue

            self.result = True

            for dir_path, filelist in self._get_files(path):

                sync_files = (filename
                              for filename in filelist
                              if is_sync_file(filename))

                # Don't process files if they are still being synced
                postpone = app.POSTPONE_IF_SYNC_FILES and any(sync_files)
                if not postpone:
                    self.log_and_output('Processing folder: {dir_path}', level=logging.DEBUG, **{'dir_path': dir_path})

                    self.prepare_files(dir_path, filelist, force)
                    self.process_files(dir_path, force=force, is_priority=is_priority,
                                       ignore_subs=ignore_subs)
                    self._clean_up(dir_path, proc_type, delete=delete_on)

                else:
                    self.log_and_output('Found temporary sync files in folder: {dir_path}', **{'dir_path': dir_path})
                    self.log_and_output('Skipping post-processing for folder: {dir_path}', **{'dir_path': dir_path})

                    self.missedfiles.append('{0}: Sync files found'.format(dir_path))

        if self.succeeded:
            self.log_and_output('Post-processing completed.')

            # Clean Kodi library
            if app.KODI_LIBRARY_CLEAN_PENDING and notifiers.kodi_notifier.clean_library():
                app.KODI_LIBRARY_CLEAN_PENDING = False

            if self.missedfiles:

                self.log_and_output('I did encounter some unprocessable items: ')

                for missed_file in self.missedfiles:
                    self.log_and_output('Missed file: {missed_file}', level=logging.WARNING, **{'missed_file': missed_file})
        else:
            self.log_and_output('Problem(s) during processing, failed for the following files/folders: ', level=logging.WARNING)
            for missed_file in self.missedfiles:
                self.log_and_output('Missed file: {missed_file}', level=logging.WARNING, **{'missed_file': missed_file})

        if all([app.USE_TORRENTS, app.TORRENT_SEED_LOCATION,
                self.process_method in ('hardlink', 'symlink', 'reflink')]):
            for info_hash, release_names in list(iteritems(app.RECENTLY_POSTPROCESSED)):
                if self.move_torrent(info_hash, release_names):
                    app.RECENTLY_POSTPROCESSED.pop(info_hash, None)

        return self.output

    def _clean_up(self, path, proc_type, delete=False):
        """Clean up post-processed folder based on the checks below."""
        # Always delete files if they are being moved or if it's explicitly wanted
        clean_folder = proc_type == 'manual' and delete
        if self.process_method == 'move' or clean_folder:

            for folder in self.IGNORED_FOLDERS:
                self.delete_folder(os.path.join(path, folder))

            if self.unwanted_files:
                self.delete_files(path, self.unwanted_files)

            if all([not app.NO_DELETE or clean_folder, self.process_method in ('move', 'copy'),
                    os.path.normpath(path) != os.path.normpath(app.TV_DOWNLOAD_DIR)]):

                check_empty = False if self.process_method == 'copy' else True
                if self.delete_folder(path, check_empty=check_empty):
                    self.log_and_output('Deleted folder: {path}', level=logging.DEBUG, **{'path': path})

    def should_process(self, path, failed=False):
        """
        Determine if a directory should be processed.

        :param path: Path we want to verify
        :param failed: (optional) Mark the directory as failed
        :return: True if the directory is valid for processing, otherwise False
        :rtype: Boolean
        """
        if not self._is_valid_folder(path, failed):
            return False

        folder = os.path.basename(path)
        if helpers.is_hidden_folder(path) or any(f == folder for f in self.IGNORED_FOLDERS):
            self.log_and_output('Ignoring folder: {folder}', level=logging.DEBUG, **{'folder': folder})
            self.missedfiles.append('{0}: Hidden or ignored folder'.format(path))
            return False

        for root, dirs, files in os.walk(path):
            for subfolder in dirs:
                if not self._is_valid_folder(os.path.join(root, subfolder), failed):
                    return False
            for each_file in files:
                if helpers.is_media_file(each_file) or helpers.is_rar_file(each_file):
                    return True
            # Stop at first subdirectories if post-processing path
            if self.directory == path:
                break

        self.log_and_output('No processable items found in folder: {path}', level=logging.DEBUG, **{'path': path})
        return False

    def _is_valid_folder(self, path, failed):
        """Verify folder validity based on the checks below."""
        folder = os.path.basename(path)

        if folder.startswith('_FAILED_'):
            self.log_and_output('The directory name indicates it failed to extract.', level=logging.DEBUG)
            failed = True
        elif folder.startswith('_UNDERSIZED_'):
            self.log_and_output('The directory name indicates that it was previously rejected for being undersized.', level=logging.DEBUG)
            failed = True

        if failed:
            self.process_failed(path)
            self.missedfiles.append('{0}: Failed download'.format(path))
            return False

        # SABnzbd: _UNPACK_, NZBGet: _unpack
        if folder.startswith(('_UNPACK_', '_unpack')):
            self.log_and_output('The directory name indicates that this release is in the process of being unpacked.', level=logging.DEBUG)
            self.missedfiles.append('{0}: Being unpacked'.format(path))
            return False

        return True

    def _get_files(self, path):
        """Return the path to a folder and its contents as a tuple."""
        # If resource_name is a file and not an NZB, process it directly
        if self.resource_name and (
            not self.resource_name.endswith('.nzb') and os.path.isfile(os.path.join(path, self.resource_name))
        ):
            yield path, [self.resource_name]
        else:
            topdown = True if self.directory == path else False
            for root, dirs, files in os.walk(path, topdown=topdown):
                if files:
                    yield root, files
                if topdown:
                    break
                del dirs  # unused variable

    def prepare_files(self, path, files, force=False):
        """Prepare files for post-processing."""
        video_files = []
        rar_files = []
        for each_file in files:
            if helpers.is_media_file(each_file):
                video_files.append(each_file)
            elif helpers.is_rar_file(each_file):
                rar_files.append(each_file)

        rar_content = []
        video_in_rar = []
        if rar_files:
            rar_content = self.unrar(path, rar_files, force)
            files.extend(rar_content)
            video_in_rar = [each_file for each_file in rar_content if helpers.is_media_file(each_file)]
            video_files.extend(video_in_rar)

        self.log_and_output('Post-processing files: {files}', level=logging.DEBUG, **{'files': files})
        self.log_and_output('Post-processing video files: {video_files}', level=logging.DEBUG, **{'video_files': video_files})

        if rar_content:
            self.log_and_output('Post-processing rar content: {rar_content}', level=logging.DEBUG, **{'rar_content': rar_content})
            self.log_and_output('Post-processing video in rar: {video_in_rar}', level=logging.DEBUG, **{'video_in_rar': video_in_rar})

        unwanted_files = [filename
                          for filename in files
                          if filename not in video_files
                          and helpers.get_extension(filename) not in
                          self.allowed_extensions]
        if unwanted_files:
            self.log_and_output('Found unwanted files: {unwanted_files}', level=logging.DEBUG, **{'unwanted_files': unwanted_files})

        self.video_files = video_files
        self.rar_content = rar_content
        self.video_in_rar = video_in_rar
        self.unwanted_files = unwanted_files

    def process_files(self, path, force=False, is_priority=None, ignore_subs=False):
        """Post-process and delete the files in a given path."""
        # TODO: Replace this with something that works for multiple video files
        if self.resource_name and len(self.video_files) > 1:
            self.resource_name = None

        if self.video_in_rar:
            video_files = set(self.video_files + self.video_in_rar)

            if self.process_method in ('hardlink', 'symlink', 'reflink'):
                process_method = self.process_method
                # Move extracted video files instead of hard/softlinking them
                self.process_method = 'move'
                self.process_media(path, self.video_in_rar, force, is_priority, ignore_subs)
                if not self.postpone_processing:
                    self.delete_files(path, self.rar_content)
                # Reset process method to initial value
                self.process_method = process_method

                self.process_media(path, video_files - set(self.video_in_rar), force,
                                   is_priority, ignore_subs)
            else:
                self.process_media(path, video_files, force, is_priority, ignore_subs)

                if app.DELRARCONTENTS and not self.postpone_processing:
                    self.delete_files(path, self.rar_content)

        else:
            self.process_media(path, self.video_files, force, is_priority, ignore_subs)

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
                log.info('Not deleting folder {folder} found the following files: {check_files}', {
                    'folder': folder, 'check_files': check_files
                })
                return False

            try:
                log.info("Deleting folder (if it's empty): {folder}", {'folder': folder})
                os.rmdir(folder)
            except (OSError, IOError) as error:
                log.warning('Unable to delete folder: {folder}: {error}', {'folder': folder, 'error': ex(error)})
                return False
        else:
            try:
                log.info('Deleting folder: {folder}', {'folder': folder})
                shutil.rmtree(folder)
            except (OSError, IOError) as error:
                log.warning('Unable to delete folder: {folder}: {error}', {'folder': folder, 'error': ex(error)})
                return False

        return True

    def delete_files(self, path, files, force=False):
        """
        Remove files from filesystem.

        :param path: path to process
        :param files: files we want to delete
        :param force: Boolean, force deletion, defaults to false
        """
        if not files:
            return

        if not self.result and force:
            self.log_and_output('Forcing deletion of files, even though last result was not successful.', level=logging.DEBUG)
        elif not self.result:
            return

        # Delete all file not needed
        for cur_file in files:
            cur_file_path = os.path.join(path, cur_file)

            if not os.path.isfile(cur_file_path):
                continue  # Prevent error when a notwantedfiles is an associated files

            self.log_and_output('Deleting file: {cur_file}', level=logging.DEBUG, **{'cur_file': cur_file})

            # check first the read-only attribute
            file_attribute = os.stat(cur_file_path)[0]
            if not file_attribute & stat.S_IWRITE:
                # File is read-only, so make it writeable
                self.log_and_output('Changing read-only flag for file: {cur_file}', level=logging.DEBUG, **{'cur_file': cur_file})
                try:
                    os.chmod(cur_file_path, stat.S_IWRITE)
                except OSError as error:
                    self.log_and_output('Cannot change permissions of {cur_file_path}: {error}',
                                        level=logging.DEBUG, **{'cur_file_path': cur_file_path, 'error': ex(error)})
            try:
                os.remove(cur_file_path)
            except OSError as error:
                self.log_and_output('Unable to delete file {cur_file}: {error}', level=logging.DEBUG, **{'cur_file': cur_file, 'error': ex(error)})

    def unrar(self, path, rar_files, force=False):
        """
        Extract RAR files.

        :param path: Path to look for files in
        :param rar_files: Names of RAR files
        :param force: process currently processing items
        :return: List of unpacked file names
        """
        unpacked_files = []

        if app.UNPACK and rar_files:
            self.log_and_output('Packed files detected: {rar_files}', level=logging.DEBUG, **{'rar_files': rar_files})

            for archive in rar_files:
                self.log_and_output('Unpacking archive: {archive}', level=logging.DEBUG, **{'archive': archive})

                failure = None
                try:
                    rar_handle = RarFile(os.path.join(path, archive))

                    # check that the rar doesnt need a password
                    if rar_handle.needs_password():
                        raise ValueError('Rar requires a password')

                    # raise an exception if the rar file is broken
                    rar_handle.testrar()

                    # Skip extraction if any file in archive has previously been extracted
                    skip_extraction = False
                    for file_in_archive in [os.path.basename(each.filename)
                                            for each in rar_handle.infolist()
                                            if not each.isdir()]:
                        if not force and self.already_postprocessed(file_in_archive):
                            self.log_and_output('Archive file already post-processed, extraction skipped: {file_in_archive}',
                                                level=logging.DEBUG, **{'file_in_archive': file_in_archive})
                            skip_extraction = True
                            break

                        if app.POSTPONE_IF_NO_SUBS and os.path.isfile(os.path.join(path, file_in_archive)):
                            self.log_and_output('Archive file already extracted, extraction skipped: {file_in_archive}',
                                                level=logging.DEBUG, **{'file_in_archive': file_in_archive})
                            skip_extraction = True
                            break

                    if not skip_extraction:
                        rar_handle.extractall(path=path)

                    for each in rar_handle.infolist():
                        if not each.isdir():
                            basename = os.path.basename(each.filename)
                            unpacked_files.append(basename)

                    del rar_handle

                except (BadRarFile, Error, NotRarFile, RarCannotExec, ValueError) as error:
                    failure = (ex(error), 'Unpacking failed with a Rar error')
                except Exception as error:
                    failure = (ex(error), 'Unpacking failed for an unknown reason')

                if failure is not None:
                    self.log_and_output('Failed unpacking archive {archive}: {failure}', level=logging.WARNING, **{'archive': archive, 'failure': failure[0]})
                    self.missedfiles.append('{0}: Unpacking failed: {1}'.format(archive, failure[1]))
                    self.result = False
                    continue

            self.log_and_output('Extracted content: {unpacked_files}', level=logging.DEBUG, **{'unpacked_files': unpacked_files})

        return unpacked_files

    def already_postprocessed(self, video_file):
        """
        Check if we already post-processed an auto snatched file.

        :param video_file: File name
        :return:
        """
        main_db_con = db.DBConnection()
        history_result = main_db_con.select(
            'SELECT showid, season, episode, indexer_id '
            'FROM history '
            'WHERE action = ? '
            'AND resource LIKE ?'
            'ORDER BY date DESC',
            [DOWNLOADED, '%' + video_file])

        if history_result:
            snatched_statuses = [SNATCHED, SNATCHED_PROPER, SNATCHED_BEST]

            tv_episodes_result = main_db_con.select(
                'SELECT manually_searched '
                'FROM tv_episodes '
                'WHERE indexer = ? '
                'AND showid = ? '
                'AND season = ? '
                'AND episode = ? '
                'AND status IN (?, ?, ?) ',
                [history_result[0]['indexer_id'],
                 history_result[0]['showid'],
                 history_result[0]['season'],
                 history_result[0]['episode']
                 ] + snatched_statuses
            )

            if not tv_episodes_result or tv_episodes_result[0]['manually_searched'] == 0:
                self.log_and_output("You're trying to post-process an automatically searched file that has"
                                    ' already been processed, skipping: {video_file}', level=logging.DEBUG, **{'video_file': video_file})
                return True

    def process_media(self, path, video_files, force=False, is_priority=None, ignore_subs=False):
        """
        Postprocess media files.

        :param path: Path to postprocess in
        :param video_files: Filenames to look for and postprocess
        :param force: Postprocess currently postprocessing file
        :param is_priority: Boolean, is this a priority download
        :param ignore_subs: True to ignore setting 'postpone if no subs'
        """
        self.postpone_processing = False

        for video in video_files:
            file_path = os.path.join(path, video)

            if not force and self.already_postprocessed(video):
                self.log_and_output('Skipping already processed file: {video}', level=logging.DEBUG, **{'video': video})
                continue

            try:
                processor = post_processor.PostProcessor(file_path, self.resource_name,
                                                         self.process_method, is_priority)

                if app.POSTPONE_IF_NO_SUBS:
                    if not self._process_postponed(processor, file_path, video, ignore_subs):
                        continue

                self.result = processor.process()
                process_fail_message = ''
            except EpisodePostProcessingFailedException as error:
                processor = None
                self.result = False
                process_fail_message = ex(error)

            if processor:
                self._output.append(processor.output)

            if self.result:
                self.log_and_output('Processing succeeded for {file_path}', **{'file_path': file_path})
            else:
                self.log_and_output('Processing failed for {file_path}: {process_fail_message}',
                                    level=logging.WARNING, **{'file_path': file_path, 'process_fail_message': process_fail_message})
                self.missedfiles.append('{0}: Processing failed: {1}'.format(file_path, process_fail_message))
                self.succeeded = False

    def _process_postponed(self, processor, path, video, ignore_subs):
        if not ignore_subs:
            if self.subtitles_enabled(path, self.resource_name):
                embedded_subs = set() if app.IGNORE_EMBEDDED_SUBS else get_embedded_subtitles(path)

                # We want to ignore embedded subtitles and video has at least one
                if accept_unknown(embedded_subs):
                    self.log_and_output("Found embedded unknown subtitles and we don't want to ignore them. "
                                        'Continuing the post-processing of this file: {video}', **{'video': video})
                elif accept_any(embedded_subs):
                    self.log_and_output('Found wanted embedded subtitles. '
                                        'Continuing the post-processing of this file: {video}', **{'video': video})
                else:
                    associated_subs = processor.list_associated_files(path, subtitles_only=True)
                    if not associated_subs:
                        self.log_and_output('No subtitles associated. Postponing the post-processing of this file: {video}',
                                            level=logging.DEBUG, **{'video': video})
                        self.postpone_processing = True
                        return False
                    else:
                        self.log_and_output('Found associated subtitles. '
                                            'Continuing the post-processing of this file: {video}', **{'video': video})
            else:
                self.log_and_output('Subtitles disabled for this show. '
                                    'Continuing the post-processing of this file: {video}', **{'video': video})
        else:
            self.log_and_output('Subtitles check was disabled for this episode in manual post-processing. '
                                'Continuing the post-processing of this file: {video}', **{'video': video})
        return True

    def process_failed(self, path):
        """Process a download that did not complete correctly."""
        if app.USE_FAILED_DOWNLOADS:
            try:
                processor = failed_processor.FailedProcessor(path, self.resource_name)
                self.result = processor.process()
                process_fail_message = ''
            except FailedPostProcessingFailedException as error:
                processor = None
                self.result = False
                process_fail_message = ex(error)

            if processor:
                self._output.append(processor.output)

            if app.DELETE_FAILED and self.result:
                if self.delete_folder(path, check_empty=False):
                    self.log_and_output('Deleted folder: {path}', level=logging.DEBUG, **{'path': path})

            if self.result:
                self.log_and_output('Failed Download Processing succeeded: {resource}, {path}', **{'resource': self.resource_name, 'path': path})
            else:
                self.log_and_output('Failed Download Processing failed: {resource}, {path}: {process_fail_message}',
                                    level=logging.WARNING, **{
                                        'resource': self.resource_name, 'path': path, 'process_fail_message': process_fail_message
                                    })

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
                parse_result = NameParser().parse(name)
                if parse_result.series.indexerid:
                    main_db_con = db.DBConnection()
                    sql_results = main_db_con.select('SELECT subtitles FROM tv_shows WHERE indexer = ? AND indexer_id = ? LIMIT 1',
                                                     [parse_result.series.indexer, parse_result.series.indexerid])
                    return bool(sql_results[0]['subtitles']) if sql_results else False

                log.warning('Empty indexer ID for: {name}', {'name': name})
            except (InvalidNameException, InvalidShowException):
                log.warning('Not enough information to parse filename into a valid show. Consider adding scene '
                            'exceptions or improve naming for: {name}', {'name': name})
        return False

    @staticmethod
    def move_torrent(info_hash, release_names):
        """Move torrent to a given seeding folder after PP."""
        if release_names:
            # Log 'release' or 'releases'
            s = 's' if len(release_names) > 1 else ''
            release_names = ', '.join(release_names)
        else:
            s = ''
            release_names = 'N/A'

        log.debug('Trying to move torrent after post-processing')
        client = torrent.get_client_class(app.TORRENT_METHOD)()
        torrent_moved = False
        try:
            torrent_moved = client.move_torrent(info_hash)
        except AttributeError:
            log.warning("Your client doesn't support moving torrents to new location")
            return False

        if torrent_moved:
            log.debug("Moved torrent for release{s} '{release}' with hash: {hash} to: '{path}'", {
                      'release': release_names, 'hash': info_hash, 'path': app.TORRENT_SEED_LOCATION, 's': s})
            return True
        else:
            log.warning("Couldn't move torrent for release{s} '{release}' with hash: {hash} to: '{path}'. "
                        'Please check logs.', {'release': release_names, 'hash': info_hash, 'path': app.TORRENT_SEED_LOCATION, 's': s})
            return False
