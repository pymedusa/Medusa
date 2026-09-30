# coding=utf-8

"""Process TV module."""

from __future__ import unicode_literals

import logging
import os
import shutil
import stat
import traceback
from builtins import object
from collections import namedtuple
from threading import Lock


from medusa import app, db, failed_processor, helpers, notifiers, post_processor, ws
from medusa.clients import torrent
from medusa.common import DOWNLOADED, SNATCHED, SNATCHED_BEST, SNATCHED_PROPER
from medusa.helper.common import is_sync_file
from medusa.helper.exceptions import (
    EpisodePostProcessingAbortException,
    EpisodePostProcessingFailedException,
    EpisodePostProcessingPostponedException,
    FailedPostProcessingFailedException,
    ex
)
from medusa.logger.adapters.style import CustomBraceAdapter
from medusa.name_parser.parser import InvalidNameException, InvalidShowException, NameParser
from medusa.queues import generic_queue
from medusa.subtitles import accept_any, accept_unknown, get_embedded_subtitles

from rarfile import BadRarFile, Error, NotRarFile, RarCannotExec, RarFile, sanitize_filename

from six import iteritems


log = CustomBraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

# Scheduled scans and queued jobs share both source files and the torrent move queue.
_PROCESS_LOCK = Lock()


class ProcessingTarget(namedtuple('ProcessingTarget', 'path directory filename')):
    """Resolved selection: validation path, scan/extraction directory, and optional file."""

    __slots__ = ()

    @property
    def file_path(self):
        """Return the selected file without rediscovering its input form."""
        return os.path.join(self.directory, self.filename) if self.filename is not None else None


MediaFile = namedtuple('MediaFile', 'name history_name')


class PostProcessQueueItem(generic_queue.QueueItem):
    """Post-process queue item class."""

    def __init__(self, path=None, info_hash=None, resource_name=None, force=False,
                 is_priority=False, process_method=None, delete_on=False, failed=False,
                 proc_type='auto', ignore_subs=False, episodes=[], client_type=None, process_single_resource=False):
        """Initialize the class."""
        generic_queue.QueueItem.__init__(self, u'Post Process')

        self.success = None
        self.started = None
        self.path = path
        self.info_hash = info_hash
        self.resource_name = resource_name
        self.force = force
        self.is_priority = is_priority
        self.delete_on = delete_on
        self.failed = failed
        self.proc_type = proc_type
        self.ignore_subs = ignore_subs
        self.episodes = episodes
        self.process_single_resource = process_single_resource

        # torrent or nzb. Pass info on what sort of download we're processing.
        # We might need this when determining the PROCESS_METHOD.
        self.client_type = client_type
        self.process_method = self.get_process_method(process_method, client_type)

        self.to_json.update({
            'success': self.success,
            'config': {
                'path': self.path,
                'info_hash': self.info_hash,
                'resource_name': self.resource_name,
                'force': self.force,
                'is_priority': self.is_priority,
                'process_method': self.process_method,
                'delete_on': self.delete_on,
                'failed': self.failed,
                'proc_type': self.proc_type,
                'ignore_subs': self.ignore_subs,
            }
        })

    def get_process_method(self, process_method, client_type):
        """Determine the correct process method.

        If client_type is provided (torrent/nzb) use that to get a
            client specific process method.
        """
        if process_method:
            return process_method

        if self.client_type and app.USE_SPECIFIC_PROCESS_METHOD:
            return app.PROCESS_METHOD_NZB if client_type == 'nzb' else app.PROCESS_METHOD_TORRENT

        return app.PROCESS_METHOD

    def update_resource(self, status):
        """
        Update the resource in db, depending on the postprocess result.

        Update the last found info_hash (in case there are duplicates).
        """
        main_db_con = db.DBConnection()
        main_db_con.action(
            'UPDATE history set client_status = ? WHERE info_hash = ?',
            [status.status, self.info_hash]
        )
        log.info('Updated history with resource path: {path} and resource: {resource} with new status {status}', {
            'path': self.path,
            'resource': self.resource_name,
            'status': status
        })

    def update_history_processed(self, process_results):
        """Update the history table when we have a processed path + resource."""
        from medusa.schedulers.download_handler import ClientStatus

        if process_results.skipped:
            log.info('Skipped post-processing for: {path} and resource: {resource} keeping existing status', {
                'path': self.path,
                'resource': self.resource_name
            })
            return

        status = ClientStatus()

        # Postpone the process, and setting the client_status.
        if not process_results.postpone_any:
            # Resource postprocessed
            status.add_status_string('Postprocessed')

            # If succeeded store Postprocessed + Completed. (384)
            # If failed store Postprocessed + Failed. (272)
            if process_results.result and process_results.succeeded and not process_results.failed:
                status.add_status_string('Completed')
                self.success = True
            else:
                status.add_status_string('Failed')
                self.success = False
            self.update_resource(status)
        else:
            log.info('Postponed post-processing for: {path} and resource: {resource} keeping existing status', {
                'path': self.path,
                'resource': self.resource_name
            })

    def process_path(self):
        """Process for when we have a valid path."""
        process_results = ProcessResult(
            self.path, self.process_method,
            failed=self.failed, episodes=self.episodes,
            process_single_resource=self.process_single_resource
        )
        process_results.process(
            resource_name=self.resource_name,
            force=self.force,
            is_priority=self.is_priority,
            delete_on=self.delete_on,
            proc_type=self.proc_type,
            ignore_subs=self.ignore_subs
        )

        # A user might want to use advanced post-processing, but opt-out of failed download handling.
        if (
            self.process_single_resource
            and (process_results.failed or not process_results.succeeded)
            and not process_results.postpone_any
        ):
            process_results.process_failed(self.path)

        # In case we have an info_hash or (nzbid), update the history table with the pp results.
        # Keep history pending if any part of the request was postponed.
        if self.info_hash and not process_results.postpone_any:
            self.update_history_processed(process_results)

        return process_results

    def run(self):
        """Run postprocess queueitem thread."""
        generic_queue.QueueItem.run(self)
        self.started = True

        try:
            log.info('Beginning postprocessing for path {path} and resource {resource}', {
                'path': self.path, 'resource': self.resource_name
            })

            # Push an update to any open Web UIs through the WebSocket
            ws.Message('QueueItemUpdate', self.to_json).push()

            if not self.path and self.resource_name:
                # We don't have a path, but do have a resource name. If this is a failed download.
                # Let's use the TV_DOWNLOAD_DIR as path combined with the resource_name.
                self.path = app.TV_DOWNLOAD_DIR

            if self.path:
                process_results = self.process_path()
                if process_results._output:
                    self.to_json.update({'output': process_results._output})

            log.info('Completed Postproccessing')

            # Use success as a flag for a finished PP. PP it self can be succeeded or failed.
            self.success = True

            # Push an update to any open Web UIs through the WebSocket
            ws.Message('QueueItemUpdate', self.to_json).push()

        # TODO: Remove the catch all exception.
        except Exception:
            self.success = False
            log.debug(traceback.format_exc())


class PostProcessorRunner(object):
    """Post Processor Scheduler Action."""

    def __init__(self):
        """Initialize the class."""
        self.amActive = False

    def run(self, force=False, **kwargs):
        """Run the postprocessor."""
        path = kwargs.pop('path', app.TV_DOWNLOAD_DIR)
        process_method = kwargs.pop('process_method', app.PROCESS_METHOD)
        failed = kwargs.pop('failed', False)

        if path is None or not os.path.isdir(path):
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
            process_results = ProcessResult(path, process_method, failed=failed)
            process_results.process(force=force, **kwargs)

            # Only initiate failed download handling,
            # if process result has failed and failed download handling is enabled.
            if process_results.failed:
                process_results.process_failed(path)

            return process_results.output

        finally:
            self.amActive = False


class ProcessResult(object):

    IGNORED_FOLDERS = ('@eaDir', '#recycle', '.@__thumb',)

    def __init__(self, path, process_method=None, failed=False, episodes=[], process_single_resource=False):
        """
        Initialize ProcessResult object.

        :param path: The root path to start postprocessing from.
        :param process_method: Process method ('copy', 'move', 'hardlink', 'symlink', 'keeplink').
        :param failed: Start the ProcessResult with a failed download.
        :param episodes: Array of episode objects.
            Used to specify the episodes to `Retry` in case of a failed download.
            Currently only used by the Download Handler.
        """
        self._output = []
        self.input_path = self._resolve_input_path(path)
        self._original_file_path = self._get_original_file_path()
        self.process_method = process_method or app.PROCESS_METHOD
        self.failed = failed
        self.resource_name = None
        self._processed_media = set()
        self._incomplete_archive_members = set()
        self._processed_torrent_hashes = set()
        self.result = True
        # Processing aborted. So we don't want to trigger any failed download handling.
        # We do want to update the history client status.
        self.aborted = False
        # Processing succeeded. Trigger failed downlaod handling and update history client status.
        self.succeeded = True
        # No processing was attempted and no explicit failure was reported.
        self.skipped = False
        # Processing postponed. Stop postprocessing and don't update history client status.
        self.postpone_processing = False
        self.missed_files = []
        self.unwanted_files = []
        self.allowed_extensions = app.ALLOWED_EXTENSIONS
        # When multiple media folders/files processed. Flag postpone_any of any them was postponed.
        self.postpone_any = False
        self.episodes = episodes
        self.process_single_resource = process_single_resource

    def _is_tv_download_dir(self, path):
        """Check if the path exists, combine with the tv_download_dir path if available."""
        if not app.TV_DOWNLOAD_DIR:
            self.log_and_output('tv_download_dir not set, not using it', level=logging.DEBUG)
            return False

        if not os.path.isdir(app.TV_DOWNLOAD_DIR):
            self.log_and_output('tv_download_dir set, but cant resove to a local directory', level=logging.DEBUG)
            return False

        if not helpers.real_path(path) != helpers.real_path(app.TV_DOWNLOAD_DIR):
            self.log_and_output('real path didnt match for the path: [] but cant resove to a local directory',
                                level=logging.DEBUG, **{'path': helpers.real_path(path), 'tv_download_dir': helpers.real_path(app.TV_DOWNLOAD_DIR)})
            return False

        return True

    def _resolve_input_path(self, path):
        """Resolve the client's input to a local file or directory."""
        resolved_path = None
        if os.path.isdir(path):
            self.log_and_output('Processing path: {path}', **{'path': path})
            resolved_path = os.path.realpath(path)

        elif os.path.isfile(path):
            self.log_and_output('Processing path: {path} as a single file', **{'path': path})
            resolved_path = os.path.realpath(path)

        # If the client and the application are not on the same machine,
        # translate the input into a local download path.
        elif self._is_tv_download_dir(path):
            resolved_path = os.path.join(
                app.TV_DOWNLOAD_DIR,
                os.path.abspath(path).split(os.path.sep)[-1]
            )
            self.log_and_output('Trying to use folder: {directory}', level=logging.DEBUG, **{'directory': resolved_path})

        else:
            self.log_and_output(
                'Unable to figure out what folder to process.'
                " If your download client and Medusa aren't on the same"
                ' machine, make sure to fill out the Post Processing Dir'
                ' field in the config.', level=logging.WARNING
            )
        return resolved_path

    def _get_original_file_path(self):
        """Capture file-only input before processing can move or remove the source."""
        # Failure cleanup must retain file scope, not expand to the containing directory.
        if self.input_path and os.path.isfile(self.input_path):
            return self.input_path
        return None

    @property
    def paths(self):
        """Return the paths we are going to try to process."""
        if self.input_path:
            # An invalid selection must not be reopened through its children.
            if os.path.isdir(self.input_path) and not self._can_process_folder(self.input_path):
                return
            yield self.input_path
            # File inputs and roots removed by successful cleanup have no children.
            if self.resource_name or not os.path.isdir(self.input_path):
                return
            try:
                for root, dirs, files in os.walk(self.input_path, onerror=self._on_walk_error):
                    for folder in dirs:
                        yield os.path.join(root, folder)
                    break
            except OSError:
                return

    def _on_walk_error(self, error):
        """Stop an incomplete directory walk and leave the download pending for retry."""
        path = error.filename or self.input_path
        self.postpone_processing = True
        self.postpone_any = True
        self.result = False
        self.log_and_output('Unable to scan folder: {path}: {error}', level=logging.WARNING,
                            **{'path': path, 'error': ex(error)})
        self.missed_files.append('{0}: Unable to scan folder'.format(path))
        raise error

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

    def _resolve_target(self, path):
        """Interpret path and release metadata once, before validation or traversal."""
        if os.path.isfile(path):
            return ProcessingTarget(path, os.path.dirname(path), os.path.basename(path))

        if not self.resource_name:
            return ProcessingTarget(path, path, None)

        combined_path = os.path.join(path, self.resource_name)
        if os.path.isdir(combined_path):
            return ProcessingTarget(path, combined_path, None)

        # An NZB name is release metadata, unless it names an existing directory.
        if (self.resource_name.endswith('.nzb')
                or (os.path.isdir(path) and os.path.basename(path) == self.resource_name)):
            return ProcessingTarget(path, path, None)

        if os.path.isfile(combined_path):
            # Keep qualified filenames and their original extraction/cleanup root.
            return ProcessingTarget(path, path, self.resource_name)

        self.log_and_output(
            'Could not get a valid path or file for processing. path: [{path}], resource: [{resource}]',
            level=logging.DEBUG, **{'path': path, 'resource': self.resource_name})
        return ProcessingTarget(path, None, None)

    @staticmethod
    def _is_media_file(path):
        """Apply both path-based sample filtering and basename-only media exclusions."""
        filename = os.path.basename(path)
        return helpers.is_media_file(path) and (filename == path or helpers.is_media_file(filename))

    def _postpone_for_sync_files(self, path, files, resource_path=None):
        """Record sync-related postponement and return whether to skip processing."""
        if not app.POSTPONE_IF_SYNC_FILES:
            return False

        sync_path = os.path.dirname(resource_path) if resource_path else path
        if resource_path:
            try:
                # Check siblings without adding them to the selected files.
                with os.scandir(sync_path) as entries:
                    postpone = any(is_sync_file(entry.name) and not entry.is_dir() for entry in entries)
            except OSError as error:
                self.postpone_processing = True
                self.postpone_any = True
                self.log_and_output(
                    'Unable to check temporary sync files in folder: {path}: {error}',
                    level=logging.WARNING, **{'path': sync_path, 'error': ex(error)})
                self.missed_files.append('{0}: Unable to check sync files'.format(sync_path))
                return True
        else:
            postpone = any(is_sync_file(filename) for filename in files)

        if not postpone:
            return False

        self.postpone_processing = True
        self.postpone_any = True
        self.log_and_output('Found temporary sync files in folder: {dir_path}', **{'dir_path': sync_path})
        self.log_and_output('Skipping post-processing for folder: {dir_path}', **{'dir_path': path})
        self.missed_files.append('{0}: Sync files found'.format(path))
        return True

    def process(self, resource_name=None, force=False, is_priority=None, delete_on=False,
                proc_type='auto', ignore_subs=False):
        """
        Scan through the files in the root directory and process whatever media files are found.

        :param resource_name: The resource that will be processed directly
        :param force: True to postprocess already postprocessed files
        :param is_priority: Boolean for whether or not is a priority download
        :param delete_on: Boolean for whether or not it should delete files
        :param proc_type: Type of postprocessing auto or manual
        :param ignore_subs: True to ignore setting 'postpone if no subs'
        """
        with _PROCESS_LOCK:
            try:
                return self._process(resource_name, force, is_priority, delete_on, proc_type, ignore_subs)
            except Exception:
                # Even an interrupted scan must leave its queued torrent moves pending.
                self.result = False
                self.succeeded = False
                raise
            finally:
                if self.input_path:
                    self._move_processed_torrents()

    def _process(self, resource_name, force, is_priority, delete_on, proc_type, ignore_subs):
        """Process one selection while holding the shared execution guard."""
        self._processed_media.clear()
        self._incomplete_archive_members.clear()
        self._processed_torrent_hashes.clear()
        if resource_name:
            self.resource_name = resource_name
            self.log_and_output('Processing resource: {resource}', level=logging.DEBUG, **{'resource': self.resource_name})

        if not self.input_path:
            self.result = False
            self.skipped = not self.failed
            return self.output

        if app.POSTPONE_IF_NO_SUBS:
            self.log_and_output("Feature 'postpone post-processing if no subtitle available' is enabled.")

        processed_items = False
        for path in self.paths:

            target = self._resolve_target(path)
            if target.directory is None:
                continue
            resource_path = target.file_path
            if resource_path and not (helpers.is_media_file(resource_path) or helpers.is_rar_file(resource_path)):
                self.log_and_output(
                    'Resource is not a recognized video or RAR file: {path}',
                    level=logging.WARNING, **{'path': resource_path})
                self.missed_files.append('{0}: Not a valid video or RAR file'.format(resource_path))
                self.succeeded = False
                self.result = False
                continue

            if not self.should_process(target.path, resource_path or target.directory):
                continue

            self.result = True

            for dir_path, filelist in self._get_files(target):
                if self._postpone_for_sync_files(dir_path, filelist, resource_path):
                    continue

                if (not app.UNPACK and any(helpers.is_rar_file(filename) for filename in filelist)
                        and not any(helpers.is_media_file(filename) for filename in filelist)):
                    self.postpone_processing = True
                    self.postpone_any = True
                    self.log_and_output('Skipping folder with archives because unpacking is disabled: {path}',
                                        **{'path': dir_path})
                    self.missed_files.append('{0}: Archive unpacking is disabled'.format(dir_path))
                    continue

                self.log_and_output('Processing folder: {dir_path}', level=logging.DEBUG, **{'dir_path': dir_path})

                self.prepare_files(dir_path, filelist, force)
                self.process_files(dir_path, force=force, is_priority=is_priority,
                                   ignore_subs=ignore_subs)
                self._clean_up(dir_path, proc_type, delete=delete_on)
                # Keep track if processed anything.
                processed_items = True

        self.skipped = not processed_items and self.succeeded and not self.failed and not self.postpone_any
        if not processed_items:
            self.result = False

        if self.succeeded:
            if not processed_items and not self.postpone_any:
                self.log_and_output('No processable items found.')
            else:
                self.log_and_output('Post-processing completed.')

            # Clean Kodi library
            if app.KODI_LIBRARY_CLEAN_PENDING and notifiers.kodi_notifier.clean_library():
                app.KODI_LIBRARY_CLEAN_PENDING = False

            if self.missed_files:
                self.log_and_output('I did encounter some unprocessable items: ')

                for missed_file in self.missed_files:
                    self.log_and_output('Missed file: {missed_file}', level=logging.WARNING, **{'missed_file': missed_file})
        else:
            self.log_and_output('Problem(s) during processing, failed for the following files/folders: ', level=logging.WARNING)
            for missed_file in self.missed_files:
                self.log_and_output('Missed file: {missed_file}', level=logging.WARNING, **{'missed_file': missed_file})

        return self.output

    def _move_processed_torrents(self):
        """Move completed torrents without relocating downloads still needed for retry."""
        scope = (os.path.normcase(os.path.abspath(self.input_path)), self.resource_name or None)
        if self.postpone_any or not self.succeeded or self.failed or not self.result:
            # Preserve candidates for retry, but do not let unrelated requests move them.
            for info_hash in self._processed_torrent_hashes:
                candidate = app.RECENTLY_POSTPROCESSED.get(info_hash)
                if candidate:
                    candidate.pending_scans.add(scope)
            return

        # History may skip all previously imported media, so release deferred moves
        # even when this successful scan did not register a new candidate.
        for candidate in list(app.RECENTLY_POSTPROCESSED.values()):
            for pending_scope in list(candidate.pending_scans):
                if self._covers_scan_scope(scope, pending_scope):
                    candidate.pending_scans.discard(pending_scope)

        if all([app.USE_TORRENTS, app.TORRENT_SEED_LOCATION,
                self.process_method in ('hardlink', 'symlink', 'reflink', 'keeplink', 'copy')]):
            for info_hash, candidate in list(iteritems(app.RECENTLY_POSTPROCESSED)):
                if not candidate.pending_scans and self.move_torrent(info_hash, candidate.release_names):
                    app.RECENTLY_POSTPROCESSED.pop(info_hash, None)

    @staticmethod
    def _covers_scan_scope(scope, pending_scope):
        """Require a matching selection or a broader directory scan to release a move."""
        if scope == pending_scope:
            return True
        path, resource_name = scope
        pending_path, _ = pending_scope
        if resource_name:
            return False
        try:
            return os.path.normcase(os.path.commonpath((path, pending_path))) == path
        except ValueError:  # Different drives cannot cover the same download.
            return False

    def _clean_up(self, path, proc_type, delete=False):
        """Clean up post-processed folder based on the checks below."""
        clean_folder = proc_type == 'manual' and delete
        if self.process_method == 'move' or clean_folder:

            for folder in self.IGNORED_FOLDERS:
                self.delete_folder(os.path.join(path, folder))

            if self.unwanted_files:
                self.delete_files(path, self.unwanted_files)

            if (proc_type != 'manual' and not app.NO_DELETE) or clean_folder:
                check_empty = False if clean_folder else True
                if self.delete_folder(path, check_empty=check_empty):
                    self.log_and_output('Deleted folder: {path}', level=logging.DEBUG, **{'path': path})

    @staticmethod
    def _get_validation_root(path):
        """Bound file validation to its download root, without widening directory requests."""
        # Preserve the trailing separator on UNC share roots for commonpath().
        root = os.path.abspath(os.path.join(path, os.curdir))
        if not os.path.isfile(path):
            return os.path.normcase(root)

        parent = os.path.dirname(root)
        if app.TV_DOWNLOAD_DIR:
            download_root = os.path.realpath(os.path.join(app.TV_DOWNLOAD_DIR, os.curdir))
            try:
                if os.path.normcase(os.path.commonpath((download_root, parent))) == os.path.normcase(download_root):
                    return os.path.normcase(download_root)
            except ValueError:  # A download root on another drive cannot contain this file.
                pass

        # Without an enclosing download root, only the immediate parent is in scope.
        return os.path.normcase(parent)

    def should_process(self, path, resource_path=None):
        """
        Determine if a selected file or directory should be processed.

        :param path: Path we want to verify
        :param resource_path: A selected file or directory within the processing path, if any
        :return: True if the directory is valid for processing, otherwise False
        :rtype: Boolean
        """
        selected_path = resource_path or path
        is_file = os.path.isfile(selected_path)
        # Validate the selected resource and its ancestors without inspecting siblings.
        paths_to_check = [path]
        if is_file or selected_path != path:
            parent = os.path.dirname(os.path.abspath(selected_path))
            paths_to_check.extend((selected_path, parent))
            # Validate intermediate folders for nested resources, without scanning siblings.
            root = self._get_validation_root(path)
            try:
                contained = os.path.normcase(os.path.commonpath((root, parent))) == root
            except ValueError:  # Paths on different drives have no common parent.
                contained = False
            while contained and os.path.normcase(parent) != root:
                next_parent = os.path.dirname(parent)
                if next_parent == parent:
                    break
                parent = next_parent
                paths_to_check.append(parent)

        for checked_path in dict.fromkeys(paths_to_check):
            if not self._can_process_folder(checked_path):
                return False

        # A single file can be passed as the path to process, for example the content
        # path of a single-file torrent. os.walk() yields nothing for a file, so that
        # case needs to be decided here.
        if is_file:
            # Full paths must also respect basename-only media exclusions.
            return self._is_media_file(selected_path) or helpers.is_rar_file(selected_path)

        scan_root = selected_path == self.input_path and not self.resource_name
        processable = False
        try:
            for root, dirs, files in os.walk(selected_path, onerror=self._on_walk_error):
                dirs[:] = [folder for folder in dirs if not self._is_ignored_folder(os.path.join(root, folder))]
                # Broad scans validate each child as its own download through paths.
                if not scan_root:
                    for subfolder in dirs:
                        if not self._is_valid_folder(os.path.join(root, subfolder)):
                            return False
                # Validate the whole release before processing any descendant.
                if not scan_root and self._postpone_for_sync_files(root, files):
                    return False
                if not scan_root:
                    # Bottom-up processing must not import partial child files before
                    # their parent archive gets a chance to repair them.
                    self._check_retained_archive_members(root, files)
                for each_file in files:
                    if self._is_media_file(os.path.join(root, each_file)) or helpers.is_rar_file(each_file):
                        processable = True
                        break
                if scan_root:
                    break
        except OSError:
            return False

        if processable:
            return True
        self.log_and_output('No processable items found in folder: {path}', level=logging.DEBUG, **{'path': path})
        return False

    def _can_process_folder(self, path):
        """Apply structural folder checks consistently to selections and descendants."""
        if not self._is_valid_folder(path):
            return False
        if self._is_ignored_folder(path):
            self.log_and_output('Ignoring folder: {folder}', level=logging.DEBUG,
                                **{'folder': os.path.basename(path)})
            self.missed_files.append('{0}: Hidden or ignored folder'.format(path))
            return False
        return True

    def _is_valid_folder(self, path):
        """Verify folder validity based on the checks below."""
        folder = os.path.basename(path)

        if folder.startswith('_FAILED_'):
            self.log_and_output('The directory name indicates it failed to extract.', level=logging.DEBUG)
        elif folder.startswith('_UNDERSIZED_'):
            self.log_and_output('The directory name indicates that it was previously rejected for being undersized.', level=logging.DEBUG)

        failed_folder = folder.startswith(('_FAILED_', '_UNDERSIZED_'))
        if failed_folder and (self.resource_name or self._original_file_path or path == self.input_path):
            # A failed child in a broad scan must not fail unrelated downloads or the scan root.
            self.failed = True
        if self.failed or failed_folder:
            self.missed_files.append('{0}: Failed download.'.format(path))
            return False

        # SABnzbd: _UNPACK_, NZBGet: _unpack
        if folder.startswith(('_UNPACK_', '_unpack')):
            self.postpone_processing = True
            self.postpone_any = True
            self.log_and_output('The directory name indicates that this release is in the process of being unpacked.', level=logging.DEBUG)
            self.missed_files.append('{0}: Being unpacked.'.format(path))
            return False

        return True

    def _is_ignored_folder(self, path):
        """Apply the shared hidden-folder and ignored-name exclusions."""
        return os.path.basename(path) in self.IGNORED_FOLDERS or helpers.is_hidden_folder(path)

    def _is_ignored_subfolder(self, path, subfolder):
        """Check a relative folder and its ancestors, excluding the root path."""
        while subfolder and subfolder != os.curdir:
            if self._is_ignored_folder(os.path.join(path, subfolder)):
                return True
            subfolder = os.path.dirname(subfolder)
        return False

    def _get_files(self, target):
        """Yield file batches from a resolved target without reinterpreting the request."""
        if target.filename is not None:
            yield target.directory, [target.filename]
            return

        if target.directory is None:
            return

        # Broad scans discover root children lazily through paths. A selected release
        # must include its descendants here because paths yields only that selection.
        topdown = self.input_path == target.directory and not self.resource_name

        def on_walk_error(error):
            # Bottom-up walks enter ignored subtrees before we can filter their files.
            if error.filename:
                subfolder = os.path.relpath(error.filename, target.directory)
                if self._is_ignored_subfolder(target.directory, subfolder):
                    return
            self._on_walk_error(error)

        try:
            for root, dirs, files in os.walk(target.directory, topdown=topdown, onerror=on_walk_error):
                if files and not self._is_ignored_subfolder(target.directory, os.path.relpath(root, target.directory)):
                    yield root, sorted(files)
                if topdown:
                    break
        except OSError:
            return

    def prepare_files(self, path, files, force=False):
        """
        Prepare files for post-processing.

        Separate the Rar and Video files. -> self.video_files
            Extract the rar files. -> self.rar_content
            Collect new video files. -> self.video_in_rar
            List unwanted files -> self.unwanted_files
        :param path: Path to start looking for rar/video files.
        :param files: Filenames from traversal, or the exact selected resource name.
        """
        video_files = []
        rar_files = []
        for each_file in files:
            if self._is_media_file(os.path.join(path, each_file)):
                # Traversal supplies basenames; a selected resource keeps its qualification.
                video_files.append(MediaFile(each_file, each_file))
            elif helpers.is_rar_file(each_file):
                rar_files.append(each_file)

        rar_content = []
        video_in_rar = []
        if rar_files:
            rar_content = self.unrar(path, rar_files, force)
            files.extend(rar_content)
            # Extraction paths may be nested, but archive history matches basenames.
            video_in_rar = [MediaFile(each_file, os.path.basename(each_file)) for each_file in rar_content
                            if self._is_media_file(os.path.join(path, each_file))
                            and not self._is_ignored_subfolder(path, os.path.dirname(each_file))]
            video_files.extend(video_in_rar)

        self.log_and_output('Post-processing files: {files}', level=logging.DEBUG, **{'files': files})
        video_names = [video.name for video in video_files]
        self.log_and_output('Post-processing video files: {video_files}', level=logging.DEBUG, **{'video_files': video_names})

        if rar_content:
            self.log_and_output('Post-processing rar content: {rar_content}', level=logging.DEBUG, **{'rar_content': rar_content})
            self.log_and_output('Post-processing video in rar: {video_in_rar}', level=logging.DEBUG,
                                **{'video_in_rar': [video.name for video in video_in_rar]})

        unwanted_files = [filename
                          for filename in files
                          if filename not in video_names
                          and helpers.get_extension(filename) not in
                          self.allowed_extensions]
        # External extraction may leave archives and their volumes alongside the videos.
        if rar_files and not app.UNPACK:
            unwanted_files = []
        if unwanted_files:
            self.log_and_output('Found unwanted files: {unwanted_files}', level=logging.DEBUG, **{'unwanted_files': unwanted_files})

        self.video_files = video_files
        self.rar_content = rar_content
        self.video_in_rar = video_in_rar
        self.unwanted_files = unwanted_files

    def process_files(self, path, force=False, is_priority=None, ignore_subs=False):
        """Post-process and delete the files in a given path."""
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
        if not folder or not os.path.isdir(folder):
            return False

        # check if it's a protected folder
        if helpers.real_path(folder) in (helpers.real_path(app.TV_DOWNLOAD_DIR),
                                         helpers.real_path(app.DEFAULT_CLIENT_PATH),
                                         helpers.real_path(app.TORRENT_PATH)):
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

        # A later successful file must not allow cleanup of failed or postponed media.
        completed = self.result and self.succeeded and not self.postpone_any
        if not completed and force:
            self.log_and_output('Forcing deletion of files, even though processing did not complete successfully.', level=logging.DEBUG)
        elif not completed:
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

    @staticmethod
    def _archive_member_is_complete(path, size):
        """Check retained output against the archive's expected uncompressed size."""
        try:
            return os.path.isfile(path) and os.path.getsize(path) == size
        except OSError:
            return False

    def _check_retained_archive_members(self, path, files):
        """Identify incomplete retained files before descending into a release."""
        if not app.UNPACK or not app.POSTPONE_IF_NO_SUBS:
            return
        for filename in files:
            if not helpers.is_rar_file(filename):
                continue
            try:
                archive = RarFile(os.path.join(path, filename))
                try:
                    for member in archive.infolist():
                        if member.isdir():
                            continue
                        name = sanitize_filename(member.filename, os.path.sep, os.name == 'nt')
                        member_path = os.path.join(path, name)
                        if not self._archive_member_is_complete(member_path, member.file_size):
                            self._incomplete_archive_members.add(os.path.normcase(os.path.abspath(member_path)))
                finally:
                    archive.close()
            except Exception as error:
                # The extraction pass reports failures; this check only protects existing output.
                self.log_and_output('Unable to check retained archive members: {archive}: {error}',
                                    level=logging.DEBUG, **{'archive': filename, 'error': ex(error)})

    def _archive_member_needs_extraction(self, path, filename, size, force=False):
        """Check a member's history and whether it is available for a subtitle retry."""
        if not force and self.already_postprocessed(os.path.basename(filename)):
            return False
        if app.POSTPONE_IF_NO_SUBS and self._archive_member_is_complete(os.path.join(path, filename), size):
            return False
        return True

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
                archive_files = []
                try:
                    rar_handle = RarFile(os.path.join(path, archive))

                    # check that the rar doesnt need a password
                    if rar_handle.needs_password():
                        raise ValueError('Rar requires a password')

                    # Match rarfile's extraction paths, including its path sanitization.
                    archive_members = [member for member in rar_handle.infolist() if not member.isdir()]
                    archive_files = [sanitize_filename(member.filename, os.path.sep, os.name == 'nt')
                                     for member in archive_members]
                    needed_members = [member for member, filename in zip(archive_members, archive_files)
                                      if self._archive_member_needs_extraction(path, filename, member.file_size, force)]
                    if needed_members or not archive_members:
                        # raise an exception if the rar file is broken
                        rar_handle.testrar()
                        if len(needed_members) == len(archive_members):
                            rar_handle.extractall(path=path)
                        else:
                            # Do not overwrite members retained for a subtitle retry.
                            rar_handle.extractall(path=path, members=needed_members)
                    else:
                        self.log_and_output('All archive members already processed or extracted, skipping extraction: {archive}',
                                            level=logging.DEBUG, **{'archive': archive})

                    unpacked_files.extend(archive_files)
                    self._incomplete_archive_members.difference_update(
                        os.path.normcase(os.path.abspath(os.path.join(path, filename))) for filename in archive_files)

                    del rar_handle

                except (BadRarFile, Error, NotRarFile, RarCannotExec, ValueError) as error:
                    failure = (ex(error), 'Unpacking failed with a Rar error')
                except Exception as error:
                    failure = (ex(error), 'Unpacking failed for an unknown reason')

                if failure is not None:
                    self._incomplete_archive_members.update(
                        os.path.normcase(os.path.abspath(os.path.join(path, filename))) for filename in archive_files)
                    self.log_and_output('Failed unpacking archive {archive}: {failure}', level=logging.WARNING, **{'archive': archive, 'failure': failure[0]})
                    self.missed_files.append('{0}: Unpacking failed: {1}'.format(archive, failure[1]))
                    self.result = False
                    self.succeeded = False
                    continue

            self.log_and_output('Extracted content: {unpacked_files}', level=logging.DEBUG, **{'unpacked_files': unpacked_files})

        return unpacked_files

    def already_postprocessed(self, video_file):
        """
        Check if we already post-processed an auto snatched file.

        :param video_file: File name
        :return:
        """
        # Match complete filenames or qualified path suffixes, treating wildcards literally.
        history_name = video_file.replace('!', '!!').replace('%', '!%').replace('_', '!_')
        main_db_con = db.DBConnection()
        history_result = main_db_con.select(
            'SELECT showid, season, episode, indexer_id '
            'FROM history '
            'WHERE action = ? '
            "AND (resource LIKE ? ESCAPE '!' "
            "OR resource LIKE ? ESCAPE '!' "
            "OR resource LIKE ? ESCAPE '!') "
            'ORDER BY date DESC',
            [DOWNLOADED, history_name, '%/' + history_name, '%\\' + history_name])

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
        :param video_files: MediaFile candidates, including their history lookup names
        :param force: Postprocess currently postprocessing file
        :param is_priority: Boolean, is this a priority download
        :param ignore_subs: True to ignore setting 'postpone if no subs'
        """
        # Keep flag for a single media process.
        # A path can have multiple media to process.
        self.postpone_processing = False

        for media in video_files:
            video = media.name
            file_path = os.path.join(path, video)
            media_path = os.path.normcase(os.path.abspath(file_path))
            if media_path in self._incomplete_archive_members:
                self.log_and_output('Skipping incomplete archive member: {file_path}', level=logging.DEBUG,
                                    **{'file_path': file_path})
                continue
            # Directory traversal can rediscover retained archive members.
            if media_path in self._processed_media:
                self.log_and_output('Skipping file already processed in this run: {file_path}',
                                    level=logging.DEBUG, **{'file_path': file_path})
                continue

            if not force and self.already_postprocessed(media.history_name):
                self.log_and_output('Skipping already processed file: {video}', level=logging.DEBUG, **{'video': video})
                continue

            try:
                processor = post_processor.PostProcessor(file_path, self.resource_name,
                                                         self.process_method, is_priority)

                if app.POSTPONE_IF_NO_SUBS and self.process_single_resource:
                    if not self._process_postponed(processor, file_path, video, ignore_subs):
                        raise EpisodePostProcessingPostponedException(
                            f'Postponing processing for file path {file_path} and resource {self.resource_name}'
                        )

                self.result = processor.process()
                if self.result:
                    self._processed_media.add(media_path)
                    if processor.info_hash in app.RECENTLY_POSTPROCESSED:
                        self._processed_torrent_hashes.add(processor.info_hash)
                process_fail_message = ''
            except EpisodePostProcessingFailedException as error:
                processor = None
                self.result = False
                process_fail_message = ex(error)
            except EpisodePostProcessingAbortException as error:
                processor = None
                self.result = True
                self.aborted = True
                process_fail_message = ex(error)
            except EpisodePostProcessingPostponedException as error:
                processor = None
                self.result = True
                process_fail_message = ex(error)

            if processor:
                self._output += processor._output

            if self.result:
                if self.aborted:
                    self.log_and_output('Processing aborted for {file_path}: {process_fail_message}',
                                        level=logging.WARNING, **{'file_path': file_path, 'process_fail_message': process_fail_message})
                elif self.postpone_processing:
                    self.log_and_output('Processing postponed for {file_path}: {process_fail_message}',
                                        level=logging.INFO, **{'file_path': file_path, 'process_fail_message': process_fail_message})
                else:
                    self.log_and_output('Processing succeeded for {file_path}', **{'file_path': file_path})

            else:
                self.log_and_output('Processing failed for {file_path}: {process_fail_message}',
                                    level=logging.WARNING, **{'file_path': file_path, 'process_fail_message': process_fail_message})
                self.missed_files.append('{0}: Processing failed: {1}'.format(file_path, process_fail_message))
                self.succeeded = False

                if not self.process_single_resource:
                    # If this PostprocessQueueItem wasn't started through the download handler
                    # or apiv2 we want to fail the media item right here.
                    self.process_failed(path, resource_name=video)

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
                        self.postpone_any = True
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

    def process_failed(self, path, resource_name=None):
        """Process a download that did not complete correctly."""
        if not app.USE_FAILED_DOWNLOADS:
            return

        if self._original_file_path:
            # Use the resolved file, not a remote client path or its containing folder.
            path = self._original_file_path

        resource_name = resource_name or self.resource_name
        if not resource_name and (self._original_file_path or os.path.isfile(path)):
            # A file-only request has no directory to inspect for a release name.
            # Keep the original cleanup target so siblings cannot be deleted.
            resource_name = os.path.basename(path)

        try:
            processor = failed_processor.FailedProcessor(
                path, resource_name, self.episodes
            )
            # Handling a failed download successfully does not make processing successful.
            failure_handled = processor.process()
            process_fail_message = ''
        except FailedPostProcessingFailedException as error:
            processor = None
            failure_handled = False
            process_fail_message = ex(error)

        if processor:
            self._output.append(processor.output)

        if app.DELETE_FAILED and failure_handled:
            if self.delete_folder(path, check_empty=False):
                self.log_and_output('Deleted folder: {path}', level=logging.DEBUG, **{'path': path})

        if failure_handled:
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
                parse_result = NameParser().parse(name, use_cache=False)
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
