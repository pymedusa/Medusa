#!/usr/bin/env python2.7
# -*- coding: utf-8 -*
"""Startup script."""
from __future__ import unicode_literals

import sys
from medusa.__main__ import main

if __name__ == '__main__':
    if sys.version_info.major == 3 and sys.version_info.minor <= 4:
        print(u'Medusa support python version from 2.7.13 > 2.7.x and python 3 from version 3.5.x, Exiting!')
        raise Exception('Incorrect python version. Shutting down!')
    main()
