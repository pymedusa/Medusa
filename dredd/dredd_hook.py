#!/usr/bin/env python
# coding=utf-8
"""Dredd hook."""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import io
import json
import os
import sys

try:
    from builtins import print as real_print
except ImportError:
    # Python 2
    from __builtin__ import print as real_print

current_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(1, os.path.join(root_dir, 'ext'))
sys.path.insert(1, os.path.join(root_dir, 'ext%d' % sys.version_info.major))

from configparser import ConfigParser

import dredd_hooks as hooks

from six import string_types
from six.moves.collections_abc import Mapping
from six.moves.urllib.parse import parse_qs, urlencode, urlparse

import yaml


api_description = None

stash = {
    'web-username': 'testuser',
    'web-password': 'testpass',
    'api-key': '1234567890ABCDEF1234567890ABCDEF',
}

hook_log = os.path.join(current_dir, 'hook.log')
try:
    os.remove(hook_log)
except OSError:
    pass


def print(*args, **kwargs):
    """Override builtin print to write to a file, because nothing prints to `stdout`."""
    with io.open(hook_log, 'a', encoding='utf-8') as fh:
        kwargs['file'] = fh
        return real_print(*args, **kwargs)


@hooks.before_all
def order_and_load_api_description(transactions):
    """Load api description."""
    global api_description

    def _sort_key(transaction):
        # DELETE transactions go last so the rest of the suite has the fixture
        # to query against. Among DELETEs we want the most-specific paths first
        # (e.g. DELETE /series/{id}/episodes/{id} BEFORE DELETE /series/{id})
        # so that child resources are removed before their parent — otherwise
        # the parent delete makes subsequent child DELETEs return 404.
        is_delete = transaction['request']['method'] == 'DELETE'
        depth = -len(transaction['origin']['resourceName'].split('/')) if is_delete else 0
        return (is_delete, depth)

    transactions.sort(key=_sort_key)

    with io.open(transactions[0]['origin']['filename'], 'rb') as stream:
        api_description = yaml.safe_load(stream)


@hooks.before_each
def configure_transaction(transaction):
    """Configure request based on x- property values for each response code."""
    base_path = api_description['basePath']

    path = transaction['origin']['resourceName']
    method = transaction['request']['method']
    status_code = int(transaction['expected']['statusCode'])
    response = api_description['paths'][path[len(base_path):]][method.lower()]['responses'][status_code]

    # Whether we should skip this test
    transaction['skip'] = response.get('x-disabled', False)

    # Add api-key
    if not response.get('x-no-api-key', False):
        transaction['request']['headers']['x-api-key'] = stash['api-key']

    # If no body is expected, skip body validation
    expected = transaction['expected']
    expected_content_type = expected['headers'].get('Content-Type')
    expected_status_code = int(expected['statusCode'])
    if expected_status_code == 204 or response.get('x-expect', {}).get('no-body', False):
        if expected.get('body'):
            del expected['body']
        if expected_content_type:
            print('Skipping content-type validation for {name!r}.'.format(name=transaction['name']))
            del expected['headers']['Content-Type']

    # Keep stash configuration in the transaction to be executed in an after hook
    transaction['x-stash'] = response.get('x-stash') or {}

    # Change request based on x-request configuration
    url = transaction['fullPath']
    parsed_url = urlparse(url)
    parsed_params = parse_qs(parsed_url.query)
    parsed_path = parsed_url.path

    request = response.get('x-request', {})
    body = request.get('body')
    body_update = request.get('body-update')
    if body is not None:
        transaction['request']['body'] = json.dumps(evaluate(body))
    elif body_update is not None:
        try:
            orig_body = json.loads(transaction['request']['body'])
        except ValueError:
            orig_body = {}

        # Use the current request body and update it with the new values
        new_body = dict(orig_body, **evaluate(body_update))
        transaction['request']['body'] = json.dumps(new_body)

    path_params = request.get('path-params')
    if path_params:
        params = {}
        resource_parts = path.split('/')
        for i, part in enumerate(url.split('/')):
            if not part:
                continue

            resource_part = resource_parts[i]
            if resource_part[0] == '{' and resource_part[-1] == '}':
                params[resource_part[1:-1]] = part

        params.update(path_params)
        new_url = path
        for name, value in params.items():
            value = evaluate(value)
            new_url = new_url.replace('{' + name + '}', str(value))

        replace_url(transaction, new_url)

    query_params = request.get('query-params')
    if query_params:
        for name, value in query_params.items():
            query_params[name] = evaluate(value)

        query_params = dict(parsed_params, **query_params)
        new_url = parsed_path if not query_params else parsed_path + '?' + urlencode(query_params)

        replace_url(transaction, new_url)


@hooks.after_each
def stash_values(transaction):
    """Stash values."""
    if 'real' in transaction and 'bodySchema' in transaction['expected']:
        body = json.loads(transaction['real']['body']) if transaction['real']['body'] else None
        headers = transaction['real']['headers']
        for name, value in transaction['x-stash'].items():
            value = evaluate(value, {'body': body, 'headers': headers})
            print('Stashing {name}: {value!r}'.format(name=name, value=value))
            stash[name] = value


def replace_url(transaction, new_url):
    """Replace with a new URL."""
    transaction['fullPath'] = new_url
    transaction['request']['uri'] = new_url
    transaction['id'] = transaction['request']['method'] + ' ' + new_url


def evaluate(expression, context=None):
    """Evaluate the expression value."""
    context = context or {'stash': stash}
    if isinstance(expression, string_types) and expression.startswith('${') and expression.endswith('}'):
        value = eval(expression[2:-1], context)
        print('Expression {expression} evaluated to {value!r}'.format(expression=expression, value=value))
        return value
    elif isinstance(expression, Mapping):
        for key, value in expression.items():
            expression[key] = evaluate(value, context=context)
    elif isinstance(expression, list):
        for i, value in enumerate(expression):
            expression[i] = evaluate(value, context=context)

    return expression


# The slug that the Dredd transactions assume already exists. POST /api/v2/series
# only enqueues an asynchronous indexer fetch, which never resolves in CI, so we
# seed the database (and the in-memory show list) ourselves before the web
# server begins accepting requests.
TEST_SERIES_INDEXER = 1  # tvdb
TEST_SERIES_ID = 301824
TEST_SERIES_EPISODES = ((1, 1), (1, 2))


def _seed_test_data():
    """Insert the tvdb301824 fixture into the database and showList."""
    from medusa import app, db
    from medusa.common import SKIPPED
    from medusa.tv.series import Series

    show_dir = os.path.join(os.getcwd(), 'tvdb{0}'.format(TEST_SERIES_ID))
    try:
        os.makedirs(show_dir)
    except OSError:
        pass

    main_db_con = db.DBConnection()

    main_db_con.upsert('tv_shows', {
        'show_name': 'Dredd Test Show',
        'location': show_dir,
        'network': '',
        'genre': '',
        'classification': '',
        'runtime': 30,
        'quality': 4,
        'airs': '',
        'status': 'Continuing',
        'flatten_folders': 0,
        'paused': 0,
        'startyear': 2017,
        'air_by_date': 0,
        'anime': 0,
        'scene': 0,
        'sports': 0,
        'subtitles': 0,
        'notify_list': '{}',
        'dvdorder': 0,
        'lang': 'en',
        'imdb_id': '',
        'last_update_indexer': 1,
        'rls_ignore_words': '',
        'rls_require_words': '',
        'default_ep_status': SKIPPED,
    }, {'indexer': TEST_SERIES_INDEXER, 'indexer_id': TEST_SERIES_ID})

    for season, episode in TEST_SERIES_EPISODES:
        main_db_con.upsert('tv_episodes', {
            'indexerid': TEST_SERIES_ID * 100 + episode,
            'name': 'Test Episode S{0:02d}E{1:02d}'.format(season, episode),
            'description': '',
            'subtitles': '',
            'subtitles_searchcount': 0,
            'subtitles_lastsearch': '0001-01-01 00:00:00',
            'airdate': 736000,
            'hasnfo': 0,
            'hastbn': 0,
            'status': SKIPPED,
            'location': '',
            'file_size': 0,
            'release_name': '',
            'is_proper': 0,
            'absolute_number': episode,
            'version': -1,
            'release_group': '',
        }, {
            'indexer': TEST_SERIES_INDEXER,
            'showid': TEST_SERIES_ID,
            'season': season,
            'episode': episode,
        })

    # Give the alias endpoints something to query against. The GET /alias
    # handler reads scene_exceptions directly so it does not require the
    # series to be present in app.showList.
    main_db_con.action(
        'INSERT OR IGNORE INTO scene_exceptions '
        '(indexer, series_id, title, season, custom) VALUES (?, ?, ?, ?, ?)',
        [TEST_SERIES_INDEXER, TEST_SERIES_ID, 'Dredd Test Alias', -1, 1],
    )

    # Drop a placeholder banner into the image cache so
    # GET /api/v2/series/{id}/asset/banner returns 200 instead of 404 (the
    # asset handler reads <CACHE_DIR>/images/<indexer>/<id>.banner.jpg).
    cache_image_dir = os.path.join(app.CACHE_DIR, 'images', 'tvdb')
    try:
        os.makedirs(cache_image_dir)
    except OSError:
        pass
    banner_path = os.path.join(cache_image_dir, '{0}.banner.jpg'.format(TEST_SERIES_ID))
    if not os.path.isfile(banner_path):
        with open(banner_path, 'wb') as fh:
            # 1x1 JPEG so the handler streams a non-empty body with a real
            # image MIME type derived from the filename.
            fh.write(
                b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01'
                b'\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07'
                b'\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14'
                b'\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444'
                b'\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01'
                b'\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01'
                b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06'
                b'\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02'
                b'\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11'
                b'\x05\x12!1A\x06\x13Qa\x07"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15'
                b'R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456789:CDEFG'
                b'HIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a'
                b'\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7'
                b'\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4'
                b'\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda'
                b'\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5'
                b'\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb'
                b'\xd0\xff\xd9'
            )

    series_obj = Series(TEST_SERIES_INDEXER, TEST_SERIES_ID)
    app.showList.append(series_obj)
    print('Seeded test fixture tvdb{0} at {1}'.format(TEST_SERIES_ID, show_dir))


def start():
    """Start application."""
    import shutil

    data_dir = os.path.join(current_dir, 'data')
    if os.path.isdir(data_dir):
        shutil.rmtree(data_dir)
    args = [
        '--datadir={0}'.format(data_dir),
        '--nolaunch',
    ]

    os.makedirs(data_dir)
    os.chdir(data_dir)
    config = ConfigParser()
    config.read('config.ini')
    config.add_section('General')
    config.set('General', 'web_username', stash['web-username'])
    config.set('General', 'web_password', stash['web-password'])
    config.set('General', 'api_key', stash['api-key'])
    with io.open('config.ini', 'w', encoding='utf-8') as configfile:
        config.write(configfile)

    sys.path.insert(1, root_dir)

    from medusa.__main__ import Application

    # Hook into load_shows_from_db so the fixture is in place before the web
    # server starts accepting requests; otherwise dependent transactions race
    # against the seed and fail with "Series not found".
    original_load_shows_from_db = Application.load_shows_from_db

    def load_shows_from_db_with_seed():
        original_load_shows_from_db()
        try:
            _seed_test_data()
        except Exception as error:  # pragma: no cover - test seed best-effort
            import traceback
            print('Failed to seed test data: {0!r}'.format(error))
            print(traceback.format_exc())

    Application.load_shows_from_db = staticmethod(load_shows_from_db_with_seed)

    application = Application()
    application.start(args)


if __name__ == '__main__':
    start()
