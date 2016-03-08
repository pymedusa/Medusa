# coding=utf-8

import logging
from requests import Session, Request
from requests.auth import AuthBase

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class AuthException(Exception):
    """
    Exception during Authentication
    """


class LoginException(AuthException):
    """
    Exception occurred during Log in
    """


class CookieAuth(AuthBase):
    """
    Authenticate session based on required cookies
    """
    def __init__(self, session=Session(), url=None, payload=None, **kwargs):
        """
        Create a Cookie Authentication

        :param session: containing cookies
        :param url: for acquiring cookies (a.k.a login url)
        :param payload:
        :keyword required: iterable of expected cookies by name
        :keyword minimum: number of expected cookies as an integer
        :param kwargs: remaining arguments to pass to login
        """

        self.session = session
        self.url = url
        self.payload = payload
        self.cookies = dict(
            required=kwargs.pop('required', dict()),
            minimum=kwargs.pop('minimum',  0),
        )
        self.kwargs = kwargs

    def login_request(self):
        """
        Creates a Request for logging in

        :return: a PreparedRequest
        """
        return Request(method='POST', url=self.url, data=self.payload, **self.kwargs).prepare()

    def login(self):
        """
        Log in the current session and validate the cookies

        :return: the login response
        """
        response = self.session.send(self.login_request())
        log.info('Logging in {}'.format(response.request.url))
        log.info('{method} {url} {status}'.format
                 (method=response.request.method, url=response.request.url, status=response.status_code))
        missing = self.missing_cookies
        if missing:
            raise LoginException('Authentication failed. Cookies: {found} Missing: {need}'.format
                                 (found=dict(self.session.cookies), need=missing))
        response.raise_for_status()
        return response

    @property
    def missing_cookies(self):
        """
        Check session for missing cookies

        :returns: the required cookies that are missing
                  or number of missing cookies
                  or True if missing
                  otherwise return None
        """
        if self.session.cookies:
            self.session.cookies.clear_expired_cookies()
            num_cookies = len(self.session.cookies)
            min_cookies = max(len(self.cookies['required']), self.cookies['minimum'])
            missing = {cookie for cookie in self.cookies['required']
                       if cookie not in self.session.cookies}
            if missing or min_cookies > num_cookies:
                return tuple(missing) or min_cookies - num_cookies
        else:
            return self.cookies['required'] or self.cookies['minimum'] or True

    def __call__(self, request):
        """
        Call a request with authentication

        :param request: prepared request requiring authentication
        :returns: request after authentication
        """
        if self.missing_cookies:
            self.login()
        return request
