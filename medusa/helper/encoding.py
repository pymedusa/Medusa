# coding=utf-8

from chardet import detect
from six import text_type

from medusa import app


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
