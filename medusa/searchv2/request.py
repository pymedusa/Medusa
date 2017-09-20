"""Search requests."""


class SearchOptions(object):
    def __init__(self, search_type=None, down_cur_quality=False, season_search=False, backlog_filter=None):
        self.search_type = search_type
        self.down_cur_quality = down_cur_quality
        self.season_search = season_search
        self.backlog_filter = backlog_filter or []


class SearchRequest(object):
    def __init__(self, series=None, segment=None, options=None, providers=None):
        # The series object
        self.series = series

        # A list of episode object that we are going to search for.
        self.segment = segment

        # An options object. For storing all the global, provider and series search options.
        self.options = options or SearchOptions()

        # A list of providers, that we are going to use to search.
        self.providers = providers
