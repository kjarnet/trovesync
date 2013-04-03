# test_client.py
import unittest
from trovesync.client import BetterClient, BetterResponse

class TestBetterClient(unittest.TestCase):
  def test_is_testable(self):
    self.testHostName = "x"
    self.testConsumerKey = "x"
    self.testConsumerSecret = "x"
    self.testToken = "x"
    self.testTokenSecret = "x"
    self.testPageSize = 5
    ts = BetterClient(
              self.testHostName, 
              self.testConsumerKey,
              self.testConsumerSecret,
              self.testToken,
              self.testTokenSecret,
              self.testPageSize)
    self.assertTrue(True)
  
class TestBetterResponse(unittest.TestCase):
  def test_is_testable(self):
    ts = BetterResponse()
    self.assertTrue(True)

