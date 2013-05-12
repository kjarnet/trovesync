import logging
from os import path
import re

from config import APPNAME
from models import Album
from client import CreateDirLocalJob, DeletePhotoLocalJob, DownloadPhotoRemoteJob, CreateAlbumRemoteJob, UploadPhotoRemoteJob, DeletePhotoRemoteJob, GetPhotoListLocalJob, GetPhotoListRemoteJob

__metaclass__ = type # make sure we use new-style classes

class Syncer:
  """ The main class for the application that does all user interaction. """

  def __init__(self, settings):
    " Constructor for Syncer "
    self.logger = logging.getLogger(APPNAME + ".Syncer")
    self.initLogging(self.logger)
    self.settings = settings
    self.albumsPath = self.settings.albumsPath
    

  def initLogging(self, logger):
    """ Setting up logging and reading credentials """
    
    " Logging (from http://docs.python.org/2/howto/logging-cookbook.html) "
    # create logger 'trovesync'
    logger = logging.getLogger(APPNAME)
    logger.setLevel(logging.DEBUG)
    # create file handler which logs from debug messages
    fh = logging.FileHandler(APPNAME + ".log")
    fh.setLevel(logging.INFO)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter and add it to the handlers
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # fh.setFormatter(formatter)
    # ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.info("Initialized logger")


  def createAlbums(self, albumMappings, remoteAlbums):
    """ Creates Albums from the data in albumMappings
      and finds the remote ids from a list of remoteAlbums
      based on the remote album name. """
    self.logger.info("Remote albums: " )
    remoteAlbumNames = [a["name"] for a in remoteAlbums]
    self.logger.info(remoteAlbumNames)
    albums = []
    for m in albumMappings:
      remoteName = m["remoteName"]
      localPath = path.join(self.albumsPath, m["localName"])
      album = Album(localPath, remoteName, 
          self.settings.backupDirName)
      for a in remoteAlbums:
        if remoteName == a["name"]:
          album.remoteId = a["id"]
          break
      albums.append(album)
    return albums



  def prepareAlbum(self, album):
    jobs = []
    if album.hasRemote():
      jobs.append(GetPhotoListRemoteJob(album))
    else:
      jobs.append(CreateAlbumRemoteJob(album))

    if album.hasLocal():
      jobs.append(GetPhotoListLocalJob(album, self.albumsPath))
    else:
      absLocalPath = path.join(self.albumsPath, album.localPath)
      jobs.append(CreateDirLocalJob(absLocalPath))

    if not album.hasBackupDir():
      absBackupPath = path.join(self.albumsPath, album.getBackupPath())
      jobs.append(CreateDirLocalJob(absBackupPath))

    return jobs


  def syncFromRemote(self, album):
    """ Delete local onlies and download remote onlies. """
    self.logger.info("Syncing remote changes to local folder.")
    jobs = []

    for f in album.getLocalOnly():
      filePath = path.join(self.albumsPath, album.localPath, f.localRelPath, f.localName)
      backupPath = path.join(self.albumsPath, album.getBackupPath(), f.localRelPath, f.localName)
      self.logger.debug("move local image "+ filePath + " to backup location "+ backupPath)
      jobs.append(DeletePhotoLocalJob(filePath, backupPath))

    for p in album.getRemoteOnly():
      self.logger.debug("download image"+ p.remoteName + " from "+ p.remotePath)
      localFullfile = path.join(self.albumsPath, album.localPath, p.remoteName)
      downloadPath = p.remotePath
      #fixedDownloadPath = re.sub(r"^http:", "https:", downloadPath)
      fixedDownloadPath = downloadPath
      if downloadPath != fixedDownloadPath:
        self.logger.warning("fixed protocol in download path to " + fixedDownloadPath)
      size = int(p.fileSize)*1024
      jobs.append(DownloadPhotoRemoteJob(fixedDownloadPath, localFullfile, size))

    return jobs

  def syncFromLocal(self, album):
    """ Upload local onlies and delete remote onlies. """
    self.logger.info("Syncing local changes to remote album.")
    jobs = []

    for f in album.getLocalOnly():
      self.logger.debug("upload to remote %s" % f)
      fullfile = path.join(self.albumsPath, album.localPath, f.localName)
      jobs.append(UploadPhotoRemoteJob(fullfile, album))

    for i in album.getRemoteOnly():
      self.logger.debug("tag remote image for deletion %s" % i["filenameOriginal"])
      jobs.append(DeletePhotoRemoteJob(i["id"]))

    return jobs

  def syncCustom(self, album):
    self.logger.info("Custom syncing.")
    for f in album.getLocalOnly():
      self.logger.info("TODO: give user a choice: delete or upload %s." % f)
    for i in album.getRemoteOnly():
      self.logger.info("TODO: give user a choice: delete or download %s.", i["filenameOriginal"])
    return []
