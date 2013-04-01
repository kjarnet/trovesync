# test_config.py
import unittest
import trovesync

class TestSyncer(unittest.TestCase):
  def test_is_testable(self):
    ts = trovesync.Config()
    self.assertTrue(True)
  

