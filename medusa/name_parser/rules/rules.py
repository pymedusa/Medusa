#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Rules: This section contains rules that enhances guessit behavior.

Coding guidelines:
For each rule:
  - Provide an explanation
  - An example of the guessit output without it
  - An example of the guessit output with it
  - Each rule should handle only one issue
  - Remember that the input might be a filepath: /Show Name/Season 1/Show Name S01E02.ext
  - Use rule.priority = POST_PROCESSOR (DO NOT change this*)
  - DO NOT use rule.dependency**
  - DO NOT change match.value. Just remove the match and append a new one with the amended value***
  - Try to avoid using `private`, `parent` and `children` matches.
    Their behaviour might change a lot in each new version

Rebulk API is really powerful. It's always good to spend some time reading about it: https://github.com/Toilal/rebulk

The main idea about the rules in this section is to navigate between the `matches` and `holes` and change the matches
according to our needs.

* Our rules should run only after all standard and default guessit rules have finished (not before that!).
** Adding several dependencies to our rules will make an implicit execution order. It could be hard to debug. Better to
have a fixed execution order, that's why the rules() method should add the rules in the correct order (explicit).
*** Rebulk API relies on the match.value, if you change them you'll get exceptions.
"""
import copy
import logging
import re

from guessit.rules.common.comparators import marker_sorted
from guessit.rules.common.formatters import cleanup
from guessit.rules.properties import website
from guessit.rules.properties.release_group import clean_groupname
from rebulk.processors import POST_PROCESS
from rebulk.rebulk import Rebulk
from rebulk.rules import AppendMatch, RemoveMatch, RenameMatch, Rule


logger = logging.getLogger(__name__)

simple_separator = ('.', 'and', ',.', '.,', '.,.', ',')
range_separator = ('-', '~', '_-_', 'to', '.to.')
episode_range_separator = range_separator + ('_-_e', '-e', '.to.e', '_to_e')


class BlacklistedReleaseGroup(Rule):
    """Blacklist some release groups."""

    priority = POST_PROCESS
    consequence = RemoveMatch
    blacklist = ('private', 'req', 'no.rar', 'season')

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        return matches.named('release_group', predicate=lambda match: match.value.lower() in self.blacklist)


class EpisodeNumberRule(Rule):
    """Episode numbers in episode title are wrongly detected as episodes.

    guessit -t episode "Show Name - S02E31 - Episode 55 (720p.HDTV)"

    Before the rule:
    For: Show Name - S02E31 - Episode 55 (720p.HDTV)
    GuessIt found: {
        "title": "Show Name",
        "season": 2,
        "episode": [
            31,
            55
        ],
        "screen_size": "720p",
        "format": "HDTV",
        "type": "episode"
    }

    After the rule:
    For: Show Name - S02E31 - Episode 55 (720p.HDTV)
    GuessIt found: {
        "title": "Show Name",
        "season": 2,
        "episode": 31,
        "screen_size": "720p",
        "format": "HDTV",
        "type": "episode"
    }
    """

    priority = POST_PROCESS
    consequence = [RemoveMatch, AppendMatch]

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        fileparts = matches.markers.named('path')
        for filepart in marker_sorted(fileparts, matches):
            episodes = matches.range(filepart.start, filepart.end, predicate=lambda match: match.name == 'episode')
            if len(episodes) < 2:
                continue

            strong_episodes = [m for m in episodes if 'SxxExx' in m.tags]
            weak_episodes = [m for m in episodes if 'SxxExx' not in m.tags]
            if not strong_episodes or not weak_episodes:
                continue

            numbers = [m.value for m in episodes]
            # check if we have consecutive numbers
            if sorted(numbers) == range(min(numbers), max(numbers) + 1):
                continue

            to_remove = weak_episodes
            to_append = []
            for e in weak_episodes:
                if matches.previous(e, lambda match: match.name == 'episode' and 'SxxExx' in match.tags):
                    episode_title = copy.copy(e.initiator)
                    episode_title.name = 'episode_title'
                    episode_title.private = False
                    to_append.append(episode_title)
                    break

            return to_remove, to_append


class FixAnimeReleaseGroup(Rule):
    """Choose the correct Anime release group.

    Anime release group is at the beginning and inside square brackets. If this pattern is found at the start of the
    filepart, use it as a release group.

    guessit -t episode "[RealGroup].Show.Name.-.462.[720p].[10bit].[SOMEPERSON].[Something]"

    without this fix:
        For: [RealGroup].Show.Name.-.462.[720p].[10bit].[SOMEPERSON].[Something]
        GuessIt found: {
            "title": "Show Name",
            "season": 4,
            "episode": 62,
            "screen_size": "720p",
            "video_profile": "10bit",
            "release_group": "[SOMEPERSON].[Something]",
            "type": "episode"
        }

    with this fix:
        For: [RealGroup].Show.Name.-.462.[720p].[10bit].[SOMEPERSON].[Something]
        GuessIt found: {
            "title": "Show Name",
            "season": 4,
            "episode": 62,
            "screen_size": "720p",
            "video_profile": "10bit",
            "release_group": "RealGroup",
            "type": "episode"
        }
    """

    priority = POST_PROCESS
    consequence = [RemoveMatch, AppendMatch]
    website_rebulk = website.website()

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        if context.get('show_type') == 'normal':
            return

        fileparts = matches.markers.named('path')
        for filepart in marker_sorted(fileparts, matches):
            # get the group (e.g.: [abc]) at the beginning of this filepart
            group = matches.markers.at_index(filepart.start, index=0, predicate=lambda marker: marker.name == 'group')
            if not group or matches.at_match(group):
                continue

            if (not matches.tagged('anime') and not matches.named('video_profile') and
                    matches.named('season') and matches.named('episode')):
                continue

            groups = matches.range(filepart.start, filepart.end, predicate=lambda match: match.name == 'release_group')
            if not groups:
                continue

            to_remove = []
            to_append = []
            if group:
                to_remove.extend(groups)
                rg = copy.copy(groups[0])
                rg.start = group.start
                rg.end = group.end
                rg.value = cleanup(group.value)
                rg.tags = ['anime']
                to_append.append(rg)
            else:
                # anime should pick the first in the list and discard the rest
                to_remove.append(groups[1:])

            return to_remove, to_append


class SpanishNewpctReleaseName(Rule):
    """Detect newpct release names.

    This rule is to handle the newpct release name style.

    e.g.: Show.Name.-.Temporada.1.720p.HDTV.x264[Cap.102]SPANISH.AUDIO-NEWPCT

    guessit -t episode "Show.Name.-.Temporada.1.720p.HDTV.x264[Cap.102]SPANISH.AUDIO-NEWPCT"

    without this rule:
        For: Show.Name.-.Temporada.1.720p.HDTV.x264[Cap.102]SPANISH.AUDIO-NEWPCT
        GuessIt found: {
            "title": "Show Name",
            "alternative_title": "Temporada",
            "episode": [
                1,
                2
            ],
            "screen_size": "720p",
            "format": "HDTV",
            "video_codec": "h264",
            "season": 1,
            "language": "Spanish",
            "episode_title": "AUDIO-NEWPCT",
            "type": "episode"
        }


    with this rule:
        For: Show.Name.-.Temporada.1.720p.HDTV.x264[Cap.102]SPANISH.AUDIO-NEWPCT
        GuessIt found: {
            "title": "Show Name",
            "season": 1,
            "episode": 2
            "screen_size": "720p",
            "format": "HDTV",
            "video_codec": "h264",
            "language": "Spanish",
            "release_group": "NEWPCT"
            "type": "episode"
        }

    """

    priority = POST_PROCESS
    consequence = [RemoveMatch, AppendMatch]
    season_re = re.compile(r'^tem(p|porada)?\W*\d*$', flags=re.IGNORECASE)
    prefix = '[cap.'
    episode_re = re.compile(r'^\[cap\.(?P<season>\d{1,2})(?P<episode>\d{2})'
                            r'(_((?P<end_season>\d{1,2})(?P<end_episode>\d{2})))?.*\]', flags=re.IGNORECASE)

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        season = matches.named('season', index=0)
        if not season:
            return

        alternative_titles = matches.named('alternative_title',
                                           predicate=lambda match: self.season_re.match(match.value.lower()))
        episode_titles = matches.named('episode_title',
                                       predicate=lambda match: self.season_re.match(match.value.lower()))

        # skip if there isn't an alternative_title or episode_title with the word season in spanish
        if not alternative_titles and not episode_titles:
            return

        fileparts = matches.markers.named('path')
        for filepart in marker_sorted(fileparts, matches):
            # retrieve all groups
            groups = matches.markers.range(filepart.start, filepart.end, predicate=lambda mk: mk.name == 'group')
            for group in groups:
                # then search the season and episode numbers: [Cap.102_103]
                m = self.episode_re.search(group.raw)
                g = m.groupdict() if m else None
                # if found and the season numbers match...
                if not g or int(g['season']) != season.value or (
                        g['end_season'] and int(g['end_season']) != season.value):
                    continue

                if not context.get('show_type'):
                    # fix the show_type as this is not anime
                    context['show_type'] = 'normal'

                to_remove = []
                to_append = []

                # remove "[Cap.] match, if any
                to_remove.extend(matches.range(group.start, group.start + len(self.prefix)))
                # remove the wrong alternative title
                to_remove.extend(alternative_titles)
                # remove the wrong episode title
                to_remove.extend(episode_titles)
                to_remove.extend(matches.range(filepart.start, filepart.end, predicate=lambda match:
                                               match.name == 'episode_title' and
                                               match.value.lower() == 'audio'))
                # remove all episode matches, since we're rebuild them
                to_remove.extend(matches.named('episode'))

                first_ep_num = int(g['episode'])
                last_ep_num = int(g['end_episode']) if g['end_episode'] else first_ep_num
                if 0 <= first_ep_num <= last_ep_num < 100:
                    start_index = group.start + len(g['season']) + len(self.prefix)

                    # rebuild all episode matches
                    for ep_num in range(first_ep_num, last_ep_num + 1):
                        new_episode = copy.copy(season)
                        new_episode.name = 'episode'
                        new_episode.tags = ['newpct']
                        new_episode.value = ep_num
                        if ep_num == first_ep_num:
                            new_episode.start = start_index
                            new_episode.end = new_episode.start + len(g['episode'])
                        elif ep_num != last_ep_num:
                            new_episode.start = start_index + len(g['episode'])
                            new_episode.end = new_episode.start + 1
                        else:
                            new_episode.start = start_index + len(g['episode']) + len(g['end_season']) + 1
                            new_episode.end = new_episode.start + len(g['end_episode'])
                        to_append.append(new_episode)

                return to_remove, to_append


class FixSeasonRangeWithGap(Rule):
    """Fix season range with gap.

    guessit -t episode "Show.Name.-.Season.1.3.4-.Mp4.1080p"

    Without this fix:
        For: Show.Name.-.Season.1.3.4-.Mp4.1080p
        GuessIt found: {
            "title": "Show Name",
            "season": 1,
            "episode": [
                3,
                4
            ],
            "container": "MP4",
            "screen_size": "1080p",
            "type": "episode"
        }

    with this fix:
        For: Show.Name.-.Season.1.3.4-.Mp4.1080p
        GuessIt found: {
            "title": "Show Name",
            "season": [1, 3, 4]
            "container": "MP4",
            "screen_size": "1080p",
            "type": "episode"
        }
    """

    priority = POST_PROCESS
    consequence = [AppendMatch, RemoveMatch]

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        to_remove = []
        to_append = []
        fileparts = matches.markers.named('path')
        for filepart in marker_sorted(fileparts, matches):
            season = matches.range(filepart.start, filepart.end, predicate=lambda match: match.name == 'season', index=0)
            if not season:
                continue

            episodes = matches.range(season.end, filepart.end,
                                     predicate=lambda match: match.name == 'episode' and 'weak-episode' in match.tags)
            if not episodes:
                continue

            if len(episodes) != len(matches.holes(season.end, episodes[-1].start, predicate=lambda hole: hole.raw in simple_separator)):
                continue

            for episode in episodes:
                new_season = copy.copy(episode)
                new_season.name = 'season'
                to_append.append(new_season)
                to_remove.append(episode)

        return to_append, to_remove


class RemoveInvalidEpisodes(Rule):
    """Remove invalid episodes.

    guessit -t episode "Show.Name.S02E06.eps2.4.m4ster-s1ave.aes.1080p.AMZN.WEBRip.DD5.1.x264-GROUP"

    Without this fix:
        For: Show.Name.S02E06.eps2.4.m4ster-s1ave.aes.1080p.AMZN.WEBRip.DD5.1.x264-GROUP
        GuessIt found: {
            "title": "Show Name",
            "season": [
                2,
                4,
                1
            ],
            "episode": 6,
            "episode_title": "eps2",
            "screen_size": "1080p",
            "format": "WEBRip",
            "audio_codec": "DolbyDigital",
            "audio_channels": "5.1",
            "video_codec": "h264",
            "release_group": "GROUP",
            "type": "episode"
        }


    with this fix:
        For: Show.Name.S02E06.eps2.4.m4ster-s1ave.aes.1080p.AMZN.WEBRip.DD5.1.x264-GROUP
        GuessIt found: {
            "title": "Show Name",
            "season": 2,
            "episode": 6,
            "episode_title": "eps2",
            "screen_size": "1080p",
            "format": "WEBRip",
            "audio_codec": "DolbyDigital",
            "audio_channels": "5.1",
            "video_codec": "h264",
            "release_group": "GROUP",
            "type": "episode"
        }
    """

    priority = POST_PROCESS
    consequence = RemoveMatch

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        to_remove = []
        fileparts = matches.markers.named('path')
        for filepart in marker_sorted(fileparts, matches):
            episode = matches.range(filepart.start, filepart.end, index=0,
                                    predicate=lambda match: match.name == 'episode' and 'SxxExx' in match.tags)
            if not episode:
                continue

            seasons = matches.range(filepart.start, filepart.end,
                                    predicate=lambda match: match.name == 'season' and match.initiator != episode.initiator)
            episodes = matches.range(filepart.start, filepart.end,
                                     predicate=(lambda match: match.name == 'episode' and
                                                'SxxExx' not in match.tags and match.initiator.raw.startswith('eps')))  # mr robot episode titles

            to_remove.extend(seasons)
            to_remove.extend(episodes)

        return to_remove


class FixSeasonAndEpisodeConflicts(Rule):
    """Fix season and episode conflict.

    - Fix release group conflict with episode and or season.
    - Certain release names contains a conflicting screen_size (e.g.: 720 without p). It confuses guessit: the guessed
    season and episode needs to be removed.
    Bug: https://github.com/guessit-io/guessit/issues/308

    e.g.: "Show.Name.S02.REPACK.720p.BluRay.DD5.1.x264-4EVERHD"
          "[SuperGroup].Show.Name.-.06.[720.Hi10p][1F5578AC]"

    guessit -t episode -G 4EVERHD "Show.Name.S02.REPACK.720p.BluRay.DD5.1.x264-4EVERHD"
    guessit -t episode "[SuperGroup].Show.Name.-.06.[720.Hi10p][1F5578AC]"

    without this fix:
        For: [SuperGroup].Show.Name.-.06.[720.Hi10p][1F5578AC]
        GuessIt found: {
            "release_group": "SuperGroup",
            "title": "Show Name",
            "episode": [
                6,
                20
            ],
            "season": 7,
            "screen_size": "720p",
            "video_profile": "10bit",
            "crc32": "1F5578AC",
            "type": "episode"
        }

    with this fix:
        For: [SuperGroup].Show.Name.-.06.[720.Hi10p][1F5578AC]
        GuessIt found: {
            "release_group": "SuperGroup",
            "title": "Show Name",
            "episode": 6,
            "screen_size": "720p",
            "video_profile": "10bit",
            "crc32": "1F5578AC",
            "type": "episode"
        }

    """

    priority = POST_PROCESS
    consequence = RemoveMatch

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        to_remove = []

        screen_sizes = matches.named('screen_size')
        for screen_size in screen_sizes:
            to_remove.extend(matches.range(screen_size.start, screen_size.end, predicate=lambda match: match.name in ('season', 'episode')))

        release_groups = matches.named('release_group')
        for group in release_groups:
            to_remove.extend(matches.range(group.start, group.end, predicate=lambda match: match.name in ('season', 'episode')))

        return to_remove


class FixInvalidTitleOrAlternativeTitle(Rule):
    """Fix invalid title/alternative title due to absolute episode numbers range.

    Some release names have season/episode defined twice (relative and absolute), and one of them becomes an
    alternative_title or a suffix in the title. This fix will remove the invalid alternative_title or the
    invalid title's suffix.

    e.g.: "Show Name - 313-314 - s16e03-04"

    guessit -t episode "Show Name - 313-314 - s16e03-04"

    without this fix:
        For: Show Name - 313-314 - s16e03-04
        GuessIt found: {
            "title": "Show Name",
            "alternative_title": "313-314",
            "season": 16,
            "episode": [
                3,
                4
            ],
            "type": "episode"
        }


    with this fix:
        For: Show Name - 313-314 - s16e03-04
        GuessIt found: {
            "title": "Show Name",
            "season": 16,
            "absolute_episode": [
                313,
                314
            ],
            "episode": [
                3,
                4
            ],
            "type": "episode"
        }
    """

    priority = POST_PROCESS
    consequence = [RemoveMatch, AppendMatch]
    absolute_re = re.compile(r'([\W|_]*)(?P<absolute_episode_start>\d{3,4})\-(?P<absolute_episode_end>\d{3,4})\W*$')
    properties = ('title', 'alternative_title', 'episode_title')

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        episodes = matches.named('episode')
        if not episodes:
            return

        fileparts = matches.markers.named('path')
        for filepart in marker_sorted(fileparts, matches):
            # retrieve all problematic titles
            problematic_titles = matches.range(filepart.start, filepart.end,
                                               predicate=lambda match: match.name in self.properties)

            to_remove = []
            to_append = []

            for title in problematic_titles:
                m = self.absolute_re.search(title.raw)
                if not m:
                    continue

                # Remove the problematic title
                to_remove.append(title)

                # Remove the title suffix
                new_value = title.raw[0: m.start()]
                if new_value:
                    # Add the correct title
                    new_title = copy.copy(title)
                    new_title.value = cleanup(new_value)
                    new_title.end = m.start()
                    to_append.append(new_title)

                # and add the absolute episode range
                g = m.groupdict()
                absolute_episode_start = int(g['absolute_episode_start'])
                absolute_episode_end = int(g['absolute_episode_end'])
                for i in range(absolute_episode_start, absolute_episode_end + 1):
                    episode = copy.copy(episodes[0])
                    episode.name = 'absolute_episode'
                    episode.value = i
                    if i == absolute_episode_start:
                        episode.start = title.start + m.start('absolute_episode_start')
                        episode.end = title.start + m.end('absolute_episode_start')
                    elif i < absolute_episode_end:
                        episode.start = title.start + m.end('absolute_episode_start')
                        episode.end = title.start + m.start('absolute_episode_end')
                    else:
                        episode.start = title.start + m.start('absolute_episode_end')
                        episode.end = title.start + m.end('absolute_episode_end')
                    to_append.append(episode)

                return to_remove, to_append


class FixWrongTitleDueToFilmTitle(Rule):
    """Fix release_group detection due to film title.

    Work-around for https://github.com/guessit-io/guessit/issues/294
    TODO: Remove when this bug is fixed

    e.g.: "Show.Name.S03E16.1080p.WEB-DL.DD5.1.H.264-GOLF68"

    guessit -t episode "Show.Name.S03E16.1080p.WEB-DL.DD5.1.H.264-GOLF68"

    without this fix:
    For: Show.Name.S03E16.1080p.WEB-DL.DD5.1.H.264-GOLF68
        GuessIt found: {
            "film_title": "Show Name",
            "season": 3,
            "episode": 16,
            "screen_size": "1080p",
            "format": "WEB-DL",
            "audio_codec": "DolbyDigital",
            "audio_channels": "5.1",
            "video_codec": "h264",
            "title": "GOL",
            "film": 68,
            "type": "episode"
        }

    with this fix:
        GuessIt found: {
            "title": "Show Name",
            "season": 3,
            "episode": 16,
            "screen_size": "1080p",
            "format": "WEB-DL",
            "audio_codec": "DolbyDigital",
            "audio_channels": "5.1",
            "video_codec": "h264",
            "release_group": "GOLF68",
            "type": "episode"
        }
    """

    priority = POST_PROCESS
    consequence = [RemoveMatch, AppendMatch, RenameMatch('title'), RenameMatch('episode')]
    blacklist = ('special', 'season', 'multi')

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        to_remove = []
        to_append = []
        to_rename = []
        to_rename_ep = []

        fileparts = matches.markers.named('path')
        for filepart in marker_sorted(fileparts, matches):
            film_title = matches.range(filepart.start, filepart.end, index=0,
                                       predicate=lambda match: match.name == 'film_title' and not match.raw.isdigit())
            if film_title:
                title = matches.range(filepart.start, filepart.end,
                                      predicate=lambda match: match.name == 'title', index=0)

                if title:
                    if title.value.lower() in self.blacklist:
                        to_remove.append(title)
                    if title.value.isdigit() and matches.previous(title, predicate=lambda m: m.name == 'episode'):
                        title.value = int(title.value)
                        to_rename_ep.append(title)

                to_rename.append(film_title)

            film = matches.range(filepart.start, filepart.end, predicate=lambda match: match.name == 'film', index=-1)
            if not film or not film.raw.isdigit():
                continue

            previous = matches.previous(film, predicate=lambda match: match.start >= filepart.start, index=0)
            if not previous:
                continue

            to_remove.append(film)
            hole = matches.holes(previous.end, film.start, index=0)
            if not hole or hole.value.lower() != 'f':
                continue

            new_property = copy.copy(previous)
            new_property.value = cleanup(previous.raw + hole.value + film.raw)
            new_property.end = film.end
            if previous.name == 'title':
                new_property.name = 'release_group'
                new_property.tags = []
                to_remove.extend(matches.named('release_group'))

            if previous.name != 'release_group':
                release_groups = matches.range(filepart.start, filepart.end,
                                               predicate=lambda match: match.name == 'release_group')
                to_remove.extend(release_groups)
            to_remove.append(previous)

            to_append.append(new_property)

        return to_remove, to_append, to_rename, to_rename_ep


class CreateAliasWithAlternativeTitles(Rule):
    """Create alias property using alternative titles.

    'alias' - post processor to create aliases using alternative titles.

    e.g.: [SuperGroup].Show.Name.-.Still+Name.-.11.[1080p]

    guessit -t episode "[SuperGroup].Show.Name.-.Still+Name.-.11.[1080p]"

    without this rule:
        For: [SuperGroup].Show.Name.-.Still+Name.-.11.[1080p]
        GuessIt found: {
            "release_group": "SuperGroup",
            "title": "Show Name",
            "alternative_title": [
                "Still",
                "Name"
            ],
            "episode": 11,
            "screen_size": "1080p",
            "type": "episode"
        }

    with this rule:
        For: [SuperGroup].Show.Name.-.Still+Name.-.11.[1080p]
        GuessIt found: {
            "release_group": "SuperGroup",
            "title": "Show Name",
            "alternative_title": [
                "Still",
                "Name"
            ],
            "alias": "Show Name - Still+Name"
            "episode": 11,
            "screen_size": "1080p",
            "type": "episode"
        }
    """

    priority = POST_PROCESS
    consequence = AppendMatch
    blacklist = ('temporada', 'temp', 'tem')

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        # Do not concatenate the titles if it's not an anime and there are languages
        if not matches.tagged('anime') and matches.named('language'):
            return

        fileparts = matches.markers.named('path')
        for filepart in marker_sorted(fileparts, matches):
            title = matches.range(filepart.start, filepart.end, predicate=lambda match: match.name == 'title', index=0)
            if not title:
                continue

            if matches.range(filepart.start, filepart.end, predicate=lambda match:
                             (match.name == 'alternative_title' and match.value.lower() in self.blacklist)):
                continue

            alternative_titles = matches.range(filepart.start, filepart.end,
                                               predicate=lambda match: match.name == 'alternative_title')
            if not alternative_titles:
                continue

            previous = title
            alias = copy.copy(title)
            alias.name = 'alias'
            alias.value = title.value

            # extended title is the concatenation between title and all alternative titles
            for alternative_title in alternative_titles:
                holes = matches.holes(start=previous.end, end=alternative_title.start)
                # if the separator is a dash, add an extra space before and after
                separators = [' ' + h.value + ' ' if h.value == '-' else h.value for h in holes]
                separator = ' '.join(separators) if separators else ' '
                alias.value += separator + alternative_title.value

                previous = alternative_title

            alias.end = previous.end
            return alias


class CreateAliasWithCountryOrYear(Rule):
    """Create alias property using country or year information.

    'alias' - post processor to create alias using country or year in addition to the existing title.

    e.g.: Show.Name.US.S03.720p.BluRay.x264-SuperGroup

    guessit -t episode "Show.Name.US.S03.720p.BluRay.x264-SuperGroup"

    without this rule:
        For: Show.Name.US.S03.720p.BluRay.x264-SuperGroup
        GuessIt found: {
            "title": "Show Name",
            "country": "UNITED STATES",
            "season": 3,
            "screen_size": "720p",
            "format": "BluRay",
            "video_codec": "h264",
            "release_group": "SuperGroup",
            "type": "episode"
        }

    with this rule:
        For: Show.Name.US.S03.720p.BluRay.x264-SuperGroup
        GuessIt found: {
            "title": "Show Name",
            "alias": "Show Name US"
            "country": "UNITED STATES",
            "season": 3,
            "screen_size": "720p",
            "format": "BluRay",
            "video_codec": "h264",
            "release_group": "SuperGroup",
            "type": "episode"
        }
    """

    priority = POST_PROCESS
    consequence = AppendMatch
    affected_names = ('country', 'year')

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        fileparts = matches.markers.named('path')
        for filepart in marker_sorted(fileparts, matches):
            title = matches.range(filepart.start, filepart.end, predicate=lambda match: match.name == 'title', index=0)
            if not title:
                continue

            after_title = matches.next(title, index=0,
                                       predicate=lambda match: (
                                           match.end <= filepart.end and match.name in self.affected_names))

            # only if there's a country or year
            if not after_title:
                continue

            # skip if season == year. E.g.: Show.Name.S2016E01
            if matches.conflicting(after_title, predicate=lambda match: match.name == 'season', index=0):
                continue

            # Only add country or year if the next match is season, episode or date
            next_match = matches.next(after_title, index=0,
                                      predicate=lambda match: match.name in ('season', 'episode', 'date'))
            if next_match:
                alias = copy.copy(title)
                alias.name = 'alias'
                alias.value = alias.value + ' ' + re.sub(r'\W*', '', str(after_title.raw))
                alias.end = after_title.end
                alias.raw_end = after_title.raw_end
                return alias


class FixTvChaosUkWorkaround(Rule):
    """Fix TV Chaos UK workaround.

    Medusa adds .hdtv.x264 to tv chaos uk releases. The video_codec might conflict with existing video_codec in the
    original release name.

    e.g.: Show.Name.Season.1.XviD.hdtv.x264

    guessit -t episode "Show.Name.Season.1.XviD.hdtv.x264"

    without this fix:
        For: Show.Name.Season.1.XviD.hdtv.x264
        GuessIt found: {
            "title": "Show Name",
            "season": 1,
            "video_codec": [
                "XviD",
                "h264"
            ],
            "format": "HDTV",
            "type": "episode"
        }

    with this fix:
        For: Show.Name.Season.1.XviD.hdtv.x264
        GuessIt found: {
            "title": "Show Name",
            "season": 1,
            "video_codec": "XviD",
            "format": "HDTV",
            "type": "episode"
        }
    """

    priority = POST_PROCESS
    consequence = RemoveMatch

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        to_remove = []

        fileparts = matches.markers.named('path')
        for filepart in marker_sorted(fileparts, matches):
            m_x264 = matches.ending(filepart.end, predicate=lambda match: match.name == 'video_codec' and match.value == 'h264', index=0)
            if not m_x264:
                continue

            m_hdtv = matches.previous(m_x264, predicate=lambda match: match.name == 'format' and match.value == 'HDTV', index=0)
            if not m_hdtv:
                continue

            video_codecs = matches.range(filepart.start, filepart.end, lambda match: match.name == 'video_codec')
            formats = matches.range(filepart.start, filepart.end, predicate=lambda match: match.name == 'format')
            unique_codecs = {v.value for v in video_codecs}
            unique_formats = {v.value for v in formats}
            if len(unique_codecs) > 1:
                to_remove.append(m_x264)
                if len(unique_formats) <= 1:
                    m_hdtv.tags.append('tvchaosuk')
            if len(unique_formats) > 1:
                to_remove.append(m_hdtv)
                if len(unique_codecs) <= 1:
                    m_x264.tags.append('tvchaosuk')

        return to_remove


class AnimeWithSeasonAbsoluteEpisodeNumbers(Rule):
    """Add season to title for specific anime patterns.

    There are animes where the title contains the season number.

    Medusa rule:
    - The season should be part of the series name
    - The episode should still use absolute numbering

    e.g.: [Group].Show.Name.S2.-.19.[1080p]

    guessit -t episode "[Group].Show.Name.S2.-.19.[1080p]"

    without this rule:
        For: [Group].Show.Name.S2.-.19.[1080p]
        GuessIt found: {
            "release_group": "Group",
            "title": "Show Name",
            "season": 2,
            "episode_title": "19",
            "screen_size": "1080p",
            "type": "episode"
        }

    with this rule:
        For: [Group].Show.Name.S2.-.19.[1080p]
        GuessIt found: {
            "release_group": "Group",
            "title": "Show Name S2",
            "absolute_episode": "19",
            "screen_size": "1080p",
            "type": "episode"
        }
    """

    priority = POST_PROCESS
    consequence = [RemoveMatch, AppendMatch]

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        if context.get('show_type') == 'normal' or not matches.tagged('anime') or matches.tagged('newpct'):
            return

        fileparts = matches.markers.named('path')
        for filepart in marker_sorted(fileparts, matches):
            seasons = matches.range(filepart.start, filepart.end, predicate=lambda match: match.name == 'season')
            for season in seasons:
                if not season.parent or not season.parent.private:
                    continue

                title = matches.previous(season, index=-1,
                                         predicate=lambda match: match.name == 'title' and match.end <= filepart.end)
                episode_title = matches.next(season, index=0,
                                             predicate=lambda match: (match.name == 'episode_title' and
                                                                      match.end <= filepart.end and
                                                                      match.value.isdigit()))

                # the previous match before the season is the series name and
                # the match after season is episode title and episode title is a number
                if not title or not episode_title:
                    continue

                to_remove = []
                to_append = []

                # adjust title to append the series name.
                # Only the season.parent contains the S prefix in its value
                new_title = copy.copy(title)
                new_title.value = ' '.join([title.value, season.parent.value])
                new_title.end = season.end

                # other fileparts might have the same season to be removed from the matches
                # e.g.: /Show.Name.S2/[Group].Show.Name.S2.-.19.[1080p]
                to_remove.extend(matches.named('season', predicate=lambda match: match.value == season.value))
                to_remove.append(title)
                to_append.append(new_title)

                # move episode_title to absolute_episode
                absolute_episode = copy.copy(episode_title)
                absolute_episode.name = 'absolute_episode'
                absolute_episode.value = int(episode_title.value)

                # always keep episode (subliminal needs it)
                episode = copy.copy(absolute_episode)
                episode.name = 'episode'

                to_remove.append(episode_title)
                to_append.append(absolute_episode)
                to_append.append(episode)
                return to_remove, to_append


class AnimeAbsoluteEpisodeNumbers(Rule):
    """Move episode numbers to absolute episode numbers for animes.

    Medusa rule: If it's an anime, prefer absolute episode numbers.

    e.g.: [Group].Show.Name.-.102.[720p]

    guessit -t episode "[Group].Show.Name.-.102.[720p]"

    without this rule:
        For: [Group].Show.Name.-.102.[720p]
        GuessIt found: {
            "release_group": "Group",
            "title": "Show Name",
            "season": 1,
            "episode": 2,
            "screen_size": "720p",
            "type": "episode"
        }

    with this rule:
        For: [Group].Show.Name.-.102.[720p]
        GuessIt found: {
            "release_group": "Group",
            "title": "Show Name",
            "absolute_episode": 102,
            "screen_size": "720p",
            "type": "episode"
        }
    """

    priority = POST_PROCESS
    consequence = [RemoveMatch, AppendMatch]

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        weak_duplicate = matches.tagged('weak-duplicate', index=0)
        # only for shows that seems to be animes
        if context.get('show_type') == 'normal' or not weak_duplicate or matches.tagged('newpct'):
            return

        # if it's not detected as anime and season (weak_duplicate) is not 0, then skip.
        if not matches.named('video_profile') and not matches.tagged('anime') and weak_duplicate.value > 0:
            return

        fileparts = matches.markers.named('path')
        for filepart in marker_sorted(fileparts, matches):
            season = matches.range(filepart.start, filepart.end, index=0,
                                   predicate=lambda match: match.name == 'season' and match.raw.isdigit())
            if not season:
                continue

            episode = matches.next(season, index=0,
                                   predicate=lambda match: (match.name == 'episode' and
                                                            match.end <= filepart.end and
                                                            match.raw.isdigit()))

            # there should be season and episode and the episode should start right after the season and both raw values
            # should be digit
            if season and episode and season.end == episode.start:
                # then make them an absolute episode:
                absolute_episode = copy.copy(episode)
                absolute_episode.name = 'absolute_episode'
                # raw value contains the season and episode altogether
                absolute_episode.value = int(episode.parent.raw if episode.parent else episode.raw)

                # always keep episode (subliminal needs it)
                corrected_episode = copy.copy(absolute_episode)
                corrected_episode.name = 'episode'

                to_remove = [season, episode]
                to_append = [absolute_episode, corrected_episode]
                return to_remove, to_append


class AbsoluteEpisodeNumbers(Rule):
    """Move episode numbers to absolute episode numbers for animes without season.

    Medusa absolute episode numbers rule. For animes without season, prefer absolute numbers.

    e.g.: Show.Name.10.720p

    guessit -t episode "Show.Name.10.720p"

    without this rule:
        For: Show.Name.10.720p
        GuessIt found: {
            "title": "Show Name",
            "episode": 10,
            "screen_size": "720p",
            "type": "episode"
        }

    with this rule:
        For: Show.Name.10.720p
        GuessIt found: {
            "title": "Show Name",
            "absolute_episode": 10,
            "screen_size": "720p",
            "type": "episode"
        }

    """

    priority = POST_PROCESS
    consequence = [RemoveMatch, AppendMatch]
    non_words_re = re.compile(r'\W')
    episode_words = ('e', 'episode', 'ep')

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        # if it seems to be anime and it doesn't have season
        if context.get('show_type') != 'normal' and not matches.named('season') and not matches.tagged('newpct'):
            episodes = matches.named('episode')
            to_remove = []
            to_append = []
            for episode in episodes:
                # And there's no episode count
                if matches.named('episode_count'):
                    # Some.Show.1of8..Title.x264.AAC.Group
                    # not absolute episode
                    return

                previous = matches.previous(episode, index=-1)
                if previous:
                    hole = matches.holes(start=previous.end, end=episode.start, index=0)
                    # and the hole is not an 'episode' word (e.g.: e, ep, episode)
                    if previous.name != 'episode':
                        if hole and self.non_words_re.sub('', hole.value).lower() in self.episode_words:
                            # if version is present, then it's an anime
                            if not matches.named('version') and not matches.tagged('anime'):
                                # Some.Show.E07.1080p.HDTV.x265-GROUP
                                # Some.Show.Episode.10.Some.Title.720p
                                # not absolute episode
                                return
                    elif hole and hole.value == '.':
                        # [GroupName].Show.Name.-.02.5.(Special).[BD.1080p]
                        # 5 is not absolute, and not an episode BTW
                        to_remove.append(episode)
                        continue

                absolute_episode = copy.copy(episode)
                absolute_episode.name = 'absolute_episode'
                to_append.append(absolute_episode)

            return to_remove, to_append


class PartsAsEpisodeNumbers(Rule):
    """Move part to episode.

    Medusa rule: Parts are treated as episodes.

    e.g.: Show.Name.Part.3.720p.HDTV.x264-Group

    guessit -t episode "Show.Name.Part.3.720p.HDTV.x264-Group"

    without the rule:
        For: Show.Name.Part.3.720p.HDTV.x264-Group
        GuessIt found: {
            "title": "Show Name",
            "part": 3,
            "screen_size": "720p",
            "format": "HDTV",
            "video_codec": "h264",
            "release_group": "Group",
            "type": "episode"
        }

    without the rule:
        For: Show.Name.Part.3.720p.HDTV.x264-Group
        GuessIt found: {
            "title": "Show Name",
            "episode": 3,
            "screen_size": "720p",
            "format": "HDTV",
            "video_codec": "h264",
            "release_group": "Group",
            "type": "episode"
        }
    """

    priority = POST_PROCESS
    consequence = RenameMatch('episode')

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        # only if there's no season and no episode
        to_rename = []
        fileparts = matches.markers.named('path')
        for filepart in marker_sorted(fileparts, matches):
            parts = matches.range(filepart.start, filepart.end, predicate=lambda match: match.name == 'part')
            if parts and not matches.range(filepart.start, filepart.end,
                                           predicate=lambda match: match.name in ('season', 'episode', 'date')):
                to_rename.extend(parts)

        return to_rename


class ExpectedTitlePostProcessor(Rule):
    r"""Post process the title when it matches an expected title.

    Expected title post processor to replace dots with spaces (needed when expected title is a regex).

    e.g.: Show.Net.S01E06.720p

    guessit -t episode -T "re:^\w+ Net\b" "Show.Net.S01E06.720p"

    without this rule:
        For: Show.Net.S01E06.720p
        GuessIt found: {
            "title": "Show.Net",
            "season": 1,
            "episode": 6,
            "screen_size": "720p",
            "type": "episode"
        }

    with this rule:
        For: Show.Net.S01E06.720p
        GuessIt found: {
            "title": "Show Net",
            "season": 1,
            "episode": 6,
            "screen_size": "720p",
            "type": "episode"
        }
    """

    priority = POST_PROCESS
    consequence = [RemoveMatch, AppendMatch]

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        # All titles that matches because of a expected title was tagged as 'expected'
        # and title.value is not in the expected list, it's a regex
        titles = matches.tagged('expected', predicate=lambda match: match.value not in context.get('expected_title'))

        to_remove = []
        to_append = []

        for title in titles:
            # Remove all dots from the title
            new_title = copy.copy(title)  # IMPORTANT - never change the value. Better to remove and add it
            new_title.value = cleanup(title.value)
            # important to remove tags from title: equivalent-ignore. Otherwise guessit exception might occur
            # when more than 2 equivalent titles are found and episode title has number that conflicts with year
            title.tags = []
            to_remove.append(title)
            to_append.append(new_title)

        return to_remove, to_append


class FixMultipleReleaseGroups(Rule):
    """Fix multiple release groups.

    TODO: Document
    """

    priority = POST_PROCESS
    consequence = RemoveMatch

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        # In case of duplicated titles, keep only the first one
        release_groups = matches.named('release_group')

        if len(release_groups) > 1:
            selected = [r for r in release_groups if r.pattern]
            if selected:
                selected = selected[0]
            else:
                selected = release_groups[0] if matches.tagged('anime') else release_groups[-1]
            # Safety:
            # Only remove matches that are different from the first match
            to_remove = matches.named('release_group', predicate=lambda match: match.span != selected.span)
            return to_remove


class FixMultipleFormats(Rule):
    """Fix multiple formats.

    Related to guessit bug: https://github.com/guessit-io/guessit/issues/327

    e.g.: Show.Name.S02E01.eps2.0.unm4sk-pt1.tc.1080p.WEB-DL.DD5.1.H264-GROUP

    guessit -t episode "Show.Name.S02E01.eps2.0.unm4sk-pt1.tc.1080p.WEB-DL.DD5.1.H264-GROUP"

    without this rule:
        For: Show.Name.S02E01.eps2.0.unm4sk-pt1.tc.1080p.WEB-DL.DD5.1.H264-GROUP
        GuessIt found: {
            "title": "Show Name",
            "season": 2,
            "episode": 1,
            "episode_title": "eps2 0 unm4sk",
            "part": 1,
            "format": [
                "Telecine",
                "WEB-DL"
            ],
            "screen_size": "1080p",
            "audio_codec": "DolbyDigital",
            "audio_channels": "5.1",
            "video_codec": "h264",
            "release_group": "GROUP",
            "type": "episode"
        }


    with this rule:
        For: Show.Name.S02E01.eps2.0.unm4sk-pt1.tc.1080p.WEB-DL.DD5.1.H264-GROUP
        GuessIt found: {
            "title": "Show Name",
            "season": 2,
            "episode": 1,
            "episode_title": "eps2 0 unm4sk",
            "part": 1,
            "format": "WEB-DL",
            "screen_size": "1080p",
            "audio_codec": "DolbyDigital",
            "audio_channels": "5.1",
            "video_codec": "h264",
            "release_group": "GROUP",
            "type": "episode"
        }
    """

    priority = POST_PROCESS
    consequence = RemoveMatch

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        fileparts = matches.markers.named('path')
        for filepart in marker_sorted(fileparts, matches):
            formats = matches.range(filepart.start, filepart.end, predicate=lambda match: match.name == 'format')
            if len(formats) < 2:
                continue

            for candidate in reversed(formats):
                previous = matches.previous(candidate, predicate=lambda match: match.name == 'screen_size')
                next_range = matches.range(candidate.end, filepart.end,
                                           lambda match: match.name in ('audio_codec', 'video_codec', 'release_group'))
                # If we have at least 3 matches near by, then discard the other formats
                if len(previous) + len(next_range) > 1:
                    invalid_formats = {f.value for f in formats[0:-1]}
                    to_remove = matches.named('format', predicate=lambda m: m.value in invalid_formats)
                    return to_remove

                if matches.conflicting(candidate):
                    to_remove = matches.named('format', predicate=lambda m: m.value in candidate.value)
                    return to_remove


class CreateProperTags(Rule):
    """Create the proper_tags property from the proper matches.

    e.g.: guessit -t episode "Show.Name.S03E08.REPACK.PROPER.HDTV.x264-GROUP"

    without this rule:
        For: Show.Name.S03E08.REPACK.PROPER.HDTV.x264-GROUP
        GuessIt found: {
            "title": "Show Name",
            "season": 3,
            "episode": 8,
            "other": "Proper",
            "proper_count": 2,
            "format": "HDTV",
            "video_codec": "h264",
            "release_group": "GROUP",
            "type": "episode"
        }

    with this rule:
        For: Show.Name.S03E08.REPACK.PROPER.HDTV.x264-GROUP
        GuessIt found: {
            "title": "Show Name",
            "season": 3,
            "episode": 8,
            "other": "Proper",
            "proper_count": 2,
            "proper_tag": ["REPACK", "PROPER"]
            "format": "HDTV",
            "video_codec": "h264",
            "release_group": "GROUP",
            "type": "episode"
        }
    """

    priority = POST_PROCESS
    consequence = AppendMatch

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        to_append = []
        for proper in matches.named('other', predicate=lambda match: match.value == 'Proper'):
            tag = copy.copy(proper)
            tag.name = 'proper_tag'
            tag.value = cleanup(proper.raw.upper())
            to_append.append(tag)

        return to_append


class ScreenSizeStandardizer(Rule):
    """Standardize the screen size.

    Fix 360i, 480i, 576i, etc which are detected as progressive.
    Rename 4K to 2160p
    """

    priority = POST_PROCESS
    consequence = [RemoveMatch, AppendMatch]

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        to_remove = []
        to_append = []
        for screen_size in matches.named('screen_size'):
            if screen_size.raw.lower().endswith('i'):
                new_size = copy.copy(screen_size)
                new_size.value = screen_size.value.replace('p', 'i')
                to_remove.append(screen_size)
                to_append.append(new_size)
            elif screen_size.value == '4K':
                new_size = copy.copy(screen_size)
                new_size.value = '2160p'
                to_remove.append(screen_size)
                to_append.append(new_size)

        return to_remove, to_append


class AudioCodecStandardizer(Rule):
    """DolbyDigital is AC3.

    Rename DolbyDigital to AC3
    """

    priority = POST_PROCESS
    consequence = [RemoveMatch, AppendMatch]

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        to_remove = []
        to_append = []
        for audio_codec in matches.named('audio_codec', predicate=lambda m: m.value in ('DolbyDigital', )):
            new_codec = copy.copy(audio_codec)
            new_codec.value = 'AC3'
            to_remove.append(audio_codec)
            to_append.append(new_codec)

        return to_remove, to_append


class FormatStandardizer(Rule):
    """DVB renamed to PDTV."""

    priority = POST_PROCESS
    consequence = [RemoveMatch, AppendMatch]

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        to_remove = []
        to_append = []
        for source in matches.named('format', predicate=lambda m: m.value in ('DVB', )):
            new_format = copy.copy(source)
            new_format.value = 'PDTV'
            to_remove.append(source)
            to_append.append(new_format)

        return to_remove, to_append


class VideoEncoderRule(Rule):
    """Add video encoders: x264, x265."""

    priority = POST_PROCESS
    consequence = AppendMatch

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        to_append = []
        for video_codec in matches.named('video_codec', lambda m: m.value in ('h264', 'h265') and 'x26' in m.raw.lower()):
            encoder = copy.copy(video_codec)
            encoder.name = 'video_encoder'
            encoder.value = encoder.value.replace('h', 'x')
            to_append.append(encoder)

        return to_append


class AvoidMultipleValuesRule(Rule):
    """Avoid multiple values."""

    priority = POST_PROCESS
    consequence = RemoveMatch

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        to_remove = []
        for name in ('episode_title', 'format', 'release_group', 'title'):
            values = matches.named(name)
            unique_values = {v.value for v in values}
            if len(unique_values) > 1:
                if name == 'title':
                    to_remove.extend(matches.named('title', predicate=lambda match: match.value != values[0].value))
                    continue

                logger.info(u"Guessed more than one '%s' for '%s': %s",
                            name, matches.input_string, u','.join(unique_values), exc_info=False)
                to_remove.extend(values)

        return to_remove


class ReleaseGroupPostProcessor(Rule):
    """Post process release group.

    Removes invalid parts from the release group property.

    e.g.: Some.Show.S02E14.1080p.HDTV.X264-GROUP[TRASH]

    guessit -t episode "Some.Show.S02E14.1080p.HDTV.X264-GROUP[TRASH]"

    without this post processor:
        For: Some.Show.S02E14.1080p.HDTV.X264-GROUP[TRASH]
        GuessIt found: {
            "title": "Some Show",
            "season": 2,
            "episode": 14,
            "screen_size": "1080p",
            "format": "HDTV",
            "video_codec": "h264",
            "release_group": "GROUP[TRASH]",
            "type": "episode"
        }


    with this post processor:
        For: Some.Show.S02E14.1080p.HDTV.X264-GROUP[TRASH]
        GuessIt found: {
            "title": "Some Show",
            "season": 2,
            "episode": 14,
            "screen_size": "1080p",
            "format": "HDTV",
            "video_codec": "h264",
            "release_group": "GROUP",
            "type": "episode"
        }
    """

    priority = POST_PROCESS
    consequence = [RemoveMatch, AppendMatch]
    regexes = [
        # italian release: drop everything after [CURA]
        re.compile(r'\[CURA\].*$', flags=re.IGNORECASE),

        # NLSubs-word
        re.compile(r'\W*\b([a-z]{1,3}[\.\-]?)?(subs?)\b\W*', flags=re.IGNORECASE),

        # https://github.com/guessit-io/guessit/issues/302
        re.compile(r'\W*\b(obfuscated|dual|audio)\b\W*', flags=re.IGNORECASE),
        re.compile(r'\W*\b(vtv|sd|avc|rp|norar|re\-?up(loads?)?)\b\W*', flags=re.IGNORECASE),
        re.compile(r'\W*\b(hebits)\b\W*', flags=re.IGNORECASE),

        # [word], (word), {word}
        re.compile(r'(?<=.)\W*[\[\(\{].+[\}\)\]]?\W*$', flags=re.IGNORECASE),

        # https://github.com/guessit-io/guessit/issues/301
        # vol255+101
        re.compile(r'\.vol\d+\+\d+', flags=re.IGNORECASE),

        # word.rar, word.gz
        re.compile(r'\.((rar)|(gz)|(\d+))$', flags=re.IGNORECASE),

        # word.rartv, word.ettv
        re.compile(r'(?<=[a-z0-9]{3})\.([a-z]+)$', flags=re.IGNORECASE),

        # word__gZasDuF
        re.compile(r'(?<=[a-z0-9]{3})_{2,}([a-z]+)$', flags=re.IGNORECASE),

        # word.a00, word.b12
        re.compile(r'(?<=[a-z0-9]{3})\.([a-z]\d{2,3})$', flags=re.IGNORECASE),

        # word-1234, word-456
        re.compile(r'(?<=[a-z0-9]{3})\-(\d{3,4})$', flags=re.IGNORECASE),

        # word-fansub
        re.compile(r'(?<=[a-z0-9]{3})\-((fan)?sub(s)?)$', flags=re.IGNORECASE),

        # ...word
        re.compile(r'^\W+', flags=re.IGNORECASE),

        # word[.
        re.compile(r'\W+$', flags=re.IGNORECASE),

        re.compile(r'\s+', flags=re.IGNORECASE),
    ]

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        release_groups = matches.named('release_group')
        to_remove = []
        to_append = []
        for release_group in release_groups:
            value = release_group.value
            for regex in self.regexes:
                value = regex.sub(' ', value).strip()
                if not value:
                    break

            if value and matches.tagged('scene') and not matches.next(release_group):
                value = value.split('-')[0]

            if release_group.value != value:
                to_remove.append(release_group)
                if value:
                    new_release_group = copy.copy(release_group)
                    new_release_group.value = clean_groupname(value)
                    to_append.append(new_release_group)

        return to_remove, to_append


def rules():
    """Return all custom rules to be applied to guessit default api.

    IMPORTANT! The order is important.
    Certain rules needs to be executed first, and others should be executed at the end.
    DO NOT define priority or dependency in each rule, it can become a mess. Better to just define the correct order
    in this method.

    Builder for rebulk object.
    :return: Created Rebulk object
    :rtype: Rebulk
    """
    return Rebulk().rules(
        BlacklistedReleaseGroup,
        FixTvChaosUkWorkaround,
        EpisodeNumberRule,
        FixAnimeReleaseGroup,
        SpanishNewpctReleaseName,
        FixInvalidTitleOrAlternativeTitle,
        FixSeasonAndEpisodeConflicts,
        FixWrongTitleDueToFilmTitle,
        FixSeasonRangeWithGap,
        RemoveInvalidEpisodes,
        AnimeWithSeasonAbsoluteEpisodeNumbers,
        AnimeAbsoluteEpisodeNumbers,
        AbsoluteEpisodeNumbers,
        PartsAsEpisodeNumbers,
        ExpectedTitlePostProcessor,
        CreateAliasWithAlternativeTitles,
        CreateAliasWithCountryOrYear,
        ReleaseGroupPostProcessor,
        FixMultipleFormats,
        FixMultipleReleaseGroups,
        ScreenSizeStandardizer,
        AudioCodecStandardizer,
        FormatStandardizer,
        VideoEncoderRule,
        CreateProperTags,
        AvoidMultipleValuesRule,
    )
