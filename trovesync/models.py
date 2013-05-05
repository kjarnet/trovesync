# models.py

import logging
import re
import hashlib
from os import path, walk, makedirs
import shutil

from config import APPNAME

__metaclass__ = type # make sure we use new-style classes

class Photo:
  def __init__(self):
    self.logger = logging.getLogger(APPNAME + ".Photo")
    self.localname = ""

class Album:
  """ Class to hold state of album-synchronization """

  " Constants "
  PHOTO_FILEPATTERN = ".*\\.jpg$"

  def __init__(self, localpath, remoteId, remoteName, backupDir, wsClient):
    self.logger = logging.getLogger(APPNAME + ".Album")
    self.localpath = localpath
    self.remoteId = remoteId
    self.remoteName = remoteName
    self.backupDir = backupDir
    self.wsClient = wsClient
    self.localonly = []
    self.remoteonly = []
    self.populatePhotos()

  def hasLocal(self):
    return path.isdir(self.localpath))

  def hasBackupDir(self):
    return path.isdir(getBackupPath())):

  def getBackupPath(self):
    return path.join(self.localpath, self.backupDir)

  def hasRemote(self):
    return not self.remoteId is None


  def syncFromRemote(self, client):
    """ Delete local onlies and download remote onlies. """
    jobs = []

    if not self.hasRemote():
      raise

    if not self.hasLocal():
      jobs.append(CreateDirLocalJob(self.localpath))

    if not self.hasBackupDir():
      jobs.append(CreateDirLocalJob(self.getBackupPath()))

    for f in self.localonly:
      filePath = path.join(self.localpath, f)
      backupPath = path.join(self.localpath, self.backupDir, f)
      self.logger.debug("move local image "+ filePath + " to backup location "+ backupPath)
      jobs.append(DeletePhotoLocalJob(filePath, backupPath))

    for i in self.remoteonly:
      self.logger.debug("download image"+ i["filenameOriginal"]+ " from "+ i["pathDownload"])
      localFullfile = path.join(self.localpath, i["filenameOriginal"])
      downloadPath = i["pathDownload"]
      fixedDownloadPath = re.sub(r"^http:", "https:", downloadPath)
      if downloadPath != fixedDownloadPath:
        self.logger.warning("fixed protocol in download path to " + fixedDownloadPath)
      size = int(i["size"])*1024
      jobs.append(DownloadPhotoJob(fixedDownloadPath, localFullfile, size))
      dbgMsg = "Response from GET %s: %s" % (
            i["pathDownload"], respDownload.getInfoStr())
      self.logger.debug(dbgMsg)

      return jobs

  def syncFromLocal(self, client):
    """ Upload local onlies and delete remote onlies. """
    jobs = []

    if not self.hasLocal():
      raise

    if not self.hasRemote():
      jobs.append(CreateAlbumJob(self))

    for f in self.localonly:
      self.logger.debug("upload to remote "+ f)
      fullfile = path.join(self.localpath, f)
      jobs.append(UploadPhotoJob(fullfile, self))

    for i in self.remoteonly:
      self.logger.debug("tag remote image for deletion " + i["filenameOriginal"])
      jobs.append(DeletePhotoJob(i["id"]))

    return jobs

  def syncCustom(self, client):
    for f in self.localonly:
      self.logger.info("TODO: give user a choice: delete or upload %s." % f)
    for i in self.remoteonly:
      self.logger.info("TODO: give user a choice: delete or download %s.", i["filenameOriginal"])

  def getRemotePhotos(self, client):
    " Get list of remote images "
    remotePhotos = self.wsClient.getAlbumPhotos(self.remoteId)
    numPhotos = len(remotePhotos)
    if numPhotos >= self.wsClient.pageSize:
      self.logger.warn("Capped at %s (maxPhotos option)." %\
            self.wsClient.pageSize)
    self.logger.debug("Remote photos (%d):" % numPhotos)
    debugFormat = "album(s):%s/%s\n  %s"
    imgDebugInfo = [debugFormat %\
      ( i["albums"], i["filenameOriginal"], i["hash"])\
      for i in remotePhotos]
    self.logger.debug(imgDebugInfo.join("\n")
    return remotePhotos

  def populatePhotos(self):
    remotePhotos = getRemotePhotos(self.wsClient)

    """ Loop through local files and compare against remote images,
        collecting local-onlies and marking common ones. """
    self.logger.debug("Local files:")
    rePhotoPattern = re.compile(Album.PHOTO_FILEPATTERN, re.IGNORECASE)
    absLocalPath = path.abspath(self.localpath)
    for currentPath, subFolders, files in walk(absLocalPath):
      if self.backupDir in subFolders:
        subFolders.remove(self.backupDir)
      relativePath = path.relpath(currentPath, absLocalPath)
      photoFiles = filter(rePhotoPattern.search, files)
      for filename in photoFiles:
        fullfile = path.join(currentPath, filename)
        self.logger.debug(fullfile)
        with open(fullfile, "rb") as imgFile:
          sha = hashlib.sha1(imgFile.read()).hexdigest()
          self.logger.debug("  "+ sha)
        for i in remoteImgs:
          if i["hash"] == sha:
            i["inSync"] = True
            break
        else: # for-else executes when for-loop terminates normally (not by break)
          self.localonly.append(path.join(relativePath, filename))

    " Add not-marked remotes to remoteonly. "
    self.remoteonly = [i for i in remoteImgs if "inSync" not in i]

