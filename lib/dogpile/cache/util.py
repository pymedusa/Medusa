from hashlib import sha1
import inspect
from ..util import compat


def function_key_generator(namespace, fn, to_str=compat.string_type):
    """Return a function that generates a string
    key, based on a given function as well as
    arguments to the returned function itself.

    This is used by :meth:`.CacheRegion.cache_on_arguments`
    to generate a cache key from a decorated function.

    It can be replaced using the ``function_key_generator``
    argument passed to :func:`.make_region`.

    """

    if namespace is None:
        namespace = '%s:%s' % (fn.__module__, fn.__name__)
    else:
        namespace = '%s:%s|%s' % (fn.__module__, fn.__name__, namespace)

    args = inspect.getargspec(fn)
    has_self = args[0] and args[0][0] in ('self', 'cls')

    def generate_key(*args, **kw):
        if kw:
            raise ValueError(
                "dogpile.cache's default key creation "
                "function does not accept keyword arguments.")
        if has_self:
            args = args[1:]

        return namespace + "|" + " ".join(map(to_str, args))
    return generate_key


def function_multi_key_generator(namespace, fn, to_str=compat.string_type):

    if namespace is None:
        namespace = '%s:%s' % (fn.__module__, fn.__name__)
    else:
        namespace = '%s:%s|%s' % (fn.__module__, fn.__name__, namespace)

    args = inspect.getargspec(fn)
    has_self = args[0] and args[0][0] in ('self', 'cls')

    def generate_keys(*args, **kw):
        if kw:
            raise ValueError(
                "dogpile.cache's default key creation "
                "function does not accept keyword arguments.")
        if has_self:
            args = args[1:]
        return [namespace + "|" + key for key in map(to_str, args)]
    return generate_keys


def sha1_mangle_key(key):
    """a SHA1 key mangler."""

    return sha1(key).hexdigest()


def length_conditional_mangler(length, mangler):
    """a key mangler that mangles if the length of the key is
    past a certain threshold.

    """
    def mangle(key):
        if len(key) >= length:
            return mangler(key)
        else:
            return key
    return mangle


