# coding=utf-8

"""Test if a retry session works."""

from medusa.session.core import MedusaSession

import pytest
from requests.exceptions import RetryError
from six import text_type


session = MedusaSession(retry_session={'retries': 1, 'status': (404,)})

url = 'https://cdn.pymedusa.com/retry.txt'

try:
    response = session.get(url)
except RetryError as error:
    assert text_type(error.message.reason) == 'too many 404 error responses'
else:
    pytest.fail()
