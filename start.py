#!/usr/bin/env python2.7
# -*- coding: utf-8 -*
"""Startup script."""
import logging
logging.basicConfig(level=logging.DEBUG)

from medusa.__main__ import main

if __name__ == '__main__':
    main()
