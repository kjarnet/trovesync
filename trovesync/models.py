import logging
import hashlib
from os import path

from config import APPNAME

__metaclass__ = type # make sure we use new-style classes

class Album:
  """ Class to hold state of album-synchronization """


  def __init__(self, localpath, remoteId, remoteName, backupDir):
    self.logger = logging.getLogger(APPNAME + ".Album")
    self.localpath = localpath
    self.remoteId = remoteId
    self.remoteName = remoteName
    self.backupDir = backupDir
    self.localonly = []
    self.remoteonly = []

  def hasLocal(self):
    return path.isdir(self.localpath)

  def hasBackupDir(self):
    return path.isdir(self.getBackupPath())

  def getBackupPath(self):
    return path.join(self.localpath, self.backupDir)

  def hasRemote(self):
    return not self.remoteId is None


  def populatePhotos(self, localPhotos, remotePhotos):

    """ Loop through local files and compare against remote images,
        collecting local-onlies and marking common ones. """
    self.logger.debug("Local files:")

    for relPath, filename, sha in localPhotos:
      for i in remotePhotos:
        if i["hash"] == sha:
          i["inSync"] = True
          break
      else: # for-else executes when for-loop terminates normally (not by break)
        self.localonly.append(Photo(filename, relPath, None, None))

    " Add not-marked remotes to remoteonly. "
    self.remoteonly = [Photo(None, None, i["name"], i["hash"]) for i in remotePhotos if "inSync" not in i]

class Photo:
  def __init__(self, localName, localRelPath, remoteName, filehash):
    self.logger = logging.getLogger(APPNAME + ".Photo")
    self.localName = localName
    self.localRelPath = localRelPath
    self.remoteName = remoteName
    self.filehash = filehash

