
from os.path import join
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base

from medusa import app

# Examples on how the Base class can be declared.
main_engine = create_engine('sqlite:///' + join(app.DATA_DIR, 'main.db'))
BaseMain = declarative_base(main_engine)


class TvShow(BaseMain):
    """"""
    __tablename__ = 'tv_shows'

    show_id = Column(Integer, primary_key=True)
    indexer_id = Column(Integer)
    indexer = Column(Integer)
    show_name = Column(String)
    location = Column(String)
    network = Column(String)
    genre = Column(String)
    classification = Column(String)
    runtime = Column(Integer)
    quality = Column(Integer)
    airs = Column(String)
    status = Column(String)
    flatten_folders = Column(Boolean)
    paused = Column(Boolean)
    startyear = Column(Integer)
    air_by_date = Column(Boolean)
    lang = Column(String)
    subtitles = Column(Boolean)
    notify_list = Column(String)
    imdb_id = Column(String)
    last_update_indexer = Column(Integer)
    dvdorder = Column(Boolean)
    archive_firstmatch = Column(Boolean)
    rls_require_words = Column(String)
    rls_ignore_words = Column(String)
    sports = Column(Boolean)
    anime = Column(Boolean)
    scene = Column(Boolean)
    default_ep_status = Column(Integer, server_default='-1')
    plot = Column(String)

    def __init__(self, indexer_id, indexer, show_name, location, quality, status, network=None, genre=None, classification=None,
                 runtime=None, airs=None, flatten_folders=False, paused=False, startyear=None, air_by_date=False, lang=None,
                 subtitles=False, notify_list=None, imdb_id=None, last_update_indexer=None, dvdorder=False, archive_firstmatch=False,
                 rls_require_words=None, rls_ignore_words=None, sports=False, anime=False, scene=False, default_ep_status=-1, plot=None):
        self.indexer_id = indexer_id
        self.indexer = indexer
        self.show_name = show_name
        self.location = location
        self.quality = quality
        self.status = status
        self.network = network
        self.genre = genre
        self.classification = classification
        self.runtime = runtime
        self.airs = airs
        self.flatten_folders = flatten_folders
        self.paused = paused
        self.startyear = startyear
        self.air_by_date = air_by_date
        self.lang = lang,
        self.subtitles = subtitles
        self.notify_list = notify_list
        self.imdb_id = imdb_id
        self.last_update_indexer = last_update_indexer
        self.dvdorder = dvdorder
        self.archive_firstmatch = archive_firstmatch
        self.rls_require_words = rls_require_words
        self.rls_ignore_words = rls_ignore_words
        self.sports = sports
        self.anime = anime
        self.scene = scene
        self.default_ep_status = default_ep_status
        self.plot = plot

    def series_id(self):
        return self.indexer_id

    def __str__(self):
        return b'{show_name} ({series_id})'.format(show_name=self.show_name, series_id=self.indexer_id)

    def __unicode__(self):
        return u'{show_name} ({series_id})'.format(show_name=self.show_name, series_id=self.indexer_id)


class TvEpisode(BaseMain):
    """"""
    __tablename__ = 'tv_episodes'

    episode_id = Column(Integer, primary_key=True)
    showid = Column(Integer, nullable=False)
    indexerid = Column(Integer, nullable=False)
    indexer = Column(Integer, nullable=False)
    name = Column(String)
    season = Column(Integer, nullable=False)
    episode = Column(Integer, nullable=False)
    description = Column(String)
    airdate = Column(String)
    hasnfo = Column(Boolean)
    hastbn = Column(Boolean)
    status = Column(Integer, server_default='-1')
    location = Column(String)
    file_size = Column(Integer)
    release_name = Column(String)
    subtitles = Column(String)
    subtitles_searchcount = Column(Integer)
    subtitles_lastsearch = Column(DateTime)
    is_proper = Column(Integer)
    scene_season = Column(Integer)
    scene_episode = Column(Integer)
    absolute_number = Column(Integer)
    scene_absolute_number = Column(Integer)
    version = Column(Integer, server_default='-1')
    release_group = Column(String)
    manually_searched = Column(Integer)

    def __init__(self, showid, indexerid, indexer, season, episode, name=None, desription=None, airdate=None, hasnfo=False,
                 hastbn=False, status=-1, location=None, file_size=None, release_name=None, subtitles=None,
                 subtitles_searchcount=None, subtitles_lastsearch=None, is_proper=False, scene_season=None,
                 scene_episode=None, absolute_number=None, scene_absolute_number=None, version=-1,
                 release_group=None, manually_searched=False):
        self.showid = showid
        self.indexerid = indexerid
        self.indexer = indexer
        self.season = season
        self.episode = episode
        self.name = name
        self.desription = desription
        self.airdate = airdate
        self.hasnfo = hasnfo
        self.hastbn = hastbn
        self.status = status
        self.location = location
        self.file_size = file_size
        self.release_name = release_name
        self.subtitles = subtitles
        self.subtitles_searchcount = subtitles_searchcount
        self.subtitles_lastsearch = subtitles_lastsearch
        self.is_proper = is_proper
        self.scene_season = scene_season
        self.scene_episode = scene_episode
        self.absolute_number = absolute_number
        self.scene_absolute_number = scene_absolute_number
        self.version = version
        self.release_group = release_group
        self.manually_searched = manually_searched

    def __str__(self):
        return b'{season}x{episode}'.format(season=self.season, episode=self.episode)

    def __unicode__(self):
        return u'{season}x{episode}'.format(season=self.season, episode=self.episode)


class SceneNumbering(BaseMain):
    """"""
    __tablename__ = 'scene_numbering'

    scene_numbering_id = Column(Integer, primary_key=True)
    indexer = Column(Integer)
    indexer_id = Column(Integer)
    season = Column(Integer)
    episode = Column(Integer)
    scene_season = Column(Integer)
    scene_episode = Column(Integer)
    absolute_number = Column(Integer)
    scene_absolute_number = Column(Integer)

    def __init__(self, indexer, indexer_id, season=None, episode=None, scene_season=None,
                 scene_episode=None, absolute_number=None, scene_absolute_number=None):
        self.indexer = indexer
        self.indexer_id = indexer_id
        self.season = season
        self.episode = episode
        self.scene_season = scene_season
        self.scene_episode = scene_episode
        self.absolute_number = absolute_number
        self.scene_absolute_number = scene_absolute_number
