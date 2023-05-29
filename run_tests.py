#!/usr/bin/env python
"""Test runner"""
import unittest

if __name__ == '__main__':
    test_suite = unittest.defaultTestLoader.discover('tests/timeclock')
    test_runner = unittest.TextTestRunner()
    test_runner.run(test_suite)
