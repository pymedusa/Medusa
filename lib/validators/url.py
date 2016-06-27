import re

from .utils import validator

ip_middle_octet = u"(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5]))"
ip_last_octet = u"(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))"

regex = re.compile(
    u"^"
    # protocol identifier
    u"(?:(?:https?|ftp)://)"
    # user:pass authentication
    u"(?:\S+(?::\S*)?@)?"
    u"(?:"
    u"(?P<private_ip>"
    # IP address exclusion
    # private & local networks
    u"(?:(?:10|127)" + ip_middle_octet + u"{2}" + ip_last_octet + u")|"
    u"(?:(?:169\.254|192\.168)" + ip_middle_octet + ip_last_octet + u")|"
    u"(?:172\.(?:1[6-9]|2\d|3[0-1])" + ip_middle_octet + ip_last_octet + u"))"
    u"|"
    # IP address dotted notation octets
    # excludes loopback network 0.0.0.0
    # excludes reserved space >= 224.0.0.0
    # excludes network & broadcast addresses
    # (first & last IP address of each class)
    u"(?P<public_ip>"
    u"(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])"
    u"" + ip_middle_octet + u"{2}"
    u"" + ip_last_octet + u")"
    u"|"
    # host name
    u"(?:(?:[a-z\u00a1-\uffff0-9]-?)*[a-z\u00a1-\uffff0-9]+)"
    # domain name
    u"(?:\.(?:[a-z\u00a1-\uffff0-9]-?)*[a-z\u00a1-\uffff0-9]+)*"
    # TLD identifier
    u"(?:\.(?:[a-z\u00a1-\uffff]{2,}))"
    u")"
    # port number
    u"(?::\d{2,5})?"
    # resource path
    u"(?:/\S*)?"
    u"$", re.UNICODE
)

pattern = re.compile(regex)


@validator
def url(value, public=False):
    """
    Return whether or not given value is a valid URL.

    If the value is valid URL this function returns ``True``, otherwise
    :class:`~validators.utils.ValidationFailure`.

    This validator is based on the wonderful `URL validator of dperini`_.

    .. _URL validator of dperini:
        https://gist.github.com/dperini/729294

    Examples::

        >>> url('http://foobar.dk')
        True

        >>> url('http://10.0.0.1')
        True

        >>> url('http://foobar.d')
        ValidationFailure(func=url, ...)

        >>> url('http://10.0.0.1', public=True)
        ValidationFailure(func=url, ...)

    .. versionadded:: 0.2

    .. versionchanged:: 0.10.2

        Added support for various exotic URLs and fixed various false
        positives.

    .. versionchanged:: 0.10.3

        Added ``public`` parameter.

    :param value: URL address string to validate
    :param public: (default=False) Set True to only allow a public IP address
    """
    if not public:
        return pattern.match(value)

    match_result = pattern.match(value)

    if match_result.groupdict()['private_ip']:
        return False

    return match_result
