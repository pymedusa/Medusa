# coding=utf-8
"""Contextual release matching for manual episode search."""

from __future__ import unicode_literals

import logging
import os
import re
import unicodedata

from medusa import scene_exceptions
from medusa.logger.adapters.style import BraceAdapter

from six import text_type

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

MIN_EPISODE_TITLE_LENGTH = 3

STRONG_EPISODE_PATTERNS = [
    re.compile(
        r'\bS(?P<season>\d{1,2})[ ._-]*E(?P<episode>\d{1,3})\b',
        re.IGNORECASE,
    ),
    re.compile(
        r'\b(?P<season>\d{1,2})x(?P<episode>\d{1,3})\b',
        re.IGNORECASE,
    ),
    re.compile(
        r'\bseason[ ._-]*(?P<season>\d+).*?episode[ ._-]*(?P<episode>\d+)\b',
        re.IGNORECASE,
    ),
    re.compile(
        r'\bsaison[ ._-]*(?P<season>\d+).*?episode[ ._-]*(?P<episode>\d+)\b',
        re.IGNORECASE,
    ),
]

SEASON_PACK_PATTERNS = [
    re.compile(r'\bs(?P<season>\d{1,2})[ ._-]*complete\b', re.IGNORECASE),
    re.compile(r'\bseason[ ._-]*(?P<season>\d+)[ ._-]*complete\b', re.IGNORECASE),
    re.compile(r'\bsaison[ ._-]*(?P<season>\d+)[ ._-]*complete\b', re.IGNORECASE),
    re.compile(r'\bseason[ ._-]*pack\b', re.IGNORECASE),
]

NON_VIDEO_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',
    '.nfo', '.sfv', '.txt', '.url', '.exe', '.com', '.bat',
    '.srt', '.sub', '.idx', '.zip', '.7z',
}


class ReleaseMatch(object):
    """Result of contextual release matching."""

    __slots__ = ('matched', 'season', 'episodes', 'method', 'reason')

    def __init__(self, matched=False, season=None, episodes=None, method=None, reason=None):
        self.matched = matched
        self.season = season
        self.episodes = episodes or []
        self.method = method
        self.reason = reason


def normalize_release_text(text):
    """Normalize text for token-sequence comparison."""
    if not text:
        return ''

    text = unicodedata.normalize('NFKD', text_type(text))
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("'", ' ').replace('\u2019', ' ').replace('`', ' ')
    text = text.casefold()
    text = re.sub(r'[\W_]+', ' ', text, flags=re.UNICODE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def normalize_to_tokens(text):
    """Return normalized whitespace-delimited tokens."""
    normalized = normalize_release_text(text)
    if not normalized:
        return []
    return normalized.split(' ')


def tokens_contain_sequence(haystack_tokens, needle_tokens):
    """Return True when needle_tokens appear as a contiguous token subsequence."""
    if not needle_tokens:
        return False

    if len(needle_tokens) > len(haystack_tokens):
        return False

    width = len(needle_tokens)
    for index in range(len(haystack_tokens) - width + 1):
        if haystack_tokens[index:index + width] == needle_tokens:
            return True
    return False


def extract_strong_numbering(release_name):
    """Extract season and episode from reliable TV numbering patterns."""
    for pattern in STRONG_EPISODE_PATTERNS:
        match = pattern.search(release_name)
        if match:
            return int(match.group('season')), [int(match.group('episode'))]
    return None


def is_explicit_season_pack(release_name):
    """Return True when the release name explicitly indicates a season pack."""
    return any(pattern.search(release_name) for pattern in SEASON_PACK_PATTERNS)


def has_explicit_non_video_extension(release_name):
    """Return True when the release name ends with a known non-video extension."""
    _, extension = os.path.splitext(release_name.lower().strip())
    return extension in NON_VIDEO_EXTENSIONS


def guessit_episode_numbers(parsed_result):
    if not parsed_result:
        return []

    episodes = parsed_result.episode_numbers or []
    if episodes:
        return list(episodes)

    guess = getattr(parsed_result, 'guess', None) or {}
    return list(guess.get('episode') or [])


def expected_release_numbering(series, target_episode):
    """Return the season and episode numbers expected in release names."""
    if series.is_scene and target_episode.scene_episode:
        return target_episode.scene_season, target_episode.scene_episode
    return target_episode.season, target_episode.episode


def _series_candidate_names(series, target_episode):
    names = {series.name}
    try:
        for title_exception in scene_exceptions.get_season_scene_exceptions(series, -1):
            names.add(title_exception.title)
        for title_exception in scene_exceptions.get_season_scene_exceptions(series, target_episode.season):
            names.add(title_exception.title)
    except (AttributeError, TypeError):
        pass
    return names


def _duplicate_episode_titles(series, normalized_title, target_episode):
    """Return episodes sharing the same normalized title as the target."""
    duplicates = []
    try:
        all_episodes = series.get_all_episodes()
    except (AttributeError, TypeError):
        return duplicates

    for episode in all_episodes:
        if normalize_release_text(episode.name) != normalized_title:
            continue
        if episode.season == target_episode.season and episode.episode == target_episode.episode:
            continue
        duplicates.append(episode)
    return duplicates


class ReleaseMatcher(object):
    """Match a provider release to a manually requested episode."""

    def __init__(self, series, requested_episodes):
        self.series = series
        self.requested_episodes = requested_episodes or []
        self.target_episode = self.requested_episodes[0] if len(self.requested_episodes) == 1 else None
        self._series_token_candidates = []
        self._target_has_ambiguous_title = False
        if self.target_episode is not None:
            for name in _series_candidate_names(series, self.target_episode):
                tokens = normalize_to_tokens(name)
                if tokens:
                    self._series_token_candidates.append(tokens)

            normalized_title = normalize_release_text(self.target_episode.name)
            if len(normalized_title) >= MIN_EPISODE_TITLE_LENGTH:
                self._target_has_ambiguous_title = bool(
                    _duplicate_episode_titles(series, normalized_title, self.target_episode)
                )

    def matches_series(self, release_name):
        """Return True when a known series alias appears as a token subsequence."""
        release_tokens = normalize_to_tokens(release_name)
        if not release_tokens:
            return False

        for candidate_tokens in self._series_token_candidates:
            if tokens_contain_sequence(release_tokens, candidate_tokens):
                return True
        return False

    def match(self, release_name, parsed_result=None):
        """Decide whether the release matches the requested episode."""
        if self.target_episode is None:
            return ReleaseMatch(matched=False, reason='implicit_season_pack')

        if has_explicit_non_video_extension(release_name):
            log.debug(
                'Rejected release because the filename extension is not a supported video type: {release_name}',
                {'release_name': release_name}
            )
            return ReleaseMatch(matched=False, reason='non_video_extension')

        if is_explicit_season_pack(release_name):
            log.debug(
                'Rejected unnumbered release instead of treating it as a season pack: {release_name}',
                {'release_name': release_name}
            )
            return ReleaseMatch(matched=False, reason='implicit_season_pack')

        if not self.matches_series(release_name):
            log.debug(
                'Rejected release because the series name was not found: {release_name}',
                {'release_name': release_name}
            )
            return ReleaseMatch(matched=False, reason='series_not_found')

        target = self.target_episode
        strong = extract_strong_numbering(release_name)
        guess_episodes = guessit_episode_numbers(parsed_result)
        normalized_title = normalize_release_text(target.name)
        title_tokens = normalize_to_tokens(target.name)
        release_tokens = normalize_to_tokens(release_name)
        title_present = (
            len(normalized_title) >= MIN_EPISODE_TITLE_LENGTH
            and tokens_contain_sequence(release_tokens, title_tokens)
        )

        if strong:
            strong_season, strong_episodes = strong
            strong_episode = strong_episodes[0]
            expected_season, expected_episode = expected_release_numbering(self.series, target)
            if strong_season == expected_season and strong_episode == expected_episode:
                log.info(
                    'Matched release using explicit season and episode numbering: {release_name}',
                    {'release_name': release_name}
                )
                return ReleaseMatch(
                    matched=True,
                    season=target.season,
                    episodes=[target.episode],
                    method='explicit_numbering',
                    reason='explicit_numbering',
                )

            log.debug(
                'Rejected release because explicit numbering conflicts with the requested episode: {release_name}',
                {'release_name': release_name}
            )
            return ReleaseMatch(matched=False, reason='explicit_number_conflict')

        if not title_present:
            if guess_episodes:
                log.debug(
                    'Rejected release because weak numbering was found without a title match: {release_name}',
                    {'release_name': release_name}
                )
            else:
                log.debug(
                    'Rejected release because no unique episode-title match was found: {release_name}',
                    {'release_name': release_name}
                )
            return ReleaseMatch(matched=False, reason='episode_title_not_found')

        if self._target_has_ambiguous_title:
            log.debug(
                'Rejected release because the episode title is ambiguous: {release_name}',
                {'release_name': release_name}
            )
            return ReleaseMatch(matched=False, reason='ambiguous_episode_title')

        if guess_episodes:
            log.debug(
                'Ignored weak episode number extracted from release suffix: {release_name}',
                {'release_name': release_name}
            )
            method = 'weak_number_ignored'
        else:
            method = 'episode_title'

        log.info(
            'Matched release using the requested episode title: {release_name}',
            {'release_name': release_name}
        )
        return ReleaseMatch(
            matched=True,
            season=target.season,
            episodes=[target.episode],
            method=method,
            reason=method,
        )
