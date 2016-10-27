# Author: Nic Wolfe <nic@wolfeden.ca>

#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.

from chardet import detect
import medusa as app
from six import text_type


def ss(var):
    """
    Converts string to Unicode, fallback encoding is forced UTF-8

    :param var: String to convert
    :return: Converted string
    """

    var = _to_unicode(var)

    try:
        var = var.encode(app.SYS_ENCODING)
    except Exception:
        try:
            var = var.encode('utf-8')
        except Exception:
            try:
                var = var.encode(app.SYS_ENCODING, 'replace')
            except Exception:
                var = var.encode('utf-8', 'ignore')

    return var


def _fix_list_encoding(var):
    """
    Converts each item in a list to Unicode

    :param var: List or tuple to convert to Unicode
    :return: Unicode converted input
    """

    if isinstance(var, (list, tuple)):
        return filter(lambda x: x is not None, map(_to_unicode, var))

    return var


def _to_unicode(var):
    """
    Converts string to Unicode, using in order: UTF-8, Latin-1, System encoding or finally what chardet wants

    :param var: String to convert
    :return: Converted string as unicode, fallback is System encoding
    """

    if isinstance(var, str):
        try:
            var = text_type(var)
        except Exception:
            try:
                var = text_type(var, 'utf-8')
            except Exception:
                try:
                    var = text_type(var, 'latin-1')
                except Exception:
                    try:
                        var = text_type(var, app.SYS_ENCODING)
                    except Exception:
                        try:
                            # Chardet can be wrong, so try it last
                            var = text_type(var, detect(var).get('encoding'))
                        except Exception:
                            var = text_type(var, app.SYS_ENCODING, 'replace')

    return var
