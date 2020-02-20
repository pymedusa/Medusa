#!/usr/bin/python
# search a show by its name:    0 = name of the show, 1 = language
show_search = 'https://www.glotz.info/api/GetSeries.php?seriesname={0}&language={1}&format=json'
# search a show by TVDB ID: 0 = API Key, 1 = TVDB ID, 2 = language
lookup_tvdb = 'https://www.glotz.info/api/{0}/series/{1}/all/{2}.json'
# get a list of aliases of a show:  0 = TVDB ID
show_aliases = 'https://www.glotz.info/v2/names/{0}'
# Get episode by ID:    0 = API Key ID, 1 = episode ID, 2 = language
episode_by_id = 'https://www.glotz.info/api/{0}/episodes/{1}/{2}.json'
# get actors of a show: 0 = API Key, 1 = TVDB ID
show_actors = 'https://www.glotz.info/api/{0}/series/{1}/actors.json'
# get banners of show:  0 = API Key, 1 = TVDB ID
show_banners = 'https://www.glotz.info/api/{0}/series/{1}/banners.json'
# get a list of recently updated shows: 0 = API Key, 1 = timestamp
show_updates = 'https://www.glotz.info/v2/shows/updated/{0}/{1}'
