import sickbeard

from helper import api_auth, api_errors

from tornado.web import RequestHandler
from tornado.routes import route

from sickrage.helper.quality import get_quality_string
from sickrage.media.ShowFanArt import ShowFanArt
from sickrage.media.ShowNetworkLogo import ShowNetworkLogo
from sickrage.media.ShowPoster import ShowPoster
from sickrage.media.ShowBanner import ShowBanner
from sickrage.show.ComingEpisodes import ComingEpisodes
from sickrage.show.History import History
from sickrage.show.Show import Show
from sickrage.system.Restart import Restart
from sickrage.system.Shutdown import Shutdown

@route('/api/v2/shows/?(.*)')
class ShowsHandler(RequestHandler):
    def prepare(self):
        api_auth(self)

    def get(self, show_id=""):
        self.indexerid = show_id
        if show_id:
            """ Get detailed information about a show """
            show_obj = Show.find(sickbeard.showList, int(self.indexerid))
            if not show_obj:
                return _responds(RESULT_FAILURE, msg="Show not found")

            show_dict = {
                "season_list": CMD_ShowSeasonList((), {"indexerid": self.indexerid}).run()["data"],
                "cache": CMD_ShowCache((), {"indexerid": self.indexerid}).run()["data"]
            }

            genre_list = []
            if show_obj.genre:
                genre_list_tmp = show_obj.genre.split("|")
                for genre in genre_list_tmp:
                    if genre:
                        genre_list.append(genre)

            show_dict["genre"] = genre_list
            show_dict["quality"] = get_quality_string(show_obj.quality)

            any_qualities, best_qualities = _map_quality(show_obj.quality)
            show_dict["quality_details"] = {"initial": any_qualities, "archive": best_qualities}

            try:
                show_dict["location"] = show_obj.location
            except ShowDirectoryNotFoundException:
                show_dict["location"] = ""

            show_dict["language"] = show_obj.lang
            show_dict["show_name"] = show_obj.name
            show_dict["paused"] = (0, 1)[show_obj.paused]
            show_dict["subtitles"] = (0, 1)[show_obj.subtitles]
            show_dict["air_by_date"] = (0, 1)[show_obj.air_by_date]
            show_dict["flatten_folders"] = (0, 1)[show_obj.flatten_folders]
            show_dict["sports"] = (0, 1)[show_obj.sports]
            show_dict["anime"] = (0, 1)[show_obj.anime]
            show_dict["airs"] = str(show_obj.airs).replace('am', ' AM').replace('pm', ' PM').replace('  ', ' ')
            show_dict["dvdorder"] = (0, 1)[show_obj.dvdorder]

            if show_obj.rls_require_words:
                show_dict["rls_require_words"] = show_obj.rls_require_words.split(", ")
            else:
                show_dict["rls_require_words"] = []

            if show_obj.rls_ignore_words:
                show_dict["rls_ignore_words"] = show_obj.rls_ignore_words.split(", ")
            else:
                show_dict["rls_ignore_words"] = []

            show_dict["scene"] = (0, 1)[show_obj.scene]
            # show_dict["archive_firstmatch"] = (0, 1)[show_obj.archive_firstmatch]
            # This might need to be here for 3rd part apps?
            show_dict["archive_firstmatch"] = 1

            show_dict["indexerid"] = show_obj.indexerid
            show_dict["tvdbid"] = helpers.mapIndexersToShow(show_obj)[1]
            show_dict["imdbid"] = show_obj.imdbid

            show_dict["network"] = show_obj.network
            if not show_dict["network"]:
                show_dict["network"] = ""
            show_dict["status"] = show_obj.status

            if try_int(show_obj.nextaired, 1) > 693595:
                dt_episode_airs = sbdatetime.sbdatetime.convert_to_setting(
                    network_timezones.parse_date_time(show_obj.nextaired, show_dict['airs'], show_dict['network']))
                show_dict['airs'] = sbdatetime.sbdatetime.sbftime(dt_episode_airs, t_preset=timeFormat).lstrip('0').replace(
                    ' 0', ' ')
                show_dict['next_ep_airdate'] = sbdatetime.sbdatetime.sbfdate(dt_episode_airs, d_preset=dateFormat)
            else:
                show_dict['next_ep_airdate'] = ''

            return self.finish({
                "status": 200,
                "show": show_dict
            })
        else:
            shows = {}
            for show in sickbeard.showList:
                # If self.paused is None: show all, 0: show un-paused, 1: show paused
                if self.paused is not None and self.paused != curShow.paused:
                    continue

                indexer_show = helpers.mapIndexersToShow(show)

                show_dict = {
                    "paused": (0, 1)[show.paused],
                    "quality": get_quality_string(show.quality),
                    "language": show.lang,
                    "air_by_date": (0, 1)[show.air_by_date],
                    "sports": (0, 1)[show.sports],
                    "anime": (0, 1)[show.anime],
                    "indexerid": show.indexerid,
                    "tvdbid": indexer_show[1],
                    "network": show.network,
                    "show_name": show.name,
                    "status": show.status,
                    "subtitles": (0, 1)[show.subtitles],
                }

                if try_int(show.nextaired, 1) > 693595:  # 1900
                    dt_episode_airs = sbdatetime.sbdatetime.convert_to_setting(
                        network_timezones.parse_date_time(show.nextaired, show.airs, show_dict['network']))
                    show_dict['next_ep_airdate'] = sbdatetime.sbdatetime.sbfdate(dt_episode_airs, d_preset=dateFormat)
                else:
                    show_dict['next_ep_airdate'] = ''

                show_dict["cache"] = CMD_ShowCache((), {"indexerid": show.indexerid}).run()["data"]
                if not show_dict["network"]:
                    show_dict["network"] = ""
                if self.sort == "name":
                    shows[show.name] = show_dict
                else:
                    shows[show.indexerid] = show_dict

            return self.finish({
                "status": 200,
                "shows": shows
            })

    def put(self, item_id):
        return self.finish({
        })
        # do your update for item

    def post(self):
        return self.finish({
        })
        # do your item creation

    def delete(self, item_id):
        return self.finish({
        })
        # do your deletion for item_id
