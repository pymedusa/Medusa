import base64
import sickbeard

from tornado.web import RequestHandler


class BaseRequestHandler(RequestHandler):
    """A base class used for shared RequestHandler methods"""

    def prepare(self):
        web_username = sickbeard.WEB_USERNAME
        web_password = sickbeard.WEB_PASSWORD
        api_key = self.get_argument("api_key", default="")
        api_username = ""
        api_password = ""

        if self.request.headers.get('Authorization'):
            auth_header = self.request.headers.get('Authorization')
            auth_decoded = base64.decodestring(auth_header[6:])
            api_username, api_password = auth_decoded.split(':', 2)
            api_key = api_username

        if (web_username != api_username and web_password != api_password) and (sickbeard.API_KEY != api_key):
            self.api_finish({
                "status": 401,
                "error": "Invalid API key"
            })
        pass

    def api_finish(self, error=None, **data):
        if error is not None:
            return self.finish(error)
        else:
            return self.finish({
                "status": 200,
                "data": data
            })
