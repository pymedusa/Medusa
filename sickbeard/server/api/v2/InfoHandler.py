from BaseRequestHandler import BaseRequestHandler

import sickbeard

class InfoHandler(BaseRequestHandler):
    def get(self, query=""):
        info_query = query.split("/")[0]
        info_data = {
            "srRoot": sickbeard.WEB_ROOT,
            "anonRedirect": sickbeard.ANON_REDIRECT,
            "anonSplitHome": sickbeard.ANIME_SPLIT_HOME,
            "comingEpsLayout": sickbeard.COMING_EPS_LAYOUT,
            "comingEpsSort": sickbeard.COMING_EPS_SORT,
            "datePreset": sickbeard.DATE_PRESET,
            "fuzzyDating": sickbeard.FUZZY_DATING,
            "historyLayout": sickbeard.HISTORY_LAYOUT,
            "homeLayout": sickbeard.HOME_LAYOUT,
            "themeName": sickbeard.THEME_NAME,
            "posterSortby": sickbeard.POSTER_SORTBY,
            "posterSortdir": sickbeard.POSTER_SORTDIR,
            "rootDirs": sickbeard.ROOT_DIRS,
            "sortArticle": sickbeard.SORT_ARTICLE,
            "timePreset": sickbeard.TIME_PRESET,
            "trimZero": sickbeard.TRIM_ZERO,
            "fanartBackground": sickbeard.FANART_BACKGROUND,
            "fanartBackgroundOpacity": sickbeard.FANART_BACKGROUND_OPACITY
        }

        if info_query:
            self.api_finish({
                "status": 200,
                "data": info_data[info_query]
            })
        else:
            self.api_finish({
                "status": 200,
                "data": info_data
            })
