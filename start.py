#!/usr/bin/env python
# -*- coding: utf-8 -*
"""Startup script."""
from __future__ import unicode_literals

import sys

from medusa.__main__ import main

if __name__ == '__main__':
    if sys.version_info.major == 3 and sys.version_info.minor < 5:
        print('Medusa supports Python 2 from version 2.7.10 and Python 3 from version 3.5.x, exiting!')
        raise Exception('Incorrect Python version. Shutting down!')
    main()
