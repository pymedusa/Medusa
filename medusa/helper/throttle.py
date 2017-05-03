# coding=utf-8

from __future__ import unicode_literals

import logging

from functools import wraps
from threading import Lock
from time import time

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class Throttle(object):
    """
    A rate limiting throttle using a token bucket algorithm.

    Can be used as a decorator or an object.
    """

    def __init__(self, calls, seconds=1, burst=False):
        self.lock = Lock()
        self.limit = calls
        self.period = seconds
        self.frequency = self.limit / float(self.period)
        self.interval = 1 / self.frequency
        log.debug(
            '{x} {calls} every {y} {seconds}'.format(
                x=self.limit,
                calls='call' if self.limit == 1 else 'calls',
                y=self.period,
                seconds='second' if self.period == 1 else 'seconds',
            )
        )
        self.tokens = int(burst)

        # Set last time to now if bursts are allowed, otherwise set
        # last time on first usage
        self.last = time() if burst else None

    def __repr__(self):
        return '{cls}(calls={self.limit!r}, seconds={self.period})'.format(
            cls=self.__class__.__name__,
            self=self,
        )

    def consume(self, amount=1):
        """
        Consume tokens when available.

        :param amount: quantity of tokens to consume
        :return: quantity of tokens consumed
        """
        with self.lock:
            now = time()

            if not self.last:
                self.last = now

            # add tokens to the bucket
            interval = now - self.last
            self.tokens += (interval * self.frequency)
            self.last = now

            # never over-fill the bucket
            if self.tokens > self.limit:
                self.tokens = self.limit

            # finally dispatch tokens if available
            if self.tokens >= amount:
                self.tokens -= amount
            else:
                amount = 0

            return amount

    def __call__(self, func, *args, **kwargs):
        """
        Decorate a callable with a Throttle instance.

        :param func: target to throttle
        :param args: to pass to the callable
        :param kwargs: to pass to the callable
        :return: a callable wrapped with a Throttle
        """
        name = '{x.__module__}.{x.__name__}'.format(x=func)
        log.debug(func)
        log.debug(
            'Attaching {throttle} to {func}: {id:X}'.format(
                throttle=self,
                id=id(self),
                func=name,
            )
        )

        @wraps(func)
        def consumer(*args, **kwargs):
            """
            Consume.

            :param args:
            :param kwargs:
            :return:
            """
            logged = False
            first_pass = True
            start = time()
            while not self.consume():
                if not logged:
                    if first_pass:
                        log.debug('Throttling {func}'.format(func=name))
                first_pass = False
            finish = time()
            log.debug('Throttled for {x} seconds'.format(x=finish - start))
            return func(*args, **kwargs)
        return consumer
