# coding=utf-8
"""Rules to create air dates from month/year release patterns.

Handles scene releases for monthly shows that use a month name or month number
with a year instead of a full YYYY.MM.DD date, for example:

  Show.Name.Mai.2016...
  Show.Name.August.2017...
  Show.Name.08.1998
  Show.Name.10.2024
  Show.Name.2011.01...

Day is set to 1 only as a technical placeholder when the release has no day.
That is NOT the broadcast day (e.g. a monthly show that airs on the first
Saturday of the month). Matching must resolve the real episode by year+month.
"""
from __future__ import unicode_literals

import copy
import re
from datetime import date

from medusa.helper.month_names import MONTH_NAME_TO_NUMBER, first_date_of_month, month_from_name

from rebulk.match import Match
from rebulk.processors import POST_PROCESS
from rebulk.rules import AppendMatch, Consequence, Rule


class SafeRemoveMatch(Consequence):
    """Like RemoveMatch, but tolerate rebulk dict/list inconsistency.

    Full paths that repeat the same token (folder + file) can leave equal
    episode matches in the delegate list while already absent from name_dict.
    Stock RemoveMatch then raises ValueError inside list.remove.
    """

    def then(self, matches, when_response, context):  # pylint: disable=unused-argument
        if when_response is None:
            return
        if not isinstance(when_response, (list, tuple)):
            when_response = [when_response]
        for match in list(when_response):
            try:
                if match in matches:
                    matches.remove(match)
            except ValueError:
                continue


_MONTH_NAMES_PATTERN = '|'.join(
    sorted((re.escape(name) for name in MONTH_NAME_TO_NUMBER), key=len, reverse=True)
)

# Title ending with a month name: "Show Name Mai" / "Show Name August"
_TITLE_MONTH_RE = re.compile(
    r'^(?P<title>.+?)(?:[\s._-]+)(?P<month>' + _MONTH_NAMES_PATTERN + r')$',
    re.IGNORECASE,
)

# Month name + year anywhere in the release (spaces or dots), e.g.
# "Show Name Mars 2012 TAG 03 2012" or "Show Name Mai 2016 ..."
# Require a non-letter/digit boundary so short tokens like "bre" do not match
# inside "cembre" (truncated Décembre display glitch). Use Unicode-aware
# letter/digit classes ([^\W_]) so Cyrillic/CJK month names are not glued to
# adjacent letters; '_' remains a valid separator.
# Trailing boundary is end or non-letter/digit so "(Avril-2021)" works.
_INPUT_MONTH_YEAR_RE = re.compile(
    r'(?<![^\W_])(?P<month>' + _MONTH_NAMES_PATTERN + r')[\s._-]+(?P<year>(?:19|20)\d{2})'
    r'(?:$|[\W_])',
    re.IGNORECASE,
)

# Letter-only scene acronyms eligible as GuessIt expected_title and compact
# month/year packs (SN04-2022). Numbered titles like 11.22.63 stay out.
_COMPACT_ALIAS_RE = re.compile(r'^[A-Za-z]{2,12}$')


def is_compact_scene_alias(alias):
    """Return True if alias is a short letter-only scene acronym."""
    if not isinstance(alias, str):
        return False
    return bool(_COMPACT_ALIAS_RE.fullmatch(alias.strip()))


# Compact scene-alias + month/year: "SN04-2022", "SN-01-24", "SN122022".
# Aliases come from GuessIt expected_title (Medusa scene exceptions), not a
# hardcoded tag. 2-digit years need a separator so "SN106" is not Jan 2006.
def _compact_alias_month_year_re(aliases):
    tokens = []
    seen = set()
    for alias in aliases or []:
        cleaned = alias.strip() if isinstance(alias, str) else ''
        if not is_compact_scene_alias(cleaned) or cleaned.casefold() in seen:
            continue
        seen.add(cleaned.casefold())
        tokens.append(re.escape(cleaned))
    if not tokens:
        return None
    tokens.sort(key=len, reverse=True)
    return re.compile(
        r'(?i)(?:^|[\s._\[(-])(?P<alias>' + '|'.join(tokens) + r')[\s._-]*'
        r'(?P<month>0?[1-9]|1[0-2])'
        r'(?:'
        r'[\s._-]*(?P<year>(?:19|20)\d{2})(?:$|[^A-Za-z0-9])'
        r'|'
        r'[\s._-]+(?P<year_short>\d{2})(?![._-]\d)(?:$|[^A-Za-z0-9])'
        r')'
    )

# Full air date: "03 juin 2023" / "Emission du 03 juin 2023" / "03 June 2023"
# Reject YYYY.MM.MonthName (the digits are a month, not a day).
_INPUT_DAY_MONTH_YEAR_RE = re.compile(
    r'(?<![^\W_])(?<!(?:19|20)\d{2}[\s._-])(?:emission[\s._-]+du[\s._-]+)?'
    r'(?P<day>0?[1-9]|[12]\d|3[01])[\s._-]+'
    r'(?P<month>' + _MONTH_NAMES_PATTERN + r')[\s._-]+'
    r'(?P<year>(?:19|20)\d{2})(?:$|[\W_])',
    re.IGNORECASE,
)

# Episode title that is only a month name (e.g. "3.aout" -> episode_title=aout)
_MONTH_ONLY_RE = re.compile(
    r'^(' + _MONTH_NAMES_PATTERN + r')$',
    re.IGNORECASE,
)

# Numeric monthly packs: MM.YYYY or YYYY.MM with 1 or 2 digit months.
# Optional spaces around separators cover "(2009 - 10)" style packs.
# Lookbehind blocks letters/digits/underscore so "Vol_1-2019" and "E02.2010" stay intact.
# Parenthesized years like "07.(2016)" do not match because '(' is not a date separator.
# A trailing non-digit allows "05_2025.mkv" / "05_2025_720p", but underscore packs that
# continue as _DD_DD... (broadcast/DVR stamps) are rejected in Pattern 2 validation.
_NUMERIC_MONTH_YEAR_RE = re.compile(
    r'(?:^|(?<![0-9A-Za-z_]))'
    r'(?:'
    r'(?P<m1>0?[1-9]|1[0-2])\s*[._-]\s*(?P<y1>(?:19|20)\d{2})'
    r'|'
    r'(?P<y2>(?:19|20)\d{2})\s*[._-]\s*(?P<m2>0?[1-9]|1[0-2])'
    r')'
    r'(?:[^0-9]|$)'
)

# After an underscore-separated MM_YYYY / YYYY_MM, more _digits_digits means the match
# is only a prefix of a longer numeric stamp (e.g. Channel.5_2025_07_18_21_00).
_UNDERSCORE_DIGIT_CHAIN_CONTINUATION_RE = re.compile(r'_\d+(?:_\d+)+')

# MM-YY (dash) or MM.YY (dot, 2-digit year). Trailing for dots rejects another
# dotted number (show titles like 11.22.63) but still allows .mkv extensions.
_NUMERIC_MONTH_SHORT_YEAR_RE = re.compile(
    r'(?:^|(?<![0-9A-Za-z_]))'
    r'(?:'
    r'(?P<month>0?[1-9]|1[0-2])-(?P<year>\d{2})(?:$|[^0-9])'
    r'|'
    r'(?P<month_dot>0?[1-9]|1[0-2])\.(?P<year_dot>\d{2})(?:$|[^0-9.]|\.[A-Za-z])'
    r')'
)


def _is_valid_year(year):
    return 1920 <= year <= 2100


def _parse_year(year_value):
    """Parse a 2- or 4-digit year string/int into a full year.

    Two-digit years use pivot 50: 00-50 -> 2000-2050, 51-99 -> 1951-1999
    (covers packs from the early 1990s through current releases).
    """
    if isinstance(year_value, int):
        year_str = str(year_value)
    else:
        year_str = str(year_value or '')
    if len(year_str) == 2 and year_str.isdigit():
        yy = int(year_str)
        return 2000 + yy if yy <= 50 else 1900 + yy
    if year_str.isdigit():
        return int(year_str)
    return None


def _single_int(value):
    if isinstance(value, list):
        if len(value) != 1:
            return None
        value = value[0]
    if isinstance(value, int):
        return value
    return None


def _unique_matches(match_list):
    """Deduplicate match objects for RemoveMatch.

    Rebulk Match equality is span/value/name/parent based, not identity.
    Passing two equal matches to RemoveMatch makes the second list.remove fail.
    """
    unique = []
    for match in match_list or []:
        if match is None:
            continue
        if match not in unique:
            unique.append(match)
    return unique


def _safe_removes(matches, match_list):
    """Deduplicate and keep only matches still present in the Matches object."""
    safe = []
    for match in _unique_matches(match_list):
        if match in matches:
            safe.append(match)
    return safe


def _path_segments(input_string):
    """Split a release name into path segments, closest to the file first.

    Library items are parsed as full paths, so the month/year token and a
    season folder can live in different segments.
    """
    segments = []
    start = 0
    for index, char in enumerate(input_string or ''):
        if char in '\\/':
            if index > start:
                segments.append((start, input_string[start:index]))
            start = index + 1
    if input_string and start < len(input_string):
        segments.append((start, input_string[start:]))
    return list(reversed(segments))


def _segment_has_sxxexx(sxxexx_matches, offset, segment):
    end = offset + len(segment)
    return any(match.start < end and match.end > offset for match in sxxexx_matches)


def _numeric_month_year_value_end(match):
    """Return the end index of the month/year values (excluding trailing boundary)."""
    if match.group('y1') is not None:
        return match.end('y1')
    return match.end('m2')


def _numeric_month_year_uses_underscore_separator(segment, match):
    """Return True when the matched MM/YYYY pair is joined by underscores."""
    if match.group('y1') is not None:
        separator = segment[match.end('m1'):match.start('y1')]
    else:
        separator = segment[match.end('y2'):match.start('m2')]
    return '_' in separator


def _is_underscore_month_year_prefix_of_digit_chain(segment, match):
    """Reject underscore MM_YYYY/YYYY_MM that continue as a longer digit stamp.

    Example rejected: ``Channel.5_2025_07_18_21_00`` (``5_2025`` is not May 2025).
    Example kept: ``Show.05_2025.mkv``, ``Show.05_2025_720p.mkv``.
    """
    if not _numeric_month_year_uses_underscore_separator(segment, match):
        return False
    rest = segment[_numeric_month_year_value_end(match):]
    return bool(_UNDERSCORE_DIGIT_CHAIN_CONTINUATION_RE.match(rest))


def _find_numeric_month_year(segment):
    """Return the first numeric month/year match that is not a stamp prefix."""
    for match in _NUMERIC_MONTH_YEAR_RE.finditer(segment):
        if _is_underscore_month_year_prefix_of_digit_chain(segment, match):
            continue
        return match
    return None


def _search_segments(regex, segments, sxxexx_matches, allow_sxxexx=False):
    """Search segments for a month/year pattern, skipping SxxExx segments.

    A season folder (Show S35/Show 01-2026.mkv) must not prevent the file name
    from being read as a monthly release, so SxxExx only blocks the segment it
    belongs to.
    """
    for offset, segment in segments:
        if not allow_sxxexx and _segment_has_sxxexx(sxxexx_matches, offset, segment):
            continue
        found = regex.search(segment)
        if found:
            return offset, segment, found
    return None, None, None


def _search_numeric_month_year_segments(segments, sxxexx_matches, allow_sxxexx=False):
    """Like _search_segments for Pattern 2, skipping stamp-prefix false positives."""
    for offset, segment in segments:
        if not allow_sxxexx and _segment_has_sxxexx(sxxexx_matches, offset, segment):
            continue
        found = _find_numeric_month_year(segment)
        if found:
            return offset, segment, found
    return None, None, None


class CreateDateFromMonthYearRelease(Rule):
    """Create a date from MonthName.YYYY or MM.YYYY / YYYY.MM monthly releases.

    guessit -t episode "Show.Name.Mai.2016.HDTV.x264-GROUP"

    without this fix:
        {
            "title": "Show Name Mai",
            "year": 2016,
            "type": "episode"
        }

    with this fix:
        {
            "title": "Show Name",
            "date": "2016-05-01",
            "date_precision": "month",
            "type": "episode"
        }

    The date day is only a placeholder. Air-by-date matching uses year+month
    (date_precision=month), because monthly shows may air on another day
    (e.g. first Saturday of the month).

    Also converts weak year-as-season patterns (not SxxExx):
      Show.Name.10.2024 -> date 2024-10-01
      Show.Name.2011.01 -> date 2011-01-01
    """

    priority = POST_PROCESS
    consequence = [SafeRemoveMatch, AppendMatch]

    @staticmethod
    def _append_full_date(to_append, start, end, parsed, input_string):
        """Append a complete air date (day is real, not a placeholder)."""
        to_append.append(Match(
            start,
            end,
            name='date',
            value=parsed,
            input_string=input_string,
            tags=['month-year-date'],
        ))

    @staticmethod
    def _clean_title_prefix(titles, to_remove, to_append, prefix):
        """Replace guessed title with text before the date token."""
        if not titles:
            return
        prefix = re.sub(r'^\s*(?:[\[(][^\])]*[\])][\s._-]*)+', '', prefix)
        prefix = re.sub(r'[\s._-]*[Ss]\d{1,4}[Ee]\d{1,4}[\s._-]*$', '', prefix)
        prefix = prefix.strip(' .-_([')
        cleaned = re.sub(r'[\s._-]+', ' ', prefix).strip(' .-_([')
        if cleaned:
            new_title = copy.copy(titles[0])
            new_title.value = cleaned
            to_remove.extend(titles)
            to_append.append(new_title)

    @staticmethod
    def _append_month_precision_date(to_append, start, end, year, month, input_string):
        """Append date + date_precision matches for a month-only release."""
        to_append.append(Match(
            start,
            end,
            name='date',
            value=first_date_of_month(year, month),
            input_string=input_string,
            tags=['month-year-date'],
        ))
        to_append.append(Match(
            start,
            end,
            name='date_precision',
            value='month',
            input_string=input_string,
            tags=['month-year-date'],
        ))

    def when(self, matches, context):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        """Evaluate the rule.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        if matches.named('date'):
            return

        to_remove = []
        to_append = []
        input_string = matches.input_string
        years = matches.named('year')
        titles = matches.named('title')
        seasons = matches.named('season')
        episodes = matches.named('episode')
        absolute_episodes = matches.named('absolute_episode') or []
        sxxexx_matches = [
            match
            for match in (seasons or []) + (episodes or [])
            if 'SxxExx' in (match.tags or [])
        ]
        segments = _path_segments(input_string)
        # Dash monthly packs like "(02-2021)" / "07-2025" are mis-parsed by
        # guessit as SxxExx with a season equal to the year (season=2021,
        # episode=2). A season whose value is a plausible year is the tell:
        # real seasons are small, so this never matches genuine SxxExx (S35E01).
        season_looks_like_year = any(
            _is_valid_year(value)
            for value in (_single_int(match.value) for match in (seasons or []))
            if value is not None
        )
        has_anime_absolute = any(
            'anime' in (match.tags or [])
            for match in absolute_episodes
        )

        # --- Pattern 0: DD + MonthName + YYYY (full air date) -----------------
        # "Show Name Emission du 03 juin 2023" / "Show Name 03 June 2023".
        # Stronger than SxxExx in the same filename: the explicit calendar date
        # is the air date (S01E01 is often a leftover from a bad rename).
        offset, segment, day_named = _search_segments(
            _INPUT_DAY_MONTH_YEAR_RE, segments, sxxexx_matches, allow_sxxexx=True,
        )
        if day_named:
            month = month_from_name(day_named.group('month'))
            year = int(day_named.group('year'))
            day = int(day_named.group('day'))
            parsed = None
            if month and _is_valid_year(year):
                try:
                    parsed = date(year, month, day)
                except ValueError:
                    parsed = None
            if parsed:
                to_remove.extend(years or [])
                to_remove.extend(seasons or [])
                to_remove.extend(episodes or [])
                to_remove.extend(absolute_episodes)
                to_remove.extend(matches.named('episode_title') or [])
                self._clean_title_prefix(
                    titles, to_remove, to_append, segment[:day_named.start()],
                )
                self._append_full_date(
                    to_append,
                    offset + day_named.start('day'),
                    offset + day_named.end('year'),
                    parsed,
                    input_string,
                )
                return _safe_removes(matches, to_remove), to_append

        # --- Pattern 0a: MonthName + YYYY in the raw release string -----------
        # Handles space-separated names and packs with trailing junk / scene tags,
        # e.g. "Show Name Mars 2012 TAG 03 2012 avi"
        # Truncated display glitches (Ao/cembre/vrier) are intentionally ignored.
        offset, segment, named = _search_segments(_INPUT_MONTH_YEAR_RE, segments, sxxexx_matches)
        if named:
            month = month_from_name(named.group('month'))
            year = int(named.group('year'))
            if month and _is_valid_year(year):
                to_remove.extend(years or [])
                to_remove.extend(seasons or [])
                to_remove.extend(episodes or [])
                to_remove.extend(absolute_episodes)
                if titles:
                    # Keep title text before the month token, taken from the
                    # matched segment so directory components of a full path
                    # do not leak into the title.
                    prefix = segment[:named.start('month')]
                    # Drop leading bracketed release tags: [GROUP], [TAG], ...
                    prefix = re.sub(r'^\s*(?:[\[(][^\])]*[\])][\s._-]*)+', '', prefix)
                    # Drop a redundant numeric year/month right before the
                    # month name (…2022.07.Juillet.2022…)
                    prefix = re.sub(r'(?:19|20)\d{2}[\s._-]+\d{1,2}[\s._-]*$', '', prefix)
                    prefix = prefix.strip(' .-_([')
                    if prefix:
                        cleaned = re.sub(r'[\s._-]+', ' ', prefix).strip(' .-_([')
                        if cleaned:
                            new_title = copy.copy(titles[0])
                            new_title.value = cleaned
                            to_remove.extend(titles)
                            to_append.append(new_title)

                self._append_month_precision_date(
                    to_append,
                    offset + named.start('month'),
                    offset + named.end('year'),
                    year,
                    month,
                    input_string,
                )
                return _safe_removes(matches, to_remove), to_append

        # --- Pattern 0b: compact scene-alias + MM + YYYY / MM-YY --------------
        # "SN04-2022" / "SN-01-24" when SN is a show scene exception
        # (GuessIt expected_title), not a hardcoded release tag.
        compact_re = _compact_alias_month_year_re(context.get('expected_title'))
        if compact_re:
            offset, segment, glued = _search_segments(compact_re, segments, sxxexx_matches)
            if glued:
                month = int(glued.group('month'))
                year_span = 'year' if glued.group('year') is not None else 'year_short'
                year = _parse_year(glued.group(year_span))
                if year is not None and _is_valid_year(year):
                    month_start = offset + glued.start('month')
                    to_remove.extend(years or [])
                    to_remove.extend(seasons or [])
                    to_remove.extend(episodes or [])
                    to_remove.extend(absolute_episodes)
                    alias_title = glued.group('alias')
                    if titles:
                        # Compact packs glue the alias to the month (SN04-2022):
                        # the guessed title then swallows the month digits.
                        new_title = copy.copy(titles[0])
                        new_title.value = alias_title
                        to_remove.extend(titles)
                        to_append.append(new_title)
                    self._append_month_precision_date(
                        to_append,
                        month_start,
                        offset + glued.end(year_span),
                        year,
                        month,
                        input_string,
                    )
                    return _safe_removes(matches, to_remove), to_append

        # --- Pattern 1: title ends with month name + year match ---------------
        if years and titles:
            year_match = years[0]
            year = _single_int(year_match.value)
            if year is not None and _is_valid_year(year):
                for title in titles:
                    month_match = _TITLE_MONTH_RE.match(title.value)
                    if not month_match:
                        continue
                    month = month_from_name(month_match.group('month'))
                    if not month:
                        continue

                    new_title = copy.copy(title)
                    new_title.value = month_match.group('title').strip(' .-_')
                    to_remove.append(title)
                    to_append.append(new_title)

                    to_remove.extend(years)
                    to_remove.extend(matches.named('season'))
                    to_remove.extend(matches.named('episode'))

                    self._append_month_precision_date(
                        to_append,
                        year_match.start,
                        year_match.end,
                        year,
                        month,
                        year_match.input_string,
                    )
                    return _safe_removes(matches, to_remove), to_append

        # --- Pattern 2: adjacent MM.YYYY or YYYY.MM (1 or 2 digit month) ------
        # Skip real SxxExx and anime absolute-episode packs (e.g. Show.-.5.2016),
        # but still handle dash monthly packs mis-parsed as season==year.
        # Invalid underscore stamp prefixes (Channel.5_2025_07_18_...) never mutate.
        if not has_anime_absolute or season_looks_like_year:
            offset, segment, numeric = _search_numeric_month_year_segments(
                segments, sxxexx_matches,
                allow_sxxexx=season_looks_like_year,
            )
            if numeric:
                if numeric.group('y1'):
                    year = int(numeric.group('y1'))
                    month = int(numeric.group('m1'))
                else:
                    year = int(numeric.group('y2'))
                    month = int(numeric.group('m2'))

                if _is_valid_year(year):
                    to_remove.extend(seasons or [])
                    to_remove.extend(episodes or [])
                    to_remove.extend(years or [])
                    to_remove.extend(matches.named('absolute_episode'))

                    if numeric.group('y1'):
                        span_start = numeric.start('m1')
                        span_end = numeric.end('y1')
                    else:
                        span_start = numeric.start('y2')
                        span_end = numeric.end('m2')

                    self._append_month_precision_date(
                        to_append,
                        offset + span_start,
                        offset + span_end,
                        year,
                        month,
                        input_string,
                    )
                    return _safe_removes(matches, to_remove), to_append

        # --- Pattern 2b: MM-YY / MM.YY (2-digit year) -------------------------
        # guessit often turns "09-24" / "09.24" into an episode or range.
        # Real SxxExx still blocked per segment. Years 01-12 stay ambiguous
        # with episode ranges (02-03, 09.10) — skip those; compact aliases use 0b.
        offset, segment, short = _search_segments(
            _NUMERIC_MONTH_SHORT_YEAR_RE, segments, sxxexx_matches,
            allow_sxxexx=season_looks_like_year,
        )
        if short:
            if short.group('year_dot') is not None:
                month = int(short.group('month_dot'))
                year_token = short.group('year_dot')
                # Dots: require YY >= 16 so episode pairs (12.13, 09.10) stay intact.
                min_yy = 16
                span_month, span_year = 'month_dot', 'year_dot'
            else:
                month = int(short.group('month'))
                year_token = short.group('year')
                # Dashes: YY > 12 (packs like 09-24).
                min_yy = 13
                span_month, span_year = 'month', 'year'
            year = _parse_year(year_token)
            if (
                year is not None
                and _is_valid_year(year)
                and int(year_token) >= min_yy
            ):
                to_remove.extend(seasons or [])
                to_remove.extend(episodes or [])
                to_remove.extend(years or [])
                to_remove.extend(absolute_episodes)
                self._append_month_precision_date(
                    to_append,
                    offset + short.start(span_month),
                    offset + short.end(span_year),
                    year,
                    month,
                    input_string,
                )
                return _safe_removes(matches, to_remove), to_append

        # --- Pattern 3: day + month name in episode_title, year elsewhere ------
        episode_titles = matches.named('episode_title')
        if years and episodes and episode_titles:
            year = _single_int(years[0].value)
            day = _single_int(episodes[0].value)
            month_title = episode_titles[0]
            month = None
            if _MONTH_ONLY_RE.match(str(month_title.value or '')):
                month = month_from_name(month_title.value)

            if (
                year is not None
                and _is_valid_year(year)
                and day is not None
                and 1 <= day <= 31
                and month is not None
            ):
                try:
                    parsed = date(year, month, day)
                except ValueError:
                    parsed = None
                if parsed:
                    to_remove.extend(years)
                    to_remove.extend(episodes)
                    to_remove.extend(episode_titles)
                    to_remove.extend(seasons)
                    to_append.append(Match(
                        years[0].start,
                        years[0].end,
                        name='date',
                        value=parsed,
                        input_string=years[0].input_string,
                        tags=['month-year-date'],
                    ))
                    return _safe_removes(matches, to_remove), to_append

        return
