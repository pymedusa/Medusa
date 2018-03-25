
from os.path import join
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from medusa import app

# Examples on how the Base class can be declared.
main_engine = create_engine('sqlite:///' + join(app.DATA_DIR, 'main.db'))
BaseMain = declarative_base(main_engine)
main_session_factory = sessionmaker(bind=main_engine)

# TODO: Test if this also works when the class is used in different threads.
Session = scoped_session(main_session_factory)


class TvShow(BaseMain):
    """"""
    __tablename__ = 'tv_shows'

    show_id = Column(Integer, primary_key=True)
    indexer = Column(Integer)
    series_id = Column('indexer_id', Integer)
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

    def __init__(self, indexer, series_id, show_name, location, quality, status, network=None, genre=None, classification=None,
                 runtime=None, airs=None, flatten_folders=False, paused=False, startyear=None, air_by_date=False, lang=None,
                 subtitles=False, notify_list=None, imdb_id=None, last_update_indexer=None, dvdorder=False, archive_firstmatch=False,
                 rls_require_words=None, rls_ignore_words=None, sports=False, anime=False, scene=False, default_ep_status=-1, plot=None):
        self.series_id = series_id
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
    series_id = Column('showid', Integer, nullable=False)
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

    def __init__(self, series_id, indexerid, indexer, season, episode, name=None, desription=None, airdate=None, hasnfo=False,
                 hastbn=False, status=-1, location=None, file_size=None, release_name=None, subtitles=None,
                 subtitles_searchcount=None, subtitles_lastsearch=None, is_proper=False, scene_season=None,
                 scene_episode=None, absolute_number=None, scene_absolute_number=None, version=-1,
                 release_group=None, manually_searched=False):
        self.series_id = series_id
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
        return b'{series}: {season}x{episode}'.format(series=self.series_id, season=self.season, episode=self.episode)

    def __unicode__(self):
        return u'{series}: {season}x{episode}'.format(series=self.series_id, season=self.season, episode=self.episode)


class SceneNumbering(BaseMain):
    """"""
    __tablename__ = 'scene_numbering'

    scene_numbering_id = Column(Integer, primary_key=True)
    indexer = Column(Integer)
    series_id = Column('indexer_id', Integer)
    season = Column(Integer)
    episode = Column(Integer)
    scene_season = Column(Integer)
    scene_episode = Column(Integer)
    absolute_number = Column(Integer)
    scene_absolute_number = Column(Integer)

    def __init__(self, indexer, series_id, season=None, episode=None, scene_season=None,
                 scene_episode=None, absolute_number=None, scene_absolute_number=None):
        self.indexer = indexer
        self.series_id = series_id
        self.season = season
        self.episode = episode
        self.scene_season = scene_season
        self.scene_episode = scene_episode
        self.absolute_number = absolute_number
        self.scene_absolute_number = scene_absolute_number


class Whitelist(BaseMain):
    """"""
    __tablename__ = 'whitelist'
    whitelist_id = Column(Integer, primary_key=True)
    indexer = Column('indexer_id', Integer, nullable=False)
    series_id = Column('show_id', Integer, nullable=False)
    keyword = Column(Integer)

    def __init__(self, indexer, series_id, keyword=None):
        self.indexer = indexer
        self.series_id = series_id
        self.keyword = keyword


class Blacklist(BaseMain):
    """"""
    __tablename__ = 'blacklist'
    blacklist_id = Column(Integer, primary_key=True)
    indexer = Column('indexer_id', Integer, nullable=False)
    series_id = Column('show_id', Integer, nullable=False)
    keyword = Column(Integer)

    def __init__(self, indexer, series_id, keyword=None):
        self.indexer = indexer
        self.series_id = series_id
        self.keyword = keyword


class DbVersion(BaseMain):
    """"""
    __tablename__ = 'db_version'
    db_version_id = Column(Integer, primary_key=True)
    db_version = Column(Integer)
    db_minor_version = Column(Integer)

    @classmethod
    def get_version(class_):
        """Return a query of users sorted by name."""
        DbVersion = class_
        q = Session.query(DbVersion).one()
        return q

    def __str__(self):
        return b'{major}.{minor}'.format(major=self.db_version, minor=self.db_minor_version)

    def __unicode__(self):
        return u'{major}.{minor}'.format(major=self.db_version, minor=self.db_minor_version)

    def __iter__(self):
        """Return the version as an iterable."""
        for i in self.db_version, self.db_minor_version:
            yield i


class History(BaseMain):
    """"""
    __tablename__ = 'history'
    history_id = Column(Integer, primary_key=True)
    action = Column(Integer, nullable=False)
    date = Column(Integer)
    indexer = Column('indexer_id', Integer, nullable=False)
    series_id = Column('showid', Integer, nullable=False)
    season = Column(Integer, nullable=False)
    episode = Column(Integer, nullable=False)
    quality = Column(Integer)
    resource = Column(String)
    provider = Column(String)
    version = Column(Integer, server_default='-1')
    proper_tags = Column(String)
    manually_searched = Column(Integer)
    info_hash = Column(String)
    size = Column(Integer)

    def __init__(self, action, date, indexer, series_id, season, episode, quality, resource, provider=-1, version=None,
                 proper_tags=None, manually_searched=None, info_hash=None, size=None):
        self.action = action
        self.date = date
        self.indexer = indexer
        self.series_id = series_id
        self.season = season
        self.episode = episode
        self.quality = quality
        self.resource = resource
        self.provider = provider
        self.version = version
        self.proper_tags = proper_tags
        self.manually_searched = manually_searched
        self.info_hash = info_hash
        self.size = size


class ImdbInfo(BaseMain):
    """"""
    __tablename__ = 'imdb_info'
    imdb_info_id = Column(Integer, primary_key=True)
    indexer = Column(Integer, nullable=False)
    series_id = Column('series_id', Integer, nullable=False)
    imdb_id = Column(String, nullable=False)
    title = Column(String)
    year = Column(Integer)
    akas = Column(String)
    runtimes = Column(Integer)
    genres = Column(String)
    countries = Column(String)
    country_codes = Column(String)
    certificates = Column(String)
    rating = Column(String)
    votes = Column(Integer)
    plot = Column(String)
    last_update = Column(Integer)

    def __init__(self, indexer, series_id, imdb_id, title=None, year=None, akas=None, runtimes=None, genres=None,
                 countries=None, country_codes=None, certificates=None, rating=None, votes=None, plot=None, last_update=None):
        self.indexer = indexer
        self.series_id = series_id
        self.imdb_id = imdb_id
        self.title = title
        self.year = year
        self.akas = akas
        self.runtimes = runtimes
        self.genres = genres
        self.countries = countries
        self.country_codes = country_codes
        self.certificates = certificates
        self.rating = rating
        self.votes = votes
        self.plot = plot
        self.last_update = last_update

    def __str__(self):
        return self.imdb_id

    def __unicode__(self):
        return self.imdb_id


class IndexerMapping(BaseMain):
    """"""
    __tablename__ = 'indexer_mapping'
    indexer_mapping_id = Column(Integer, primary_key=True)
    indexer = Column(Integer, nullable=False)
    series_id = Column('indexer_id', Integer, nullable=False)
    mindexer = Column(Integer, nullable=False)
    mseries_id = Column('mindexer_id', Integer, nullable=False)

    def __init__(self, indexer, series_id, mindexer, mseries_id):
        self.indexer = indexer
        self.series_id = series_id
        self.mindexer = mindexer
        self.mseries_id = mseries_id


class Info(BaseMain):
    """"""
    __tablename__ = 'info'
    info_id = Column(Integer, primary_key=True)
    last_backlog = Column(Integer, nullable=False)
    last_indexer = Column(Integer, nullable=False)
    last_proper_search = Column(Integer, nullable=False)

    def __init__(self, last_backlog, last_indexer, last_proper_search):
        self.last_backlog = last_backlog
        self.last_indexer = last_indexer
        self.last_proper_search = last_proper_search

    @classmethod
    def get_version(class_):
        """Return a query of users sorted by name."""
        q = Session.query(class_).one()
        return q

    def __str__(self):
        return b'backlog: {0}, indexer: {1}, proper search: {2}'.format(
            self.last_backlog, self.last_indexer, self.last_proper_search
        )

    def __unicode__(self):
        return u'backlog: {0}, indexer: {1}, proper search: {2}'.format(
            self.last_backlog, self.last_indexer, self.last_proper_search
        )

    def __iter__(self):
        """Return the version as an iterable."""
        for i in self.last_backlog, self.last_indexer, self.last_proper_search:
            yield i


class XemRefresh(BaseMain):
    """"""
    __tablename__ = 'xem_refresh'
    xem_refresh_id = Column(Integer, primary_key=True)
    indexer = Column(Integer, nullable=False)
    series_id = Column('indexer_id', Integer, nullable=False)
    last_refreshed = Column(Integer)

    def __init__(self, indexer, series_id, last_refreshed):
        self.indexer = indexer
        self.series_id = series_id
        self.last_refreshed = last_refreshed

    @classmethod
    def get_version(class_, indexer, series_id):
        """Return a query of users sorted by name."""
        q = Session.query(class_).filter(class_.indexer == indexer).filter(class_.series_id == series_id).one()
        return q
