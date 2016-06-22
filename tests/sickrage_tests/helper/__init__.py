# coding=utf-8
"""
Tests for SickRage helpers
"""

from __future__ import print_function

import unittest

from common_tests import CommonTests
from quality_tests import QualityTests

if __name__ == '__main__':
    print('=====> Running all test in "sickrage_tests.helper" <=====')

    TEST_CLASSES = [
        CommonTests,
        QualityTests,
    ]

    for test_class in TEST_CLASSES:
        SUITE = unittest.TestLoader().loadTestsFromTestCase(test_class)
        unittest.TextTestRunner(verbosity=2).run(SUITE)
