# -*- coding: utf-8 -*-
"""
Classic deprecation warning
===========================

Classic ``@deprecated`` decorator to deprecate old python classes, functions or methods.

"""
import functools
import inspect
import warnings

import wrapt

string_types = (type(b''), type(u''))


class ClassicAdapter(wrapt.AdapterFactory):
    """
    Classic adapter -- *for advanced usage only*

    This adapter is used to get the deprecation message according to the wrapped object type:
    class, function, standard method, static method, or class method.

    This is the base class of the :class:`~deprecated.sphinx.SphinxAdapter` class
    which is used to update the wrapped object docstring.

    You can also inherit this class to change the deprecation message.

    In the following example, we change the message into "The ... is deprecated.":

    .. code-block:: python

       import inspect

       from deprecated.classic import ClassicAdapter
       from deprecated.classic import deprecated


       class MyClassicAdapter(ClassicAdapter):
           def get_deprecated_msg(self, wrapped, instance):
               if instance is None:
                   if inspect.isclass(wrapped):
                       fmt = "The class {name} is deprecated."
                   else:
                       fmt = "The function {name} is deprecated."
               else:
                   if inspect.isclass(instance):
                       fmt = "The class method {name} is deprecated."
                   else:
                       fmt = "The method {name} is deprecated."
               if self.reason:
                   fmt += " ({reason})"
               if self.version:
                   fmt += " -- Deprecated since version {version}."
               return fmt.format(name=wrapped.__name__,
                                 reason=self.reason or "",
                                 version=self.version or "")

    Then, you can use your ``MyClassicAdapter`` class like this in your source code:

    .. code-block:: python

       @deprecated(reason="use another function", adapter_cls=MyClassicAdapter)
       def some_old_function(x, y):
           return x + y
    """

    def __init__(self, reason="", version="", action='always', category=DeprecationWarning):
        self.reason = reason or ""
        self.version = version or ""
        self.action = action
        self.category = category
        super(ClassicAdapter, self).__init__()

    def get_deprecated_msg(self, wrapped, instance):
        if instance is None:
            if inspect.isclass(wrapped):
                fmt = "Call to deprecated class {name}."
            else:
                fmt = "Call to deprecated function (or staticmethod) {name}."
        else:
            if inspect.isclass(instance):
                fmt = "Call to deprecated class method {name}."
            else:
                fmt = "Call to deprecated method {name}."
        if self.reason:
            fmt += " ({reason})"
        if self.version:
            fmt += " -- Deprecated since version {version}."
        return fmt.format(name=wrapped.__name__,
                          reason=self.reason or "",
                          version=self.version or "")

    def __call__(self, wrapped):
        if inspect.isclass(wrapped):
            old_new1 = wrapped.__new__

            def wrapped_cls(unused, *args, **kwargs):
                msg = self.get_deprecated_msg(wrapped, None)
                with warnings.catch_warnings():
                    warnings.simplefilter(self.action, self.category)
                    warnings.warn(msg, category=self.category, stacklevel=2)
                return old_new1(*args, **kwargs)

            wrapped.__new__ = classmethod(wrapped_cls)

        return wrapped


def deprecated(*args, **kwargs):
    """
    This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.

    **Classic usage:**

    To use this, decorate your deprecated function with **@deprecated** decorator:

    .. code-block:: python

       from deprecated import deprecated


       @deprecated
       def some_old_function(x, y):
           return x + y

    You can also decorate a class or a method:

    .. code-block:: python

       from deprecated import deprecated


       class SomeClass(object):
           @deprecated
           def some_old_method(self, x, y):
               return x + y


       @deprecated
       class SomeOldClass(object):
           pass

    You can give a "reason" message to help the developer to choose another function/class,
    and a "version" number to specify the starting version number of the deprecation.

    .. code-block:: python

       from deprecated import deprecated


       @deprecated(reason="use another function", version='1.2.0')
       def some_old_function(x, y):
           return x + y

    """
    if args and isinstance(args[0], string_types):
        kwargs['reason'] = args[0]
        args = args[1:]

    if args and not callable(args[0]):
        raise TypeError(repr(type(args[0])))

    if args:
        action = kwargs.get('action', 'always')
        category = kwargs.get('category', DeprecationWarning)
        adapter_cls = kwargs.pop('adapter_cls', ClassicAdapter)
        adapter = adapter_cls(**kwargs)

        wrapped = args[0]
        if inspect.isclass(wrapped):
            wrapped = adapter(wrapped)
            return wrapped

        elif inspect.isfunction(wrapped):

            @wrapt.decorator(adapter=adapter)
            def wrapper_function(wrapped_, instance_, args_, kwargs_):
                msg = adapter.get_deprecated_msg(wrapped_, instance_)
                with warnings.catch_warnings():
                    warnings.simplefilter(action, category)
                    warnings.warn(msg, category=category, stacklevel=2)
                return wrapped_(*args_, **kwargs_)

            return wrapper_function(wrapped)

        else:
            raise TypeError(repr(type(wrapped)))

    return functools.partial(deprecated, **kwargs)
