# coding=utf-8
import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '../lib')))
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '../ext')))
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

sys._called_from_test = True
