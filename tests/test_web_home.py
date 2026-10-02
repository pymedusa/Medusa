# coding=utf-8
"""Regression tests for query arguments on the home-page shell."""

from unittest.mock import Mock

from medusa.server.web.home.handler import Home

import pytest

from tornado.web import Application


HOME_BODY = '<main>Medusa home</main>'


@pytest.fixture
def home_render(monkeypatch, app_config):
    """Render a known shell and detect exceptions swallowed by the dispatcher."""
    app_config('WEB_USERNAME', '')
    app_config('WEB_PASSWORD', '')
    template = Mock()
    template.render.return_value = HOME_BODY
    exceptions = Mock()
    monkeypatch.setattr('medusa.server.web.home.handler.PageTemplate', Mock(return_value=template))
    monkeypatch.setattr('medusa.server.web.core.base.exception_handler.handle', exceptions)
    return template, exceptions


@pytest.fixture
def app(home_render):
    """Exercise the actual Home dispatcher through a local Tornado application."""
    return Application([(r'/home(/?.*)', Home)])


@pytest.mark.gen_test
@pytest.mark.parametrize('method', ['GET', 'POST'])
@pytest.mark.parametrize('query', ['', '0=value', 'unrelated=value', '0=first&0=second'])
async def test_home_renders_with_query_arguments(http_client, base_url, home_render, method, query):
    """Unused query arguments must not prevent either HTTP method from rendering."""
    template, exceptions = home_render
    url = base_url + '/home/' + ('?' + query if query else '')
    options = {'method': method}
    if method == 'POST':
        options['body'] = ''

    response = await http_client.fetch(url, **options)

    assert response.code == 200
    assert response.body == HOME_BODY.encode('utf-8')
    template.render.assert_called_once_with()
    exceptions.assert_not_called()


@pytest.mark.gen_test
async def test_home_renders_with_form_arguments(http_client, base_url, home_render):
    """POST form fields reach the same dispatcher without becoming render arguments."""
    template, exceptions = home_render

    response = await http_client.fetch(
        base_url + '/home/', method='POST', body='0=first&0=second',
        headers={'Content-Type': 'application/x-www-form-urlencoded'})

    assert response.code == 200
    assert response.body == HOME_BODY.encode('utf-8')
    template.render.assert_called_once_with()
    exceptions.assert_not_called()
