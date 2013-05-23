# test_model.py
import unittest
from trovesync.models import Photo, Album

class TestPhoto(unittest.TestCase):
  def test_can_be_initialized(self):
    localName = "local name"
    localRelPath = "./something/"
    remoteName = "remote name"
    remotePath = "something/something/"
    filehash = "abcdef"
    fileSize = 200
    ts = Photo(localName, localRelPath, 
      remoteName, remotePath, filehash, fileSize)
    self.assertIsInstance(ts, Photo)



class TestAlbum(unittest.TestCase):

  def setUp(self):
    self.testLocalpath = "./"
    self.testRemoteName = "xyz"
    self.testBackupDir = "bak"
    self.testAlbum = Album(
      self.testLocalpath,
      self.testRemoteName,
      self.testBackupDir,
      )
    
  def test_can_be_initialized(self):
    self.assertIsInstance(self.testAlbum, Album)
  
  def test_can_add_local_photos_to_empty(self):
    localPhotos = [
      Photo("local name 1", "./localRelPath/", None, None, "filehash 1", 300),
      Photo("local name 2", "./localRelPath/", None, None, "filehash 2", 300),
      Photo("local name 3", "./localRelPath/", None, None, "filehash 3", 300),
      Photo("local name 4", "./localRelPath/", None, None, "filehash 4", 300),
      Photo("local name 5", "./localRelPath/", None, None, "filehash 5", 300)
      ]
    self.testAlbum.setLocalPhotos(localPhotos)
    self.assertItemsEqual(self.testAlbum.getLocalOnly(), localPhotos)

  def test_can_add_remote_photos_to_empty(self):
    remotePhotos = [
      Photo(None, None, "remote name 1", "remotePath/", "filehash 1", 300),
      Photo(None, None, "remote name 2", "remotePath/", "filehash 2", 300),
      Photo(None, None, "remote name 3", "remotePath/", "filehash 3", 300),
      Photo(None, None, "remote name 4", "remotePath/", "filehash 4", 300),
      Photo(None, None, "remote name 5", "remotePath/", "filehash 5", 300)
      ]
    self.testAlbum.setRemotePhotos(remotePhotos)
    self.assertItemsEqual(self.testAlbum.getRemoteOnly(), remotePhotos)

  def test_can_add_local_then_remote_photos_with_overlap(self):
    localPhotos = [
      Photo("local name 1", "./localRelPath/", None, None, "filehash 1", 300),
      Photo("local name 2", "./localRelPath/", None, None, "filehash 2", 300),
      Photo("local name 3", "./localRelPath/", None, None, "filehash 3", 300),
      Photo("local name 4", "./localRelPath/", None, None, "filehash 4", 300),
      Photo("local name 5", "./localRelPath/", None, None, "filehash 5", 300)
      ]
    remotePhotos = [
      Photo(None, None, "remote name 1", "remotePath/", "filehash 6", 300),
      Photo(None, None, "remote name 2", "remotePath/", "filehash 7", 300),
      Photo(None, None, "remote name 3", "remotePath/", "filehash 5", 300),
      Photo(None, None, "remote name 4", "remotePath/", "filehash 2", 300),
      Photo(None, None, "remote name 5", "remotePath/", "filehash 3", 300)
      ]
    localOnly = [
      localPhotos[0],
      localPhotos[3]
    ]
    remoteOnly = [
      remotePhotos[0],
      remotePhotos[1]
    ]
      
    self.testAlbum.setLocalPhotos(localPhotos)
    self.testAlbum.setRemotePhotos(remotePhotos)
    self.assertItemsEqual(self.testAlbum.getLocalOnly(), localOnly)
    self.assertItemsEqual(self.testAlbum.getRemoteOnly(), remoteOnly)

  def test_can_add_remote_then_local_photos_with_overlap(self):
    localPhotos = [
      Photo("local name 1", "./localRelPath/", None, None, "filehash 1", 300),
      Photo("local name 2", "./localRelPath/", None, None, "filehash 2", 300),
      Photo("local name 3", "./localRelPath/", None, None, "filehash 3", 300),
      Photo("local name 4", "./localRelPath/", None, None, "filehash 4", 300),
      Photo("local name 5", "./localRelPath/", None, None, "filehash 5", 300)
      ]
    remotePhotos = [
      Photo(None, None, "remote name 1", "remotePath/", "filehash 6", 300),
      Photo(None, None, "remote name 2", "remotePath/", "filehash 7", 300),
      Photo(None, None, "remote name 3", "remotePath/", "filehash 5", 300),
      Photo(None, None, "remote name 4", "remotePath/", "filehash 2", 300),
      Photo(None, None, "remote name 5", "remotePath/", "filehash 3", 300)
      ]
    localOnly = [
      localPhotos[0],
      localPhotos[3]
    ]
    remoteOnly = [
      remotePhotos[0],
      remotePhotos[1]
    ]
      
    self.testAlbum.setRemotePhotos(remotePhotos)
    self.testAlbum.setLocalPhotos(localPhotos)
    self.assertItemsEqual(self.testAlbum.getLocalOnly(), localOnly)
    self.assertItemsEqual(self.testAlbum.getRemoteOnly(), remoteOnly)

  def test_can_add_local_and_remote_photos_without_overlap(self):
    localPhotos = [
      Photo("local name 1", "./localRelPath/", None, None, "filehash 1", 300),
      Photo("local name 2", "./localRelPath/", None, None, "filehash 2", 300),
      Photo("local name 3", "./localRelPath/", None, None, "filehash 3", 300),
      Photo("local name 4", "./localRelPath/", None, None, "filehash 4", 300),
      Photo("local name 5", "./localRelPath/", None, None, "filehash 5", 300)
      ]
    remotePhotos = [
      Photo(None, None, "remote name 1", "remotePath/", "filehash 6", 300),
      Photo(None, None, "remote name 2", "remotePath/", "filehash 7", 300),
      Photo(None, None, "remote name 3", "remotePath/", "filehash 8", 300),
      Photo(None, None, "remote name 4", "remotePath/", "filehash 9", 300),
      Photo(None, None, "remote name 5", "remotePath/", "filehash 10", 300)
      ]
      
    self.testAlbum.setLocalPhotos(localPhotos)
    self.testAlbum.setRemotePhotos(remotePhotos)
    self.assertItemsEqual(self.testAlbum.getLocalOnly(), localPhotos)
    self.assertItemsEqual(self.testAlbum.getRemoteOnly(), remotePhotos)

    
  def test_can_add_local_and_remote_photos_all_overlapping(self):
    localPhotos = [
      Photo("local name 1", "./localRelPath/", None, None, "filehash 1", 300),
      Photo("local name 2", "./localRelPath/", None, None, "filehash 2", 300),
      Photo("local name 3", "./localRelPath/", None, None, "filehash 3", 300),
      Photo("local name 4", "./localRelPath/", None, None, "filehash 4", 300),
      Photo("local name 5", "./localRelPath/", None, None, "filehash 5", 300)
      ]
    remotePhotos = [
      Photo(None, None, "remote name 1", "remotePath/", "filehash 4", 300),
      Photo(None, None, "remote name 2", "remotePath/", "filehash 1", 300),
      Photo(None, None, "remote name 3", "remotePath/", "filehash 5", 300),
      Photo(None, None, "remote name 4", "remotePath/", "filehash 2", 300),
      Photo(None, None, "remote name 5", "remotePath/", "filehash 3", 300)
      ]
      
    self.testAlbum.setLocalPhotos(localPhotos)
    self.testAlbum.setRemotePhotos(remotePhotos)
    self.assertEqual(self.testAlbum.getLocalOnly(), [])
    self.assertEqual(self.testAlbum.getRemoteOnly(), [])

