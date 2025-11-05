# Copyright (C) 2001-2006 Python Software Foundation
# Author: Barry Warsaw
# Contact: email-sig@python.org

"""Class representing image/* type MIME documents."""
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

__all__ = ['MIMEImage']

from future.backports.email import encoders
from future.backports.email.mime.nonmultipart import MIMENonMultipart

def _guess_image_type(data):
    """Return the image type (png, gif, jpeg) based on the first bytes of data."""
    if not data or len(data) < 10:
        return None
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    # GIF: 'GIF87a' or 'GIF89a'
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
    # JPEG: starts with FF D8
    if data[:2] == b'\xff\xd8':
        return 'jpeg'
    # Could add more formats (BMP, WebP, TIFF) if needed
    return None

class MIMEImage(MIMENonMultipart):
    """Class for generating image/* type MIME documents."""

    def __init__(self, _imagedata, _subtype=None,
                 _encoder=encoders.encode_base64, **_params):
        """Create an image/* type MIME document.

        _imagedata is a string containing the raw image data.  If this data
        can be decoded by the standard Python `imghdr' module, then the
        subtype will be automatically included in the Content-Type header.
        Otherwise, you can specify the specific image subtype via the _subtype
        parameter.

        _encoder is a function which will perform the actual encoding for
        transport of the image data.  It takes one argument, which is this
        Image instance.  It should use get_payload() and set_payload() to
        change the payload to the encoded form.  It should also add any
        Content-Transfer-Encoding or other headers to the message as
        necessary.  The default encoding is Base64.

        Any additional keyword arguments are passed to the base class
        constructor, which turns them into parameters on the Content-Type
        header.
        """
        if _subtype is None:
            _subtype = _guess_image_type(_imagedata)
        if _subtype is None:
            raise TypeError('Could not guess image MIME subtype')
        MIMENonMultipart.__init__(self, 'image', _subtype, **_params)
        self.set_payload(_imagedata)
        _encoder(self)
