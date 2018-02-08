#!/usr/bin/env python2.7
# -*- coding: utf-8 -*
"""Startup script."""
import logging
logging.basicConfig(
    format='%(created).3f %(levelname).1s %(threadName)s'
           ' %(lineno)5d %(name)-35s'
           '>> %(message)s',
    datefmt='%y.%j %H:%M:%S',
    level=logging.DEBUG,
)

if __name__ == '__main__':
    from medusa.__main__ import main
    main()
