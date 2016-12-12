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


class ProcessResult(object):  # pylint: disable=too-few-public-methods
    def __init__(self):
        self.result = True
        self.output = ''
        self.missedfiles = []
        self.aggresult = True


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
            logger.log(u"Not deleting folder %s found the following files: %s" %
                       (folder, check_files), logger.INFO)
            return False

        try:
            logger.log(u"Deleting folder (if it's empty): %s" % folder)
            os.rmdir(folder)
        except (OSError, IOError) as e:
            logger.log(u"Warning: unable to delete folder: %s: %s" % (folder, ex(e)), logger.WARNING)
            return False
    else:
        try:
            logger.log(u"Deleting folder: " + folder)
            shutil.rmtree(folder)
        except (OSError, IOError) as e:
            logger.log(u"Warning: unable to delete folder: %s: %s" % (folder, ex(e)), logger.WARNING)
            return False

    return True


def delete_files(processPath, notwantedFiles, result, force=False):
    """
    Remove files from filesystem.

    :param processPath: path to process
    :param notwantedFiles: files we do not want
    :param result: Processor results
    :param force: Boolean, force deletion, defaults to false
    """
    if not result.result and force:
        result.output += logHelper(u"Forcing deletion of files, even though last result was not successful", logger.DEBUG)
    elif not result.result:
        return

    # Delete all file not needed
    for cur_file in notwantedFiles:

        cur_file_path = os.path.join(processPath, cur_file)

        if not os.path.isfile(cur_file_path):
            continue  # Prevent error when a notwantedfiles is an associated files

        result.output += logHelper(u"Deleting file: %s" % cur_file, logger.DEBUG)

        # check first the read-only attribute
        file_attribute = os.stat(cur_file_path)[0]
        if not file_attribute & stat.S_IWRITE:
            # File is read-only, so make it writeable
            result.output += logHelper(u"Changing ReadOnly Flag for file: %s" % cur_file, logger.DEBUG)
            try:
                os.chmod(cur_file_path, stat.S_IWRITE)
            except OSError as e:
                result.output += logHelper(u"Cannot change permissions of %s: %s" %
                                           (cur_file_path, ex(e)), logger.DEBUG)
        try:
            os.remove(cur_file_path)
        except OSError as e:
            result.output += logHelper(u"Unable to delete file %s: %s" % (cur_file, e.strerror), logger.DEBUG)


def logHelper(logMessage, logLevel=logger.INFO):
    logger.log(logMessage, logLevel)
    return logMessage + u"\n"


#def OneRunPP():
#    isRunning = [False]
#
#    def decorate(func):
#        @wraps(func)
#        def func_wrapper(*args, **kargs):
#            if isRunning[0]:
#                return logHelper(u'Post processor is already running', logger.WARNING)

#            isRunning[0] = True
#            ret = func(*args, **kargs)
#            isRunning[0] = False
#            return ret
#        return func_wrapper
#    return decorate


# pylint: disable=too-many-arguments,too-many-branches,too-many-statements,too-many-locals
#@OneRunPP()
def processDir(dirName, nzbName=None, process_method=None, force=False, is_priority=None,
               delete_on=False, failed=False, proc_type="auto", ignore_subs=False):
    """
    Scan through the files in dirName and process whatever media files are found.

    :param dirName: The folder name to look in
    :param nzbName: The NZB name which resulted in this folder being downloaded
    :param process_method: Process methodo: hardlink, move, softlink, etc.
    :param force: True to postprocess already postprocessed files
    :param is_priority: Boolean for whether or not is a priority download
    :param delete_on: Boolean for whether or not it should delete files
    :param failed: Boolean for whether or not the download failed
    :param proc_type: Type of postprocessing auto or manual
    :param ignore_subs: True to ignore setting 'postpone if no subs'
    """

    result = ProcessResult()

    # if they passed us a real dir then assume it's the one we want
    if os.path.isdir(dirName):
        dirName = os.path.realpath(dirName)
        result.output += logHelper(u"Processing folder %s" % dirName, logger.DEBUG)

    # if the client and the application are not on the same machine translate the directory into a network directory
    elif all([app.TV_DOWNLOAD_DIR,
              os.path.isdir(app.TV_DOWNLOAD_DIR),
              os.path.normpath(dirName) == os.path.normpath(app.TV_DOWNLOAD_DIR)]):
        dirName = os.path.join(app.TV_DOWNLOAD_DIR, os.path.abspath(dirName).split(os.path.sep)[-1])
        result.output += logHelper(u"Trying to use folder: %s " % dirName, logger.DEBUG)

    # if we didn't find a real dir then quit
    if not os.path.isdir(dirName):
        result.output += logHelper(u"Unable to figure out what folder to process. "
                                   u"If your downloader and Medusa aren't on the same PC "
                                   u"make sure you fill out your TV download dir in the config.",
                                   logger.DEBUG)
        return result.output

    path, dirs, files = get_path_dir_files(dirName, nzbName, proc_type)

    files = [x for x in files if not is_torrent_or_nzb_file(x)]
    SyncFiles = [x for x in files if is_sync_file(x)]
    nzbNameOriginal = nzbName

    # Don't post process if files are still being synced and option is activated
    postpone = SyncFiles and app.POSTPONE_IF_SYNC_FILES

    # Warn user if 'postpone if no subs' is enabled. Will debug possible user issues with PP
    if app.POSTPONE_IF_NO_SUBS:
        result.output += logHelper(u"Feature 'postpone post-processing if no subtitle available' is enabled", logger.INFO)

    if not postpone:
        result.output += logHelper(u"PostProcessing Path: %s" % path, logger.INFO)
        result.output += logHelper(u"PostProcessing Dirs: %s" % str(dirs), logger.DEBUG)

        videoFiles = [x for x in files if helpers.is_media_file(x)]
        rarFiles = [x for x in files if helpers.is_rar_file(x)]
        rarContent = ""
        if rarFiles and not (app.POSTPONE_IF_NO_SUBS and videoFiles):
            # Unpack only if video file was not already extracted by 'postpone if no subs' feature
            rarContent = unRAR(path, rarFiles, force, result)
            files += rarContent
            videoFiles += [x for x in rarContent if helpers.is_media_file(x)]
        videoInRar = [x for x in rarContent if helpers.is_media_file(x)] if rarContent else ''

        result.output += logHelper(u"PostProcessing Files: %s" % files, logger.DEBUG)
        result.output += logHelper(u"PostProcessing VideoFiles: %s" % videoFiles, logger.DEBUG)
        result.output += logHelper(u"PostProcessing RarContent: %s" % rarContent, logger.DEBUG)
        result.output += logHelper(u"PostProcessing VideoInRar: %s" % videoInRar, logger.DEBUG)

        # If nzbName is set and there's more than one videofile in the folder, files will be lost (overwritten).
        nzbName = None if len(videoFiles) >= 2 else nzbName

        process_method = process_method if process_method else app.PROCESS_METHOD
        result.result = True

        # Don't Link media when the media is extracted from a rar in the same path
        if process_method in (u'hardlink', u'symlink') and videoInRar:
            process_media(path, videoInRar, nzbName, u'move', force, is_priority, ignore_subs, result)
            delete_files(path, rarContent, result)
            for video in set(videoFiles) - set(videoInRar):
                process_media(path, [video], nzbName, process_method, force, is_priority, ignore_subs, result)
        elif app.DELRARCONTENTS and videoInRar:
            process_media(path, videoInRar, nzbName, process_method, force, is_priority, ignore_subs, result)
            delete_files(path, rarContent, result, True)
            for video in set(videoFiles) - set(videoInRar):
                process_media(path, [video], nzbName, process_method, force, is_priority, ignore_subs, result)
        else:
            for video in videoFiles:
                process_media(path, [video], nzbName, process_method, force, is_priority, ignore_subs, result)

    else:
        result.output += logHelper(u"Found temporary sync files: %s in path: %s" % (SyncFiles, path))
        result.output += logHelper(u"Skipping post processing for folder: %s" % path)
        result.missedfiles.append(u"%s : Syncfiles found" % path)

    # Process Video File in all TV Subdir
    for curDir in [x for x in dirs if validateDir(path, x, nzbNameOriginal, failed, result)]:
        result.result = True

        for processPath, _, fileList in os.walk(os.path.join(path, curDir), topdown=False):

            if not validateDir(path, processPath, nzbNameOriginal, failed, result):
                continue

            SyncFiles = [x for x in fileList if is_sync_file(x)]

            # Don't post process if files are still being synced and option is activated
            postpone = SyncFiles and app.POSTPONE_IF_SYNC_FILES

            if not postpone:
                videoFiles = [x for x in fileList if helpers.is_media_file(x)]
                rarFiles = [x for x in fileList if helpers.is_rar_file(x)]
                rarContent = ""
                if rarFiles and not (app.POSTPONE_IF_NO_SUBS and videoFiles):
                    # Unpack only if video file was not already extracted by 'postpone if no subs' feature
                    rarContent = unRAR(processPath, rarFiles, force, result)
                    fileList = set(fileList + rarContent)
                    videoFiles += [x for x in rarContent if helpers.is_media_file(x)]

                videoInRar = [x for x in rarContent if helpers.is_media_file(x)] if rarContent else ''
                notwantedFiles = [x for x in fileList if x not in videoFiles]
                if notwantedFiles:
                    result.output += logHelper(u"Found unwanted files: %s" % notwantedFiles, logger.DEBUG)

                # Don't Link media when the media is extracted from a rar in the same path
                if process_method in (u'hardlink', u'symlink') and videoInRar:
                    process_media(processPath, videoInRar, nzbName, u'move', force, is_priority, ignore_subs, result)
                    process_media(processPath, set(videoFiles) - set(videoInRar), nzbName, process_method, force,
                                  is_priority, ignore_subs, result)
                    delete_files(processPath, rarContent, result)
                elif app.DELRARCONTENTS and videoInRar:
                    process_media(processPath, videoInRar, nzbName, process_method, force, is_priority, ignore_subs, result)
                    process_media(processPath, set(videoFiles) - set(videoInRar), nzbName, process_method, force,
                                  is_priority, ignore_subs, result)
                    delete_files(processPath, rarContent, result, True)
                else:
                    process_media(processPath, videoFiles, nzbName, process_method, force, is_priority, ignore_subs, result)

                    # Delete all file not needed and avoid deleting files if Manual PostProcessing
                    if not(process_method == u"move" and result.result) or (proc_type == u"manual" and not delete_on):
                        continue

                    delete_folder(os.path.join(processPath, u'@eaDir'))
                    delete_files(processPath, notwantedFiles, result)

                    if all([not app.NO_DELETE or proc_type == u"manual",
                            process_method == u"move",
                            os.path.normpath(processPath) != os.path.normpath(app.TV_DOWNLOAD_DIR)]):

                        if delete_folder(processPath, check_empty=True):
                            result.output += logHelper(u"Deleted folder: %s" % processPath, logger.DEBUG)

            else:
                result.output += logHelper(u"Found temporary sync files: %s in path: %s" % (SyncFiles, processPath))
                result.output += logHelper(u"Skipping post processing for folder: %s" % processPath)
                result.missedfiles.append(u"%s : Syncfiles found" % path)

    if result.aggresult:
        result.output += logHelper(u"Successfully processed")

        # Clean library from KODI after PP ended
        if app.KODI_LIBRARY_CLEAN_PENDING and notifiers.kodi_notifier.clean_library():
            app.KODI_LIBRARY_CLEAN_PENDING = False

        if result.missedfiles:
            result.output += logHelper(u"I did encounter some unprocessable items: ")
            for missedfile in result.missedfiles:
                result.output += logHelper(u"[%s]" % missedfile)
    else:
        result.output += logHelper(u"Problem(s) during processing, failed the following files/folders: ", logger.WARNING)
        for missedfile in result.missedfiles:
            result.output += logHelper(u"[%s]" % missedfile, logger.WARNING)

    return result.output


def validateDir(path, dirName, nzbNameOriginal, failed, result):
    """
    Check if directory is valid for processing.

    :param path: Path to use
    :param dirName: Directory to check
    :param nzbNameOriginal: Original NZB name
    :param failed: Previously failed objects
    :param result: Previous results
    :return: True if dir is valid for processing, False if not
    """
    dirName = ss(dirName)

    IGNORED_FOLDERS = [u'.AppleDouble', u'.@__thumb', u'@eaDir']
    folder_name = os.path.basename(dirName)
    if folder_name in IGNORED_FOLDERS:
        return False

    result.output += logHelper(u"Processing folder " + dirName, logger.DEBUG)

    if folder_name.startswith(u'_FAILED_'):
        result.output += logHelper(u"The directory name indicates it failed to extract.", logger.DEBUG)
        failed = True
    elif folder_name.startswith(u'_UNDERSIZED_'):
        result.output += logHelper(u"The directory name indicates that it was previously rejected for being undersized.", logger.DEBUG)
        failed = True
    elif folder_name.upper().startswith(u'_UNPACK'):
        result.output += logHelper(u"The directory name indicates that this release is in the process of being unpacked.", logger.DEBUG)
        result.missedfiles.append(u"%s : Being unpacked" % dirName)
        return False

    if failed:
        process_failed(os.path.join(path, dirName), nzbNameOriginal, result)
        result.missedfiles.append(u"%s : Failed download" % dirName)
        return False

    if helpers.is_hidden_folder(os.path.join(path, dirName)):
        result.output += logHelper(u"Ignoring hidden folder: %s" % dirName, logger.DEBUG)
        result.missedfiles.append(u"%s : Hidden folder" % dirName)
        return False

    # make sure the dir isn't inside a show dir
    main_db_con = db.DBConnection()
    sql_results = main_db_con.select("SELECT location FROM tv_shows")

    for sqlShow in sql_results:
        if dirName.lower().startswith(os.path.realpath(sqlShow["location"]).lower() + os.sep) or \
                dirName.lower() == os.path.realpath(sqlShow["location"]).lower():

            result.output += logHelper(
                u"Cannot process an episode that's already been moved to its show dir, skipping " + dirName,
                logger.WARNING)
            return False

    # Get the videofile list for the next checks
    allFiles = []
    allDirs = []
    for _, processdir, fileList in os.walk(os.path.join(path, dirName), topdown=False):
        allDirs += processdir
        allFiles += fileList

    videoFiles = [x for x in allFiles if helpers.is_media_file(x)]
    allDirs.append(dirName)

    # check if the dir have at least one tv video file
    for video in videoFiles:
        try:
            NameParser().parse(video, cache_result=False)
            return True
        except (InvalidNameException, InvalidShowException) as error:
            result.output += logHelper(u"{}".format(error), logger.DEBUG)

    for proc_dir in allDirs:
        try:
            NameParser().parse(proc_dir, cache_result=False)
            return True
        except (InvalidNameException, InvalidShowException) as error:
            result.output += logHelper(u"{}".format(error), logger.DEBUG)

    if app.UNPACK:
        # Search for packed release
        packedFiles = [x for x in allFiles if helpers.is_rar_file(x)]

        for packed in packedFiles:
            try:
                NameParser().parse(packed, cache_result=False)
                return True
            except (InvalidNameException, InvalidShowException) as error:
                result.output += logHelper(u"{}".format(error), logger.DEBUG)

    result.output += logHelper(u"%s : No processable items found in the folder" % dirName, logger.DEBUG)
    return False


def unRAR(path, rarFiles, force, result):
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

        result.output += logHelper(u"Packed releases detected: %s" % rarFiles, logger.DEBUG)

        for archive in rarFiles:

            result.output += logHelper(u"Unpacking archive: %s" % archive, logger.DEBUG)

            failure = None
            try:
                rar_handle = RarFile(os.path.join(path, archive))

                # Skip extraction if any file in archive has previously been extracted
                skip_file = False
                for file_in_archive in [os.path.basename(x.filename) for x in rar_handle.infolist() if not x.isdir]:
                    if already_postprocessed(path, file_in_archive, force, result):
                        result.output += logHelper(u"Archive file already post-processed, extraction skipped: %s" %
                                                   file_in_archive, logger.DEBUG)
                        skip_file = True
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
                result.output += logHelper(u'Failed Unrar archive {}: {}'.format(archive, failure[0]), logger.WARNING)
                result.missedfiles.append(u'{} : Unpacking failed: {}'.format(archive, failure[1]))
                result.result = False
                continue

        result.output += logHelper(u"UnRar content: %s" % unpacked_files, logger.DEBUG)

    return unpacked_files


def already_postprocessed(dir_name, video_file, force, result):
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
        result.output += logHelper(u"You're trying to post-process a file that has already "
                                   u"been processed, skipping: {0}".format(video_file), logger.DEBUG)
        return True

    return False


def process_media(processPath, videoFiles, nzbName, process_method, force, is_priority, ignore_subs, result):
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

        if already_postprocessed(processPath, cur_video_file, force, result):
            result.output += logHelper(u"Skipping already processed file: %s" % cur_video_file, logger.DEBUG)
            result.output += logHelper(u"Skipping already processed dir: %s" % processPath, logger.DEBUG)
            continue

        try:
            processor = post_processor.PostProcessor(cur_video_file_path, nzbName, process_method, is_priority)

            # This feature prevents PP for files that do not have subtitle associated with the video file
            if app.POSTPONE_IF_NO_SUBS:
                if not ignore_subs:
                    if subtitles_enabled(cur_video_file_path, nzbName):
                        embedded_subs = set() if app.IGNORE_EMBEDDED_SUBS else get_embedded_subtitles(cur_video_file_path)

                        # If user don't want to ignore embedded subtitles and video has at least one, don't post pone PP
                        if accept_unknown(embedded_subs):
                            result.output += logHelper(u"Found embedded unknown subtitles and we don't want to ignore them. "
                                                       u"Continuing the post-process of this file: %s" % cur_video_file)
                        elif accept_any(embedded_subs):
                            result.output += logHelper(u"Found wanted embedded subtitles. "
                                                       u"Continuing the post-process of this file: %s" % cur_video_file)
                        else:
                            associated_files = processor.list_associated_files(cur_video_file_path, subtitles_only=True)
                            if not [f for f in associated_files if f[-3:] in subtitle_extensions]:
                                result.output += logHelper(u"No subtitles associated. Postponing the post-process of this file:"
                                                           u" %s" % cur_video_file, logger.DEBUG)
                                continue
                            else:
                                result.output += logHelper(u"Found subtitles associated. "
                                                           u"Continuing the post-process of this file: %s" % cur_video_file)
                    else:
                        result.output += logHelper(u"Subtitles disabled for this show. "
                                                   u"Continuing the post-process of this file: %s" % cur_video_file)
                else:
                    result.output += logHelper(u"Subtitles check was disabled for this episode in Manual PP. "
                                               u"Continuing the post-process of this file: %s" % cur_video_file)

            result.result = processor.process()
            process_fail_message = u""
        except EpisodePostProcessingFailedException as e:
            result.result = False
            process_fail_message = ex(e)

        if processor:
            result.output += processor.log

        if result.result:
            result.output += logHelper(u"Processing succeeded for %s" % cur_video_file_path)
        else:
            result.output += logHelper(u"Processing failed for %s: %s" % (cur_video_file_path, process_fail_message), logger.WARNING)
            result.missedfiles.append(u"%s : Processing failed: %s" % (cur_video_file_path, process_fail_message))
            result.aggresult = False


def get_path_dir_files(dirName, nzbName, proc_type):
    """
    Get files in a path

    :param dirName: Directory to start in
    :param nzbName: NZB file, if present
    :param proc_type: auto/manual
    :return: a tuple of (path,dirs,files)
    """
    path = u""
    dirs = []
    files = []

    if dirName == app.TV_DOWNLOAD_DIR and not nzbName or proc_type == u"manual":  # Scheduled Post Processing Active
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


def process_failed(dirName, nzbName, result):
    """Process a download that did not complete correctly."""
    if app.USE_FAILED_DOWNLOADS:
        processor = None

        try:
            processor = failed_processor.FailedProcessor(dirName, nzbName)
            result.result = processor.process()
            process_fail_message = u""
        except FailedPostProcessingFailedException as e:
            result.result = False
            process_fail_message = ex(e)

        if processor:
            result.output += processor.log

        if app.DELETE_FAILED and result.result:
            if delete_folder(dirName, check_empty=False):
                result.output += logHelper(u"Deleted folder: %s" % dirName, logger.DEBUG)

        if result.result:
            result.output += logHelper(u"Failed Download Processing succeeded: (%s, %s)" % (nzbName, dirName))
        else:
            result.output += logHelper(u"Failed Download Processing failed: (%s, %s): %s" %
                                       (nzbName, dirName, process_fail_message), logger.WARNING)


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
                return bool(sql_results[0]["subtitles"]) if sql_results else False

            logger.log(u'Empty indexer ID for: {name}'.format(name=name), logger.WARNING)
        except (InvalidNameException, InvalidShowException):
            logger.log(u'Not enough information to parse filename into a valid show. Consider adding scene exceptions '
                       u'or improve naming for: {name}'.format(name=name), logger.WARNING)
    return False
