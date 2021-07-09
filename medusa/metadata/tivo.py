# coding=utf-8

from __future__ import division, unicode_literals

import datetime
import io
import logging
import os

from medusa import helpers
from medusa.helper.common import episode_num
from medusa.helper.exceptions import ex
from medusa.indexers.api import indexerApi
from medusa.indexers.exceptions import IndexerEpisodeNotFound, IndexerSeasonNotFound
from medusa.logger.adapters.style import BraceAdapter
from medusa.metadata import generic

from six import text_type

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class TIVOMetadata(generic.GenericMetadata):
    """
    Metadata generation class for TIVO.

    The following file structure is used:

    show_root/Season ##/filename.ext            (*)
    show_root/Season ##/.meta/filename.ext.txt  (episode metadata)

    This class only generates episode specific metadata files, it does NOT generate a default.txt file.
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

        self.name = 'TIVO'

        self._ep_nfo_extension = 'txt'

        # web-ui metadata template
        # self.eg_show_metadata = '<i>not supported</i>'
        self.eg_episode_metadata = 'Season##\\.meta\\<i>filename</i>.ext.txt'
        # self.eg_fanart = '<i>not supported</i>'
        # self.eg_poster = '<i>not supported</i>'
        # self.eg_banner = '<i>not supported</i>'
        # self.eg_episode_thumbnails = '<i>not supported</i>'
        # self.eg_season_posters = '<i>not supported</i>'
        # self.eg_season_banners = '<i>not supported</i>'
        # self.eg_season_all_poster = '<i>not supported</i>'
        # self.eg_season_all_banner = '<i>not supported</i>'

    # Override with empty methods for unsupported features
    def retrieveShowMetadata(self, folder):
        # no show metadata generated, we abort this lookup function
        return None, None, None

    def create_show_metadata(self, show_obj):
        pass

    def update_show_indexer_metadata(self, show_obj):
        pass

    def get_show_file_path(self, show_obj):
        pass

    def create_fanart(self, show_obj):
        pass

    def create_poster(self, show_obj):
        pass

    def create_banner(self, show_obj):
        pass

    def create_episode_thumb(self, ep_obj):
        pass

    @staticmethod
    def get_episode_thumb_path(ep_obj):
        pass

    def create_season_posters(self, ep_obj):
        pass

    def create_season_banners(self, ep_obj):
        pass

    def create_season_all_poster(self, show_obj):
        pass

    def create_season_all_banner(self, show_obj):
        pass

    # Override generic class
    def get_episode_file_path(self, ep_obj):
        """
        Returns a full show dir/.meta/episode.txt path for Tivo
        episode metadata files.

        Note, that pyTivo requires the metadata filename to include the original extention.

        ie If the episode name is foo.avi, the metadata name is foo.avi.txt

        ep_obj: a Episode object to get the path for
        """
        if os.path.isfile(ep_obj.location):
            metadata_file_name = '{file}.{extension}'.format(
                file=os.path.basename(ep_obj.location),
                extension=self._ep_nfo_extension
            )
            metadata_dir_name = os.path.join(os.path.dirname(ep_obj.location), '.meta')
            metadata_file_path = os.path.join(metadata_dir_name, metadata_file_name)
        else:
            log.debug(u'Episode location does not exist: {path}',
                      {'path': ep_obj.location})
            return u''
        return metadata_file_path

    def _ep_data(self, ep_obj):
        """
        Creates a key value structure for a Tivo episode metadata file and
        returns the resulting data object.

        ep_obj: a Episode instance to create the metadata file for.

        Lookup the show in http://thetvdb.com/ using the python library:

        https://github.com/dbr/indexer_api/

        The results are saved in the object myShow.

        The key values for the tivo metadata file are from:

        http://pytivo.sourceforge.net/wiki/index.php/Metadata
        """

        data = ''

        eps_to_write = [ep_obj] + ep_obj.related_episodes

        my_show = self._get_show_data(ep_obj.series)
        if not my_show:
            return None

        for ep_to_write in eps_to_write:

            try:
                my_ep = my_show[ep_to_write.season][ep_to_write.episode]
            except (IndexerEpisodeNotFound, IndexerSeasonNotFound):
                log.debug(
                    u'Unable to find episode {number} on {indexer}... has it been removed? Should I delete from db?', {
                        'number': episode_num(ep_to_write.season, ep_to_write.episode),
                        'indexer': indexerApi(ep_obj.series.indexer).name,
                    }
                )
                return None

            if ep_obj.season == 0 and not getattr(my_ep, 'firstaired', None):
                my_ep['firstaired'] = text_type(datetime.date.fromordinal(1))

            if not (getattr(my_ep, 'episodename', None) and getattr(my_ep, 'firstaired', None)):
                return None

            if getattr(my_show, 'seriesname', None):
                data += ('title : {title}\n'.format(title=my_show['seriesname']))
                data += ('seriesTitle : {title}\n'.format(title=my_show['seriesname']))

            data += ('episodeTitle : {title}\n'.format(title=ep_to_write._format_pattern('%Sx%0E %EN')))

            # This should be entered for episodic shows and omitted for movies. The standard tivo format is to enter
            # the season number followed by the episode number for that season. For example, enter 201 for season 2
            # episode 01.

            # This only shows up if you go into the Details from the Program screen.

            # This seems to disappear once the video is transferred to TiVo.

            # NOTE: May not be correct format, missing season, but based on description from wiki leaving as is.
            data += ('episodeNumber : {ep_num}\n'.format(ep_num=ep_to_write.episode))

            # Must be entered as true or false. If true, the year from originalAirDate will be shown in parentheses
            # after the episode's title and before the description on the Program screen.

            # FIXME: Hardcode isEpisode to true for now, not sure how to handle movies
            data += 'isEpisode : true\n'

            # Write the synopsis of the video here
            # Micrsoft Word's smartquotes can die in a fire.
            sanitized_description = ep_to_write.description
            # Replace double curly quotes
            sanitized_description = sanitized_description.replace(u'\u201c', "'").replace(u'\u201d', "'")
            # Replace single curly quotes
            sanitized_description = sanitized_description.replace(u'\u2018', "'").replace(u'\u2019', "'").replace(u'\u02BC', "'")

            data += ('description : {desc}\n'.format(desc=sanitized_description))

            # Usually starts with 'SH' and followed by 6-8 digits.
            # TiVo uses zap2it for their data, so the series id is the zap2it_id.
            if getattr(my_show, 'zap2it_id', None):
                data += ('seriesId : {zap2it}\n'.format(zap2it=my_show['zap2it_id']))

            # This is the call sign of the channel the episode was recorded from.
            if getattr(my_show, 'network', None):
                data += ('callsign : {network}\n'.format(network=my_show['network']))

            # This must be entered as yyyy-mm-ddThh:mm:ssZ (the t is capitalized and never changes, the Z is also
            # capitalized and never changes). This is the original air date of the episode.
            # NOTE: Hard coded the time to T00:00:00Z as we really don't know when during the day the first run happened.
            if ep_to_write.airdate != datetime.date.fromordinal(1):
                data += ('originalAirDate : {airdate}T00:00:00Z\n'.format(airdate=ep_to_write.airdate))

            # This shows up at the beginning of the description on the Program screen and on the Details screen.
            if getattr(my_show, '_actors', None):
                for actor in my_show['_actors']:
                    if 'name' in actor and actor['name'].strip():
                        data += ('vActor : {actor}\n'.format(actor=actor['name'].strip()))

            # This is shown on both the Program screen and the Details screen.
            if getattr(my_ep, 'rating', None):
                try:
                    rating = float(my_ep['rating'])
                except ValueError:
                    rating = 0.0
                # convert 10 to 4 star rating. 4 * rating / 10
                # only whole numbers or half numbers work. multiply by 2, round, divide by 2.0
                rating = round(8 * rating / 10) / 2.0
                data += ('starRating : {rating}\n'.format(rating=rating))

            # This is shown on both the Program screen and the Details screen.
            # It uses the standard TV rating system of: TV-Y7, TV-Y, TV-G, TV-PG, TV-14, TV-MA and TV-NR.
            if getattr(my_show, 'contentrating', None):
                data += ('tvRating : {rating}\n'.format(rating=my_show['contentrating']))

            # This field can be repeated as many times as necessary or omitted completely.
            if ep_obj.series.genre:
                for genre in ep_obj.series.genre.split('|'):
                    if genre:
                        data += ('vProgramGenre : {genre}\n'.format(genre=genre))

                        # NOTE: The following are metadata keywords are not used
                        # displayMajorNumber
                        # showingBits
                        # displayMinorNumber
                        # colorCode
                        # vSeriesGenre
                        # vGuestStar, vDirector, vExecProducer, vProducer, vWriter, vHost, vChoreographer
                        # partCount
                        # partIndex

        return data

    def write_ep_file(self, ep_obj):
        """
        Generates and writes ep_obj's metadata under the given path with the
        given filename root. Uses the episode's name with the extension in
        _ep_nfo_extension.

        ep_obj: Episode object for which to create the metadata

        file_name_path: The file name to use for this metadata. Note that the extension
                will be automatically added based on _ep_nfo_extension. This should
                include an absolute path.
        """

        data = self._ep_data(ep_obj)

        if not data:
            return False

        nfo_file_path = self.get_episode_file_path(ep_obj)
        nfo_file_dir = os.path.dirname(nfo_file_path)

        if not (nfo_file_path and nfo_file_dir):
            log.debug(u'Unable to write episode nfo file because episode location is missing.')
            return False

        try:
            if not os.path.isdir(nfo_file_dir):
                log.debug(u'Metadata directory missing, creating it at {location}',
                          {'location': nfo_file_dir})
                os.makedirs(nfo_file_dir)
                helpers.chmod_as_parent(nfo_file_dir)

            log.debug(u'Writing episode nfo file to {location}',
                      {'location': nfo_file_path})

            with io.open(nfo_file_path, 'wb') as nfo_file:
                # Calling encode directly, b/c often descriptions have wonky characters.
                nfo_file.write(data.encode('utf-8'))

            helpers.chmod_as_parent(nfo_file_path)

        except EnvironmentError as e:
            log.error(
                u'Unable to write file to {path} - are you sure the folder is writable? {error}',
                {'path': nfo_file_path, 'error': ex(e)}
            )
            return False

        return True


# present a standard 'interface' from the module
metadata_class = TIVOMetadata
