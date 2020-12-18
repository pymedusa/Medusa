# coding=utf-8
"""Configuration for pytest."""
from __future__ import unicode_literals

from medusa.server.core import get_apiv2_handlers
import pytest
import tornado.web

from six import iteritems


TEST_API_KEY = 'myhiddenkey'

@pytest.fixture(scope='session')
def app():
    from medusa import app as medusa_app
    medusa_app.APP_VERSION = '0.0.0'
    return tornado.web.Application(get_apiv2_handlers(''))


@pytest.fixture
def auth_headers(app_config):
    username = app_config('WEB_USERNAME', 'user')
    password = app_config('WEB_PASSWORD', 'password')

    return dict(auth_username=username, auth_password=password)


@pytest.fixture
def create_url(app_config, base_url):
    def create(url, **kwargs):
        api_key = app_config('API_KEY', TEST_API_KEY)
        params = dict(api_key=api_key)
        params.update(kwargs)
        q = '?' + ('&'.join(['{0}={1}'.format(k, v) for k, v in iteritems(params)])) if params else ''
        url = '{base}{url}{query}'.format(base=base_url, url=url, query=q)
        return url

    return create
