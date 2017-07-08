import logging
from medusa.logger.adapters.style import BraceAdapter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Filter(object):
    def __init__(self, search_result, results=None):
        self.search_result = search_result
        self.results = results


class FilterVerifyPackage(Filter):
    def __init__(self, search_result, results=None):
        super(FilterVerifyPackage, self).__init__(search_result, results)

    def filter(self):
        assert self.search_result.search_mode, 'Missing search_mode attribute!.'
        if self.search_result.search_mode == 'sponly':
            if self.search_result.parsed_result.episode_numbers:
                log.debug(
                    'This is supposed to be a season pack search but the result {0} is not a valid '
                    'season pack, skipping it', self.search_result.name
                )
                self.results.remove(self.search_result)
                return False
        return True

