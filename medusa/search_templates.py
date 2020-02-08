# coding=utf-8

"""Scene exceptions module."""

from __future__ import unicode_literals

import logging
from collections import namedtuple

from medusa import db
from medusa.logger.adapters.style import BraceAdapter
from medusa.scene_exceptions import get_season_scene_exceptions

logger = BraceAdapter(logging.getLogger(__name__))
logger.logger.addHandler(logging.NullHandler())

SearchTemplate = namedtuple('Template', 'template, title, series, season, enabled, default')

class SearchTemplates(object):
    def __init__(self, show_obj=None):
        """Initialize a search template object."""
        self.show_obj = show_obj
        self.templates = []
        self.search_separator = ' '
        self.main_db_con = db.DBConnection()

    def generate(self):
        """
        Generate a list of search templates.

        Load existing search templates from main.db search_templates.
        Add default search templates from scene_exceptions when needed.
        """

        assert self.show_obj, 'You need to configure a show object before generating exceptions.'

        # Create the default templates. Don't add them when their already in the list
        scene_exceptions = self.main_db_con.select(
            'SELECT season, show_name '
            'FROM scene_exceptions '
            'WHERE indexer=? AND series_id=? AND show_name IS NOT ?',
            [self.show_obj.indexer, self.show_obj.series_id, self.show_obj.name]
        ) or []

        show_name = {'season': -1, 'show_name': self.show_obj.name}

        for exception in [show_name] + scene_exceptions:
            # Add the default search template to db
            template = self._get_episode_search_strings(exception['show_name'], exception['season'])

            new_values = {
                'template': template,
                'title': exception['show_name'],
                'indexer': self.show_obj.indexer,
                'series_id': self.show_obj.series_id,
                'season': exception['season'],
                '`default`': 1
            }
            control_values = {
                'indexer': self.show_obj.indexer,
                'series_id': self.show_obj.series_id,
                'title': exception['show_name'],
                '`default`': 1
            }

            # use a custom update/insert method to get the data into the DB
            self.main_db_con.upsert('search_templates', new_values, control_values)

        self.read_from_db()

    def save(self, template):
        """Validate template and save to db."""

        new_values = {
            'template': template['template'],
            'title': template['title'],
            'indexer': self.show_obj.indexer,
            'series_id': self.show_obj.series_id,
            'season': template['season'],
            '`default`': template['default'],
            'enabled': template['enabled']
        }
        control_values = {
            'indexer': self.show_obj.indexer,
            'series_id': self.show_obj.series_id,
            'title': template['title'],
            '`default`': template['default']
        }

        # use a custom update/insert method to get the data into the DB
        self.main_db_con.upsert('search_templates', new_values, control_values)


    def read_from_db(self):
        self.templates = []
        templates = self.main_db_con.select(
            'SELECT * '
            'FROM search_templates '
            'WHERE indexer=? AND series_id=?',
            [self.show_obj.indexer, self.show_obj.series_id]
        ) or []

        for template in templates:
            # search_template_id = template['search_template_id']
            search_template = template['template']
            title = template['title']
            season = template['season']
            enabled = bool(template['enabled'])
            default = bool(template['default'])

            self.templates.append(SearchTemplate(
                # search_template_id=search_template_id,
                template=search_template,
                title=title,
                series=self.show_obj,
                season=season,
                enabled=enabled,
                default=default
            ))

    def _create_air_by_date_search_string(self, title):
        """Create a search string used for series that are indexed by air date."""
        return title + self.search_separator + '%A-D'

    def _create_sports_search_string(self, title):
        """Create a search string used for sport series."""
        episode_string = title + self.search_separator
        episode_string += '%ADb'
        return episode_string.strip()

    def _create_anime_search_string(self, title, season):
        """Create a search string used for as anime 'marked' shows."""
        episode_string = title + self.search_separator

        # If the show name is a season scene exception, we want to use the episode number
        if title in get_season_scene_exceptions(
                self.show_obj, season):
            # This is apparently a season exception, let's use the episode instead of absolute
            ep = '%XE'
        else:
            ep = '%XAB' if self.show_obj.is_scene else '%AB'

        episode_string += ep

        return episode_string.strip()

    def _create_default_search_string(self, title):
        """Create a default search string, used for standard type S01E01 tv series."""
        episode_string = title + self.search_separator

        episode_string += 'S%0XS' if self.show_obj.is_scene else 'S%0S'
        episode_string += 'E%XE' if self.show_obj.is_scene else 'E%0E'

        return episode_string.strip()

    def _get_episode_search_strings(self, title, season=-1):
        """Get episode search template string."""
        if self.show_obj.air_by_date:
            return self._create_air_by_date_search_string(title)
        elif self.show_obj.sports:
            return self._create_sports_search_string(title)
        elif self.show_obj.anime:
            return self._create_anime_search_string(title, season)
        else:
            return self._create_default_search_string(title)

    def update(self, templates):
        """
        Update the search templates.

        Enable/Disable default templates.
        Add/Remote/Update custom templates.
        """
        for template in templates:
            # TODO: add validation
            self.save(template)

    def to_json(self):
        """Return in json format."""
        return [
            {'title': search_template.title,
             'template': search_template.template,
             'season': search_template.season,
             'enabled': search_template.enabled,
             'default': search_template.default} for search_template in self.templates
        ]
