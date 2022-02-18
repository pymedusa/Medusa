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

SearchTemplate = namedtuple('Template', 'id, template, title, series, season, enabled, default, season_search')


class SearchTemplates(object):
    """Search template manager for a show."""

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

        # Create the default templates. Don't add them when they are already in the list
        if not self.show_obj.aliases:
            scene_exceptions = self.main_db_con.select(
                'SELECT season, title '
                'FROM scene_exceptions '
                'WHERE indexer = ? AND series_id = ? AND title IS NOT ?',
                [self.show_obj.indexer, self.show_obj.series_id, self.show_obj.name]
            ) or []
        else:
            scene_exceptions = [{'season': exception.season, 'title': exception.title} for exception in self.show_obj.aliases]

        show_name = {'season': -1, 'title': self.show_obj.name}

        for exception in [show_name] + scene_exceptions:
            self._generate_episode_search_pattern(exception)
            self._generate_season_search_pattern(exception)

        self.read_from_db()

        return self.templates

    def _clean(self):
        """Clean up templates when there is no scene exception for it anymore."""
        # Get the default title search string for Episode and Season
        self.main_db_con.action("""
            DELETE from search_templates
            WHERE indexer = ?
            AND series_id = ?
            AND title not in (select title from scene_exceptions where indexer = ? and series_id = ?)
            AND title != ?
        """, [
            self.show_obj.indexer, self.show_obj.series_id,
            self.show_obj.indexer, self.show_obj.series_id,
            self.show_obj.name,
        ])

    def _generate_episode_search_pattern(self, exception):
        """Insert default search template into db."""
        template = self._get_episode_search_strings(exception['title'], exception['season'])

        new_values = {
            'template': template,
            'title': exception['title'],
            'indexer': self.show_obj.indexer,
            'series_id': self.show_obj.series_id,
            'season': exception['season'],
            '`default`': 1,
            'season_search': 0
        }
        control_values = {
            'indexer': self.show_obj.indexer,
            'series_id': self.show_obj.series_id,
            'title': exception['title'],
            'season': exception['season'],
            '`default`': 1,
            '`season_search`': 0
        }

        logger.debug(
            'Generating default search template for show {show}, creating template {template}, title {title}, season {season}',
            {'show': self.show_obj.name, 'template': template, 'title': exception['title'], 'season': exception['season']}
        )

        # use a custom update/insert method to get the data into the DB
        self.main_db_con.upsert('search_templates', new_values, control_values)

    def _generate_season_search_pattern(self, exception):
        """Add the default search template to db."""
        template = self._get_season_search_strings(exception['title'])

        new_values = {
            'template': template,
            'title': exception['title'],
            'indexer': self.show_obj.indexer,
            'series_id': self.show_obj.series_id,
            'season': exception['season'],
            '`default`': 1,
            'season_search': 1
        }
        control_values = {
            'template': template,
            'indexer': self.show_obj.indexer,
            'series_id': self.show_obj.series_id,
            'title': exception['title'],
            'season': exception['season'],
            '`default`': 1,
            '`season_search`': 1
        }

        # use a custom update/insert method to get the data into the DB
        self.main_db_con.upsert('search_templates', new_values, control_values)

    def save(self, template):
        """Validate template and save to db."""
        new_values = {
            'template': template['template'],
            'title': template['title'],
            'indexer': self.show_obj.indexer,
            'series_id': self.show_obj.series_id,
            'season': template['season'],
            '`default`': template['default'],
            'enabled': template['enabled'],
            'season_search': template['seasonSearch']
        }
        control_values = {
            'indexer': self.show_obj.indexer,
            'series_id': self.show_obj.series_id,
            'title': template['title'],
            'template': template['template'],
            'season': template['season']
        }

        # use a custom update/insert method to get the data into the DB
        self.main_db_con.upsert('search_templates', new_values, control_values)

    def read_from_db(self):
        """Read templates from db, and re-create the this.templates array."""
        # Start with cleaning up any templates for scene_exceptions that have been removed.
        self._clean()

        self.templates = []
        templates = self.main_db_con.select(
            'SELECT * '
            'FROM search_templates '
            'WHERE indexer=? AND series_id=?',
            [self.show_obj.indexer, self.show_obj.series_id]
        ) or []

        for template in templates:
            search_template_id = template['search_template_id']
            search_template = template['template']
            title = template['title']
            season = template['season']
            enabled = bool(template['enabled'])
            default = bool(template['default'])
            season_search = bool(template['season_search'])

            self.templates.append(SearchTemplate(
                id=search_template_id,
                template=search_template,
                title=title,
                series=self.show_obj,
                season=season,
                enabled=enabled,
                default=default,
                season_search=season_search
            ))

    def _create_air_by_date_search_string(self, title):
        """Create a search string used for series that are indexed by air date."""
        return '%SN' + self.search_separator + '%A-D'

    def _create_sports_search_string(self, title):
        """Create a search string used for sport series."""
        episode_string = '%SN' + self.search_separator
        episode_string += '%ADb'
        return episode_string.strip()

    def _create_anime_search_string(self, title, season):
        """Create a search string used for as anime 'marked' shows."""
        episode_string = '%SN' + self.search_separator

        # If the show name is a season scene exception, we want to use the episode number
        if title in [scene_exception.title for scene_exception in get_season_scene_exceptions(self.show_obj, season)]:
            # This is apparently a season exception, let's use the episode instead of absolute
            ep = '%0XE'
        else:
            ep = '%XAB' if self.show_obj.is_scene else '%AB'

        episode_string += ep

        return episode_string.strip()

    def _create_default_search_string(self, title):
        """Create a default search string, used for standard type S01E01 tv series."""
        episode_string = '%SN' + self.search_separator

        episode_string += 'S%0XS' if self.show_obj.is_scene else 'S%0S'
        episode_string += 'E%0XE' if self.show_obj.is_scene else 'E%0E'

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

    def _get_season_search_strings(self, title):
        """
        Get season search template string.

        Let's try to mimic a basic season search string, based on the chosen format.
        Note that this is aducated guess, as some providers can override the season search strings.
        We do not take this into account.

        :param title: Show's title.
        """
        episode_string = '%SN' + self.search_separator

        if self.show_obj.air_by_date or self.show_obj.sports:
            season_search_string = episode_string + '%A-D'
        elif self.show_obj.anime:
            season_search_string = episode_string + 'Season'
        else:
            season_search_string = episode_string + 'S%0S'

        return season_search_string

    def remove_custom(self):
        """Remove all custom templates for this show."""
        self.main_db_con.action("""
            DELETE from search_templates
            WHERE indexer = ?
            AND series_id = ?
            AND `default` = 0
        """, [
            self.show_obj.indexer, self.show_obj.series_id,
        ])

    def update(self, templates):
        """
        Update the search templates.

        Enable/Disable default templates.
        Add/Remote/Update custom templates.
        """
        self.templates = []
        self.remove_custom()
        for template in templates:
            # TODO: add validation
            # Check if the scene exception still exists in db
            find_scene_exception = self.main_db_con.select(
                'SELECT season, title '
                'FROM scene_exceptions '
                'WHERE indexer = ? AND series_id = ? '
                'AND title = ? AND season = ?',
                [self.show_obj.indexer, self.show_obj.series_id, template['title'], template['season']]
            )
            if not find_scene_exception and template['title'] != self.show_obj.name:
                continue

            # Save to db
            self.save(template)

            # Update the template in self.templates
            new_template = SearchTemplate(
                id=template.get('id'),
                template=template['template'],
                title=template['title'],
                series=self.show_obj,
                season=template['season'],
                enabled=template['enabled'],
                default=template['default'],
                season_search=template['seasonSearch']
            )

            self.templates.append(new_template)

        return self.templates

    def to_json(self):
        """Return in json format."""
        return [{
            'id': search_template.id,
            'title': search_template.title,
            'template': search_template.template,
            'season': search_template.season,
            'enabled': search_template.enabled,
            'default': search_template.default,
            'seasonSearch': search_template.season_search} for search_template in self.templates
        ]
