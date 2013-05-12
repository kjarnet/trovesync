import logging
from os import path

from config import APPNAME

__metaclass__ = type # make sure we use new-style classes

class Album:
  """ Class to hold state of album-synchronization """


  def __init__(self, localPath, remoteName, backupDir):
    self.logger = logging.getLogger(APPNAME + ".Album")
    self.localPath = localPath
    self.remoteName = remoteName
    self.backupDir = backupDir
    self.remoteId = None
    self._photos = []

  def hasLocal(self):
    return path.isdir(self.localPath)

  def hasBackupDir(self):
    return path.isdir(self.getBackupPath())

  def getBackupPath(self):
    return path.join(self.localPath, self.backupDir)

  def hasRemote(self):
    return not self.remoteId is None

  def setLocalPhotos(self, photos):
    newPhotos = []
    for newp in photos:
      for exp in self._photos:
        if newp.filehash == exp.filehash:
          exp.localName = newp.localName
          exp.localRelPath = newp.localRelPath
          break
      else: # Not found in existing photos (may be localonly)
        newPhotos.append(newp)
    self._photos += newPhotos
    

  def setRemotePhotos(self, photos):
    newPhotos = []
    for newp in photos:
      for exp in self._photos:
        if newp.filehash == exp.filehash:
          exp.remoteName = newp.remoteName
          exp.remotePath = newp.remotePath
          break
      else: # Not found in existing photos (may be remoteonly)
        newPhotos.append(newp)
    self._photos += newPhotos

  def getRemoteOnly(self):
    return [p for p in self._photos if p.localName is None]

  def getLocalOnly(self):
    return [p for p in self._photos if p.remoteName is None]

class Photo:
  def __init__(self, localName, localRelPath,
      remoteName, remotePath, filehash, fileSize):
    self.logger = logging.getLogger(APPNAME + ".Photo")
    self.localName = localName
    self.localRelPath = localRelPath
    self.remoteName = remoteName
    self.remotePath = remotePath
    self.filehash = filehash
    self.fileSize = fileSize

