import unittest
import trovesync
from utils import MockObject

__metaclass__ = type # make sure we use new-style classes


class TestSyncer(unittest.TestCase):
  def test_is_testable(self):
    mockSettings = MockObject()
    mockSettings.albumsPath = "/some/absolute/path/"
    trovesync.Syncer(mockSettings)
    self.assertTrue(True)
  

