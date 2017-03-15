# coding=utf-8
"""Logger factory module. Return preconfigured instances to be used by the application."""

import logging


def get_logger(name):
    """Return a preconfigured logger instance."""
    return logging.getLogger(name)
