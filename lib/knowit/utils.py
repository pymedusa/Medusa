# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import OrderedDict
from datetime import timedelta

import babelfish
from six import string_types
import yaml


def todict(obj, classkey=None):
    """Transform an object to dict."""
    if isinstance(obj, string_types):
        return obj
    elif isinstance(obj, dict):
        data = {}
        for (k, v) in obj.items():
            data[k] = todict(v, classkey)
        return data
    elif hasattr(obj, '_ast'):
        return todict(obj._ast())
    elif hasattr(obj, '__iter__'):
        return [todict(v, classkey) for v in obj]
    elif hasattr(obj, '__dict__'):
        data = OrderedDict([(key, todict(value, classkey))
                            for key, value in obj.__dict__.items()
                            if not callable(value) and not key.startswith('_')])
        if classkey is not None and hasattr(obj, '__class__'):
            data[classkey] = obj.__class__.__name__
        return data
    return obj


class CustomDumper(yaml.SafeDumper):
    """Custom YAML Dumper."""

    pass


class CustomLoader(yaml.SafeLoader):
    """Custom YAML Loader."""

    pass


def default_representer(dumper, data):
    """Default representer."""
    return dumper.represent_str(str(data))


def ordered_dict_representer(dumper, data):
    """Representer for OrderedDict."""
    return dumper.represent_mapping('tag:yaml.org,2002:map', data.items())


CustomDumper.add_representer(OrderedDict, ordered_dict_representer)
CustomDumper.add_representer(babelfish.Language, default_representer)
CustomDumper.add_representer(timedelta, default_representer)
