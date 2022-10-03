# coding=utf-8
"""Plex metadata module."""

from __future__ import unicode_literals

import io
import logging
import os

from medusa import helpers
from medusa.indexers.imdb.api import ImdbIdentifier
from medusa.logger.adapters.style import BraceAdapter
from medusa.metadata import generic

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class PlexMetadata(generic.GenericMetadata):
    """
    Metadata generation class for Plex (.plexmatch).

    The following file structure is used:
    show_root/.plexmatch (series level match file)
    """

    def __init__(self,
                 show_metadata=False,
                 episode_metadata=False,
                 fanart=False,
                 poster=False,
                 banner=False,
                 episode_thumbnails=False,
                 season_posters=False,
                 season_banners=False,
                 season_all_poster=False,
                 season_all_banner=False):
        """Plex Metadata constructor."""
        generic.GenericMetadata.__init__(self,
                                         show_metadata,
                                         episode_metadata,
                                         fanart,
                                         poster,
                                         banner,
                                         episode_thumbnails,
                                         season_posters,
                                         season_banners,
                                         season_all_poster,
                                         season_all_banner)

        self.name = 'Plex'
        self._show_metadata_filename = '.plexmatch'

        # web-ui metadata template
        self.eg_show_metadata = '.plexmatch'
        self.eg_episode_metadata = '.plexmatch'
        # self.eg_fanart = '<i>not supported</i>'
        # self.eg_poster = 'cover.jpg'
        # self.eg_banner = '<i>not supported</i>'
        # self.eg_episode_thumbnails = 'Season##\\<i>filename</i>.ext.cover.jpg'
        # self.eg_season_posters = '<i>not supported</i>'
        # self.eg_season_banners = '<i>not supported</i>'
        # self.eg_season_all_poster = '<i>not supported</i>'
        # self.eg_season_all_banner = '<i>not supported</i>'

    def _show_data(self, show_obj):
        """
        Create a .plexmatch file.

        returns the resulting data object.
        show_obj: a Series instance to create the .plexmatch for
        """
        file_content = f'Title: {show_obj.title}\n'
        file_content += f'Year: {show_obj.start_year}\n'

        # Add main indexer
        externals = {}
        if show_obj.identifier.indexer.slug in ('tvdb', 'tmdb', 'imdb'):
            show_id = show_obj.identifier.id
            if (show_obj.identifier.indexer.slug == 'imdb'):
                show_id = ImdbIdentifier(show_id).imdb_id

            externals[f'{show_obj.identifier.indexer.slug}id'] = str(show_id)

        for indexer_slug in ('tvdb', 'tmdb', 'imdb'):
            if indexer_slug == show_obj.identifier.indexer.slug:
                continue

            external_id = show_obj.externals.get(f'{indexer_slug}_id')
            if not external_id:
                continue

            if (indexer_slug == 'imdb'):
                external_id = ImdbIdentifier(external_id).imdb_id

            externals[f'{indexer_slug}id'] = str(external_id)

        for external, external_id in externals.items():
            file_content += f'{external}: {external_id}\n'

        return file_content

    def write_show_file(self, show_obj):
        """
        Generate and write show_obj's metadata under the given path to the filename given by get_show_file_path().

        show_obj: Series object for which to create the metadata

        Note that this method expects that _show_data will return a string,
        which will be written to a text file.
        """
        data = self._show_data(show_obj)

        if not data:
            return False

        plexmatch_file_path = self.get_show_file_path(show_obj)
        plexmatch_file_dir = os.path.dirname(plexmatch_file_path)

        try:
            if not os.path.isdir(plexmatch_file_dir):
                log.debug(
                    'Metadata directory did not exist, creating it at {location}',
                    {'location': plexmatch_file_dir}
                )
                os.makedirs(plexmatch_file_dir)
                helpers.chmod_as_parent(plexmatch_file_dir)

            log.debug(
                'Writing show plexmatch file to {location}',
                {'location': plexmatch_file_dir}
            )

            plexmatch_file = io.open(plexmatch_file_path, 'wb')
            plexmatch_file.write(data.encode('utf-8'))
            plexmatch_file.close()
            helpers.chmod_as_parent(plexmatch_file_path)
        except IOError as error:
            log.error(
                'Unable to write file to {location} - are you sure the folder is writable? {error}',
                {'location': plexmatch_file_path, 'error': error}
            )
            return False

        return True

    def _ep_data(self, current_content, ep_obj):
        """
        Create an array with show plus episode info.

        All existing lines are imported. And the line with episode info for this specific
        episode is replaced.

        show_obj: a Episode instance to create the new episode / special line for.
        """
        new_data = []
        episodes = []

        for line in current_content:
            line = line.strip()  # Remove the \n
            if line.lower().startswith('ep:') or line.lower().startswith('sp:'):
                # If the episode is the same as the one we want to add, don't add it.
                # We're going to re-add this later.
                if line.lower().startswith(f'ep: {ep_obj.slug}') or line.lower().startswith(f'sp: {ep_obj.slug}'):
                    continue

                episodes.append(line)
            else:
                new_data.append(line)

        # Add the location for the new episode.
        if ep_obj.series.location in ep_obj.location and ep_obj.location.replace(ep_obj.series.location, ''):
            location = ep_obj.location.replace(ep_obj.series.location, '')
            if location:
                if ep_obj.season == 0:
                    episodes.append(f'sp: {ep_obj.episode:02d}: {location}')
                else:
                    episodes.append(f'ep: {ep_obj.slug}: {location}')

        return new_data + episodes

    def write_ep_file(self, ep_obj):
        """
        Add episode information to the .plexmatch file.

        The episode hint:value pairs are used to match an episode filename to a specific episode.

        Uses the format of:
        ep: S01E12: /Season 01/Episode 12 - Finale Part 2.mkv

        :param ep_obj: Episode object for which to create the metadata
        """
        # Parse existing .plexmatch data
        plexmatch_file_path = self.get_show_file_path(ep_obj.series)
        plexmatch_file_dir = os.path.dirname(plexmatch_file_path)

        with open(plexmatch_file_path, 'r', encoding='utf-8', errors='replace') as f:
            current_content = f.readlines()

        data = self._ep_data(current_content, ep_obj)

        if not data:
            return False

        if not (plexmatch_file_path and plexmatch_file_dir):
            log.debug('Unable to write episode plexmatch file because episode location is missing.')
            return False

        try:
            if not os.path.isdir(plexmatch_file_dir):
                log.debug('Metadata directory missing, creating it at {location}',
                          {'location': plexmatch_file_dir})
                os.makedirs(plexmatch_file_dir)
                helpers.chmod_as_parent(plexmatch_file_dir)

            log.debug('Writing episode plexmatch file to {location}',
                      {'location': plexmatch_file_path})

            with open(plexmatch_file_path, 'w', encoding='utf-8', errors='replace') as outfile:
                outfile.write('\n'.join(data))

            helpers.chmod_as_parent(plexmatch_file_path)
        except IOError:
            log.error('Unable to write file to {location}', {'location': plexmatch_file_path})
            return False

        return True

    def create_show_metadata(self, show_obj):
        """Create show metadata."""
        if self.show_metadata and show_obj and (not self._has_show_metadata(show_obj) or self.overwrite_nfo):
            log.debug(
                'Metadata provider {name} creating series metadata for {series}',
                {'name': self.name, 'series': show_obj.name}
            )
            return self.write_show_file(show_obj)
        return False

    def create_episode_metadata(self, ep_obj):
        """Create episode metadata."""
        if self.episode_metadata and ep_obj:
            if not self._has_show_metadata(ep_obj.series):
                self.write_show_file(ep_obj.series)
            log.debug(
                'Metadata provider {name} creating episode metadata for {episode}',
                {'name': self.name, 'episode': ep_obj.pretty_name()}
            )
            return self.write_ep_file(ep_obj)
        return False

    # Override with empty methods for unsupported features
    def retrieveShowMetadata(self, folder):
        """Disable retrieve show by metadata."""
        return None, None, None

    def update_show_indexer_metadata(self, show_obj):
        """Disable update show metadata."""
        return


# present a standard "interface" from the module
metadata_class = PlexMetadata
