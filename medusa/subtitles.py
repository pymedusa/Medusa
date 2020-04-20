# coding=utf-8
# Based on Antoine Bertin's <diaoulael@gmail.com> work
# and originally written by Nyaran <nyayukko@gmail.com>
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
"""Subtitles module."""
from __future__ import division
from __future__ import unicode_literals

import datetime
import logging
import operator
import os
import subprocess
import sys
import time
from builtins import object
from builtins import str

from babelfish import Country, Language, LanguageConvertError, LanguageReverseError, language_converters

from dogpile.cache.api import NO_VALUE

import knowit

from medusa import app, db, helpers, history
from medusa.cache import cache, memory_cache
from medusa.common import DOWNLOADED, SNATCHED, SNATCHED_BEST, SNATCHED_PROPER, cpu_presets
from medusa.helper.common import dateTimeFormat, episode_num, remove_extension, subtitle_extensions
from medusa.helper.exceptions import ex
from medusa.helpers import is_media_file, is_rar_file
from medusa.show.show import Show

from six import binary_type, iteritems, string_types, text_type

from subliminal import ProviderPool, compute_score, provider_manager, refine, save_subtitles, scan_video
from subliminal.core import search_external_subtitles
from subliminal.score import episode_scores
from subliminal.subtitle import get_subtitle_path

logger = logging.getLogger(__name__)

PROVIDER_POOL_EXPIRATION_TIME = datetime.timedelta(minutes=15).total_seconds()
VIDEO_EXPIRATION_TIME = datetime.timedelta(days=1).total_seconds()

subtitle_key = u'subtitle={id}'
video_key = u'{name}:video|{{video_path}}'.format(name=__name__)

episode_refiners = ('metadata', 'release', 'tvepisode', 'tvdb', 'omdb')

PROVIDER_URLS = {
    'addic7ed': 'http://www.addic7ed.com',
    'argenteam': 'https://argenteam.net',
    'legendastv': 'http://www.legendas.tv',
    'napiprojekt': 'http://www.napiprojekt.pl',
    'opensubtitles': 'http://www.opensubtitles.org',
    'opensubtitlesvip': 'http://www.opensubtitles.org',
    'podnapisi': 'https://www.podnapisi.net',
    'shooter': 'http://www.shooter.cn',
    'subtitulamos': 'https://www.subtitulamos.tv',
    'thesubdb': 'http://www.thesubdb.com',
    'tvsubtitles': 'http://www.tvsubtitles.net',
    'wizdom': 'http://wizdom.xyz'
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
    for current_service in app.SUBTITLES_SERVICES_LIST:
        if current_service in provider_manager.names():
            new_list.append({'name': current_service,
                             'url': PROVIDER_URLS[current_service]
                             if current_service in PROVIDER_URLS else lmgtfy % current_service,
                             'image': current_service + '.png',
                             'enabled': app.SUBTITLES_SERVICES_ENABLED[current_index] == 1})
        current_index += 1

    for current_service in sorted(provider_manager.names()):
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
    :rtype: set
    """
    return frozenset(app.SUBTITLES_LANGUAGES).intersection(subtitle_code_filter())


def get_needed_languages(subtitles):
    """Given the existing subtitles, returns a set of the needed subtitles.

    :param subtitles: the existing subtitles (opensubtitles codes)
    :type subtitles: set of str
    :return: the needed subtitles
    :rtype: set of babelfish.Language
    """
    if not app.SUBTITLES_MULTI:
        return set() if 'und' in subtitles else from_codes(wanted_languages())
    return from_codes(wanted_languages().difference(subtitles))


def subtitle_code_filter():
    """Return a set of all 3-letter code languages of opensubtitles.

    :return: all 3-letter language codes
    :rtype: set of str
    """
    return {code for code in language_converters['opensubtitles'].codes if len(code) == 3}


def needs_subtitles(subtitles):
    """Given the existing subtitles and wanted languages, returns True if subtitles are still needed.

    :param subtitles: the existing subtitles
    :type subtitles: set of str or list of str or str
    :return: True if subtitles are needed
    :rtype: bool
    """
    wanted = wanted_languages()
    if not wanted:
        return False

    if isinstance(subtitles, string_types):
        subtitles = {subtitle.strip() for subtitle in subtitles.split(',') if subtitle.strip()}

    if app.SUBTITLES_MULTI:
        return bool(wanted.difference(subtitles))

    return 'und' not in subtitles


def from_code(code, unknown='und'):
    """Convert an opensubtitles language code to a proper babelfish.Language object.

    :param code: an opensubtitles language code to be converted
    :type code: str
    :param unknown: the code to be returned for unknown language codes
    :type unknown: str or None
    :return: a language object
    :rtype: babelfish.Language
    """
    code = code.strip()
    if code and code in language_converters['opensubtitles'].codes:
        return Language.fromopensubtitles(code)  # pylint: disable=no-member

    return Language(unknown) if unknown else None


def from_codes(codes):
    """Convert opensubtitles language codes to a proper babelfish.Language object.

    :param codes: an opensubtitles language code to be converted
    :type codes: set of str or list of str
    :return: a list of language object
    :rtype: set of babelfish.Language
    """
    return {from_code(language) for language in codes}


def from_ietf_code(code, unknown='und'):
    """Convert an IETF code to a proper babelfish.Language object.

    :param code: an IETF language code
    :type code: str
    :param unknown: the code to be returned for unknown language codes
    :type unknown: str or None
    :return: a language object
    :rtype: babelfish.Language
    """
    try:
        return Language.fromietf(code)
    except (LanguageReverseError, ValueError):
        return Language(unknown) if unknown else None


def from_country_code_to_name(code):
    """Convert a 2 letter country code to a country name.

    :param code: the 2 letter country code
    :type code: str
    :return: the country name
    :rtype: str
    """
    try:
        return Country(code.upper()).name
    except ValueError:
        return


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


def accept_unknown(subtitles):
    """Whether or not there's any valid unknown subtitle for the specified video.

    :param subtitles:
    :type subtitles: set of babelfish.Language
    :return:
    :rtype: bool
    """
    return app.ACCEPT_UNKNOWN_EMBEDDED_SUBS and Language('und') in subtitles


def accept_any(subtitles):
    """Whether or not there's any valid subtitle for the specified video.

    :param subtitles:
    :type subtitles: set of babelfish.Language
    :return:
    :rtype: bool
    """
    wanted = from_codes(wanted_languages())
    return bool(subtitles & wanted)


def get_embedded_subtitles(video_path):
    """Return all embedded subtitles for the given video path.

    :param video_path: video filename to be checked
    :type video_path: str
    :return:
    :rtype: set of babelfish.Language
    """
    try:
        knowledge = knowit.know(video_path)
    except knowit.KnowitException as error:
        logger.warning('An error occurred while parsing: {0}\n'
                       'KnowIt reported:\n{1}'.format(video_path, error))
        return set()

    tracks = knowledge.get('subtitle', [])
    found_languages = {s['language'] for s in tracks if 'language' in s}
    if found_languages:
        logger.info(u'Found embedded subtitles: {subs}', subs=found_languages)
    return found_languages


def score_subtitles(subtitles_list, video):
    """Score all subtitles in the specified list for the given video.

    :param subtitles_list:
    :type subtitles_list: list of subliminal.subtitle.Subtitle
    :param video:
    :type video: subliminal.video.Video
    :return:
    :rtype: tuple(subliminal.subtitle.Subtitle, int)
    """
    providers_order = {d['name']: i for i, d in enumerate(sorted_service_list())}
    result = sorted([(s, compute_score(s, video, hearing_impaired=app.SUBTITLES_HEARING_IMPAIRED),
                    -1 * providers_order.get(s.provider_name, 1000))
                     for s in subtitles_list], key=operator.itemgetter(1, 2), reverse=True)
    return [(s, score) for (s, score, provider_order) in result]


def list_subtitles(tv_episode, video_path=None, limit=40):
    """List subtitles for the given episode in the given path.

    :param tv_episode:
    :type tv_episode: medusa.tv.Episode
    :param video_path:
    :type video_path: text_type
    :param limit:
    :type limit: int
    :return:
    :rtype: list of dict
    """
    subtitles_dir = get_subtitles_dir(video_path)
    release_name = tv_episode.release_name

    languages = from_codes(wanted_languages())

    video = get_video(tv_episode, video_path, subtitles_dir=subtitles_dir, subtitles=False,
                      embedded_subtitles=False, release_name=release_name)
    pool = get_provider_pool()
    pool.discarded_providers.clear()
    subtitles_list = pool.list_subtitles(video, languages)
    scored_subtitles = score_subtitles(subtitles_list, video)[:limit]
    for subtitle, _ in scored_subtitles:
        cache.set(subtitle_key.format(id=subtitle.id).encode('utf-8'), subtitle)

    logger.debug('Scores computed for release: {release}'.format(release=os.path.basename(video_path)))

    max_score = episode_scores['hash']
    max_scores = set(episode_scores) - {'hearing_impaired', 'hash'}
    factor = max_score / 9
    return [{'id': subtitle.id,
             'provider': subtitle.provider_name,
             'missing_guess': sorted(list(max_scores - subtitle.get_matches(video))),
             'lang': subtitle.language.opensubtitles,
             'score': round(10 * (factor / (float(factor - 1 - score + max_score)))),
             'sub_score': score,
             'hearing_impaired': subtitle.hearing_impaired,
             'max_score': max_score,
             'min_score': get_min_score(),
             'filename': get_subtitle_description(subtitle)}
            for subtitle, score in scored_subtitles]


def save_subtitle(tv_episode, subtitle_id, video_path=None):
    """Save the subtitle with the given id.

    :param tv_episode:
    :type tv_episode: medusa.tv.Episode
    :param subtitle_id:
    :type subtitle_id: text_type
    :param video_path:
    :type video_path: text_type
    :return:
    :rtype: list of str
    """
    subtitle = cache.get(subtitle_key.format(id=subtitle_id).encode('utf-8'))
    if subtitle == NO_VALUE:
        logger.error('Unable to find cached subtitle ID: %s', subtitle_id)
        return

    release_name = tv_episode.release_name
    subtitles_dir = get_subtitles_dir(video_path)
    video = get_video(tv_episode, video_path, subtitles_dir=subtitles_dir, subtitles=False,
                      embedded_subtitles=False, release_name=release_name)

    pool = get_provider_pool()
    if pool.download_subtitle(subtitle):
        return save_subs(tv_episode, video, [subtitle], video_path=video_path)


def download_subtitles(tv_episode, video_path=None, subtitles=True, embedded_subtitles=True, lang=None):
    """Download missing subtitles for the given episode.

    Checks whether subtitles are needed or not

    :param tv_episode: the episode to download subtitles
    :type tv_episode: medusa.tv.Episode
    :param video_path: the video path. If none, the episode location will be used
    :type video_path: str
    :param subtitles: True if existing external subtitles should be taken into account
    :type subtitles: bool
    :param embedded_subtitles: True if embedded subtitles should be taken into account
    :type embedded_subtitles: bool
    :param lang:
    :type lang: str
    :return: a sorted list of the opensubtitles codes for the downloaded subtitles
    :rtype: list of str
    """
    video_path = video_path or tv_episode.location
    show_name = tv_episode.series.name
    season = tv_episode.season
    episode = tv_episode.episode
    release_name = tv_episode.release_name
    ep_num = episode_num(season, episode) or episode_num(season, episode, numbering='absolute')
    subtitles_dir = get_subtitles_dir(video_path)

    if lang:
        logger.debug(u'Force re-downloading subtitle language: %s', lang)
        languages = {from_code(lang)}
    else:
        languages = get_needed_languages(tv_episode.subtitles)

    if not languages:
        logger.debug(u'Episode already has all needed subtitles, skipping %s %s', show_name, ep_num)
        return []

    logger.debug(u'Checking subtitle candidates for %s %s (%s)', show_name, ep_num, os.path.basename(video_path))
    video = get_video(tv_episode, video_path, subtitles_dir=subtitles_dir, subtitles=subtitles,
                      embedded_subtitles=embedded_subtitles, release_name=release_name)
    if not video:
        logger.info(u'Exception caught in subliminal.scan_video for %s', video_path)
        return []

    if app.SUBTITLES_PRE_SCRIPTS:
        run_subs_pre_scripts(video_path)

    pool = get_provider_pool()
    subtitles_list = pool.list_subtitles(video, languages)
    for provider in pool.providers:
        if provider in pool.discarded_providers:
            logger.debug(u'Could not search in %s provider. Discarding for now', provider)

    if not subtitles_list:
        logger.info(u'No subtitles found for %s', os.path.basename(video_path))
        return []

    min_score = get_min_score()
    scored_subtitles = score_subtitles(subtitles_list, video)
    for subtitle, score in scored_subtitles:
        logger.debug(u'[{0:>13s}:{1:<5s}] score = {2:3d}/{3:3d} for {4}'.format(
            subtitle.provider_name, text_type(subtitle.language), score,
            min_score, get_subtitle_description(subtitle)))

    found_subtitles = pool.download_best_subtitles(subtitles_list, video, languages=languages,
                                                   hearing_impaired=app.SUBTITLES_HEARING_IMPAIRED,
                                                   min_score=min_score, only_one=not app.SUBTITLES_MULTI)

    if not found_subtitles:
        logger.info(u'No subtitles found for %s with a minimum score of %d',
                    os.path.basename(video_path), min_score)
        return []

    return save_subs(tv_episode, video, found_subtitles, video_path=video_path)


def save_subs(tv_episode, video, found_subtitles, video_path=None):
    """Save subtitles.

    :param tv_episode: the episode to download subtitles
    :type tv_episode: sickbeard.tv.Episode
    :param video:
    :type video: subliminal.Video
    :param found_subtitles:
    :type found_subtitles: list of subliminal.Subtitle
    :param video_path: the video path. If none, the episode location will be used
    :type video_path: str
    :return: a sorted list of the opensubtitles codes for the downloaded subtitles
    :rtype: list of str
    """
    video_path = video_path or tv_episode.location
    show_name = tv_episode.series.name
    season = tv_episode.season
    episode = tv_episode.episode
    episode_name = tv_episode.name
    show_indexerid = tv_episode.series.indexerid
    subtitles_dir = get_subtitles_dir(video_path)
    saved_subtitles = save_subtitles(video, found_subtitles, directory=subtitles_dir,
                                     single=not app.SUBTITLES_MULTI, encoding='utf-8')

    for subtitle in saved_subtitles:
        logger.info(u'Found subtitle for %s in %s provider with language %s', os.path.basename(video_path),
                    subtitle.provider_name, subtitle.language.opensubtitles)
        subtitle_path = compute_subtitle_path(subtitle, video_path, subtitles_dir)
        helpers.chmod_as_parent(subtitle_path)
        helpers.fix_set_group_id(subtitle_path)

        if app.SUBTITLES_EXTRA_SCRIPTS and is_media_file(video_path):
            subtitle_path = compute_subtitle_path(subtitle, video_path, subtitles_dir)
            run_subs_extra_scripts(video_path=video_path, subtitle_path=subtitle_path,
                                   subtitle_language=subtitle.language, show_name=show_name, season=season,
                                   episode=episode, episode_name=episode_name, show_indexerid=show_indexerid)

        if app.SUBTITLES_HISTORY:
            logger.debug(u'Logging to history downloaded subtitle from provider %s and language %s',
                         subtitle.provider_name, subtitle.language.opensubtitles)
            history.log_subtitle(tv_episode, subtitle)

    # Refresh the subtitles property
    if tv_episode.location:
        tv_episode.refresh_subtitles()

    return sorted({subtitle.language.opensubtitles for subtitle in saved_subtitles})


@memory_cache.cache_on_arguments(expiration_time=PROVIDER_POOL_EXPIRATION_TIME)
def get_provider_pool():
    """Return the subliminal provider pool to be used.

    :return: subliminal provider pool to be used
    :rtype: subliminal.ProviderPool
    """
    logger.debug(u'Creating a new ProviderPool instance')
    provider_configs = {'addic7ed': {'username': app.ADDIC7ED_USER,
                                     'password': app.ADDIC7ED_PASS},
                        'legendastv': {'username': app.LEGENDASTV_USER,
                                       'password': app.LEGENDASTV_PASS},
                        'opensubtitles': {'username': app.OPENSUBTITLES_USER,
                                          'password': app.OPENSUBTITLES_PASS},
                        'opensubtitlesvip': {'username': app.OPENSUBTITLES_USER,
                                             'password': app.OPENSUBTITLES_PASS}}
    return ProviderPool(providers=enabled_service_list(), provider_configs=provider_configs)


def compute_subtitle_path(subtitle, video_path, subtitles_dir):
    """Return the full subtitle path that's computed by subliminal.

    :param subtitle: the subtitle
    :type subtitle: subliminal.Subtitle
    :param video_path: the video path
    :type video_path: str
    :param subtitles_dir: the subtitles directory
    :type subtitles_dir: str or None
    :return: the computed subtitles path
    :rtype: str
    """
    subtitle_path = get_subtitle_path(video_path, subtitle.language if app.SUBTITLES_MULTI else None)
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

    if not app.SUBTITLES_MULTI and len(new_subtitles) == 1:
        current_subtitles.remove(new_subtitles[0])
        current_subtitles.append('und')

    return current_subtitles


def get_min_score():
    """Return the min score to be used by subliminal.

    Perfect match = series + year + season + episode + release_group
    Non-perfect match = series + year + season + episode

    :return: min score to be used to download subtitles
    :rtype: int
    """
    min_score = episode_scores['series'] + episode_scores['year'] + episode_scores['season'] + episode_scores['episode']
    if app.SUBTITLES_PERFECT_MATCH:
        min_score += episode_scores['release_group']

    return min_score


def get_current_subtitles(tv_episode):
    """Return a list of current subtitles for the episode.

    :param tv_episode:
    :type tv_episode: medusa.tv.Episode
    :return: the current subtitles (3-letter opensubtitles codes) for the specified video
    :rtype: list of str
    """
    video_path = tv_episode.location
    # invalidate the cached video entry for the given path
    invalidate_video_cache(video_path)

    # get the latest video information
    video = get_video(tv_episode, video_path)
    if not video:
        logger.info(u"Exception caught in subliminal.scan_video, subtitles couldn't be refreshed for %s", video_path)
    else:
        return get_subtitles(video)


def _encode(value):
    """Encode the value using the specified encoding.

    It fallbacks to UTF-8 if not defined

    :param value: the value to be encoded
    :type value: str
    :param encoding: the encoding to be used
    :type encoding: str
    :return: the encoded value
    :rtype: str
    """
    if isinstance(value, binary_type):
        return value

    encoding = app.SYS_ENCODING

    try:
        return value.encode(encoding)
    except UnicodeEncodeError:
        logger.debug(u'Failed to encode to %s, falling back to UTF-8: %r',
                     encoding, value)
        return value.encode('utf-8')


def _decode(value):
    """Decode the value using the specified encoding.

    It fallbacks to UTF-8 if not defined

    :param value: the value to be encoded
    :type value: str
    :param encoding: the encoding to be used
    :type encoding: str
    :return: the decoded value
    :rtype: unicode
    """
    if isinstance(value, text_type):
        return value

    encoding = app.SYS_ENCODING

    try:
        return text_type(value, encoding)
    except UnicodeDecodeError:
        logger.debug(u'Failed to decode to %s, falling back to UTF-8: %r',
                     encoding, value)
        return text_type(value, 'utf-8')


def get_subtitle_description(subtitle):
    """Return a human readable name/description for the given subtitle (if possible).

    :param subtitle: the given subtitle
    :type subtitle: subliminal.Subtitle
    :return: name/description
    :rtype: str
    """
    desc = None
    sub_id = text_type(subtitle.id)
    if hasattr(subtitle, 'hash') and subtitle.hash:
        desc = text_type(subtitle.hash)
    if hasattr(subtitle, 'filename') and subtitle.filename:
        desc = subtitle.filename
    elif hasattr(subtitle, 'version') and subtitle.version:
        desc = text_type(subtitle.version)
    elif hasattr(subtitle, 'name') and subtitle.name:
        desc = subtitle.name
    if hasattr(subtitle, 'release') and subtitle.release:
        desc = subtitle.release
    if hasattr(subtitle, 'releases') and subtitle.releases:
        desc = text_type(subtitle.releases)

    return sub_id if not desc else desc


def invalidate_video_cache(video_path):
    """Invalidate the cached subliminal.video.Video for the specified path.

    :param video_path: the video path
    :type video_path: str
    """
    key = video_key.format(video_path=video_path)
    memory_cache.delete(key)
    logger.debug(u'Cached video information under key %s was invalidated', key)


def get_video(tv_episode, video_path, subtitles_dir=None, subtitles=True, embedded_subtitles=None, release_name=None):
    """Return the subliminal video for the given path.

    The video_path is used as a key to cache the video to avoid
    scanning and parsing the video metadata all the time

    :param tv_episode:
    :type tv_episode: medusa.tv.Episode
    :param video_path: the video path
    :type video_path: str
    :param subtitles_dir: the subtitles directory
    :type subtitles_dir: str or None
    :param subtitles: True if existing external subtitles should be taken into account
    :type subtitles: bool or None
    :param embedded_subtitles: True if embedded subtitles should be taken into account
    :type embedded_subtitles: bool or None
    :param release_name: the release name
    :type release_name: str or None
    :return: video
    :rtype: subliminal.video.Video
    """
    key = video_key.format(video_path=video_path)
    payload = {'subtitles_dir': subtitles_dir, 'subtitles': subtitles, 'embedded_subtitles': embedded_subtitles,
               'release_name': release_name}
    cached_payload = memory_cache.get(key, expiration_time=VIDEO_EXPIRATION_TIME)
    if cached_payload != NO_VALUE and {k: v for k, v in iteritems(cached_payload) if k != 'video'} == payload:
        logger.debug(u'Found cached video information under key %s', key)
        return cached_payload['video']

    video_is_mkv = video_path.endswith('.mkv')
    subtitles_dir = subtitles_dir or get_subtitles_dir(video_path)

    logger.debug(u'Scanning video %s...', video_path)

    try:
        video = scan_video(video_path)
    except ValueError as error:
        logger.warning(u'Unable to scan video: %s. Error: %r', video_path, error)
    else:

        if subtitles:
            video.subtitle_languages |= set(search_external_subtitles(video_path, directory=subtitles_dir).values())

        if embedded_subtitles is None:
            embedded_subtitles = bool(not app.IGNORE_EMBEDDED_SUBS and video_is_mkv)

        refine(video, episode_refiners=episode_refiners, embedded_subtitles=embedded_subtitles,
               release_name=release_name, tv_episode=tv_episode)

        video.alternative_series = [alias.title for alias in tv_episode.series.aliases]

        payload['video'] = video
        memory_cache.set(key, payload)
        logger.debug(u'Video information cached under key %s', key)

        return video


def get_subtitles_dir(video_path):
    """Return the correct subtitles directory based on the user configuration.

    If the directory doesn't exist, it will be created

    :param video_path: the video path
    :type video_path: str
    :return: the subtitles directory
    :rtype: str
    """
    if not app.SUBTITLES_DIR:
        return os.path.dirname(video_path)

    if os.path.isabs(app.SUBTITLES_DIR):
        return _decode(app.SUBTITLES_DIR)

    new_subtitles_path = os.path.join(os.path.dirname(video_path), app.SUBTITLES_DIR)
    if helpers.make_dir(new_subtitles_path):
        helpers.chmod_as_parent(new_subtitles_path)
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


def delete_unwanted_subtitles(dirpath, filename):
    """Delete unwanted subtitles for the given filename in the specified dirpath.

    :param dirpath: the directory path to be used
    :type dirpath: str
    :param filename: the subtitle filename
    :type dirpath: str
    """
    if not app.SUBTITLES_MULTI or not app.SUBTITLES_KEEP_ONLY_WANTED or \
            filename.rpartition('.')[2] not in subtitle_extensions:
        return

    code = filename.rsplit('.', 2)[1].lower().replace('_', '-')
    language = from_code(code, unknown='') or from_ietf_code(code)
    found_language = None
    try:
        found_language = language.opensubtitles
    except LanguageConvertError:
        logger.info(u"Unable to convert language code '%s' for: %s", code, filename)

    if found_language and found_language not in app.SUBTITLES_LANGUAGES:
        try:
            os.remove(os.path.join(dirpath, filename))
        except OSError as error:
            logger.info(u"Couldn't delete subtitle: %s. Error: %s", filename, ex(error))
        else:
            logger.debug(u"Deleted '%s' because we don't want subtitle language '%s'. We only want '%s' language(s)",
                         filename, language, ','.join(app.SUBTITLES_LANGUAGES))


class SubtitlesFinder(object):
    """The SubtitlesFinder will be executed every hour but will not necessarily search and download subtitles.

    Only if the defined rule is true.
    """

    def __init__(self):
        """Initialize class with the default constructor."""
        self.amActive = False

    @staticmethod
    def subtitles_download_in_pp():
        """Check for needed subtitles in the post process folder."""
        from medusa.tv import Episode

        logger.info(u'Checking for needed subtitles in Post-Process folder')

        # Check if PP folder is set
        if not app.TV_DOWNLOAD_DIR or not os.path.isdir(app.TV_DOWNLOAD_DIR):
            logger.warning(u'You must set a valid post-process folder in "Post Processing" settings')
            return

        # Search for all wanted languages
        if not wanted_languages():
            return

        SubtitlesFinder.unpack_rar_files(app.TV_DOWNLOAD_DIR)

        run_post_process = False
        for root, _, files in os.walk(app.TV_DOWNLOAD_DIR, topdown=False):
            # Skip folders that are being used for unpacking
            if u'_UNPACK' in root.upper():
                continue
            for filename in sorted(files):
                # Delete unwanted subtitles before downloading new ones
                delete_unwanted_subtitles(root, filename)

                if not is_media_file(filename):
                    continue

                video_path = os.path.join(root, filename)
                tv_episode = Episode.from_filepath(video_path)

                if not tv_episode:
                    logger.debug(u'%s cannot be parsed to an episode', filename)
                    continue

                if tv_episode.status not in (SNATCHED, SNATCHED_PROPER, SNATCHED_BEST):
                    continue

                if not tv_episode.series.subtitles:
                    logger.debug(u'Subtitle disabled for show: %s. Running post-process to PP it', filename)
                    run_post_process = True
                    continue

                # Should not consider existing subtitles from db if it's a replacement
                new_release_name = remove_extension(filename)
                if tv_episode.release_name and new_release_name != tv_episode.release_name:
                    logger.debug(u"As this is a release replacement I'm not going to consider existing "
                                 u'subtitles or release name from database to refine the new release')
                    logger.debug(u"Replacing old release name '%s' with new release name '%s'",
                                 tv_episode.release_name, new_release_name)
                    tv_episode.subtitles = []
                    tv_episode.release_name = new_release_name
                embedded_subtitles = bool(not app.IGNORE_EMBEDDED_SUBS and video_path.endswith('.mkv'))
                downloaded_languages = download_subtitles(tv_episode, video_path=video_path,
                                                          subtitles=False, embedded_subtitles=embedded_subtitles)

                # Don't run post processor unless at least one file has all of the needed subtitles OR
                # if user don't want to ignore embedded subtitles and wants to consider 'unknown' as wanted sub,
                # and .mkv has one.
                if not app.PROCESS_AUTOMATICALLY and not run_post_process:
                    if not needs_subtitles(downloaded_languages):
                        run_post_process = True
                    elif not app.IGNORE_EMBEDDED_SUBS:
                        embedded_subs = get_embedded_subtitles(video_path)
                        run_post_process = accept_unknown(embedded_subs) or accept_any(embedded_subs)

        if run_post_process:
            logger.info(u'Starting post-process with default settings now that we found subtitles')
            app.post_processor_scheduler.forceRun()

    @staticmethod
    def unpack_rar_files(dirpath):
        """Unpack any existing rar files present in the specified dirpath.

        :param dirpath: the directory path to be used
        :type dirpath: str
        """
        from medusa import process_tv
        for root, _, files in os.walk(dirpath, topdown=False):
            # Skip folders that are being used for unpacking
            if u'_UNPACK' in root.upper():
                continue
            rar_files = [rar_file for rar_file in files if is_rar_file(rar_file)]
            if rar_files and app.UNPACK:
                video_files = [video_file for video_file in files if is_media_file(video_file)]
                if not video_files or root == app.TV_DOWNLOAD_DIR:
                    logger.debug(u'Found rar files in post-process folder: %s', rar_files)
                    process_tv.ProcessResult(app.TV_DOWNLOAD_DIR).unrar(root, rar_files, False)
            elif rar_files and not app.UNPACK:
                logger.warning(u'Unpack is disabled. Skipping: %s', rar_files)

    def run(self, force=False):  # pylint: disable=too-many-branches, too-many-statements, too-many-locals
        """Check for needed subtitles for users' shows.

        :param force: True if a force search needs to be executed
        :type force: bool
        """
        if self.amActive:
            logger.debug(u'Subtitle finder is still running, not starting it again')
            return

        if not app.USE_SUBTITLES:
            logger.warning(u'Subtitle search is disabled. Please enabled it')
            return

        if not enabled_service_list():
            logger.warning(u'Not enough services selected. At least 1 service is required to search subtitles in the '
                           u'background')
            return

        self.amActive = True

        def dhm(td):
            """Create the string for subtitles delay."""
            days_delay = td.days
            hours_delay = td.seconds // 60 ** 2
            minutes_delay = (td.seconds // 60) % 60
            ret = (u'', '{days} days, '.format(days=days_delay))[days_delay > 0] + \
                  (u'', '{hours} hours, '.format(hours=hours_delay))[hours_delay > 0] + \
                  (u'', '{minutes} minutes'.format(minutes=minutes_delay))[minutes_delay > 0]
            if days_delay == 1:
                ret = ret.replace('days', 'day')
            if hours_delay == 1:
                ret = ret.replace('hours', 'hour')
            if minutes_delay == 1:
                ret = ret.replace('minutes', 'minute')
            return ret.rstrip(', ')

        if app.POSTPONE_IF_NO_SUBS:
            self.subtitles_download_in_pp()

        logger.info(u'Checking for missed subtitles')

        main_db_con = db.DBConnection()
        # Shows with air date <= 30 days, have a limit of 100 results
        # Shows with air date > 30 days, have a limit of 200 results
        sql_args = [{'age_comparison': '<=', 'limit': 100}, {'age_comparison': '>', 'limit': 200}]
        sql_like_languages = '%' + ','.join(sorted(wanted_languages())) + '%' if app.SUBTITLES_MULTI else '%und%'
        sql_results = []
        for args in sql_args:
            sql_results += main_db_con.select(
                'SELECT '
                's.show_name, '
                'e.indexer,'
                'e.showid, '
                'e.season, '
                'e.episode,'
                'e.release_name, '
                'e.status, '
                'e.subtitles, '
                'e.subtitles_searchcount AS searchcount, '
                'e.subtitles_lastsearch AS lastsearch, '
                'e.location, (? - e.airdate) as age '
                'FROM '
                'tv_episodes AS e '
                'INNER JOIN tv_shows AS s '
                'ON (e.showid = s.indexer_id AND e.indexer = s.indexer) '
                'WHERE '
                's.subtitles = 1 '
                'AND s.paused = 0 '
                'AND e.status = ? '
                'AND e.season > 0 '
                "AND e.location != '' "
                'AND age {} 30 '
                'AND e.subtitles NOT LIKE ? '
                'ORDER BY '
                'lastsearch ASC '
                'LIMIT {}'.format
                (args['age_comparison'], args['limit']),
                [datetime.datetime.now().toordinal(), DOWNLOADED, sql_like_languages]
            )

        if not sql_results:
            logger.info('No subtitles to download')
            self.amActive = False
            return

        for ep_to_sub in sql_results:

            # give the CPU a break
            time.sleep(cpu_presets[app.CPU_PRESET])

            ep_num = episode_num(ep_to_sub['season'], ep_to_sub['episode']) or \
                episode_num(ep_to_sub['season'], ep_to_sub['episode'], numbering='absolute')
            subtitle_path = _encode(ep_to_sub['location'])
            if not os.path.isfile(subtitle_path):
                logger.debug('Episode file does not exist, cannot download subtitles for %s %s',
                             ep_to_sub['show_name'], ep_num)
                continue

            if app.SUBTITLES_STOP_AT_FIRST and ep_to_sub['subtitles']:
                logger.debug('Episode already has one subtitle, skipping %s %s', ep_to_sub['show_name'], ep_num)
                continue

            if not needs_subtitles(ep_to_sub['subtitles']):
                logger.debug('Episode already has all needed subtitles, skipping %s %s',
                             ep_to_sub['show_name'], ep_num)
                continue

            try:
                lastsearched = datetime.datetime.strptime(ep_to_sub['lastsearch'], dateTimeFormat)
            except ValueError:
                lastsearched = datetime.datetime.min

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
                    logger.debug('Subtitle search for %s %s delayed for %s',
                                 ep_to_sub['show_name'], ep_num, dhm(delay))
                    continue

            show_object = Show.find_by_id(app.showList, ep_to_sub['indexer'], ep_to_sub['showid'])
            if not show_object:
                logger.debug('Show with ID %s not found in the database', ep_to_sub['showid'])
                continue

            episode_object = show_object.get_episode(ep_to_sub['season'], ep_to_sub['episode'])
            if isinstance(episode_object, str):
                logger.debug('%s %s not found in the database', ep_to_sub['show_name'], ep_num)
                continue

            episode_object.download_subtitles()

        logger.info('Finished checking for missed subtitles')
        self.amActive = False


def run_subs_pre_scripts(video_path):
    """Execute the subtitles pre-scripts for the given video path.

    :param video_path: the video path
    :type video_path: str
    """
    run_subs_scripts(video_path, app.SUBTITLES_PRE_SCRIPTS, video_path)


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
    run_subs_scripts(video_path, app.SUBTITLES_EXTRA_SCRIPTS, video_path, subtitle_path,
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
    for script_path in scripts:

        if not os.path.isfile(script_path):
            logger.warning(u'Subtitle script {0} is not a file.'.format(script_path))
            continue

        if not script_path.endswith('.py'):
            logger.warning(u'Subtitle script {0} is not a Python file.'.format(script_path))
            continue

        logger.info(u'Running subtitle %s-script: %s', 'extra' if len(args) > 1 else 'pre', script_path)
        script_cmd = [sys.executable, script_path] + [str(arg) for arg in args]

        # use subprocess to run the command and capture output
        logger.info(u'Executing command: %s', script_cmd)
        try:
            process = subprocess.Popen(script_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, cwd=app.PROG_DIR)
            out, _ = process.communicate()  # @UnusedVariable
            logger.debug(u'Script result: %s', out)

        except Exception as error:
            logger.info(u'Unable to run subtitles script: %r', ex(error))

    invalidate_video_cache(video_path)
