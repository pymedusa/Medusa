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
        api_finish(2)
    pass

def api_finish(error_code=-1, **data):
    ERRORS = {
        "-1": {
            "status": 500,
            "errors": [{
                "userMessage": "Unknown Error",
                "internalMessage": "Unknown Error",
                "code": -1,
                "more info": "https://docs.pymedusa.com/api/v2/error/-1"
            }]
        },
        "1": {
            "status": 404,
            "errors": [{
                "userMessage": "Show not found",
                "internalMessage": "Show not found",
                "code": 1,
                "more info": "https://docs.pymedusa.com/api/v2/error/1"
            }]
        },
        "2": {
            "status": 401,
            "errors": [{
                "userMessage": "Sorry, your API key is invalid",
                "internalMessage": "Invalid API key",
                "code": 2,
                "more info": "https://docs.pymedusa.com/api/v2/error/2"
            }]
        }
    }

    if error_code != -1:
        return self.finish({
            "status": 200,
            "data": data
        })

    if error_code in ERRORS:
        error = ERRORS[error_code]
        return self.finish({
            "status": error.status,
            "errors": error.errors
        })
