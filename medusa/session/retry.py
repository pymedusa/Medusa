"""Session class retry method."""

import logging

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def requests_retry_session(session, retry_session):
    """Retry session.

    :param retry_session: dict expecting following params: retries, backoff_factor, status
        retries: number of retries to allow
        backoff_factor: to apply between attempts after the second try
        status: a set of HTTP status codes that we should force a retry on.

    Docs: http://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html#module-urllib3.util.retry
    By default, the retry only fires for these conditions:
    - Could not get a connection from the pool.
    - TimeoutError
    - HTTPException raised (from http.client in Python 3 else httplib)
    - SocketError
    - ProtocolError

    Most errors are resolved immediately by a second try without a delay),
    urllib3 will sleep for {backoff factor} * (2 ^ ({number of total retries} - 1)) seconds
    https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html#module-urllib3.util.retry

    """
    session = session or requests.Session()
    retries = retry_session.get('retries', 3)
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=retry_session.get('backoff_factor', 2),
        status_forcelist=retry_session.get('status', (500, 502, 503, 504, 509)),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session
