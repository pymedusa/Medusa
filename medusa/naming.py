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

import datetime
import os

from . import app, common, logger, tv
from .common import DOWNLOADED, Quality
from .name_parser.parser import InvalidNameException, InvalidShowException, NameParser

name_presets = (
    '%SN - %Sx%0E - %EN',
    '%S.N.S%0SE%0E.%E.N',
    '%Sx%0E - %EN',
    'S%0SE%0E - %EN',
    'Season %0S/%S.N.S%0SE%0E.%Q.N-%RG'
)

name_anime_presets = name_presets

name_abd_presets = (
    '%SN - %A-D - %EN',
    '%S.N.%A.D.%E.N.%Q.N',
    '%Y/%0M/%S.N.%A.D.%E.N-%RG'
)

name_sports_presets = (
    '%SN - %A-D - %EN',
    '%S.N.%A.D.%E.N.%Q.N',
    '%Y/%0M/%S.N.%A.D.%E.N-%RG'
)


class TVShow(object):  # pylint: disable=too-few-public-methods
    def __init__(self):
        self.name = "Show Name"
        self.genre = "Comedy"
        self.indexerid = 1
        self.air_by_date = 0
        self.sports = 0
        self.anime = 0
        self.scene = 0

    def _is_anime(self):
        """
        Find out if show is anime
        :return: True if show is anime, False if not
        """
        return bool(self.anime)

    is_anime = property(_is_anime)

    def _is_sports(self):
        """
        Find out if show is sports
        :return: True if show is sports, False if not
        """
        return bool(self.sports)

    is_sports = property(_is_sports)

    def _is_scene(self):
        """
        Find out if show is scene numbering
        :return: True if show is scene numbering, False if not
        """
        return bool(self.scene)

    is_scene = property(_is_scene)


class TVEpisode(tv.Episode):  # pylint: disable=too-many-instance-attributes
    def __init__(self, season, episode, absolute_number, name):  # pylint: disable=super-init-not-called
        super(TVEpisode, self).__init__(None, season, episode)
        self.related_episodes = []
        self.name = name
        self.absolute_number = absolute_number
        self.scene_season = season
        self.scene_episode = episode
        self.scene_absolute_number = absolute_number
        self.airdate = datetime.date(2010, 3, 9)
        self.status = Quality.composite_status(common.DOWNLOADED, common.Quality.SDTV)
        self.release_name = 'Show.Name.S02E03.HDTV.x264-RLSGROUP'
        self.is_proper = True
        self.show = TVShow()


def check_force_season_folders(pattern=None, multi=None, anime_type=None):
    """
    Checks if the name can still be parsed if you strip off the folders to determine if we need to force season folders
    to be enabled or not.

    :return: true if season folders need to be forced on or false otherwise.
    """
    if pattern is None:
        pattern = app.NAMING_PATTERN

    if anime_type is None:
        anime_type = app.NAMING_ANIME

    valid = not validate_name(pattern, None, anime_type, file_only=True)

    if multi is not None:
        valid = valid or not validate_name(pattern, multi, anime_type, file_only=True)

    return valid


def check_valid_naming(pattern=None, multi=None, anime_type=None):
    """
    Checks if the name is can be parsed back to its original form for both single and multi episodes.

    :return: true if the naming is valid, false if not.
    """
    if pattern is None:
        pattern = app.NAMING_PATTERN

    if anime_type is None:
        anime_type = app.NAMING_ANIME

    logger.log(u"Checking whether the pattern " + pattern + " is valid for a single episode", logger.DEBUG)
    valid = validate_name(pattern, None, anime_type)

    if multi is not None:
        logger.log(u"Checking whether the pattern " + pattern + " is valid for a multi episode", logger.DEBUG)
        valid = valid and validate_name(pattern, multi, anime_type)

    return valid


def check_valid_abd_naming(pattern=None):
    """
    Checks if the name is can be parsed back to its original form for an air-by-date format.

    :return: true if the naming is valid, false if not.
    """
    if pattern is None:
        pattern = app.NAMING_PATTERN

    logger.log(u"Checking whether the pattern " + pattern + " is valid for an air-by-date episode", logger.DEBUG)
    valid = validate_name(pattern, abd=True)

    return valid


def check_valid_sports_naming(pattern=None):
    """
    Checks if the name is can be parsed back to its original form for an sports format.

    :return: true if the naming is valid, false if not.
    """
    if pattern is None:
        pattern = app.NAMING_PATTERN

    logger.log(u"Checking whether the pattern " + pattern + " is valid for an sports episode", logger.DEBUG)
    valid = validate_name(pattern, sports=True)

    return valid


def validate_name(pattern, multi=None, anime_type=None,  # pylint: disable=too-many-arguments, too-many-return-statements
                  file_only=False, abd=False, sports=False):
    """
    See if we understand a name

    :param pattern: Name to analyse
    :param multi: Is this a multi-episode name
    :param anime_type: Is this anime
    :param file_only: Is this just a file or a dir
    :param abd: Is air-by-date enabled
    :param sports: Is this sports
    :return: True if valid name, False if not
    """
    ep = generate_sample_ep(multi, abd, sports, anime_type)

    new_name = ep.formatted_filename(pattern, multi, anime_type) + '.ext'
    new_path = ep.formatted_dir(pattern, multi)
    if not file_only:
        new_name = os.path.join(new_path, new_name)

    if not new_name:
        logger.log(u"Unable to create a name out of " + pattern, logger.DEBUG)
        return False

    logger.log(u"Trying to parse " + new_name, logger.DEBUG)

    try:
        result = NameParser(show=ep.show, naming_pattern=True).parse(new_name)
    except (InvalidNameException, InvalidShowException) as error:
        logger.log(u"{}".format(error), logger.DEBUG)
        return False

    logger.log(u"The name " + new_name + " parsed into " + str(result), logger.DEBUG)

    if abd or sports:
        if result.air_date != ep.airdate:
            logger.log(u"Air date incorrect in parsed episode, pattern isn't valid", logger.DEBUG)
            return False
    elif anime_type != 3:
        if len(result.ab_episode_numbers) and result.ab_episode_numbers != [x.absolute_number for x in [ep] + ep.related_episodes]:
            logger.log(u"Absolute numbering incorrect in parsed episode, pattern isn't valid", logger.DEBUG)
            return False
    else:
        if result.season_number != ep.season:
            logger.log(u"Season number incorrect in parsed episode, pattern isn't valid", logger.DEBUG)
            return False
        if result.episode_numbers != [x.episode for x in [ep] + ep.related_episodes]:
            logger.log(u"Episode numbering incorrect in parsed episode, pattern isn't valid", logger.DEBUG)
            return False

    return True


def generate_sample_ep(multi=None, abd=False, sports=False, anime_type=None):
    # make a fake episode object
    ep = TVEpisode(2, 3, 3, "Ep Name")

    # pylint: disable=protected-access
    ep.status = Quality.composite_status(DOWNLOADED, Quality.HDTV)
    ep.airdate = datetime.date(2011, 3, 9)

    if abd:
        ep.release_name = 'Show.Name.2011.03.09.HDTV.x264-RLSGROUP'
        ep.show.air_by_date = 1
    elif sports:
        ep.release_name = 'Show.Name.2011.03.09.HDTV.x264-RLSGROUP'
        ep.show.sports = 1
    else:
        if anime_type != 3:
            ep.show.anime = 1
            ep.release_name = 'Show.Name.003.HDTV.x264-RLSGROUP'
        else:
            ep.release_name = 'Show.Name.S02E03.HDTV.x264-RLSGROUP'

    if multi is not None:
        ep.name = "Ep Name (1)"

        if anime_type != 3:
            ep.show.anime = 1

            ep.release_name = 'Show.Name.003-004.HDTV.x264-RLSGROUP'

            secondEp = TVEpisode(2, 4, 4, "Ep Name (2)")
            secondEp.status = Quality.composite_status(DOWNLOADED, Quality.HDTV)
            secondEp.release_name = ep.release_name

            ep.related_episodes.append(secondEp)
        else:
            ep.release_name = 'Show.Name.S02E03E04E05.HDTV.x264-RLSGROUP'

            secondEp = TVEpisode(2, 4, 4, "Ep Name (2)")
            secondEp.status = Quality.composite_status(DOWNLOADED, Quality.HDTV)
            secondEp.release_name = ep.release_name

            thirdEp = TVEpisode(2, 5, 5, "Ep Name (3)")
            thirdEp.status = Quality.composite_status(DOWNLOADED, Quality.HDTV)
            thirdEp.release_name = ep.release_name

            ep.related_episodes.append(secondEp)
            ep.related_episodes.append(thirdEp)

    return ep


def test_name(pattern, multi=None, abd=False, sports=False, anime_type=None):
    ep = generate_sample_ep(multi, abd, sports, anime_type)

    return {'name': ep.formatted_filename(pattern, multi, anime_type), 'dir': ep.formatted_dir(pattern, multi)}
