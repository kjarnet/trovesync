# test_model.py
import unittest
from trovesync.models import Photo, Album

class TestPhoto(unittest.TestCase):
  def test_is_testable(self):
    localName = "local name"
    localRelPath = "./something/"
    remoteName = "remote name"
    remoteRelPath = "something/something/"
    filehash = "abcdef"
    fileSize = 200
    ts = Photo(localName, localRelPath, 
      remoteName, remoteRelPath, filehash, fileSize)
    self.assertIsInstance(ts, Photo)


class TestAlbum(unittest.TestCase):
  def test_is_testable(self):
    testLocalpath = "./"
    testRemoteName = "xyz"
    testBackupDir = "bak"
    ts = Album(
      testLocalpath,
      testRemoteName,
      testBackupDir,
      )
    self.assertIsInstance(ts, Album)
  

