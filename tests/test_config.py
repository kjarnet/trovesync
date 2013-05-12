# test_config.py
import unittest
from trovesync.config import Config

class TestConfig(unittest.TestCase):
  def test_is_testable(self):
    host = "testhost.trovebox.com"
    consumerKey = "testconsumerkey"
    consumerSecret = "testconsumersecret"
    token = "testtoken"
    tokenSecret = "testtokensecret"
    Config(host, consumerKey, consumerSecret, token, tokenSecret)
    self.assertTrue(True)
  

