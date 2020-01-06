# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import logging
import re

from babelfish import Language, language_converters

from guessit import guessit

from requests import Session

from subliminal.cache import EPISODE_EXPIRATION_TIME, region
from subliminal.exceptions import ProviderError
from subliminal.matches import guess_matches
from subliminal.providers import ParserBeautifulSoup, Provider
from subliminal.score import get_equivalent_release_groups
from subliminal.subtitle import Subtitle, fix_line_ending
from subliminal.utils import sanitize, sanitize_release_group
from subliminal.video import Episode

logger = logging.getLogger(__name__)

language_converters.register('subtitulamos = medusa.subtitle_providers.converters.subtitulamos:SubtitulamosConverter')


class SubtitulamosSubtitle(Subtitle):
    """Subtitulamos Subtitle."""

    provider_name = 'subtitulamos'

    def __init__(self, language, hearing_impaired, page_link, series, season, episode, title, year, version,
                 download_link):
        super(SubtitulamosSubtitle, self).__init__(language, hearing_impaired, page_link)
        self.page_link = page_link
        self.series = series
        self.season = season
        self.episode = episode
        self.title = title
        self.year = year
        self.version = version
        self.download_link = download_link

    @property
    def id(self):
        return self.download_link

    def get_matches(self, video):
        matches = set()

        # series name
        if video.series and sanitize(self.series) == sanitize(video.series):
            matches.add('series')
        # season
        if video.season and self.season == video.season:
            matches.add('season')
        # episode
        if video.episode and self.episode == video.episode:
            matches.add('episode')
        # title of the episode
        if video.title and sanitize(self.title) == sanitize(video.title):
            matches.add('title')
        # year
        if video.original_series and self.year is None or video.year and video.year == self.year:
            matches.add('year')
        # release_group
        if (video.release_group and self.version
                and any(r in sanitize_release_group(self.version)
                        for r in get_equivalent_release_groups(
                            sanitize_release_group(video.release_group)))):
            matches.add('release_group')
        # resolution
        if video.resolution and self.version and video.resolution in self.version.lower():
            matches.add('resolution')
        # other properties
        matches |= guess_matches(video, guessit(self.version), partial=True)

        return matches


class SubtitulamosProvider(Provider):
    """Subtitulamos Provider."""

    languages = {Language('por', 'BR')} | {Language(l) for l in [
        'cat', 'eng', 'glg', 'por', 'spa'
    ]}
    video_types = (Episode,)
    server_url = 'https://www.subtitulamos.tv/'
    search_url = server_url + 'search/query'

    def initialize(self):
        self.session = Session()
        self.session.headers['User-Agent'] = self.user_agent

    def terminate(self):
        self.session.close()

    @region.cache_on_arguments(expiration_time=EPISODE_EXPIRATION_TIME)
    def _search_url_titles(self, series, season, episode, year=None):
        """Search the URL titles by kind for the given `title`, `season` and `episode`.

        :param str series: series to search for.
        :param int season: season to search for.
        :param int episode: episode to search for.
        :param int year: year to search for.
        :return: the episode URL.
        :rtype: str

        """
        # make the search
        logger.info('Searching episode url for %s, season %d, episode %d', series, season, episode)
        episode_url = None

        search = '{} {}x{}'.format(series, season, episode)
        r = self.session.get(self.search_url, headers={'Referer': self.server_url}, params={'q': search}, timeout=10)
        r.raise_for_status()

        if r.status_code != 200:
            logger.warning('Error getting episode url')
            raise ProviderError('%s: Error getting episode url', self.__class__.__name__.upper())

        results = json.loads(r.text)

        for result in results:
            title = sanitize(result['name'])

            # attempt series with year
            if sanitize('{} ({})'.format(series, year)) in title:
                for episode_data in result['episodes']:
                    if season == episode_data['season'] and episode == episode_data['number']:
                        episode_url = self.server_url + 'episodes/{}'.format(episode_data['id'])
                        logger.info('Episode url found with year %s', episode_url)
                        return episode_url
            # attempt series without year
            elif sanitize(series) in title:
                for episode_data in result['episodes']:
                    if season == episode_data['season'] and episode == episode_data['number']:
                        episode_url = self.server_url + 'episodes/{}'.format(episode_data['id'])
                        logger.info('Episode url found without year %s', episode_url)
                        return episode_url

        return episode_url

    def query(self, series, season, episode, year=None):
        # get the episode url
        episode_url = self._search_url_titles(series, season, episode, year)
        if episode_url is None:
            logger.info('No episode url found for %s, season %d, episode %d', series, season, episode)
            return []

        r = self.session.get(episode_url, headers={'Referer': self.server_url}, timeout=10)
        r.raise_for_status()

        soup = ParserBeautifulSoup(r.content, ['lxml', 'html.parser'])

        # get episode title
        logger.debug('Getting episode title')

        title_pattern = re.compile('{}x{:02d} - (.+)'.format(season, episode))
        title = title_pattern.search(soup.select('.episode-name')[0].get_text(strip=True).lower()).group(1)

        logger.debug('Episode title found: "%s"', title.upper())

        subtitles = []
        for sub in soup.find_all('div', attrs={'id': 'progress_buttons_row'}):
            # read the language
            language = Language.fromsubtitulamos(
                sub.find_previous('div', class_='subtitle_language').get_text(strip=True)
            )
            hearing_impaired = False

            # modify spanish latino subtitle language to only spanish and set hearing_impaired = True
            # because if exists spanish and spanish latino subtitle for the same episode, the score will be
            # higher with spanish subtitle. Spanish subtitle takes priority.
            if language == Language('spa', 'MX'):
                language = Language('spa')
                hearing_impaired = True

            # read the release subtitle
            release = sub.find_next('div', class_='version_name').get_text(strip=True)

            # ignore incomplete subtitles
            status = sub.find_next('div', class_='subtitle_buttons').contents[1]
            # if there isn't <a> tag, subtitle not finished and no link available to download it
            if status.name != 'a':
                logger.info('Ignoring subtitle in [%s] because it is not finished', language)
                continue

            # read the subtitle url
            subtitle_url = self.server_url + status['href'][1:]
            subtitle = SubtitulamosSubtitle(language, hearing_impaired, episode_url, series, season, episode, title,
                                            year, release, subtitle_url)
            logger.info('Found subtitle %r', subtitle)
            subtitles.append(subtitle)

        return subtitles

    def list_subtitles(self, video, languages):
        return [s for s in self.query(video.series, video.season, video.episode,
                                      video.year)
                if s.language in languages]

    def download_subtitle(self, subtitle):
        # download the subtitle
        logger.info('Downloading subtitle %s', subtitle.download_link)
        r = self.session.get(subtitle.download_link, headers={'Referer': subtitle.page_link},
                             timeout=10)
        r.raise_for_status()

        subtitle.content = fix_line_ending(r.content)
