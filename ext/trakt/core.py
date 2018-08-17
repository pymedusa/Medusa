# -*- coding: utf-8 -*-
"""Objects, properties, and methods to be shared across other modules in the
trakt package
"""
from __future__ import print_function
import json
import logging
import os
import requests
import six
import sys
import time
from collections import namedtuple
from functools import wraps
from requests.compat import urljoin
from requests_oauthlib import OAuth2Session
from trakt import errors

__author__ = 'Jon Nappi'
__all__ = ['Airs', 'Alias', 'Comment', 'Genre', 'get', 'delete', 'post', 'put',
           'init', 'BASE_URL', 'CLIENT_ID', 'CLIENT_SECRET', 'REDIRECT_URI',
           'HEADERS', 'CONFIG_PATH', 'OAUTH_TOKEN', 'OAUTH_REFRESH',
           'PIN_AUTH', 'OAUTH_AUTH', 'AUTH_METHOD', 'APPLICATION_ID']

#: The base url for the Trakt API. Can be modified to run against different
#: Trakt.tv environments
BASE_URL = 'https://api-v2launch.trakt.tv/'

#: The Trakt.tv OAuth Client ID for your OAuth Application
CLIENT_ID = None

#: The Trakt.tv OAuth Client Secret for your OAuth Application
CLIENT_SECRET = None

#: The OAuth2 Redirect URI for your OAuth Application
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'

#: Default request HEADERS
HEADERS = {'Content-Type': 'application/json', 'trakt-api-version': '2'}

#: Default path for where to store your trakt.tv API authentication information
CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.pytrakt.json')

#: Your personal Trakt.tv OAUTH Bearer Token
OAUTH_TOKEN = api_key = None

# Your OAUTH refresh token
OAUTH_REFRESH = None

#: Flag used to enable Trakt PIN authentication
PIN_AUTH = 'PIN'

#: Flag used to enable Trakt OAuth authentication
OAUTH_AUTH = 'OAUTH'

#: Flag used to enable Trakt OAuth device authentication
DEVICE_AUTH = 'DEVICE'

#: The currently enabled authentication method. Default is ``PIN_AUTH``
AUTH_METHOD = PIN_AUTH

#: The ID of the application to register with, when using PIN authentication
APPLICATION_ID = None


def _store(**kwargs):
    """Helper function used to store Trakt configurations at ``CONFIG_PATH``

    :param kwargs: Keyword args to store at ``CONFIG_PATH``
    """
    with open(CONFIG_PATH, 'w') as config_file:
        json.dump(kwargs, config_file)


def _get_client_info(app_id=False):
    """Helper function to poll the user for Client ID and Client Secret
    strings

    :return: A 2-tuple of client_id, client_secret
    """
    global APPLICATION_ID
    print('If you do not have a client ID and secret. Please visit the '
          'following url to create them.')
    print('http://trakt.tv/oauth/applications')
    client_id = six.moves.input('Please enter your client id: ')
    client_secret = six.moves.input('Please enter your client secret: ')
    if app_id:
        msg = 'Please enter your application ID ({default}): '.format(
            default=APPLICATION_ID)
        user_input = six.moves.input(msg)
        if user_input:
            APPLICATION_ID = user_input
    return client_id, client_secret


def pin_auth(pin=None, client_id=None, client_secret=None, store=False):
    """Generate an access_token from a Trakt API PIN code.

    :param pin: Optional Trakt API PIN code. If one is not specified, you will
        be prompted to go generate one
    :param store: Boolean flag used to determine if your trakt api auth data
        should be stored locally on the system. Default is :const:`False` for
        the security conscious
    :return: Your OAuth access token
    """
    global OAUTH_TOKEN, CLIENT_ID, CLIENT_SECRET
    CLIENT_ID, CLIENT_SECRET = client_id, client_secret
    if client_id is None and client_secret is None:
        CLIENT_ID, CLIENT_SECRET = _get_client_info(app_id=True)
    if pin is None and APPLICATION_ID is None:
        print('You must set the APPLICATION_ID of the Trakt application you '
              'wish to use. You can find this ID by visiting the following '
              'URL.')
        print('https://trakt.tv/oauth/applications')
        sys.exit(1)
    if pin is None:
        print('If you do not have a Trakt.tv PIN, please visit the following '
              'url and log in to generate one.')
        pin_url = 'https://trakt.tv/pin/{id}'.format(id=APPLICATION_ID)
        print(pin_url)
        pin = six.moves.input('Please enter your PIN: ')
    args = {'code': pin,
            'redirect_uri': REDIRECT_URI,
            'grant_type': 'authorization_code',
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET}

    response = requests.post(''.join([BASE_URL, '/oauth/token']), data=args)
    OAUTH_TOKEN = response.json().get('access_token', None)

    if store:
        _store(CLIENT_ID=CLIENT_ID, CLIENT_SECRET=CLIENT_SECRET,
               OAUTH_TOKEN=OAUTH_TOKEN, APPLICATION_ID=APPLICATION_ID)
    return OAUTH_TOKEN


def oauth_auth(username, client_id=None, client_secret=None, store=False):
    """Generate an access_token to allow your application to authenticate via
    OAuth

    :param username: Your trakt.tv username
    :param client_id: Your Trakt OAuth Application's Client ID
    :param client_secret: Your Trakt OAuth Application's Client Secret
    :param store: Boolean flag used to determine if your trakt api auth data
        should be stored locally on the system. Default is :const:`False` for
        the security conscious
    :return: Your OAuth access token
    """
    global CLIENT_ID, CLIENT_SECRET, OAUTH_TOKEN
    if client_id is None and client_secret is None:
        client_id, client_secret = _get_client_info()
    CLIENT_ID, CLIENT_SECRET = client_id, client_secret
    HEADERS['trakt-api-key'] = CLIENT_ID

    authorization_base_url = urljoin(BASE_URL, '/oauth/authorize')
    token_url = urljoin(BASE_URL, '/oauth/token')

    # OAuth endpoints given in the API documentation
    oauth = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, state=None)

    # Redirect user to Trakt for authorization
    authorization_url, _ = oauth.authorization_url(authorization_base_url,
                                                   username=username)
    print('Please go here and authorize,', authorization_url)

    # Get the authorization verifier code from the callback url
    response = six.moves.input('Paste the Code returned here: ')
    # Fetch, assign, and return the access token
    oauth.fetch_token(token_url, client_secret=CLIENT_SECRET, code=response)
    OAUTH_TOKEN = oauth.token['access_token']

    if store:
        _store(CLIENT_ID=CLIENT_ID, CLIENT_SECRET=CLIENT_SECRET,
               OAUTH_TOKEN=OAUTH_TOKEN)
    return oauth.token['access_token']


def get_device_code(client_id=None, client_secret=None):
    """Generate a device code, used for device oauth authentication.

    Trakt docs: https://trakt.docs.apiary.io/#reference/
    authentication-devices/device-code
    :param client_id: Your Trakt OAuth Application's Client ID
    :param client_secret: Your Trakt OAuth Application's Client Secret
    :param store: Boolean flag used to determine if your trakt api auth data
        should be stored locally on the system. Default is :const:`False` for
        the security conscious
    :return: Your OAuth device code.
    """
    global CLIENT_ID, CLIENT_SECRET, OAUTH_TOKEN
    if client_id is None and client_secret is None:
        client_id, client_secret = _get_client_info()
    CLIENT_ID, CLIENT_SECRET = client_id, client_secret
    HEADERS['trakt-api-key'] = CLIENT_ID

    device_code_url = urljoin(BASE_URL, '/oauth/device/code')
    headers = {'Content-Type': 'application/json'}
    data = {"client_id": CLIENT_ID}

    device_response = requests.post(device_code_url, json=data,
                                    headers=headers).json()
    print('Your user code is: {user_code}, please navigate to '
          '{verification_url} to authenticate'.format(
            user_code=device_response.get('user_code'),
            verification_url=device_response.get('verification_url')
          ))

    device_response['requested'] = time.time()
    return device_response


def get_device_token(device_code, client_id=None, client_secret=None,
                     store=False):
    """
    Trakt docs: https://trakt.docs.apiary.io/#reference/
    authentication-devices/get-token
    Response:
    {
      "access_token": "",
      "token_type": "bearer",
      "expires_in": 7776000,
      "refresh_token": "",
      "scope": "public",
      "created_at": 1519329051
    }
    :return: Information regarding the authentication polling.
    :return type: dict
    """
    global CLIENT_ID, CLIENT_SECRET, OAUTH_TOKEN, OAUTH_REFRESH
    if client_id is None and client_secret is None:
        client_id, client_secret = _get_client_info()
    CLIENT_ID, CLIENT_SECRET = client_id, client_secret
    HEADERS['trakt-api-key'] = CLIENT_ID

    data = {
        "code": device_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }

    response = requests.post(urljoin(BASE_URL, '/oauth/device/token'),
                             json=data)

    # We only get json on success.
    if response.status_code == 200:
        data = response.json()
        OAUTH_TOKEN = data.get('access_token')
        OAUTH_REFRESH = data.get('refresh_token')

        if store:
            _store(
                CLIENT_ID=CLIENT_ID, CLIENT_SECRET=CLIENT_SECRET,
                OAUTH_TOKEN=OAUTH_TOKEN, OAUTH_REFRESH=OAUTH_REFRESH
            )

    return response


def device_auth(client_id=None, client_secret=None, store=False):
    """Process for authenticating using device authentication.

    The function will attempt getting the device_id, and provide
    the user with a url and code. After getting the device
    id, a timer is started to poll periodic for a successful authentication.
    This is a blocking action, meaning you
    will not be able to run any other code, while waiting for an access token.

    If you want more control over the authentication flow, use the functions
    get_device_code and get_device_token.
    Where poll_for_device_token will check if the "offline"
    authentication was successful.

    :param client_id: Your Trakt OAuth Application's Client ID
    :param client_secret: Your Trakt OAuth Application's Client Secret
    :param store: Boolean flag used to determine if your trakt api auth data
        should be stored locally on the system. Default is :const:`False` for
        the security conscious
    :return: A dict with the authentication result.
    Or False of authentication failed.
    """
    error_messages = {
        404: 'Invalid device_code',
        409: 'You already approved this code',
        410: 'The tokens have expired, restart the process',
        418: 'You explicitly denied this code',
    }

    success_message = (
        "You've been succesfully authenticated. "
        "With access_token {access_token} and refresh_token {refresh_token}"
    )

    response = get_device_code(client_id=client_id,
                               client_secret=client_secret)
    device_code = response['device_code']
    interval = response['interval']

    # No need to check for expiration, the API will notify us.
    while True:
        response = get_device_token(device_code, client_id, client_secret,
                                    store)

        if response.status_code == 200:
            print(success_message.format_map(response.json()))
            break

        elif response.status_code == 429:  # slow down
            interval *= 2

        elif response.status_code != 400:  # not pending
            print(error_messages.get(response.status_code, response.reason))
            break

        time.sleep(interval)

    return response


auth_method = {
    PIN_AUTH: pin_auth, OAUTH_AUTH: oauth_auth, DEVICE_AUTH: device_auth
}


def init(*args, **kwargs):
    """Run the auth function specified by *AUTH_METHOD*"""
    return auth_method.get(AUTH_METHOD, PIN_AUTH)(*args, **kwargs)


Airs = namedtuple('Airs', ['day', 'time', 'timezone'])
Alias = namedtuple('Alias', ['title', 'country'])
Genre = namedtuple('Genre', ['name', 'slug'])
Comment = namedtuple('Comment', ['id', 'parent_id', 'created_at', 'comment',
                                 'spoiler', 'review', 'replies', 'user',
                                 'updated_at', 'likes', 'user_rating'])


def _bootstrapped(f):
    """Bootstrap your authentication environment when authentication is needed
    and if a file at `CONFIG_PATH` exists. The process is completed by setting
    the client id header.
    """
    @wraps(f)
    def inner(*args, **kwargs):
        global CLIENT_ID, CLIENT_SECRET, OAUTH_TOKEN, OAUTH_REFRESH
        global APPLICATION_ID
        if (CLIENT_ID is None or CLIENT_SECRET is None) and \
                os.path.exists(CONFIG_PATH):
            # Load in trakt API auth data fron CONFIG_PATH
            with open(CONFIG_PATH) as config_file:
                config_data = json.load(config_file)

            if CLIENT_ID is None:
                CLIENT_ID = config_data.get('CLIENT_ID', None)
            if CLIENT_SECRET is None:
                CLIENT_SECRET = config_data.get('CLIENT_SECRET', None)
            if OAUTH_TOKEN is None:
                OAUTH_TOKEN = config_data.get('OAUTH_TOKEN', None)
            if OAUTH_REFRESH is None:
                OAUTH_REFRESH = config_data.get('OAUTH_REFRESH', None)
            if APPLICATION_ID is None:
                APPLICATION_ID = config_data.get('APPLICATION_ID', None)

            # For backwards compatability with trakt<=2.3.0
            if api_key is not None and OAUTH_TOKEN is None:
                OAUTH_TOKEN = api_key
        return f(*args, **kwargs)
    return inner


class Core(object):
    """This class contains all of the functionality required for interfacing
    with the Trakt.tv API
    """

    def __init__(self):
        """Create a :class:`Core` instance and give it a logger attribute"""
        self.logger = logging.getLogger('trakt.core')

        # Get all of our exceptions except the base exception
        errs = [getattr(errors, att) for att in errors.__all__
                if att != 'TraktException']

        # Map HTTP response codes to exception types
        self.error_map = {err.http_code: err for err in errs}

    @staticmethod
    def _get_first(f, *args, **kwargs):
        """Extract the first value from the provided generator function *f*

        :param f: A generator function to extract data from
        :param args: Non keyword args for the generator function
        :param kwargs: Keyword args for the generator function
        :return: The full url for the resource, a generator, and either a data
            payload or `None`
        """
        generator = f(*args, **kwargs)
        uri = next(generator)
        if not isinstance(uri, (str, tuple)):
            # Allow properties to safetly yield arbitrary data
            return uri
        if isinstance(uri, tuple):
            uri, data = uri
            return BASE_URL + uri, generator, data
        else:
            return BASE_URL + uri, generator, None

    def _handle_request(self, method, url, data=None):
        """Handle actually talking out to the trakt API, logging out debug
        information, raising any relevant `TraktException` Exception types,
        and extracting and returning JSON data

        :param method: The HTTP method we're executing on. Will be one of
            post, put, delete, get
        :param url: The fully qualified url to send our request to
        :param data: Optional data payload to send to the API
        :return: The decoded JSON response from the Trakt API
        :raises TraktException: If any non-200 return code is encountered
        """
        self.logger.debug('%s: %s', method, url)
        HEADERS['trakt-api-key'] = CLIENT_ID
        HEADERS['Authorization'] = 'Bearer {0}'.format(OAUTH_TOKEN)
        self.logger.debug('headers: %s', str(HEADERS))
        self.logger.debug('method, url :: %s, %s', method, url)
        if method == 'get':  # GETs need to pass data as params, not body
            response = requests.request(method, url, params=data,
                                        headers=HEADERS)
        else:
            response = requests.request(method, url, data=json.dumps(data),
                                        headers=HEADERS)
        self.logger.debug('RESPONSE [%s] (%s): %s', method, url, str(response))
        if response.status_code in self.error_map:
            raise self.error_map[response.status_code]()
        elif response.status_code == 204:  # HTTP no content
            return None
        json_data = json.loads(response.content.decode('UTF-8', 'ignore'))
        return json_data

    @_bootstrapped
    def get(self, f):
        """Perform a HTTP GET request using the provided uri yielded from the
        *f* co-routine. The processed JSON results are then sent back to the
        co-routine for post-processing, the results of which are then returned

        :param f: Generator co-routine that yields uri, args, and processed
            results
        :return: The results of the generator co-routine
        """
        @wraps(f)
        def inner(*args, **kwargs):
            resp = self._get_first(f, *args, **kwargs)
            if not isinstance(resp, tuple):
                # Handle cached property responses
                return resp
            url, generator, _ = resp
            json_data = self._handle_request('get', url)
            try:
                return generator.send(json_data)
            except StopIteration:
                return None
        return inner

    @_bootstrapped
    def delete(self, f):
        """Perform an HTTP DELETE request using the provided uri

        :param f: Function that returns a uri to delete to
        """
        @wraps(f)
        def inner(*args, **kwargs):
            generator = f(*args, **kwargs)
            uri = next(generator)
            url = BASE_URL + uri
            self._handle_request('delete', url)
        return inner

    @_bootstrapped
    def post(self, f):
        """Perform an HTTP POST request using the provided uri and optional
        args yielded from the *f* co-routine. The processed JSON results are
        then sent back to the co-routine for post-processing, the results of
        which are then returned

        :param f: Generator co-routine that yields uri, args, and processed
            results
        :return: The results of the generator co-routine
        """
        @wraps(f)
        def inner(*args, **kwargs):
            url, generator, args = self._get_first(f, *args, **kwargs)
            json_data = self._handle_request('post', url, data=args)
            try:
                return generator.send(json_data)
            except StopIteration:
                return None
        return inner

    @_bootstrapped
    def put(self, f):
        """Perform an HTTP PUT request using the provided uri and optional args
        yielded from the *f* co-routine. The processed JSON results are then
        sent back to the co-routine for post-processing, the results of which
        are then returned

        :param f: Generator co-routine that yields uri, args, and processed
            results
        :return: The results of the generator co-routine
        """
        @wraps(f)
        def inner(*args, **kwargs):
            url, generator, args = self._get_first(f, *args, **kwargs)
            json_data = self._handle_request('put', url, data=args)
            try:
                return generator.send(json_data)
            except StopIteration:
                return None
        return inner


# Here we can simplify the code in each module by exporting these instance
# method decorators as if they were simple functions.
CORE = Core()
get = CORE.get
post = CORE.post
delete = CORE.delete
put = CORE.put
