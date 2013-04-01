# test_init.py
import unittest
import trovesync

class TestSyncer(unittest.TestCase):
  def test_is_testable(self):
    ts = trovesync.Syncer()
    self.assertTrue(True)
  

