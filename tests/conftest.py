# coding=utf-8
"""Configuration for pytest."""
import logging
from logging.handlers import RotatingFileHandler

from babelfish.language import Language
from github.AuthenticatedUser import AuthenticatedUser
from github.Gist import Gist
from github.Issue import Issue
from github.MainClass import Github
from github.Organization import Organization
from github.Repository import Repository
from medusa import app, cache
from medusa.common import DOWNLOADED, Quality
from medusa.helper.common import dateTimeFormat
from medusa.indexers.indexer_config import INDEXER_TVDBV2
from medusa.logger import CensoredFormatter, ContextFilter, FORMATTER_PATTERN, instance
from medusa.logger import read_loglines as logger_read_loglines
from medusa.tv import Episode, Series
from medusa.version_checker import CheckVersion
from mock.mock import Mock
import pytest

from subliminal.subtitle import Subtitle
from subliminal.video import Video
import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode, SequenceNode


def pytest_collection_modifyitems(config, items):
    """Disable test execution if -p no:unittest is defined."""
    plugins = config.getoption('plugins', default=None)
    if plugins and 'no:unittest' in plugins:
        for item in reversed(items):
            if isinstance(item, pytest.Function):
                items.remove(item)


def _construct_mapping(self, node, deep=False):
    """Custom yaml map constructor to allow lists to be key of a map.

    :param self:
    :param node:
    :param deep:
    :return:
    """
    if not isinstance(node, MappingNode):
        raise ConstructorError(None, None, 'expected a mapping node, but found %s' % node.id, node.start_mark)
    mapping = {}
    for key_node, value_node in node.value:
        is_sequence = isinstance(key_node, SequenceNode)
        key = self.construct_object(key_node, deep=deep or is_sequence)
        try:
            if is_sequence:
                key = tuple(key)
            hash(key)
        except TypeError as exc:
            raise ConstructorError('while constructing a mapping', node.start_mark,
                                   'found unacceptable key (%s)' % exc, key_node.start_mark)
        value = self.construct_object(value_node, deep=deep)
        mapping[key] = value
    return mapping


yaml.Loader.add_constructor('tag:yaml.org,2002:map', _construct_mapping)

sequence_number = 1


def _patch_object(monkeypatch, target, **kwargs):
    for field, value in kwargs.items():
        target.__dict__[field] = value
        monkeypatch.setattr(type(target), field, lambda this: this.field, raising=False)
    return target


@pytest.fixture(scope="session", autouse=True)
def execute_before_any_test():
    cache.fallback()


@pytest.fixture
def app_config(monkeypatch):
    def config(name, value):
        monkeypatch.setattr(app, name, value)
        return value

    return config


@pytest.fixture
def tvshow(create_tvshow):
    return create_tvshow(indexer=INDEXER_TVDBV2, indexerid=12, name='Show Name', imdbid='tt0000000')


@pytest.fixture
def tvepisode(tvshow, create_tvepisode):
    return create_tvepisode(show=tvshow, season=3, episode=4, indexer=34, file_size=1122334455,
                            name='Episode Title', status=Quality.composite_status(DOWNLOADED, Quality.FULLHDBLURAY),
                            release_group='SuperGroup')


@pytest.fixture
def video():
    return Video.fromname('Show.Name.S03E04.mkv')


@pytest.fixture
def create_sub(monkeypatch):
    def create(language, **kwargs):
        target = Subtitle(Language.fromopensubtitles(language))
        return _patch_object(monkeypatch, target, **kwargs)

    return create


@pytest.fixture
def create_tvshow(monkeypatch):
    def create(indexer=INDEXER_TVDBV2, indexerid=0, lang='', quality=Quality.UNKNOWN, flatten_folders=0,
               enabled_subtitles=0, **kwargs):
        monkeypatch.setattr(Series, '_load_from_db', lambda method: None)
        target = Series(indexer=indexer, indexerid=indexerid, lang=lang, quality=quality,
                        flatten_folders=flatten_folders, enabled_subtitles=enabled_subtitles)
        return _patch_object(monkeypatch, target, **kwargs)

    return create


@pytest.fixture
def create_tvepisode(monkeypatch):
    def create(show, season, episode, filepath='', **kwargs):
        monkeypatch.setattr(Episode, '_specify_episode', lambda method, season, episode: None)
        target = Episode(show=show, season=season, episode=episode, filepath=filepath)
        return _patch_object(monkeypatch, target, **kwargs)

    return create


@pytest.fixture
def create_file(tmpdir):
    def create(filename, lines=None, **kwargs):
        f = tmpdir.ensure(filename)
        f.write_binary('\n'.join(lines or []))
        return str(f)

    return create


@pytest.fixture
def version_checker(monkeypatch):
    target = CheckVersion()
    monkeypatch.setattr(target, 'need_update', lambda: False)
    return target


@pytest.fixture
def commit_hash(monkeypatch):
    target = 'abcdef0'
    monkeypatch.setattr(app, 'CUR_COMMIT_HASH', target)
    return target


@pytest.fixture
def logfile(tmpdir):
    target = str(tmpdir.ensure('logfile.log'))
    instance.log_file = target
    return target


@pytest.fixture
def rotating_file_handler(logfile):
    handler = RotatingFileHandler(logfile, maxBytes=512 * 1024, backupCount=10, encoding='utf-8')
    handler.setFormatter(CensoredFormatter(FORMATTER_PATTERN, dateTimeFormat))
    handler.setLevel(logging.DEBUG)
    return handler


@pytest.fixture
def logger(rotating_file_handler, commit_hash):
    print('Using commit_hash {}'.format(commit_hash))
    target = logging.getLogger('testing_logger')
    target.addFilter(ContextFilter())
    target.addHandler(rotating_file_handler)
    target.propagate = False
    target.setLevel(logging.DEBUG)

    return target


@pytest.fixture
def read_loglines(logfile):
    return logger_read_loglines(logfile)


@pytest.fixture
def github(monkeypatch, github_user, github_organization):
    target = Github(login_or_token='_test_user_', password='_test_password_', user_agent='MedusaTests')
    monkeypatch.setattr(target, 'get_user', lambda *args, **kwargs: github_user)
    monkeypatch.setattr(target, 'get_organization', lambda login: github_organization)
    return target


@pytest.fixture
def github_user(monkeypatch):
    target = AuthenticatedUser(Mock(), Mock(), dict(), True)

    def create_gist(public, files):
        _patch_object(monkeypatch, target, public=public,
                      files={name: fc._identity['content'] for name, fc in files.items()})
        return target

    monkeypatch.setattr(target, 'create_gist', create_gist)
    return target


@pytest.fixture
def github_gist():
    return Gist(Mock(), Mock(), dict(), True)


@pytest.fixture
def github_organization(monkeypatch, github_repo):
    target = Organization(Mock(), Mock(), dict(), True)
    monkeypatch.setattr(target, 'get_repo', lambda name: github_repo)
    return target


@pytest.fixture
def github_repo():
    return Repository(Mock(), Mock(), dict(), True)


@pytest.fixture
def create_github_issue(monkeypatch):
    def create(title, body=None, locked=False, number=1, **kwargs):
        target = Issue(Mock(), Mock(), dict(), True)
        raw_data = {
            'locked': locked
        }
        _patch_object(monkeypatch, target, number=number, title=title, body=body, raw_data=raw_data)
        return target

    return create


@pytest.fixture
def raise_github_exception():
    def raise_ex(exception_type, http_status):
        raise exception_type(http_status, {})

    return raise_ex
