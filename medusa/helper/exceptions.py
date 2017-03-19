# coding=utf-8

from medusa.helper.encoding import ss
from six import text_type


def ex(e):
    """
    :param e: The exception to convert into a unicode string
    :return: A unicode string from the exception text if it exists
    """

    message = u''

    if not e or not e.args:
        return message

    for arg in e.args:
        if arg is not None:
            if isinstance(arg, (str, text_type)):
                fixed_arg = ss(arg)
            else:
                try:
                    fixed_arg = u'error %s' % ss(str(arg))
                except Exception:
                    fixed_arg = None

            if fixed_arg:
                if not message:
                    message = fixed_arg
                else:
                    try:
                        message = u'{} : {}'.format(message, fixed_arg)
                    except UnicodeError:
                        message = u'{} : {}'.format(
                            text_type(message, errors='replace'),
                            text_type(fixed_arg, errors='replace'))

    return message
