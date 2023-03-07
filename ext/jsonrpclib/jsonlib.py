#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Loads the "best" Python library available for the current interpreter and
provides a single interface for all

:authors: Thomas Calmant
:copyright: Copyright 2022, Thomas Calmant
:license: Apache License 2.0
:version: 0.4.3.2

..

    Copyright 2022 Thomas Calmant

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

# Standard library
import json
import sys

# ------------------------------------------------------------------------------

# Module version
__version_info__ = (0, 4, 3, 2)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# Python version flag
PYTHON_2 = sys.version_info[0] < 3

# ------------------------------------------------------------------------------


class JsonHandler(object):
    """
    Parent class for JSON handlers
    """

    def get_methods(self):
        """
        Returns the loads and dumps methods
        """
        if PYTHON_2:
            # We use the Py2 API with an encoding argument
            return json.loads, json.dumps

        def dumps_py3(obj, encoding="utf-8"):
            return json.dumps(obj)

        return json.loads, dumps_py3


class CJsonHandler(JsonHandler):
    """
    Handler based on cjson
    """

    def get_methods(self):
        import cjson

        def dumps_cjson(obj, encoding="utf-8"):
            return cjson.encode(obj)

        return cjson.decode, dumps_cjson


class SimpleJsonHandler(JsonHandler):
    """
    Handler based on simplejson
    """

    def get_methods(self):
        import simplejson

        return simplejson.loads, simplejson.dumps


class UJsonHandler(JsonHandler):
    """
    Handler based on ujson
    """

    def get_methods(self):
        import ujson

        def dumps_ujson(obj, encoding="utf-8"):
            return ujson.dumps(obj)

        return ujson.loads, dumps_ujson


def get_handler():
    # type: () -> JsonHandler
    """
    Returns the best available Json parser
    """
    for handler_class in (UJsonHandler, SimpleJsonHandler, CJsonHandler):
        handler = handler_class()
        try:
            loader, dumper = handler.get_methods()
        except ImportError:
            # Library is missing
            pass
        else:
            try:
                # Check if the library really works
                loader(dumper({"answer": 42}))
                break
            except Exception:
                pass
    else:
        handler = JsonHandler()

    return handler


def get_handler_methods():
    """
    Returns the load and dump methods of the best Json handler
    """
    return get_handler().get_methods()
