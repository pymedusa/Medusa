#!/usr/bin/env python2.7
# -*- coding: utf-8 -*
"""Script for backwards compatibility."""

from __future__ import unicode_literals

import sys

from start import Application


if __name__ == '__main__':
    # start application
    application = Application()
    application.start(sys.argv[1:])
