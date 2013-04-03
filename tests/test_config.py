# test_config.py
import unittest
from trovesync.config import Config

class TestConfig(unittest.TestCase):
  def test_is_testable(self):
    ts = Config()
    self.assertTrue(True)
  

