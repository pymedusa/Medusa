# coding=utf-8
# Author: medariox <dariox@gmx.com>,
# based on Antoine Bertin's <diaoulael@gmail.com> work
# and originally written by Nyaran <nyayukko@gmail.com>
# URL: https://github.com/PyMedusa/SickRage/
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.

import os
import re
import datetime
import operator
import traceback
import subprocess
import sickbeard
from babelfish import Language, language_converters
from subliminal import (compute_score, ProviderPool, provider_manager, refiner_manager, refine, region, save_subtitles,
                        scan_video)
from subliminal.core import search_external_subtitles
from subliminal.score import episode_scores
from subliminal.subtitle import get_subtitle_path
from sickbeard import logger
from sickbeard import history
from sickbeard import db
from sickbeard import processTV
from sickbeard.helpers import remove_non_release_groups, isMediaFile, isRarFile
from sickrage.helper.common import episode_num, dateTimeFormat, subtitle_extensions
from sickrage.helper.exceptions import ex
from sickrage.show.Show import Show

PROVIDER_POOL_EXPIRATION_TIME = datetime.timedelta(minutes=15).total_seconds()
VIDEO_EXPIRATION_TIME = datetime.timedelta(days=1).total_seconds()

provider_manager.register('itasa = subliminal.providers.itasa:ItaSAProvider')
provider_manager.register('legendastv = subliminal.providers.legendastv:LegendasTvProvider')
provider_manager.register('napiprojekt = subliminal.providers.napiprojekt:NapiProjektProvider')

refiner_manager.register('release = sickbeard.refiners.release:refine')

region.configure('dogpile.cache.memory')

episode_refiners = ('metadata', 'release', 'tvdb', 'omdb')

PROVIDER_URLS = {
    'addic7ed': 'http://www.addic7ed.com',
    'itasa': 'http://www.italiansubs.net',
    'legendastv': 'http://www.legendas.tv',
    'napiprojekt': 'http://www.napiprojekt.pl',
    'opensubtitles': 'http://www.opensubtitles.org',
    'podnapisi': 'http://www.podnapisi.net',
    'shooter': 'http://www.shooter.cn',
    'subscenter': 'http://www.subscenter.org',
    'thesubdb': 'http://www.thesubdb.com',
    'tvsubtitles': 'http://www.tvsubtitles.net'
}


def sorted_service_list():
    """Returns an list of subliminal providers (it's not sorted, but the order matters!)

    Each item in the list is a dict containing:
        name: str: provider name
        url: str: provider url
        image: str: provider image
        enabled: bool: whether the provider is enabled or not

    :return: a list of subliminal providers.
    :rtype: list of dict
    """
    new_list = []
    lmgtfy = 'http://lmgtfy.com/?q=%s'

    current_index = 0
    for current_service in sickbeard.SUBTITLES_SERVICES_LIST:
        if current_service in provider_manager.names():
            new_list.append({'name': current_service,
                             'url': PROVIDER_URLS[current_service]
                             if current_service in PROVIDER_URLS else lmgtfy % current_service,
                             'image': current_service + '.png',
                             'enabled': sickbeard.SUBTITLES_SERVICES_ENABLED[current_index] == 1})
        current_index += 1

    for current_service in provider_manager.names():
        if current_service not in [service['name'] for service in new_list]:
            new_list.append({'name': current_service,
                             'url': PROVIDER_URLS[current_service]
                             if current_service in PROVIDER_URLS else lmgtfy % current_service,
                             'image': current_service + '.png',
                             'enabled': False})
    return new_list


def enabled_service_list():
    """Returns an ordered list of enabled and valid subliminal provider names

    :return: list of provider names
    :rtype: list of str
    """
    return [service['name'] for service in sorted_service_list() if service['enabled']]


def wanted_languages():
    """Returns the wanted language codes

    :return: set of wanted subtitles (opensubtitles codes)
    :rtype: frozenset
    """
    return frozenset(sickbeard.SUBTITLES_LANGUAGES).intersection(subtitle_code_filter())


def get_needed_languages(subtitles):
    """Given the existing subtitles, returns a set of the needed subtitles

    :param subtitles: the existing subtitles (opensubtitles codes)
    :type subtitles: set of str
    :return: the needed subtitles
    :rtype: set of babelfish.Language
    """
    if not sickbeard.SUBTITLES_MULTI:
        return set() if 'und' in subtitles else {from_code(language) for language in wanted_languages()}
    return {from_code(language) for language in wanted_languages().difference(subtitles)}


def subtitle_code_filter():
    """Returns a set of all 3-letter code languages of opensubtitles

    :return: all 3-letter language codes
    :rtype: set of str
    """
    return {code for code in language_converters['opensubtitles'].codes if len(code) == 3}


def needs_subtitles(subtitles):
    """Given the existing subtitles and wanted languages, returns True if subtitles are still needed

    :param subtitles: the existing subtitles
    :type subtitles: set of str
    :return: True if subtitles are needed
    :rtype: bool
    """
    wanted = wanted_languages()
    if not wanted:
        return False

    if isinstance(subtitles, basestring):
        subtitles = {subtitle.strip() for subtitle in subtitles.split(',') if subtitle.strip()}

    if sickbeard.SUBTITLES_MULTI:
        return wanted.difference(subtitles)

    return 'und' not in subtitles


def from_code(code, unknown='und'):
    """Converts an opensubtitles language code to a proper babelfish.Language object

    :param code: an opensubtitles language code to be converted
    :type code: str
    :param unknown: the code to be returned for unknown language codes
    :type unknown: str
    :return: a language object
    :rtype: babelfish.Language
    """
    code = code.strip()
    if code and code in language_converters['opensubtitles'].codes:
        return Language.fromopensubtitles(code)  # pylint: disable=no-member

    return Language(unknown) if unknown else None


def from_ietf_code(code, unknown='und'):
    """Converts an IETF code to a proper babelfish.Language object

    :param code: an IETF language code
    :type code: str
    :param unknown: the code to be returned for unknown language codes
    :type unknown: str
    :return: a language object
    :rtype: babelfish.Language
    """
    try:
        return Language.fromietf(code)
    except ValueError:
        return Language(unknown) if unknown else None


def name_from_code(code):
    """Returns the language name for the given language code

    :param code: the opensubtitles language code
    :type code: str
    :return: the language name
    :rtype: str
    """
    return from_code(code).name


def code_from_code(code):
    """Converts an opensubtitles code to a 3-letter opensubtitles code

    :param code: an opensubtitles language code
    :type code: str
    :return: a 3-letter opensubtitles language code
    :rtype: str
    """

    return from_code(code).opensubtitles


def download_subtitles(video_path, show_name, season, episode, episode_name, show_indexerid, release_name, status,
                       existing_subtitles):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
    """Downloads missing subtitles for the given episode

    Checks whether subtitles are needed or not

    :param video_path: the video path
    :type video_path: str
    :param show_name: the show name
    :type show_name: str
    :param season: the season number
    :type season: int
    :param episode: the episode number
    :type episode: int
    :param episode_name: the episode name
    :type episode_name: str
    :param show_indexerid: the show indexerid
    :type show_indexerid: int
    :param release_name: the release name
    :type release_name: str
    :param status: the show status
    :type status: int
    :param existing_subtitles: list of existing subtitles (opensubtitles codes)
    :type existing_subtitles: list of str
    :return: a sorted list of the opensubtitles codes for the downloaded subtitles
    :rtype: list of str
    """
    ep_num = episode_num(season, episode) or episode_num(season, episode, numbering='absolute')
    languages = get_needed_languages(existing_subtitles)

    if not languages:
        logger.log(u'Episode already has all needed subtitles, skipping {0} {1}'.format
                   (show_name, ep_num), logger.DEBUG)
        return list()

    logger.log(u'Checking subtitle candidates for {0} {1} ({2})'.format
               (show_name, ep_num, os.path.basename(video_path)), logger.DEBUG)

    subtitles_dir = get_subtitles_dir(video_path)
    found_subtitles = download_best_subs(video_path, subtitles_dir, release_name, languages)

    for subtitle in found_subtitles:
        if sickbeard.SUBTITLES_EXTRA_SCRIPTS and isMediaFile(video_path):
            subtitle_path = compute_subtitle_path(subtitle, video_path, subtitles_dir)
            run_subs_extra_scripts(video_path=video_path, subtitle_path=subtitle_path,
                                   subtitle_language=subtitle.language, show_name=show_name, season=season,
                                   episode=episode, episode_name=episode_name, show_indexerid=show_indexerid)
        if sickbeard.SUBTITLES_HISTORY:
            logger.log(u'history.logSubtitle {0}, {1}'.format
                       (subtitle.provider_name, subtitle.language.opensubtitles), logger.DEBUG)
            history.logSubtitle(show_indexerid, season, episode, status, subtitle)

    return sorted({subtitle.language.opensubtitles for subtitle in found_subtitles})


def download_best_subs(video_path, subtitles_dir, release_name, languages, subtitles=True, embedded_subtitles=True,
                       provider_pool=None):
    """Downloads the best subtitle for the given video

    :param video_path: the video path
    :type video_path: str
    :param subtitles_dir: the subtitles directory
    :type subtitles_dir: str
    :param release_name: the release name for the given video
    :type release_name: str
    :param languages: the needed languages
    :type languages: set of babelfish.Language
    :param subtitles: True if existing external subtitles should be taken into account
    :type subtitles: bool
    :param embedded_subtitles: True if embedded subtitles should be taken into account
    :type embedded_subtitles: bool
    :param provider_pool: provider pool to be used
    :type provider_pool: subliminal.ProviderPool
    :return: the downloaded subtitles
    :rtype: list of subliminal.subtitle.Subtitle
    """
    try:
        video = get_video(video_path, subtitles_dir=subtitles_dir, subtitles=subtitles,
                          embedded_subtitles=embedded_subtitles, release_name=release_name)

        if not video:
            logger.log(u'Exception caught in subliminal.scan_video for {0}'.format(video_path), logger.DEBUG)
            return list()

        pool = provider_pool or get_provider_pool()

        if sickbeard.SUBTITLES_PRE_SCRIPTS:
            run_subs_pre_scripts(video_path)

        subtitles_list = pool.list_subtitles(video, languages)
        for provider in pool.providers:
            if provider in pool.discarded_providers:
                logger.log(u'Could not search in {0} provider. Discarding for now'.format(provider), logger.DEBUG)

        if not subtitles_list:
            logger.log(u'No subtitles found for {0}'.format(video_path))
            return list()

        min_score = get_min_score()
        scored_subtitles = sorted([(s, compute_score(s, video, hearing_impaired=sickbeard.SUBTITLES_HEARING_IMPAIRED))
                                  for s in subtitles_list], key=operator.itemgetter(1), reverse=True)
        for subtitle, score in scored_subtitles:
            logger.log(u'[{0:>13s}:{1:<5s}] score = {2:3d}/{3:3d} for {4}'.format
                       (subtitle.provider_name, subtitle.language, score, min_score,
                        get_subtitle_description(subtitle)), logger.DEBUG)

        found_subtitles = pool.download_best_subtitles(subtitles_list, video, languages=languages,
                                                       hearing_impaired=sickbeard.SUBTITLES_HEARING_IMPAIRED,
                                                       min_score=min_score, only_one=not sickbeard.SUBTITLES_MULTI)

        if not found_subtitles:
            logger.log(u'No subtitles found for {0} with min_score {1}'.format(video_path, min_score))
            return list()

        save_subtitles(video, found_subtitles, directory=subtitles_dir, single=not sickbeard.SUBTITLES_MULTI)

        for subtitle in found_subtitles:
            logger.log(u'Found subtitle for {0} in {1} provider with language {2}'.format
                       (video_path, subtitle.provider_name, subtitle.language.opensubtitles), logger.INFO)
            subtitle_path = compute_subtitle_path(subtitle, video_path, subtitles_dir)

            sickbeard.helpers.chmodAsParent(subtitle_path)
            sickbeard.helpers.fixSetGroupID(subtitle_path)

        return found_subtitles
    except IOError as error:
        if 'No space left on device' in ex(error):
            logger.log(u'Not enough space on the drive to save subtitles', logger.WARNING)
        else:
            logger.log(traceback.format_exc(), logger.WARNING)
    except Exception as error:
        logger.log(u'Exception: {0}'.format(error), logger.DEBUG)
        logger.log(u'Error occurred when downloading subtitles for: {0}'.format(video_path))
        logger.log(traceback.format_exc(), logger.ERROR)

    return list()


@region.cache_on_arguments(expiration_time=PROVIDER_POOL_EXPIRATION_TIME)
def get_provider_pool():
    """Returns the subliminal provider pool to be used

    :return: subliminal provider pool to be used
    :rtype: subliminal.ProviderPool
    """
    logger.log(u'Creating a new ProviderPool instance', logger.DEBUG)
    provider_configs = {'addic7ed': {'username': sickbeard.ADDIC7ED_USER,
                                     'password': sickbeard.ADDIC7ED_PASS},
                        'itasa': {'username': sickbeard.ITASA_USER,
                                  'password': sickbeard.ITASA_PASS},
                        'legendastv': {'username': sickbeard.LEGENDASTV_USER,
                                       'password': sickbeard.LEGENDASTV_PASS},
                        'opensubtitles': {'username': sickbeard.OPENSUBTITLES_USER,
                                          'password': sickbeard.OPENSUBTITLES_PASS}}
    return ProviderPool(providers=enabled_service_list(), provider_configs=provider_configs)


def compute_subtitle_path(subtitle, video_path, subtitles_dir):
    """Returns the full subtitle path that's computed by subliminal

    :param subtitle: the subtitle
    :type subtitle: subliminal.Subtitle
    :param video_path: the video path
    :type video_path: str
    :param subtitles_dir: the subtitles directory
    :type subtitles_dir: str
    :return: the computed subtitles path
    :rtype: str
    """
    subtitle_path = get_subtitle_path(video_path, subtitle.language if sickbeard.SUBTITLES_MULTI else None)
    return os.path.join(subtitles_dir, os.path.split(subtitle_path)[1]) if subtitles_dir else subtitle_path


def merge_subtitles(existing_subtitles, new_subtitles):
    """Merges the existing and new subtitles to a single list

    Consolidates the existing_subtitles and the new_subtitles into a resulting list without repetitions. If
    SUBTITLES_MULTI is disabled and there's only one new subtitle, an `und` element is added to the returning list
    instead of using the new_subtitles.

    :param existing_subtitles: list: opensubtitles codes of the existing subtitles
    :type existing_subtitles: list of str
    :param new_subtitles: list: opensubtitles codes of the new subtitles
    :type new_subtitles: list of str
    :return: list of opensubtitles codes of the resulting subtitles
    :rtype: list of str
    """
    current_subtitles = sorted(
        {subtitle for subtitle in new_subtitles + existing_subtitles}) if existing_subtitles else new_subtitles

    if not sickbeard.SUBTITLES_MULTI and len(new_subtitles) == 1:
        current_subtitles.remove(new_subtitles[0])
        current_subtitles.append('und')

    return current_subtitles


def get_min_score():
    """Returns the min score to be used by subliminal

    Perfect match = hash - resolution (subtitle for 720p is the same as for 1080p) - video_codec - audio_codec
    Non-perfect match = series + year + season + episode

    :return: min score to be used to download subtitles
    :rtype: int
    """
    if sickbeard.SUBTITLES_PERFECT_MATCH:
        return episode_scores['hash'] - (episode_scores['resolution'] +
                                         episode_scores['video_codec'] +
                                         episode_scores['audio_codec'])

    return episode_scores['series'] + episode_scores['year'] + episode_scores['season'] + episode_scores['episode']


def get_current_subtitles(video_path):
    """Returns a list of current subtitles for the episode

    :param video_path: the video path
    :type video_path: str
    :return: the current subtitles (3-letter opensubtitles codes) for the specified video
    :rtype: list of str
    """
    video = get_video(video_path)
    if not video:
        logger.log(u"Exception caught in subliminal.scan_video, subtitles couldn't be refreshed", logger.DEBUG)
    else:
        return get_subtitles(video)


def encode(value, encoding='utf-8', fallback=None):
    """Encodes the value using the specified encoding

    It fallbacks to the specified encoding or SYS_ENCODING if not defined

    :param value: the value to be encoded
    :type value: str
    :param encoding: the encoding to be used
    :type encoding: str
    :param fallback: the fallback encoding to be used
    :type fallback: str
    :return: the encoded value
    :rtype: str
    """
    try:
        return value.encode(encoding)
    except UnicodeEncodeError:
        return value.encode(fallback or sickbeard.SYS_ENCODING)


def get_subtitle_description(subtitle):
    """Returns a human readable name/description for the given subtitle (if possible)

    :param subtitle: the given subtitle
    :type subtitle: subliminal.Subtitle
    :return: name/description
    :rtype: str
    """
    desc = None
    if hasattr(subtitle, 'filename') and subtitle.filename:
        desc = subtitle.filename.lower()
    elif hasattr(subtitle, 'name') and subtitle.name:
        desc = subtitle.name.lower()
    if hasattr(subtitle, 'release') and subtitle.release:
        desc = subtitle.release.lower()
    if hasattr(subtitle, 'releases') and subtitle.releases:
        desc = str(subtitle.releases).lower()

    if not desc:
        desc = subtitle.id

    return subtitle.id + '-' + desc if desc not in subtitle.id else desc


def get_video(video_path, subtitles_dir=None, subtitles=True, embedded_subtitles=None, release_name=None):
    """Returns the subliminal video for the given path

    :param video_path: the video path
    :type video_path: str
    :param subtitles_dir: the subtitles directory
    :type subtitles_dir: str
    :param subtitles: True if existing external subtitles should be taken into account
    :type subtitles: bool
    :param embedded_subtitles: True if embedded subtitles should be taken into account
    :type embedded_subtitles: bool
    :param release_name: the release name
    :type release_name: str
    :return: video
    :rtype: subliminal.video
    """
    return _get_video(video_path, subtitles_dir, subtitles, embedded_subtitles, release_name)


@region.cache_on_arguments(expiration_time=VIDEO_EXPIRATION_TIME)  # Should we provide a way to invalidate this cache?
def _get_video(video_path, subtitles_dir, subtitles, embedded_subtitles, release_name):
    """Internal get_video method since dogpile cache default function_key_generator doesn't accept keyword arguments
    """
    try:
        video_path = encode(video_path)
        subtitles_dir = encode(subtitles_dir or get_subtitles_dir(video_path))

        logger.log(u'Scanning video {0}...'.format(video_path), logger.DEBUG)
        video = scan_video(video_path)

        # external subtitles
        if subtitles:
            video.subtitle_languages |= set(search_external_subtitles(video_path, directory=subtitles_dir).values())

        if embedded_subtitles is None:
            embedded_subtitles = bool(not sickbeard.EMBEDDED_SUBTITLES_ALL and video_path.endswith('.mkv'))

        refine(video, episode_refiners=episode_refiners, embedded_subtitles=embedded_subtitles,
               release_name=release_name)
        return video
    except Exception as error:
        logger.log(u'Exception: {0}'.format(error), logger.DEBUG)


def get_subtitles_dir(video_path):
    """Returns the correct subtitles directory based on the user configuration.

    If the directory doesn't exist, it will be created

    :param video_path: the video path
    :type video_path: str
    :return: the subtitles directory
    :rtype: str
    """
    if not sickbeard.SUBTITLES_DIR:
        return os.path.dirname(video_path)

    if os.path.isabs(sickbeard.SUBTITLES_DIR):
        return sickbeard.SUBTITLES_DIR

    new_subtitles_path = os.path.join(os.path.dirname(video_path), sickbeard.SUBTITLES_DIR)
    if sickbeard.helpers.makeDir(new_subtitles_path):
        sickbeard.helpers.chmodAsParent(new_subtitles_path)
    else:
        logger.log(u'Unable to create subtitles folder {0}'.format(new_subtitles_path), logger.WARNING)

    return new_subtitles_path


def get_subtitles(video):
    """Returns a sorted list of detected subtitles for the given video file.

    :param video: the video to be inspected
    :type video: subliminal.video
    :return: sorted list of opensubtitles code for the given video
    :rtype: list of str
    """
    result_list = [l.opensubtitles for l in video.subtitle_languages if hasattr(l, 'opensubtitles') and l.opensubtitles]
    return sorted(result_list)


def unpack_rar_files(dirpath):
    """Unpacks any existing rar files present in the specified dirpath

    :param dirpath: the directory path to be used
    :type dirpath: str
    """
    for root, _, files in os.walk(dirpath, topdown=False):
        rar_files = [rar_file for rar_file in files if isRarFile(rar_file)]
        if rar_files and sickbeard.UNPACK:
            video_files = [video_file for video_file in files if isMediaFile(video_file)]
            if u'_UNPACK' not in root and (not video_files or root == sickbeard.TV_DOWNLOAD_DIR):
                logger.log(u'Found rar files in post-process folder: {0}'.format(rar_files), logger.DEBUG)
                result = processTV.ProcessResult()
                processTV.unRAR(root, rar_files, False, result)
        elif rar_files and not sickbeard.UNPACK:
            logger.log(u'Unpack is disabled. Skipping: {0}'.format(rar_files), logger.WARNING)


def delete_unwanted_subtitles(dirpath, filename):
    """Deletes unwanted subtitles for the given filename in the specified dirpath

    :param dirpath: the directory path to be used
    :type dirpath: str
    :param filename: the subtitle filename
    :type dirpath: str
    """
    if not sickbeard.SUBTITLES_MULTI or not sickbeard.SUBTITLES_KEEP_ONLY_WANTED or \
            filename.rpartition('.')[2] not in subtitle_extensions:
        return

    code = filename.rsplit('.', 2)[1].lower().replace('_', '-')
    language = from_code(code, unknown='') or from_ietf_code(code, unknown='und')

    if language.opensubtitles not in sickbeard.SUBTITLES_LANGUAGES:
        try:
            os.remove(os.path.join(dirpath, filename))
            logger.log(u"Deleted '{0}' because we don't want subtitle language '{1}'. We only want '{2}' language(s)".
                       format(filename, language, ','.join(sickbeard.SUBTITLES_LANGUAGES)), logger.DEBUG)
        except Exception as error:
            logger.log(u"Couldn't delete subtitle: {0}. Error: {1}".format(filename, ex(error)), logger.DEBUG)


def clear_non_release_groups(filepath):
    """Removes non release groups from the name of the given file path.

    It also renames/moves the file to the path

    :param filepath: the file path
    :type filepath: str
    :return: the new file path
    :rtype: str
    """
    try:
        # Remove non release groups from video file. Needed to match subtitles
        new_filepath = remove_non_release_groups(filepath)
        if new_filepath != filepath:
            os.rename(filepath, new_filepath)
            filepath = new_filepath
    except Exception as error:
        logger.log(u"Couldn't remove non release groups from video file. Error: {0}".format(ex(error)), logger.DEBUG)

    return filepath


class SubtitlesFinder(object):
    """The SubtitlesFinder will be executed every hour but will not necessarily search and download subtitles.

    Only if the defined rule is true.
    """

    def __init__(self):
        self.amActive = False

    @staticmethod
    def subtitles_download_in_pp():  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """Checks for needed subtitles in the post process folder.
        """
        logger.log(u'Checking for needed subtitles in Post-Process folder', logger.INFO)

        # Check if PP folder is set
        if not sickbeard.TV_DOWNLOAD_DIR or not os.path.isdir(sickbeard.TV_DOWNLOAD_DIR):
            logger.log(u'You must set a valid post-process folder in "Post Processing" settings', logger.WARNING)
            return

        # Search for all wanted languages
        languages = {from_code(language) for language in wanted_languages()}
        if not languages:
            return

        unpack_rar_files(sickbeard.TV_DOWNLOAD_DIR)

        pool = get_provider_pool()
        run_post_process = False
        for root, _, files in os.walk(sickbeard.TV_DOWNLOAD_DIR, topdown=False):
            for filename in sorted(files):
                filename = clear_non_release_groups(filename)

                # Delete unwanted subtitles before downloading new ones
                delete_unwanted_subtitles(root, filename)

                if not isMediaFile(filename):
                    continue

                if processTV.subtitles_enabled(filename) is False:
                    logger.log(u"Subtitle disabled for show: {0}".format(filename), logger.DEBUG)
                    continue

                video_path = os.path.join(root, filename)
                release_name = os.path.splitext(filename)[0]
                found_subtitles = download_best_subs(video_path, root, release_name, languages, subtitles=False,
                                                     embedded_subtitles=False, provider_pool=pool)
                downloaded_languages = [s.language.opensubtitles for s in found_subtitles]

                # Don't run post processor unless at least one file has all of the needed subtitles
                if not run_post_process and not needs_subtitles(downloaded_languages):
                    run_post_process = True

        if run_post_process:
            logger.log(u'Starting post-process with default settings now that we found subtitles')
            processTV.processDir(sickbeard.TV_DOWNLOAD_DIR)

    def run(self, force=False):  # pylint: disable=too-many-branches, too-many-statements, too-many-locals
        """Checks for needed subtitles for users' shows

        :param force: True if a force search needs to be executed
        :type force: bool
        """
        if not sickbeard.USE_SUBTITLES:
            return

        if not sickbeard.subtitles.enabled_service_list():
            logger.log(u'Not enough services selected. At least 1 service is required to '
                       u'search subtitles in the background', logger.WARNING)
            return

        self.amActive = True

        def dhm(td):
            days = td.days
            hours = td.seconds // 60 ** 2
            minutes = (td.seconds // 60) % 60
            ret = (u'', '{} days, '.format(days))[days > 0] + \
                  (u'', '{} hours, '.format(hours))[hours > 0] + \
                  (u'', '{} minutes'.format(minutes))[minutes > 0]
            if days == 1:
                ret = ret.replace('days', 'day')
            if hours == 1:
                ret = ret.replace('hours', 'hour')
            if minutes == 1:
                ret = ret.replace('minutes', 'minute')
            return ret.rstrip(', ')

        if sickbeard.SUBTITLES_DOWNLOAD_IN_PP:
            self.subtitles_download_in_pp()

        logger.log(u'Checking for missed subtitles', logger.INFO)

        database = db.DBConnection()
        # Shows with air date <= 30 days, have a limit of 100 results
        # Shows with air date > 30 days, have a limit of 200 results
        sql_args = [{'age_comparison': '<=', 'limit': 100}, {'age_comparison': '>', 'limit': 200}]
        sql_like_languages = '%' + ','.join(sorted(wanted_languages())) + '%' if sickbeard.SUBTITLES_MULTI else '%und%'
        sql_results = []
        for args in sql_args:
            sql_results += database.select(
                "SELECT "
                "   s.show_name, "
                "   e.showid, "
                "   e.season, "
                "   e.episode,"
                "   e.release_name, "
                "   e.status, "
                "   e.subtitles, "
                "   e.subtitles_searchcount AS searchcount, "
                "   e.subtitles_lastsearch AS lastsearch, "
                "   e.location, (? - e.airdate) as age "
                "FROM "
                "   tv_episodes AS e "
                "INNER JOIN "
                "   tv_shows AS s "
                "ON (e.showid = s.indexer_id) "
                "WHERE"
                "   s.subtitles = 1 "
                "   AND (e.status LIKE '%4' OR e.status LIKE '%6') "
                "   AND e.season > 0 "
                "   AND e.location != '' "
                "   AND age {} 30 "
                "   AND e.subtitles NOT LIKE ? "
                "ORDER BY "
                "   lastsearch ASC "
                "LIMIT {}".format
                (args['age_comparison'], args['limit']), [datetime.datetime.now().toordinal(), sql_like_languages]
            )

        if not sql_results:
            logger.log(u'No subtitles to download', logger.INFO)
            self.amActive = False
            return

        for ep_to_sub in sql_results:
            ep_num = episode_num(ep_to_sub['season'], ep_to_sub['episode']) or \
                     episode_num(ep_to_sub['season'], ep_to_sub['episode'], numbering='absolute')
            subtitle_path = encode(ep_to_sub['location'], encoding=sickbeard.SYS_ENCODING, fallback='utf-8')
            if not os.path.isfile(subtitle_path):
                logger.log(u'Episode file does not exist, cannot download subtitles for {0} {1}'.format
                           (ep_to_sub['show_name'], ep_num), logger.DEBUG)
                continue

            if not needs_subtitles(ep_to_sub['subtitles']):
                logger.log(u'Episode already has all needed subtitles, skipping {0} {1}'.format
                           (ep_to_sub['show_name'], ep_num), logger.DEBUG)
                continue

            try:
                lastsearched = datetime.datetime.strptime(ep_to_sub['lastsearch'], dateTimeFormat)
            except ValueError:
                lastsearched = datetime.datetime.min

            try:
                if not force:
                    now = datetime.datetime.now()
                    days = int(ep_to_sub['age'])
                    delay_time = datetime.timedelta(hours=1 if days <= 10 else 8 if days <= 30 else 30 * 24)

                    # Search every hour until 10 days pass
                    # After 10 days, search every 8 hours, after 30 days search once a month
                    # Will always try an episode regardless of age for 3 times
                    if lastsearched + delay_time > now and int(ep_to_sub['searchcount']) > 2:
                        logger.log(u'Subtitle search for {0} {1} delayed for {2}'.format
                                   (ep_to_sub['show_name'], ep_num, dhm(lastsearched + delay_time - now)), logger.DEBUG)
                        continue

                show_object = Show.find(sickbeard.showList, int(ep_to_sub['showid']))
                if not show_object:
                    logger.log(u'Show with ID {0} not found in the database'.format(ep_to_sub['showid']), logger.DEBUG)
                    continue

                episode_object = show_object.getEpisode(ep_to_sub['season'], ep_to_sub['episode'])
                if isinstance(episode_object, str):
                    logger.log(u'{0} {1} not found in the database'.format
                               (ep_to_sub['show_name'], ep_num), logger.DEBUG)
                    continue

                try:
                    episode_object.download_subtitles()
                except Exception as error:
                    logger.log(u'Unable to find subtitles for {0} {1}. Error: {2}'.format
                               (ep_to_sub['show_name'], ep_num, ex(error)), logger.ERROR)
                    continue

            except Exception as error:
                logger.log(u'Error while searching subtitles for {0} {1}. Error: {2}'.format
                           (ep_to_sub['show_name'], ep_num, ex(error)), logger.WARNING)
                continue

        logger.log(u'Finished checking for missed subtitles', logger.INFO)
        self.amActive = False


def run_subs_pre_scripts(video_path):
    """Executes the subtitles pre-scripts for the given video path

    :param video_path: the video path
    :type video_path: str
    """
    run_subs_scripts(sickbeard.SUBTITLES_PRE_SCRIPTS, [video_path])


def run_subs_extra_scripts(video_path, subtitle_path, subtitle_language, show_name, season, episode, episode_name,
                           show_indexerid):
    """Executes the subtitles extra-scripts for the given video path

    :param video_path: the video path
    :type video_path: str
    :param subtitle_path: the downloaded subtitle path
    :type subtitle_path: str
    :param subtitle_language: the subtitle language
    :type subtitle_language: babelfish.Language
    :param show_name: the show name
    :type show_name: str
    :param season: the episode season number
    :type season: int
    :param episode: the episode number
    :type episode: int
    :param episode_name: the episode name
    :type episode_name: str
    :param show_indexerid: the show indexer id
    :type show_indexerid: int
    """
    run_subs_scripts(sickbeard.SUBTITLES_EXTRA_SCRIPTS,
                     [video_path, subtitle_path, subtitle_language.opensubtitles, show_name, str(season), str(episode),
                      episode_name, str(show_indexerid)])


def run_subs_scripts(scripts, script_args):
    """Execute subtitle scripts

    :param scripts: the script commands to be executed
    :type scripts: list of str
    :param script_args: the arguments to be passed to the script
    :type script_args: list of str
    """
    for script_name in scripts:
        script_cmd = [piece for piece in re.split("( |\\\".*?\\\"|'.*?')", script_name) if piece.strip()]

        logger.log(u'Running subtitle {0}-script: {1}'.format('extra' if len(script_args) > 1 else 'pre', script_name))
        inner_cmd = script_cmd + script_args

        # use subprocess to run the command and capture output
        logger.log(u'Executing command: {0}'.format(inner_cmd))
        try:
            process = subprocess.Popen(inner_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, cwd=sickbeard.PROG_DIR)
            out, _ = process.communicate()  # @UnusedVariable
            logger.log(u'Script result: {0}'.format(out), logger.DEBUG)

        except Exception as error:
            logger.log(u'Unable to run subtitles script: {0}'.format(ex(error)))
