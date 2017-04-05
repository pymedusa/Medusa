
import datetime
from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Boolean, Column,  DateTime, Integer, String
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func

from medusa.indexers.indexer_config import (EXTERNAL_ANIDB, EXTERNAL_IMDB, EXTERNAL_TRAKT, INDEXER_TMDB,
                                            INDEXER_TVDBV2, INDEXER_TVMAZE)

engine = create_engine('sqlite:///:memory:', echo=True)

Base = declarative_base()


class Indexer(Base):
    __tablename__ = 'indexer'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255))
    mapped_to = Column(String(255))
    identifier = Column(String(255))
    indexer_id = Column(Integer)
    is_indexer = Column(Boolean)


class RecommededShow(Base):
    __tablename__ = 'recommended'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255))
    show_id = Column(String(255))
    image_href = Column(String(255))
    image_src = Column(String(255))
    cached_image = Column(String(255))
    votes = Column(Integer)
    rating = Column(String(255))
    already_added = Column(Boolean)
    created = Column(DateTime(timezone=True), server_default=func.now())
    updated = Column(DateTime(timezone=True), onupdate=func.now())
    rec_show_source_id = Column(Integer, ForeignKey('indexer.indexer_id'))
    default_indexer_id = Column(Integer, ForeignKey('indexer.indexer_id'))

    rec_show_source = relationship("Indexer", foreign_keys=[rec_show_source_id])
    default_indexer = relationship("Indexer", foreign_keys=[default_indexer_id])

# initial loading of indexer table

indexers = [
    {'id': INDEXER_TVDBV2,
     'name': 'TVDBv2',
     'mapped_to': 'tvdb_id',
     'identifier': 'tvdb',
     'is_indexer': True},
    {'id': INDEXER_TVMAZE,
     'name': 'TVMaze',
     'mapped_to': 'tvmaze_id',
     'identifier': 'tvmaze',
     'is_indexer': True},
    {'id': INDEXER_TMDB,
     'name': 'TMDB',
     'mapped_to': 'tmdb_id',
     'identifier': 'tmdb',
     'is_indexer': True},
    {'id': EXTERNAL_IMDB,
     'name': 'IMDB',
     'mapped_to': 'imdb_id',
     'identifier': 'imdb',
     'is_indexer': False},
    {'id': EXTERNAL_ANIDB,
     'name': 'AniDB',
     'mapped_to': 'anidb_id',
     'identifier': 'anidb',
     'is_indexer': False},
    {'id': EXTERNAL_TRAKT,
     'name': 'Trakt',
     'mapped_to': 'trakt_id',
     'identifier': 'trakt',
     'is_indexer': False}
]

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

session = Session()
if not session.query(Indexer).all():
    session.bulk_insert_mappings(Indexer, indexers)
    session.commit()

