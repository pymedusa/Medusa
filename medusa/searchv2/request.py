"""Search requests."""


class SearchOptions(object):
    def __init__(self, search_type, down_cur_quality=False, season_search=False):
        self.search_type = search_type
        self.down_cur_quality = down_cur_quality
        self.season_search = season_search


class SearchRequest(object):
    def __init__(self, series=None, segment=None, options=None, providers=None):
        # The series object
        self.series = series

        # A list of episode object that we are going to search for.
        self.segment = segment

        # An options object. For storing all the global, provider and series search options.
        self.options = options

        # A list of providers, that we are going to use to search.
        self.providers = providers
