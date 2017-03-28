"""Dredd hook."""
import ConfigParser
import json

import dredd_hooks as hooks

web_username = 'testuser'
web_password = 'testpass'
api_key = '1234567890ABCDEF1234567890ABCDEF'

stash = {}


@hooks.before_each
def add_api_key(transaction):
    """Add api key."""
    transaction['request']['headers']['x-api-key'] = api_key


@hooks.before('/api/v2/authenticate'
              ' > Return a JWT for the provided user. This is required for all other routes'
              ' > 200'
              ' > application/json; charset=UTF-8')
def add_auth(transaction):
    """Add auth."""
    del transaction['request']['headers']['x-api-key']
    data = json.loads(transaction['request']['body'])
    data['username'] = web_username
    data['password'] = web_password
    transaction['request']['body'] = json.dumps(data)


@hooks.before_each
def skip_body_validation(transaction):
    """Skip body validation when no body is expected."""
    expected = transaction['expected']
    expected_content_type = expected['headers'].get('Content-Type')
    expected_status_code = int(expected['statusCode'])
    # print(transaction['name'])
    if not expected_content_type or expected_status_code == 204:
        print('Skipping body validation for "{name}".'.format(name=transaction['name']))
        del expected['body']

        if 'schema' in transaction['expected']:
            print('Skipping schema validation for "{name}".'.format(name=transaction['name']))
            del expected['schema']

        if expected_content_type:
            print('Skipping content-type validation for "{name}".'.format(name=transaction['name']))
            del expected['headers']['Content-Type']


@hooks.before('/api/v2/series/{id}/operation > Create an operation that relates to a specific series > 201 > '
              'application/json; charset=UTF-8')
def before_post_series_operation(transaction):
    """Skip the following operation: http 201 - ARCHIVE_EPISODES."""
    transaction['skip'] = True


@hooks.before('/api/v2/log > Log a message > 201 > application/json; charset=UTF-8')
def post_log_no_body(transaction):
    """Skip body validation when creating a log message."""
    del transaction['expected']['body']
    del transaction['expected']['headers']['Content-Type']


@hooks.after('/api/v2/alias > Create a new alias > 201 > application/json; charset=UTF-8')
def stash_alias_id(transaction):
    """Stash alias id."""
    data = json.loads(transaction['real']['body'])
    stash['alias_id'] = data['id']


@hooks.before('/api/v2/alias/{id} > Replace alias data > 204 > application/json; charset=UTF-8')
def before_put_alias(transaction):
    """Replace alias id with the stashed one."""
    transaction['fullPath'] = transaction['fullPath'].replace('123456', str(stash['alias_id']))
    transaction['request']['uri'] = transaction['fullPath']
    data = json.loads(transaction['request']['body'])
    data['id'] = stash['alias_id']
    transaction['request']['body'] = json.dumps(data)


@hooks.before('/api/v2/alias/{id} > Delete an alias > 204 > application/json; charset=UTF-8')
def before_delete_alias(transaction):
    """Replace alias id with the stashed one."""
    transaction['fullPath'] = transaction['fullPath'].replace('123456', str(stash['alias_id']))
    transaction['request']['uri'] = transaction['fullPath']


def start():
    """Start application."""
    import os
    import shutil
    import sys

    current_dir = os.path.dirname(__file__)
    app_dir = os.path.abspath(os.path.join(current_dir, '..'))
    data_dir = os.path.abspath(os.path.join(current_dir, 'data'))
    if os.path.isdir(data_dir):
        shutil.rmtree(data_dir)
    args = [
        '--datadir={0}'.format(data_dir),
        '--nolaunch',
    ]

    os.makedirs(data_dir)
    os.chdir(data_dir)
    config = ConfigParser.RawConfigParser()
    config.read('config.ini')
    config.add_section('General')
    config.set('General', 'web_username', web_username)
    config.set('General', 'web_password', web_password)
    config.set('General', 'api_key', api_key)
    with open('config.ini', 'wb') as configfile:
        config.write(configfile)

    sys.path.insert(1, app_dir)

    from medusa.__main__ import Application
    application = Application()
    application.start(args)

if __name__ == '__main__':
    start()
