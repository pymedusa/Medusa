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
from __future__ import unicode_literals

import copy
import logging
import re

from guessit.rules.common.comparators import marker_sorted
from guessit.rules.common.formatters import cleanup

from rebulk.processors import POST_PROCESS
from rebulk.rebulk import Rebulk
from rebulk.rules import AppendMatch, RemoveMatch, RenameMatch, Rule

from six import text_type
from six.moves import range

log = logging.getLogger(__name__)

simple_separator = ('.', 'and', ',.', '.,', '.,.', ',', '.&.', ' & ')
range_separator = ('-', '~', '_-_', 'to', '.to.')


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
            "color_depth": "10-bit",
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
            "color_depth": "10-bit",
            "release_group": "RealGroup",
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
        if context.get('show_type') == 'normal':
            return

        fileparts = matches.markers.named('path')
        for filepart in marker_sorted(fileparts, matches):
            # get the group (e.g.: [abc]) at the beginning of this filepart
            group = matches.markers.at_index(filepart.start, index=0, predicate=lambda marker: marker.name == 'group')
            if not group or matches.at_match(group):
                continue

            # don't use websites as release group
            websites = matches.named('website')
            if websites and any(ws for ws in websites if ws.value in group.value):
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


class FixInvalidAbsoluteReleaseGroups(Rule):
    """Fix invalid release groups due to absolute episode numbers range.

    Some release names have season/episode defined twice (relative and absolute), and the ending
    absolute episode becomes the release_group. This fix will remove the invalid release_group
    and add the correct absolute episode ranges.

    e.g.: "Show.Name.s16e03-05.313-315"

    guessit -t episode "Show.Name.s16e03-05.313-315"

    without this fix:
        For: Show.Name.s16e03-05.313-315
        GuessIt found: {
            "title": "Show Name",
            "season": 16,
            "episode": [
                3,
                4,
                5
            ],
            "absolute_episode": 313,
            "release_group": "315",
            "type": "episode"
        }


    with this fix:
        For: Show.Name.s16e03-05.313-315
        GuessIt found: {
            "title": "Show Name",
            "season": 16,
            "episode": [
                3,
                4,
                5
            ],
            "absolute_episode": [
                313,
                314,
                315
            ],
            "type": "episode"
        }
    """

    priority = POST_PROCESS
    consequence = [RemoveMatch, AppendMatch]
    absolute_re = re.compile(r'([\W|_]*)(?P<absolute_episode_start>\d{2,4})(?:-(?P<absolute_episode_end>\d{3,4}))?\W*$')

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
            # retrieve all problematic groups
            problematic_groups = matches.range(filepart.start, filepart.end,
                                               predicate=lambda match: match.name == 'release_group')

            to_remove = []
            to_append = []

            for group in problematic_groups:
                filename = fileparts[-1].raw
                m = self.absolute_re.search(filename)
                if not m:
                    continue

                # Remove the problematic group
                to_remove.append(group)

                # and add the absolute episode range
                g = m.groupdict()
                if not g['absolute_episode_end']:
                    continue

                absolute_episode_start = int(g['absolute_episode_start'])
                absolute_episode_end = int(g['absolute_episode_end'] or g['absolute_episode_start'])
                for i in range(absolute_episode_start, absolute_episode_end + 1):
                    episode = copy.copy(group)
                    episode.name = 'absolute_episode'
                    episode.value = i
                    if i == absolute_episode_start:
                        episode.start = group.start + m.start('absolute_episode_start')
                        episode.end = group.start + m.end('absolute_episode_start')
                    elif i < absolute_episode_end:
                        episode.start = group.start + m.end('absolute_episode_start')
                        episode.end = group.start + m.start('absolute_episode_end')
                    else:
                        episode.start = group.start + m.start('absolute_episode_end')
                        episode.end = group.start + m.end('absolute_episode_end')

                    to_append.append(episode)

                return to_remove, to_append


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
            return [alias]


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
            "source": "Blu-ray",
            "video_codec": "H.264",
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
            "source": "Blu-ray",
            "video_codec": "H.264",
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
                alias.value = alias.value + ' ' + re.sub(r'\W*', '', after_title.raw)
                alias.end = after_title.end
                alias.raw_end = after_title.raw_end
                return [alias]


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
                "Xvid",
                "H.264"
            ],
            "source": "HDTV",
            "type": "episode"
        }

    with this fix:
        For: Show.Name.Season.1.XviD.hdtv.x264
        GuessIt found: {
            "title": "Show Name",
            "season": 1,
            "video_codec": "Xvid",
            "source": "HDTV",
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
            m_x264 = matches.ending(filepart.end, predicate=lambda match: match.name == 'video_codec' and match.value == 'H.264', index=0)
            if not m_x264:
                continue

            m_hdtv = matches.previous(m_x264, predicate=lambda match: match.name == 'source' and match.value == 'HDTV', index=0)
            if not m_hdtv:
                continue

            video_codecs = matches.range(filepart.start, filepart.end, lambda match: match.name == 'video_codec')
            sources = matches.range(filepart.start, filepart.end, predicate=lambda match: match.name == 'source')
            if len(video_codecs) > 1:
                to_remove.append(m_x264)
                if len(sources) <= 1:
                    m_hdtv.tags.append('tvchaosuk')
            if len(sources) > 1:
                to_remove.append(m_hdtv)
                if len(video_codecs) <= 1:
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
        if context.get('show_type') == 'normal' or not matches.tagged('anime'):
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
            "episode": 102,
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
        if context.get('show_type') == 'normal' or not weak_duplicate:
            return

        # if it's not detected as anime and season (weak_duplicate) is not 0, then skip.
        if not matches.named('video_profile') and not matches.tagged('anime') and weak_duplicate.value > 0:
            is_anime = False
            groups = matches.markers.named('group')
            for group in groups:
                screen_size = matches.range(group.start, group.end, index=0, predicate=lambda match: match.name == 'screen_size')
                if screen_size:
                    is_anime = True
                    screen_size.tags.append('anime')
                    break
            if not is_anime:
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
                absolute_episode.start = season.start
                # raw value contains the season and episode altogether
                absolute_episode.value = int(episode.parent.raw if episode.parent else episode.raw)

                # always keep episode (subliminal needs it)
                corrected_episode = copy.copy(absolute_episode)
                corrected_episode.name = 'episode'
                corrected_episode.start = season.start

                to_remove = [season, episode]
                to_append = [absolute_episode, corrected_episode]

                episode_title = matches.next(episode, index=0, predicate=lambda match: match.name == 'episode_title' and match.value.isdigit())
                if episode_title:
                    if matches.input_string[episode.end:episode_title.start + 1] in range_separator:
                        end_value = int(episode_title.value)
                        for i in range(absolute_episode.value + 1, end_value + 1):
                            episode = copy.copy(absolute_episode)
                            episode.value = i
                            if i < end_value:
                                episode.start = episode.end
                                episode.end = episode_title.start
                            else:
                                episode.start = episode_title.start
                                episode.end = episode_title.end

                            ep = copy.copy(episode)
                            ep.name = 'episode'
                            to_append.append(episode)
                            to_append.append(ep)

                        to_remove.append(episode_title)

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
        if context.get('show_type') != 'normal' and not matches.named('season'):
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
                            if (context.get('show_type') != 'anime' and
                                    not matches.named('version') and not matches.tagged('anime')):
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
            "source": "HDTV",
            "video_codec": "H.264",
            "release_group": "Group",
            "type": "episode"
        }

    without the rule:
        For: Show.Name.Part.3.720p.HDTV.x264-Group
        GuessIt found: {
            "title": "Show Name",
            "episode": 3,
            "screen_size": "720p",
            "source": "HDTV",
            "video_codec": "H.264",
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


class RemoveInvalidEpisodeSeparator(Rule):
    """Remove invalid episode title between absolute episode ranges.

    e.g.: [Zero-Raws].Show.Name.493-498.&.500-507.(CX.1280x720.VFR.x264.AAC)

    guessit -t episode "[Zero-Raws].Show.Name.493-498.&.500-507.(CX.1280x720.VFR.x264.AAC)"

    without the rule:
        For: [Zero-Raws].Show.Name.493-498.&.500-507.(CX.1280x720.VFR.x264.AAC)
        GuessIt found: {
            "release_group": "Zero-Raws",
            "title": "Show Name",
            "episode": [
                493,
                ...
                507
            ],
            "episode_title": "&",
            "screen_size": "720p",
            "aspect_ratio": 1.778,
            "subtitle_language": "French",
            "video_codec": "H.264",
            "audio_codec": "AAC",
            "type": "episode"
        }

    without the rule:
        For: [Zero-Raws].Show.Name.493-498.&.500-507.(CX.1280x720.VFR.x264.AAC)
        GuessIt found: {
            "release_group": "Zero-Raws",
            "title": "Show Name",
            "episode": [
                493,
                ...
                507
            ],
            "screen_size": "720p",
            "aspect_ratio": 1.778,
            "subtitle_language": "French",
            "video_codec": "H.264",
            "audio_codec": "AAC",
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
        episode_title = matches.named('episode_title')

        if len(episode_title) == 1:
            previous = matches.previous(episode_title[0], predicate=lambda match: match.name == 'absolute_episode')
            next_match = matches.next(episode_title[0], predicate=lambda match: match.name == 'absolute_episode')
            if previous and next_match and episode_title[0].raw in simple_separator:
                to_remove = episode_title
                return to_remove


class RemoveYearAsSeason(Rule):
    """Remove invalid season from year.

    Related bug report: https://github.com/guessit-io/guessit/issues/561

    e.g.: Show.Name.2016.Nice.Title.1080p.SESO.WEBRip.AAC2.0.x264-monkee

    guessit -t episode "Show.Name.2016.Nice.Title.1080p.SESO.WEBRip.AAC2.0.x264-monkee"

    without the rule:
        For: Show.Name.2016.Nice.Title.1080p.SESO.WEBRip.AAC2.0.x264-monkee
        GuessIt found: {
            "title": "Show Name",
            "season": 20,
            "year": 2016,
            "episode_title": "Nice Title",
            "screen_size": "1080p",
            "streaming_service": "SeeSo",
            "source": "Web",
            "other": "Rip",
            "audio_codec": "AAC",
            "audio_channels": "2.0",
            "video_codec": "H.264",
            "release_group": "monkee",
            "type": "episode"
        }

    with the rule:
        For: Show.Name.2016.Nice.Title.1080p.SESO.WEBRip.AAC2.0.x264-monkee
        GuessIt found: {
            "title": "Show Name",
            "year": 2016,
            "episode_title": "Nice Title",
            "screen_size": "1080p",
            "streaming_service": "SeeSo",
            "source": "Web",
            "other": "Rip",
            "audio_codec": "AAC",
            "audio_channels": "2.0",
            "video_codec": "H.264",
            "release_group": "monkee",
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
        year = matches.named('year')
        if not year:
            return

        season = matches.named('season')
        if season and season[-1].initiator.value.endswith(text_type(year[0].value)):
            to_remove = season[-1]
            return to_remove


class FixMultipleReleaseGroups(Rule):
    """Fix multiple release groups.

    e.g.: Show.Name.S04E23.Parley.720p.HDTV.x264.DIMENSION.P00/SNLA0423.720p.HDTV.X264-DIMENSION

    guessit -t episode "Show.Name.S04E23.Parley.720p.HDTV.x264.DIMENSION.P00/SNLA0423.720p.HDTV.X264-DIMENSION"

    without the rule:
        For: Show.Name.S04E23.Parley.720p.HDTV.x264.DIMENSION.P00/SNLA0423.720p.HDTV.X264-DIMENSION
        GuessIt found: {
            "title": "Show Name",
            "season": 4,
            "episode": 23,
            "episode_title": "Parley",
            "screen_size": "720p",
            "source": "HDTV",
            "video_codec": "H.264",
            "release_group": "DIMENSION.P00",
            "type": "episode"
        }

    with the rule:
        For: Show.Name.S04E23.Parley.720p.HDTV.x264.DIMENSION.P00/SNLA0423.720p.HDTV.X264-DIMENSION
        GuessIt found: {
            "title": "Show Name",
            "season": 4,
            "episode": 23,
            "episode_title": "Parley",
            "screen_size": "720p",
            "source": "HDTV",
            "video_codec": "H.264",
            "release_group": "DIMENSION",
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


class FixParentFolderReplacingTitle(Rule):
    """Fix folder name replacing title when it ends with digits.

    Related bug report: https://github.com/guessit-io/guessit/issues/565

    e.g.: /Comedy 23/Funny.Show.S4E19.mkv

    guessit -t episode "/Comedy 23/Funny.Show.S4E19.mkv"

    without the rule:
        For: /Comedy 23/Funny.Show.S4E19.mkv
        GuessIt found: {
            "title": "Comedy",
            "episode_title": "Funny Show",
            "season": 4,
            "episode": 19,
            "container": "mkv",
            "mimetype": "video/x-matroska",
            "type": "episode"
        }

    with the rule:
        For: /Comedy 23/Funny.Show.S4E19.mkv
        GuessIt found: {
            "title": "Funny Show",
            "season": 4,
            "episode": 19,
            "container": "mkv",
            "mimetype": "video/x-matroska",
            "type": "episode"
        }
    """

    priority = POST_PROCESS
    consequence = [RemoveMatch, AppendMatch]
    ends_with_digit = re.compile(r'(_|\W)\d+$')

    def when(self, matches, context):
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        fileparts = matches.markers.named('path')
        parts_len = len(fileparts)
        if parts_len < 2:
            return

        episode_title = matches.named('episode_title')
        if episode_title:
            second_part = fileparts[parts_len - 2].value
            if self.ends_with_digit.search(second_part):
                title = matches.named('title')
                if not title or second_part.startswith(title[0].value):
                    episode_title[0].name = 'title'
                    to_append = episode_title
                    to_remove = title

                    return to_remove, to_append


class FixWordAsLanguage(Rule):
    """Fix word getting parsed as language with multiple fileparts.

    e.g.: Por Trece Razones - Temporada 2 [HDTV 720p][Cap.201][AC3 5.1 Castellano]/Por Trece Razones 2x01 [des202].mkv

    without the rule:
        GuessIt found: {
            "language": [
                "Portuguese",
                "Catalan"
            ],
            "title": "Trece Razones",
            "season": 2,
            "source": "HDTV",
            "screen_size": "720p",
            "episode": 1,
            "audio_codec": "Dolby Digital",
            "audio_channels": "5.1",
            "release_group": "des202",
            "container": "mkv",
            "mimetype": "video/x-matroska",
            "type": "episode"
        }

    with the rule:
        GuessIt found: {
            "language": "Catalan",
            "title": "Por Trece Razones",
            "season": 2,
            "source": "HDTV",
            "screen_size": "720p",
            "episode": 1,
            "audio_codec": "Dolby Digital",
            "audio_channels": "5.1",
            "release_group": "des202",
            "container": "mkv",
            "mimetype": "video/x-matroska",
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
        languages = matches.named('language')
        if not languages:
            return

        fileparts = matches.markers.named('path')
        parts_len = len(fileparts)
        if parts_len < 2:
            return

        titles = matches.named('title')
        first_title = titles[0]
        last_title = titles[-1]

        # Always use the first langauge
        first_language = languages[0]
        for language in languages[1:]:
            if language.start < first_language.start:
                first_language = language

        lang_start = first_language.start
        lang_end = first_language.end

        start = end = None
        # Language is before titles
        if lang_end == first_title.start:
            start = lang_start
            end = last_title.end
        # Language is after titles
        elif last_title.end == lang_start:
            start = first_title.start
            end = lang_end
        # Language is between titles
        elif len(titles) > 1:
            lang_code = last_title.value.split()[0].lower()
            if lang_code in context.get('allowed_languages', []):
                start = first_title.start
                end = last_title.end

        if start is not None:
            second_filepart = fileparts[parts_len - 2]
            rel_start = start - second_filepart.start
            rel_end = end - second_filepart.end

            new_title = second_filepart.value[rel_start:rel_end]
            titles[0].value = cleanup(new_title)

            to_append = titles[0]
            to_remove = first_language

            return to_remove, to_append


class FixMultipleSources(Rule):
    """Fix multiple sources.

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
            "source": [
                "Telecine",
                "Web"
            ],
            "screen_size": "1080p",
            "audio_codec": "Dolby Digital",
            "audio_channels": "5.1",
            "video_codec": "H.264",
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
            "source": "Web",
            "screen_size": "1080p",
            "audio_codec": "Dolby Digital",
            "audio_channels": "5.1",
            "video_codec": "H.264",
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
            sources = matches.range(filepart.start, filepart.end, predicate=lambda match: match.name == 'source')
            if len(sources) < 2:
                continue

            for candidate in reversed(sources):
                previous = matches.previous(candidate, predicate=lambda match: match.name == 'screen_size')
                next_range = matches.range(candidate.end, filepart.end,
                                           lambda match: match.name in ('audio_codec', 'video_codec', 'release_group'))
                # If we have at least 3 matches near by, then discard the other sources
                if len(previous) + len(next_range) > 1:
                    invalid_sources = {f.value for f in sources[0:-1]}
                    to_remove = matches.named('source', predicate=lambda m: m.value in invalid_sources)
                    return to_remove

                if matches.conflicting(candidate):
                    to_remove = matches.named('source', predicate=lambda m: m.value in candidate.value)
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
            "source": "HDTV",
            "video_codec": "H.264",
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
            "source": "HDTV",
            "video_codec": "H.264",
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


class AudioCodecStandardizer(Rule):
    """Dolby Digital is AC3.

    Rename Dolby Digital to AC3
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
        for audio_codec in matches.named('audio_codec', predicate=lambda m: m.value in ('Dolby Digital', )):
            new_codec = copy.copy(audio_codec)
            new_codec.value = 'AC3'
            to_remove.append(audio_codec)
            to_append.append(new_codec)

        return to_remove, to_append


class SourceStandardizer(Rule):
    """Digital TV renamed to PDTV."""

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
        for source in matches.named('source', predicate=lambda m: m.value in ('Digital TV', )):
            new_source = copy.copy(source)
            new_source.value = 'PDTV'
            to_remove.append(source)
            to_append.append(new_source)

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
        for video_codec in matches.named('video_codec', lambda m: m.value in ('H.264', 'H.265') and 'x26' in m.raw.lower()):
            encoder = copy.copy(video_codec)
            encoder.name = 'video_encoder'
            encoder.value = encoder.value.replace('H.', 'x')
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
        for name in ('episode_title', 'source', 'release_group', 'title'):
            values = matches.named(name)
            unique_values = {v.value for v in values}
            if len(unique_values) > 1:
                if name == 'title':
                    to_remove.extend(matches.named('title', predicate=lambda match: match.value != values[0].value))
                    continue

                log.debug(u"Guessed more than one '%s' for '%s': %s",
                          name, matches.input_string, ','.join(unique_values), exc_info=False)
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
            "source": "HDTV",
            "video_codec": "H.264",
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
            "source": "HDTV",
            "video_codec": "H.264",
            "release_group": "GROUP",
            "type": "episode"
        }
    """

    priority = POST_PROCESS
    consequence = [RemoveMatch, AppendMatch]
    regexes = [
        # italian release: drop everything after [CURA]
        re.compile(r'\[CURA\].*$', flags=re.IGNORECASE),

        # https://github.com/guessit-io/guessit/issues/302
        re.compile(r'\W*\b(obfuscated)\b\W*', flags=re.IGNORECASE),
        re.compile(r'\W*\b(scrambled)\b\W*', flags=re.IGNORECASE),
        re.compile(r'\W*\b(vtv|sd|rp|norar|re-?up(loads?)?)\b\W*', flags=re.IGNORECASE),
        re.compile(r'\W*\b(hebits)\b\W*', flags=re.IGNORECASE),

        # [word], (word), {word}
        re.compile(r'(?<=.)\W*[\[({].+[\})\]]?\W*$', flags=re.IGNORECASE),

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
        re.compile(r'(?<=[a-z0-9]{3})-(\d{3,4})$', flags=re.IGNORECASE),

        # word-fansub
        re.compile(r'(?<=[a-z0-9]{3})-((fan)?sub(s)?)$', flags=re.IGNORECASE),

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
                    new_release_group.value = value
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
        FixAnimeReleaseGroup,
        FixInvalidAbsoluteReleaseGroups,
        AnimeWithSeasonAbsoluteEpisodeNumbers,
        AnimeAbsoluteEpisodeNumbers,
        AbsoluteEpisodeNumbers,
        PartsAsEpisodeNumbers,
        RemoveInvalidEpisodeSeparator,
        RemoveYearAsSeason,
        CreateAliasWithAlternativeTitles,
        CreateAliasWithCountryOrYear,
        ReleaseGroupPostProcessor,
        FixParentFolderReplacingTitle,
        FixWordAsLanguage,
        FixMultipleSources,
        FixMultipleReleaseGroups,
        AudioCodecStandardizer,
        SourceStandardizer,
        VideoEncoderRule,
        CreateProperTags,
        AvoidMultipleValuesRule,
    )
