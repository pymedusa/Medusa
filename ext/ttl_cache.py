#!/usr/bin/env python3

import functools
import random


def cache(ttl, typed=False, ignore_error=False, random_base=0):
    """Time To Live Cache

    Decorator to wrap a function with a memoizing callable that has TTL result
    """

    try:
        from time import monotonic
    except ImportError:
        from time import time as monotonic

    def wrap(fn):
        from pickle import dumps

        def _hash(x):
            if isinstance(x, dict):
                x = tuple(sorted(x.items()))
            try:
                hash(x)
            except TypeError:
                x = (dumps(x), )
            return x

        _tmp = {}

        @functools.wraps(fn)
        def fn_wrapped(*args, **kwargs):
            result = _tmp  # fake identifier
            now = monotonic()
            key = _hash(args) + _hash(kwargs)
            if typed:
                key += tuple(map(type, args))
            if key in _tmp:
                cd, result = _tmp[key]
                if cd > now:
                    return result

            try:
                result = fn(*args, **kwargs)
            except Exception:
                if ignore_error and result is not _tmp:
                    return result
                raise  # no previous result in _tmp

            cd = now + ttl + random.random() * random_base
            _tmp[key] = cd, result
            return result

        return fn_wrapped

    if callable(ttl):
        fn, ttl = ttl, 60.0
        return wrap(fn)

    ttl = float(ttl)

    return wrap


if __name__ == '__main__':
    from time import sleep
    @cache
    def test_1():
        pass
    @cache(5)
    def test_2():
        pass
    @cache(10, ignore_error=True)
    def test_3():
        pass
    @cache(1, random_base=1.0)
    def test(*args, **kwargs):
        print(test, args, kwargs)
    test(9, z=[99])
    sleep(0)
    test(9, z=[99])  # cached
    sleep(1.5)
    test(9, z=[99])
else:
    from sys import modules
    self = modules[__name__]
    modules[__name__] = self.cache
