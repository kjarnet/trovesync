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
    self.prepareLocal()
    self.prepareRemote()

  def prepareLocal(self):
    """ Preparations needing to be made to local folders
        (typically called by __init__) """
    if(not path.isdir(self.localpath)):
      raise Exception
    backupPath = path.join(self.localpath, self.backupDir)
    if(not path.isdir(backupPath)):
      self.logger.debug("Creating backup-folder: " + backupPath)
      makedirs(backupPath)

  def prepareRemote(self):
    """ Preparations needing to be made to remote album
        (typically called by __init__) """
    if self.remoteId is None:
      resp = self.wsClient.createAlbum(self.remoteName)
      self.remoteId = resp.data["id"]

  def syncFromRemote(self, client):
    for f in self.localonly:
      fullfile = path.join(self.localpath, f)
      backupPath = path.join(self.localpath, self.backupDir)
      self.logger.debug("move local image "+ fullfile + " to backup location "+ backupPath)
      shutil.move(fullfile, backupPath)
    for i in self.remoteonly:
      self.logger.debug("download image"+ i["filenameOriginal"]+ " from "+ i["pathDownload"])
      localFullfile = path.join(self.localpath, i["filenameOriginal"])
      downloadPath = i["pathDownload"]
      fixedDownloadPath = re.sub(r"^http:", "https:", downloadPath)
      if downloadPath != fixedDownloadPath:
        self.logger.warning("fixed protocol in download path to " + fixedDownloadPath)
      respDownload = client.download(
          fixedDownloadPath, localFullfile, int(i["size"])*1024)
      dbgMsg = "Response from GET %s: %s" % (
            i["pathDownload"], respDownload.getInfoStr())
      self.logger.debug(dbgMsg)

  def syncFromLocal(self, client):
    for f in self.localonly:
      self.logger.debug("upload to remote "+ f)
      fullfile = path.join(self.localpath, f)
      respRaw = client.uploadPhoto(self.remoteId, fullfile)
      # respUpload = json.loads(respRaw)
      respUpload = respRaw.getInfoStr()
      self.logger.debug("Respons from upload: %s" % respUpload)

    for i in self.remoteonly:
      self.logger.debug("tag remote image for deletion " + i["filenameOriginal"])
      respRaw = client.softDeletePhoto(i["id"])
      # respTagPhoto = json.loads(respRaw)
      respTagPhoto = respRaw.getInfoStr()
      self.logger.debug("Image %s tagged for deletion." % i["id"])

  def syncCustom(self, client):
    for f in self.localonly:
      self.logger.info("TODO: give user a choice: delete or upload %s." % f)
    for i in self.remoteonly:
      self.logger.info("TODO: give user a choice: delete or download %s.", i["filenameOriginal"])

  def populatePhotos(self):
    " Get list of remote images "
    remoteImgs = self.wsClient.getAlbumPhotos(self.remoteId)
    self.logger.debug("Remote images:")
    for i in remoteImgs:
      self.logger.debug("album(s):%s/%s" % (
            str(i["albums"]), i["filenameOriginal"]))
      self.logger.debug("  "+ i["hash"])
    self.logger.debug("Count: "+ str(len(remoteImgs)))
    if len(remoteImgs) >= self.wsClient.pageSize:
      self.logger.debug("Capped at %s (maxPhotos option)." %\
            self.wsClient.pageSize)

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

