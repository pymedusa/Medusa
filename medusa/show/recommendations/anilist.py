# coding=utf-8
"""Anilist recommended show class."""
from __future__ import unicode_literals

import logging
import traceback

from medusa.cache import recommended_series_cache
from medusa.indexers.config import EXTERNAL_ANILIST
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSession
from medusa.show.recommendations.recommended import (
    BasePopular,
    RecommendedShow,
    create_key_from_series
)


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class AniListPopular(BasePopular):  # pylint: disable=too-few-public-methods
    """Anilist popular class."""

    BASE_URL = 'https://graphql.anilist.co'
    TITLE = 'AniList'
    CACHE_SUBFOLDER = __name__.split('.')[-1] if '.' in __name__ else __name__

    def __init__(self):
        """Class retrieves a specified recommended show list from Anilist.

        List of returned shows is mapped to a RecommendedShow object
        """
        super(AniListPopular, self).__init__()
        self.cache_subfolder = AniListPopular.CACHE_SUBFOLDER
        self.recommender = AniListPopular.TITLE
        self.source = EXTERNAL_ANILIST
        self.base_url = AniListPopular.BASE_URL
        self.session = MedusaSession()

    @recommended_series_cache.cache_on_arguments(namespace='anilist', function_key_generator=create_key_from_series)
    def _create_recommended_show(self, show):
        """Create the RecommendedShow object from the returned showobj."""
        rec_show = RecommendedShow(
            self,
            show['id'],
            show['title']['userPreferred'],
            **{
                'rating': show['averageScore'] / 10 if show['averageScore'] else 0,
                'votes': show['popularity'],
                'image_href': f"https://anilist.co/anime/{show['id']}",
                'ids': {
                    'anilist_id': show['id']
                },
                'is_anime': True,
                'subcat': f"{show['startDate']['year']}_{show['season'].lower()}",
                'genres': [genre.lower() for genre in show['genres']],
                'plot': show['description']
            }
        )

        # Check cache or get and save image
        use_default = self.default_img_src if not show['coverImage']['large'] else None
        rec_show.cache_image(show['coverImage']['large'], default=use_default)

        return rec_show

    def fetch_popular_shows(self, year, season):
        """Get popular show information from IMDB."""
        result = []

        query = 'query($page:Int = 1 $id:Int $type:MediaType $isAdult:Boolean = false $search:String $format:[MediaFormat]$status:MediaStatus $countryOfOrigin:CountryCode $source:MediaSource $season:MediaSeason $seasonYear:Int $year:String $onList:Boolean $yearLesser:FuzzyDateInt $yearGreater:FuzzyDateInt $episodeLesser:Int $episodeGreater:Int $durationLesser:Int $durationGreater:Int $chapterLesser:Int $chapterGreater:Int $volumeLesser:Int $volumeGreater:Int $licensedBy:[String]$genres:[String]$excludedGenres:[String]$tags:[String]$excludedTags:[String]$minimumTagRank:Int $sort:[MediaSort]=[POPULARITY_DESC,SCORE_DESC]){Page(page:$page,perPage:20){pageInfo{total perPage currentPage lastPage hasNextPage}media(id:$id type:$type season:$season format_in:$format status:$status countryOfOrigin:$countryOfOrigin source:$source search:$search onList:$onList seasonYear:$seasonYear startDate_like:$year startDate_lesser:$yearLesser startDate_greater:$yearGreater episodes_lesser:$episodeLesser episodes_greater:$episodeGreater duration_lesser:$durationLesser duration_greater:$durationGreater chapters_lesser:$chapterLesser chapters_greater:$chapterGreater volumes_lesser:$volumeLesser volumes_greater:$volumeGreater licensedBy_in:$licensedBy genre_in:$genres genre_not_in:$excludedGenres tag_in:$tags tag_not_in:$excludedTags minimumTagRank:$minimumTagRank sort:$sort isAdult:$isAdult){id title{userPreferred}coverImage{extraLarge large color}startDate{year month day}endDate{year month day}bannerImage season description type format status(version:2)episodes duration chapters volumes genres isAdult averageScore popularity nextAiringEpisode{airingAt timeUntilAiring episode}mediaListEntry{id status}studios(isMain:true){edges{isMain node{id name}}}}}}'
        variables = {
            'page': 1,
            'type': 'ANIME',
            'seasonYear': year,
            'season': season.upper(),
            'sort': 'SCORE_DESC',
            'format': ['TV']
        }

        try:
            response = self.session.post(self.base_url, json={'query': query, 'variables': variables})
            results = response.json()['data']
        except Exception as error:
            log.warning('Unable to get Anilist shows: {0!r}', error)
            return []

        if not results.get('Page') or not results['Page'].get('media'):
            return []

        for show in results['Page']['media']:
            try:
                recommended_show = self._create_recommended_show(show)
                if recommended_show:
                    recommended_show.save_to_db()
                    result.append(recommended_show)
            except Exception:
                log.warning('Could not parse AniDB show, with exception: {0}', traceback.format_exc())

        return result
