# coding=utf-8
"""Request handler for general information."""

import medusa as app
from .base import BaseRequestHandler


class InfoHandler(BaseRequestHandler):
    """Info request handler."""

    def get(self, query=''):
        """Query general information.

        :param query:
        :type query: str
        """
        info_query = query.split('/')[0]
        info_data = {
            'anonRedirect': app.ANON_REDIRECT,
            'anonSplitHome': app.ANIME_SPLIT_HOME,
            'comingEpsLayout': app.COMING_EPS_LAYOUT,
            'comingEpsSort': app.COMING_EPS_SORT,
            'datePreset': app.DATE_PRESET,
            'fuzzyDating': app.FUZZY_DATING,
            'historyLayout': app.HISTORY_LAYOUT,
            'homeLayout': app.HOME_LAYOUT,
            'themeName': app.THEME_NAME,
            'posterSortby': app.POSTER_SORTBY,
            'posterSortdir': app.POSTER_SORTDIR,
            'rootDirs': app.ROOT_DIRS,
            'sortArticle': app.SORT_ARTICLE,
            'timePreset': app.TIME_PRESET,
            'trimZero': app.TRIM_ZERO,
            'fanartBackground': app.FANART_BACKGROUND,
            'fanartBackgroundOpacity': app.FANART_BACKGROUND_OPACITY,
            'subtitlesMulti': app.SUBTITLES_MULTI
        }

        if info_query:
            if info_query not in info_data:
                return self.api_finish(status=404, error='{key} not found'.format(key=info_query))

        self.api_finish(data=info_data[info_query] if info_query else info_data)
