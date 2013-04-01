# test_client.py
import unittest
import trovesync

class TestSyncer(unittest.TestCase):
  def test_is_testable(self):
    ts = trovesync.BetterClient()
    self.assertTrue(True)
  

