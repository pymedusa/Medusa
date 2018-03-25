from os.path import join
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base

from medusa import app

# Examples on how the Base class can be declared.
failed_engine = create_engine('sqlite:///' + join(app.DATA_DIR, 'failed.db'))
BaseFailed = declarative_base(failed_engine)
