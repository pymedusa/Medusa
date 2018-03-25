# set up a scoped_session

from contextlib import contextmanager
from sqlalchemy import create_engine, __version__ as sqlal_version
from sqlalchemy.orm import scoped_session, sessionmaker

from medusa.models.application import main_engine
from medusa.models.cache import cache_engine
from medusa.models.failed import failed_engine

min_version = (1, 2, 3)

if tuple(map(int, sqlal_version.split('.'))) < min_version:
    raise Exception('Medusa requires at least sqlalchemy version {min_version}'.format(min_version=min_version))

main_session_factory = sessionmaker(bind=main_engine)
cache_engine_factory = sessionmaker(bind=cache_engine)
failed_engine_factory = sessionmaker(bind=failed_engine)

SessionMain = scoped_session(main_session_factory)
SessionCache = scoped_session(cache_engine_factory)
SessionFailed = scoped_session(failed_engine_factory)

DB = {'main': SessionMain, 'cache': SessionCache, 'failed': SessionFailed}


@contextmanager
def session_scope(database=None):
    """Provide a transactional scope around a series of operations."""
    session = DB.get(database, SessionMain)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
