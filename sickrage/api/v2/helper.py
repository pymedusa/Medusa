import sickbeard
import base64

def api_auth(self):
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
        # @TODO: Move the errors into sickrage/api/v2/errors.py
        self.finish({
            "status": 403,
            "errors": [{
                "userMessage": "Sorry, your API key is invalid",
                "internalMessage": "Invalid API key",
                "code": 34, # @TODO: This should be a error code that we can use for the "more info" section
                "more info": "https://pymedusa.github.io/sickrage/api/v2/errors/12345" # @TODO: This should goto a documention page
            }]
        })
    pass

def api_errors(self):
    ERRORS = {
        1: ""
    }
