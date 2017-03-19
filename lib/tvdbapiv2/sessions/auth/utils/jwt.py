# coding=utf-8

"""Utilities for working with JSON Web Tokens (JWT)."""

import logging

import json
from base64 import urlsafe_b64decode
from six import text_type

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def jwt_decode(data):
    """Decode a JSON Web Token (JWT)."""
    # make sure data is binary
    if isinstance(data, text_type):
        log.debug('Encoding the JWT token as UTF-8')
        data = data.encode('utf-8')

    # pad the data to a multiple of 4 bytes
    remainder = len(data) % 4
    if remainder > 0:
        length = 4 - remainder
        log.debug('Padding the JWT with {x} bytes'.format(x=length))
        data += b'=' * length

    # base64 decode the data
    data = urlsafe_b64decode(data)

    # convert the decoded json to a string
    data = data.decode('utf-8')

    # return the json string as a dict
    result = json.loads(data)
    log.info('JWT Successfully decoded')
    return result


def jwt_payload(token):
    """Get the payload from a JSON Web Token."""
    # split the token into its header, payload, and signature
    header, payload, signature = token.split('.')
    log.debug('Payload extracted from JWT.')
    del header  # unused
    del signature  # unused
    return jwt_decode(payload)
