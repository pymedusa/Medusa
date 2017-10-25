from collections import Iterable
from six import text_type


def generate(it):
    """
    Generate items from an iterable.

    :param it: an iterable
    :return: items from an iterable
        If the iterable is a string yield the entire string
        If the item is not iterable, yield the item
    """
    if isinstance(it, Iterable) and not isinstance(it, text_type):
        for item in it:
            yield item
    else:
        yield it
