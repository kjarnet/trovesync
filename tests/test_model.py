# test_model.py
import unittest
from trovesync.models import Photo, Album

class MockClient:
  def __init__(self):
    self.pageSize = 1

  def getAlbumPhotos(self, remoteId):
    return []

class TestPhoto(unittest.TestCase):
  def test_is_testable(self):
    ts = Photo()
    self.assertIsInstance(ts, Photo)


class TestAlbum(unittest.TestCase):
  def test_is_testable(self):
    self.testLocalpath = "./"
    self.testRemoteId = "xyz"
    self.testRemoteName = "test album"
    self.testBackupDir = "bak"
    self.testWsClient = MockClient()
    ts = Album(
      self.testLocalpath,
      self.testRemoteId,
      self.testRemoteName,
      self.testBackupDir,
      self.testWsClient
      )
    self.assertIsInstance(ts, Album)
  

