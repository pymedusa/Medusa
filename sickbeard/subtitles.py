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

import datetime
import logging
import operator
import os
import re
import subprocess
import time
import traceback

from babelfish import Language, language_converters
from six import iteritems
from dogpile.cache.api import NO_VALUE
from subliminal import (compute_score, ProviderPool, provider_manager, refine, refiner_manager, region, save_subtitles,
                        scan_video)
from subliminal.core import search_external_subtitles
from subliminal.score import episode_scores
from subliminal.subtitle import get_subtitle_path

import sickbeard
from sickbeard.common import cpu_presets
from sickrage.helper.common import dateTimeFormat, episode_num, subtitle_extensions
from sickrage.helper.exceptions import ex
from sickrage.show.Show import Show

from . import db, history, processTV
from .helpers import isMediaFile, isRarFile, remove_non_release_groups

logger = logging.getLogger(__name__)

PROVIDER_POOL_EXPIRATION_TIME = datetime.timedelta(minutes=15).total_seconds()
VIDEO_EXPIRATION_TIME = datetime.timedelta(days=1).total_seconds()

provider_manager.register('itasa = subliminal.providers.itasa:ItaSAProvider')
provider_manager.register('napiprojekt = subliminal.providers.napiprojekt:NapiProjektProvider')

refiner_manager.register('release = sickbeard.refiners.release:refine')

region.configure('dogpile.cache.memory')
video_key = u'{name}:video|{{video_path}}'.format(name=__name__)

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
    """Return an list of subliminal providers (it's not sorted, but the order matters!).

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
    """Return an ordered list of enabled and valid subliminal provider names.

    :return: list of provider names
    :rtype: list of str
    """
    return [service['name'] for service in sorted_service_list() if service['enabled']]


def wanted_languages():
    """Return the wanted language codes.

    :return: set of wanted subtitles (opensubtitles codes)
    :rtype: frozenset
    """
    return frozenset(sickbeard.SUBTITLES_LANGUAGES).intersection(subtitle_code_filter())


def get_needed_languages(subtitles):
    """Given the existing subtitles, returns a set of the needed subtitles.

    :param subtitles: the existing subtitles (opensubtitles codes)
    :type subtitles: list of str
    :return: the needed subtitles
    :rtype: set of babelfish.Language
    """
    if not sickbeard.SUBTITLES_MULTI:
        return set() if 'und' in subtitles else {from_code(language) for language in wanted_languages()}
    return {from_code(language) for language in wanted_languages().difference(subtitles)}


def subtitle_code_filter():
    """Return a set of all 3-letter code languages of opensubtitles.

    :return: all 3-letter language codes
    :rtype: set of str
    """
    return {code for code in language_converters['opensubtitles'].codes if len(code) == 3}


def needs_subtitles(subtitles):
    """Given the existing subtitles and wanted languages, returns True if subtitles are still needed.

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
    """Convert an opensubtitles language code to a proper babelfish.Language object.

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
    """Convert an IETF code to a proper babelfish.Language object.

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
    """Return the language name for the given language code.

    :param code: the opensubtitles language code
    :type code: str
    :return: the language name
    :rtype: str
    """
    return from_code(code).name


def code_from_code(code):
    """Convert an opensubtitles code to a 3-letter opensubtitles code.

    :param code: an opensubtitles language code
    :type code: str
    :return: a 3-letter opensubtitles language code
    :rtype: str
    """
    return from_code(code).opensubtitles


def download_subtitles(video_path, show_name, season, episode, episode_name, show_indexerid, release_name, status,
                       existing_subtitles):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
    """Download missing subtitles for the given episode.

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
        logger.debug(u'Episode already has all needed subtitles, skipping %s %s', show_name, ep_num)
        return []

    logger.debug(u'Checking subtitle candidates for %s %s (%s)', show_name, ep_num, os.path.basename(video_path))

    subtitles_dir = get_subtitles_dir(video_path)
    found_subtitles = download_best_subs(video_path, subtitles_dir, release_name, languages)

    for subtitle in found_subtitles:
        if sickbeard.SUBTITLES_EXTRA_SCRIPTS and isMediaFile(video_path):
            subtitle_path = compute_subtitle_path(subtitle, video_path, subtitles_dir)
            run_subs_extra_scripts(video_path=video_path, subtitle_path=subtitle_path,
                                   subtitle_language=subtitle.language, show_name=show_name, season=season,
                                   episode=episode, episode_name=episode_name, show_indexerid=show_indexerid)
        if sickbeard.SUBTITLES_HISTORY:
            logger.debug(u'history.logSubtitle %s, %s', subtitle.provider_name, subtitle.language.opensubtitles)
            history.logSubtitle(show_indexerid, season, episode, status, subtitle)

    return sorted({subtitle.language.opensubtitles for subtitle in found_subtitles})


def download_best_subs(video_path, subtitles_dir, release_name, languages, subtitles=True, embedded_subtitles=True,
                       provider_pool=None):
    """Download the best subtitle for the given video.

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
            logger.info(u'Exception caught in subliminal.scan_video for %s', video_path)
            return []

        pool = provider_pool or get_provider_pool()

        if sickbeard.SUBTITLES_PRE_SCRIPTS:
            run_subs_pre_scripts(video_path)

        subtitles_list = pool.list_subtitles(video, languages)
        for provider in pool.providers:
            if provider in pool.discarded_providers:
                logger.debug(u'Could not search in %s provider. Discarding for now', provider)

        if not subtitles_list:
            logger.info(u'No subtitles found for %s', os.path.basename(video_path))
            return []

        min_score = get_min_score()
        scored_subtitles = sorted([(s, compute_score(s, video, hearing_impaired=sickbeard.SUBTITLES_HEARING_IMPAIRED))
                                  for s in subtitles_list], key=operator.itemgetter(1), reverse=True)
        for subtitle, score in scored_subtitles:
            logger.debug(u'[{0:>13s}:{1:<5s}] score = {2:3d}/{3:3d} for {4}'.format(
                subtitle.provider_name, subtitle.language, score, min_score, get_subtitle_description(subtitle)))

        found_subtitles = pool.download_best_subtitles(subtitles_list, video, languages=languages,
                                                       hearing_impaired=sickbeard.SUBTITLES_HEARING_IMPAIRED,
                                                       min_score=min_score, only_one=not sickbeard.SUBTITLES_MULTI)

        if not found_subtitles:
            logger.info(u'No subtitles found for %s with a minimum score of %d',
                        os.path.basename(video_path), min_score)
            return []

        save_subtitles(video, found_subtitles, directory=_encode(subtitles_dir), single=not sickbeard.SUBTITLES_MULTI)

        for subtitle in found_subtitles:
            logger.info(u'Found subtitle for %s in %s provider with language %s', os.path.basename(video_path),
                        subtitle.provider_name, subtitle.language.opensubtitles)
            subtitle_path = compute_subtitle_path(subtitle, video_path, subtitles_dir)

            sickbeard.helpers.chmodAsParent(subtitle_path)
            sickbeard.helpers.fixSetGroupID(subtitle_path)

        return found_subtitles
    except IOError as error:
        if 'No space left on device' in ex(error):
            logger.warning(u'Not enough space on the drive to save subtitles')
        else:
            logger.warning(traceback.format_exc())
    except Exception as error:
        logger.debug(u'Exception: %s', error)
        logger.info(u'Error occurred when downloading subtitles for: %s', video_path)
        logger.error(traceback.format_exc())

    return []


@region.cache_on_arguments(expiration_time=PROVIDER_POOL_EXPIRATION_TIME)
def get_provider_pool():
    """Return the subliminal provider pool to be used.

    :return: subliminal provider pool to be used
    :rtype: subliminal.ProviderPool
    """
    logger.debug(u'Creating a new ProviderPool instance')
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
    """Return the full subtitle path that's computed by subliminal.

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
    """Merge the existing and new subtitles to a single list.

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
    """Return the min score to be used by subliminal.

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
    """Return a list of current subtitles for the episode.

    :param video_path: the video path
    :type video_path: str
    :return: the current subtitles (3-letter opensubtitles codes) for the specified video
    :rtype: list of str
    """
    # invalidate the cached video entry for the given path
    invalidate_video_cache(video_path)

    # get the latest video information
    video = get_video(video_path)
    if not video:
        logger.info(u"Exception caught in subliminal.scan_video, subtitles couldn't be refreshed for %s", video_path)
    else:
        return get_subtitles(video)


def _encode(value, encoding='utf-8', fallback=None):
    """Encode the value using the specified encoding.

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
        logger.debug(u'Failed to encode to %s, falling back to %s: %r',
                     encoding, fallback or sickbeard.SYS_ENCODING, value)
        return value.encode(fallback or sickbeard.SYS_ENCODING)


def _decode(value, encoding='utf-8', fallback=None):
    """Decode the value using the specified encoding.

    It fallbacks to the specified encoding or SYS_ENCODING if not defined

    :param value: the value to be encoded
    :type value: str
    :param encoding: the encoding to be used
    :type encoding: str
    :param fallback: the fallback encoding to be used
    :type fallback: str
    :return: the decoded value
    :rtype: unicode
    """
    try:
        return value.decode(encoding)
    except UnicodeDecodeError:
        logger.debug(u'Failed to decode to %s, falling back to %s: %r',
                     encoding, fallback or sickbeard.SYS_ENCODING, value)
        return value.decode(fallback or sickbeard.SYS_ENCODING)


def get_subtitle_description(subtitle):
    """Return a human readable name/description for the given subtitle (if possible).

    :param subtitle: the given subtitle
    :type subtitle: subliminal.Subtitle
    :return: name/description
    :rtype: str
    """
    desc = None
    sub_id = unicode(subtitle.id)
    if hasattr(subtitle, 'filename') and subtitle.filename:
        desc = subtitle.filename.lower()
    elif hasattr(subtitle, 'name') and subtitle.name:
        desc = subtitle.name.lower()
    if hasattr(subtitle, 'release') and subtitle.release:
        desc = subtitle.release.lower()
    if hasattr(subtitle, 'releases') and subtitle.releases:
        desc = unicode(subtitle.releases).lower()

    if not desc:
        desc = sub_id

    return sub_id + '-' + desc if desc not in sub_id else desc


def invalidate_video_cache(video_path):
    """Invalidate the cached subliminal.video.Video for the specified path.

    :param video_path: the video path
    :type video_path: str
    """
    key = video_key.format(video_path=video_path)
    region.delete(key)
    logger.debug(u'Cached video information under key %s was invalidated', key)


def get_video(video_path, subtitles_dir=None, subtitles=True, embedded_subtitles=None, release_name=None):
    """Return the subliminal video for the given path.

    The video_path is used as a key to cache the video to avoid
    scanning and parsing the video metadata all the time

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
    :rtype: subliminal.video.Video
    """
    key = video_key.format(video_path=video_path)
    payload = {'subtitles_dir': subtitles_dir, 'subtitles': subtitles, 'embedded_subtitles': embedded_subtitles,
               'release_name': release_name}
    cached_payload = region.get(key, expiration_time=VIDEO_EXPIRATION_TIME)
    if cached_payload != NO_VALUE and {k: v for k, v in iteritems(cached_payload) if k != 'video'} == payload:
        logger.debug(u'Found cached video information under key %s', key)
        return cached_payload['video']

    try:
        video_path = _encode(video_path)
        subtitles_dir = _encode(subtitles_dir or get_subtitles_dir(video_path))

        logger.debug(u'Scanning video %s...', video_path)
        video = scan_video(video_path)

        # external subtitles
        if subtitles:
            video.subtitle_languages |= set(search_external_subtitles(video_path, directory=subtitles_dir).values())

        if embedded_subtitles is None:
            embedded_subtitles = bool(not sickbeard.EMBEDDED_SUBTITLES_ALL and video_path.endswith('.mkv'))

        refine(video, episode_refiners=episode_refiners, embedded_subtitles=embedded_subtitles,
               release_name=release_name)

        payload['video'] = video
        region.set(key, payload)
        logger.debug(u'Video information cached under key %s', key)

        return video
    except Exception as error:
        logger.info(u'Exception: %s', error)


def get_subtitles_dir(video_path):
    """Return the correct subtitles directory based on the user configuration.

    If the directory doesn't exist, it will be created

    :param video_path: the video path
    :type video_path: str
    :return: the subtitles directory
    :rtype: str
    """
    if not sickbeard.SUBTITLES_DIR:
        return os.path.dirname(video_path)

    if os.path.isabs(sickbeard.SUBTITLES_DIR):
        return _decode(sickbeard.SUBTITLES_DIR)

    new_subtitles_path = os.path.join(os.path.dirname(video_path), sickbeard.SUBTITLES_DIR)
    if sickbeard.helpers.makeDir(new_subtitles_path):
        sickbeard.helpers.chmodAsParent(new_subtitles_path)
    else:
        logger.warning(u'Unable to create subtitles folder %s', new_subtitles_path)

    return new_subtitles_path


def get_subtitles(video):
    """Return a sorted list of detected subtitles for the given video file.

    :param video: the video to be inspected
    :type video: subliminal.video.Video
    :return: sorted list of opensubtitles code for the given video
    :rtype: list of str
    """
    result_list = [l.opensubtitles for l in video.subtitle_languages if hasattr(l, 'opensubtitles') and l.opensubtitles]
    return sorted(result_list)


def unpack_rar_files(dirpath):
    """Unpack any existing rar files present in the specified dirpath.

    :param dirpath: the directory path to be used
    :type dirpath: str
    """
    for root, _, files in os.walk(dirpath, topdown=False):
        rar_files = [rar_file for rar_file in files if isRarFile(rar_file)]
        if rar_files and sickbeard.UNPACK:
            video_files = [video_file for video_file in files if isMediaFile(video_file)]
            if u'_UNPACK' not in root and (not video_files or root == sickbeard.TV_DOWNLOAD_DIR):
                logger.debug(u'Found rar files in post-process folder: %s', rar_files)
                result = processTV.ProcessResult()
                processTV.unRAR(root, rar_files, False, result)
        elif rar_files and not sickbeard.UNPACK:
            logger.warning(u'Unpack is disabled. Skipping: %s', rar_files)


def delete_unwanted_subtitles(dirpath, filename):
    """Delete unwanted subtitles for the given filename in the specified dirpath.

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
            logger.debug(u"Deleted '%s' because we don't want subtitle language '%s'. We only want '%s' language(s)",
                         filename, language, ','.join(sickbeard.SUBTITLES_LANGUAGES))
        except Exception as error:
            logger.info(u"Couldn't delete subtitle: %s. Error: %s", filename, ex(error))


def clear_non_release_groups(filepath, filename):
    """Remove non release groups from the name of the given file path.

    It also renames/moves the file to the path

    :param filepath: the file path
    :param filename: the file name
    :type filepath: str
    :return: the new file path
    :rtype: str
    """
    try:
        # Remove non release groups from video file. Needed to match subtitles
        new_filename = remove_non_release_groups(filename)
        if new_filename != filename:
            os.rename(os.path.join(filepath, filename), os.path.join(filepath, new_filename))
            filename = new_filename
    except Exception as error:
        logger.debug(u"Couldn't remove non release groups from video file. Error: %s", ex(error))

    return filename


class SubtitlesFinder(object):
    """The SubtitlesFinder will be executed every hour but will not necessarily search and download subtitles.

    Only if the defined rule is true.
    """

    def __init__(self):
        self.amActive = False

    @staticmethod
    def subtitles_download_in_pp():  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """Check for needed subtitles in the post process folder."""
        logger.info(u'Checking for needed subtitles in Post-Process folder')

        # Check if PP folder is set
        if not sickbeard.TV_DOWNLOAD_DIR or not os.path.isdir(sickbeard.TV_DOWNLOAD_DIR):
            logger.warning(u'You must set a valid post-process folder in "Post Processing" settings')
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
                # Delete unwanted subtitles before downloading new ones
                delete_unwanted_subtitles(root, filename)

                if not isMediaFile(filename):
                    continue

                filename = clear_non_release_groups(root, filename)
                video_path = os.path.join(root, filename)

                if processTV.subtitles_enabled(video_path) is False:
                    logger.debug(u'Subtitle disabled for show: %s', filename)
                    continue

                release_name = os.path.splitext(filename)[0]
                found_subtitles = download_best_subs(video_path, root, release_name, languages, subtitles=False,
                                                     embedded_subtitles=False, provider_pool=pool)
                downloaded_languages = {s.language.opensubtitles for s in found_subtitles}

                # Don't run post processor unless at least one file has all of the needed subtitles
                if not run_post_process and not needs_subtitles(downloaded_languages):
                    run_post_process = True

        if run_post_process:
            logger.info(u'Starting post-process with default settings now that we found subtitles')
            processTV.processDir(sickbeard.TV_DOWNLOAD_DIR)

    def run(self, force=False):  # pylint: disable=too-many-branches, too-many-statements, too-many-locals
        """Check for needed subtitles for users' shows.

        :param force: True if a force search needs to be executed
        :type force: bool
        """
        if self.amActive:
            logger.log(u"Subtitle finder is still running, not starting it again", logger.DEBUG)
            return

        if not sickbeard.USE_SUBTITLES:
            logger.log(u"Subtitle search is disabled. Please enabled it", logger.WARNING)
            return

        if not sickbeard.subtitles.enabled_service_list():
            logger.warning(u'Not enough services selected. At least 1 service is required to search subtitles in the '
                           u'background')
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

        logger.info(u'Checking for missed subtitles')

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
            logger.info(u'No subtitles to download')
            self.amActive = False
            return

        for ep_to_sub in sql_results:

            # give the CPU a break
            time.sleep(cpu_presets[sickbeard.CPU_PRESET])

            ep_num = episode_num(ep_to_sub['season'], ep_to_sub['episode']) or \
                     episode_num(ep_to_sub['season'], ep_to_sub['episode'], numbering='absolute')
            subtitle_path = _encode(ep_to_sub['location'], encoding=sickbeard.SYS_ENCODING, fallback='utf-8')
            if not os.path.isfile(subtitle_path):
                logger.debug(u'Episode file does not exist, cannot download subtitles for %s %s',
                             ep_to_sub['show_name'], ep_num)
                continue

            if not needs_subtitles(ep_to_sub['subtitles']):
                logger.debug(u'Episode already has all needed subtitles, skipping %s %s', ep_to_sub['show_name'], ep_num)
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
                    delay = lastsearched + delay_time - now

                    # Search every hour until 10 days pass
                    # After 10 days, search every 8 hours, after 30 days search once a month
                    # Will always try an episode regardless of age for 3 times
                    # The time resolution is minute
                    # Only delay is the it's bigger than one minute and avoid wrongly skipping the search slot.
                    if delay.total_seconds() > 60 and int(ep_to_sub['searchcount']) > 2:
                        logger.debug(u'Subtitle search for %s %s delayed for %s',
                                     ep_to_sub['show_name'], ep_num, dhm(delay))
                        continue

                show_object = Show.find(sickbeard.showList, int(ep_to_sub['showid']))
                if not show_object:
                    logger.debug(u'Show with ID %s not found in the database', ep_to_sub['showid'])
                    continue

                episode_object = show_object.getEpisode(ep_to_sub['season'], ep_to_sub['episode'])
                if isinstance(episode_object, str):
                    logger.debug(u'%s %s not found in the database', ep_to_sub['show_name'], ep_num)
                    continue

                try:
                    episode_object.download_subtitles()
                except Exception as error:
                    logger.error(u'Unable to find subtitles for %s %s. Error: %s',
                                 ep_to_sub['show_name'], ep_num, ex(error))
                    continue

            except Exception as error:
                logger.warning(u'Error while searching subtitles for %s %s. Error: %s',
                               ep_to_sub['show_name'], ep_num, ex(error))
                continue

        logger.info(u'Finished checking for missed subtitles')
        self.amActive = False


def run_subs_pre_scripts(video_path):
    """Execute the subtitles pre-scripts for the given video path.

    :param video_path: the video path
    :type video_path: str
    """
    run_subs_scripts(video_path, sickbeard.SUBTITLES_PRE_SCRIPTS, video_path)


def run_subs_extra_scripts(video_path, subtitle_path, subtitle_language, show_name, season, episode, episode_name,
                           show_indexerid):
    """Execute the subtitles extra-scripts for the given video path.

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
    run_subs_scripts(video_path, sickbeard.SUBTITLES_EXTRA_SCRIPTS, video_path, subtitle_path,
                     subtitle_language.opensubtitles, show_name, season, episode, episode_name, show_indexerid)


def run_subs_scripts(video_path, scripts, *args):
    """Execute subtitle scripts.

    :param video_path: the video path
    :type video_path: str
    :param scripts: the script commands to be executed
    :type scripts: list of str
    :param args: the arguments to be passed to the script
    :type args: list of str
    """
    for script_name in scripts:
        script_cmd = [piece for piece in re.split("( |\\\".*?\\\"|'.*?')", script_name) if piece.strip()]
        script_cmd.extend(str(arg) for arg in args)

        logger.info(u'Running subtitle %s-script: %s', 'extra' if len(args) > 1 else 'pre', script_name)

        # use subprocess to run the command and capture output
        logger.info(u'Executing command: %s', script_cmd)
        try:
            process = subprocess.Popen(script_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, cwd=sickbeard.PROG_DIR)
            out, _ = process.communicate()  # @UnusedVariable
            logger.debug(u'Script result: %s', out)

        except Exception as error:
            logger.info(u'Unable to run subtitles script: %s', ex(error))

    invalidate_video_cache(video_path)
