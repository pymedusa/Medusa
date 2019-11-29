import re

from .utils import validator

pattern = re.compile(
    r'^(?:[a-z0-9]'  # First character of the domain
    r'(?:[a-z0-9-_]{0,61}[a-z0-9])?\.)'  # Sub domain + hostname
    r'+[a-z0-9][a-z0-9-_]{0,61}'  # First 61 characters of the gTLD
    r'[a-z0-9]$'  # Last character of the gTLD
)


@validator
def domain(value):
    """
    Return whether or not given value is a valid domain.

    If the value is valid domain name this function returns ``True``, otherwise
    :class:`~validators.utils.ValidationFailure`.

    Examples::

        >>> domain('example.com')
        True

        >>> domain('example.com/')
        ValidationFailure(func=domain, ...)


    Supports IDN domains as well::

        >>> domain('xn----gtbspbbmkef.xn--p1ai')
        True

    .. versionadded:: 0.9

    .. versionchanged:: 0.10

        Added support for internationalized domain name (IDN) validation.

    :param value: domain string to validate
    """
    return pattern.match(value)
