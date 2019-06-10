# coding=utf-8
"""Threaded Request Handler."""
from __future__ import unicode_literals

import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from types import MethodType

from six import PY2

from tornado.concurrent import Future as TornadoFuture
from tornado.gen import coroutine
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler


def update_thread_name(func, thread_prefix):
    """Update the thread name for each spawned thread."""
    @wraps(func)
    def inner():
        try:
            # Examples: Thread_7, ThreadPoolExecutor-N_7
            old_prefix, number = threading.current_thread().name.rsplit('_', 1)
        except ValueError:  # not enough values to unpack (expected 2, got 1)
            pass
        else:
            threading.current_thread().name = '{0}_{1}'.format(thread_prefix, number)
        return func()
    return inner


class ThreadedRequestHandler(RequestHandler):
    """A multi-threaded request handler class."""

    # Set this when subclassing to customize the name prefix for executor threads
    thread_prefix = 'Thread'

    executor = ThreadPoolExecutor()

    def initialize(self):
        """
        Override the request method to use the async dispatcher.

        This function is called for each request.
        """
        name = self.request.method.lower()
        # Wrap the original method with the code needed to run it asynchronously
        method = self.make_async(name)
        # Bind the wrapped method to self.<name>
        setattr(self, name, method)

    def pre_async_check(self):
        """
        Override this method to optionally stop the request before it gets processed.

        If the return value is not `None`, responds to the request with the returned value.
        """
        return

    def make_async(self, method_name):
        """
        Wrap a method with an async wrapper.

        :param method_name: The name of the method to wrap (e.g. `get`, `post`).
        :type method_name: str
        :return: An instance-bound async-wrapped method.
        :rtype: MethodType
        """
        method = getattr(self, method_name)

        @coroutine
        def async_call(self, *args, **kwargs):
            """Call the actual HTTP method asynchronously."""
            content = self.pre_async_check()
            if content is not None:
                self.finish(content)
                return

            # Pre-check passed, run the method in a thread
            if PY2:
                # On Python 2, the original exception stack trace is not passed from the executor.
                # This is a workaround based on https://stackoverflow.com/a/27413025/7597273
                tornado_future = TornadoFuture()

                def wrapper():
                    try:
                        result = method(*args, **kwargs)
                    except:  # noqa: E722 [do not use bare 'except']
                        tornado_future.set_exc_info(sys.exc_info())
                    else:
                        tornado_future.set_result(result)

                wrapper = update_thread_name(wrapper, self.thread_prefix)
                # `executor.submit()` returns a `concurrent.futures.Future`; wait for it to finish, but ignore the result
                yield self.executor.submit(wrapper)
                # When this future is yielded, any stored exceptions are raised (with the correct stack trace).
                content = yield tornado_future
            else:
                # On Python 3+, exceptions contain their original stack trace.
                prepared = partial(method, *args, **kwargs)
                prepared = update_thread_name(prepared, self.thread_prefix)
                content = yield IOLoop.current().run_in_executor(self.executor, prepared)

            self.finish(content)

        # This creates a bound method `self.async_call`,
        # so that it could substitute the original method in the class instance.
        return MethodType(async_call, self)
