import sys
import logging
import json
from os import path
import re

from config import APPNAME
from models import Album
from client import RemoteJob, LocalJob, GetAlbumListRemoteJob, CreateDirLocalJob, DeletePhotoLocalJob, DownloadPhotoRemoteJob, CreateAlbumRemoteJob, UploadPhotoRemoteJob, DeletePhotoRemoteJob, GetPhotoListLocalJob, GetPhotoListRemoteJob

__metaclass__ = type # make sure we use new-style classes

class Settings:
  """ Users credentials and other settings. """

  def __init__( self,
                host,
                consumerKey,
                consumerSecret,
                token,
                tokenSecret,
                albumsPath = ".",
                backupDirName = "bak",
                maxPhotos = 1000,
                albumMappings = []
              ):
    self.logger = logging.getLogger(APPNAME + ".Settings")
    self.credentials = {
      "hostName": host,
      "consumerKey": consumerKey,
      "consumerSecret": consumerSecret,
      "token": token,
      "tokenSecret": tokenSecret,
      "pageSize": maxPhotos
    }
    self.albumsPath = albumsPath
    self.backupDirName = backupDirName
    self.albumMappings = albumMappings

  @classmethod
  def fromFile(cls, filepath):
    logger = logging.getLogger(APPNAME + ".Settings")
    with open(filepath) as credfile:
      cred = json.load(credfile)
    logger.debug("cred.json: %s" % cred)
    newObj = cls( 
                cred["host"],
                cred["consumerKey"],
                cred["consumerSecret"],
                cred["token"],
                cred["tokenSecret"],
                cred["albumsPath"],
                cred["backupDirName"],
                cred["maxPhotos"],
                cred["albums"]
                  )
    return newObj


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
    remoteAlbumNames = [a["name"] for a in remoteAlbums]
    self.logger.info(remoteAlbumNames)
    albums = []
    self.logger.info("Remote albums: " )
    for m in albumMappings:
      remoteId = None
      remoteName = m["remoteName"]
      for a in remoteAlbums:
        if remoteName == a["name"]:
          remoteId = a["id"]
          break
      localpath = path.join(self.albumsPath, m["localName"])
      albums.append(
        Album(localpath, remoteId, remoteName, 
          self.settings.backupDirName)
        )
    return albums


  def sync(self, client):
    """ Choose albums to synchronize """
    remoteAlbums = GetAlbumListRemoteJob().execute(client).data
    albums = self.createAlbums(self.settings.albumMappings, remoteAlbums)

    for album in albums:
      self.prepareAlbum(album, client)

    direction = ""
    for album in albums:
      remoteOnlyNames = [i["filenameOriginal"] for i in album.remoteonly]
      self.logger.info("Syncing album %s against folder %s." % (
        album.remoteName, album.localpath))
      self.logger.info("Local only: %s" % album.localonly)
      self.logger.info("Remote only: %s" % remoteOnlyNames)

      """ Choose sync direction """
      if "a" not in direction:
        syncQuestion = "Do you want to sync " +\
          "[r]emote changes to local folder, " +\
          "[l]ocal changes to remote album or " +\
          "[c]hoose action for each picture [r/l/c]" +\
          "\n  (add \"a\" to apply to all albums, " +\
          "i.e. [ra/la/ca])? "
        direction = self.ask(syncQuestion, ["r", "l", "c", "ra", "la", "ca"])

      """ Synchronize! """
      if "r" in direction:
        self.logger.info("Syncing remote changes to local folder.")
        jobs = self.syncFromRemote(album)
      elif "l" in direction:
        self.logger.info("Syncing local changes to remote album.")
        jobs = self.syncFromLocal(album)
      else:
        self.logger.info("Custom syncing.")
        jobs = self.syncCustom(album)

      doContinue = self.ask("Do you want to execute these jobs %s?" % jobs,
        ["y", "n"])
      if doContinue != "y":
          self.logger.info("User quit.")
          sys.exit(1)

      for j in jobs:
        if isinstance(j, RemoteJob):
          j.execute(client)
        elif isinstance(j, LocalJob):
          j.execute()
        else:
          raise Exception()

  def prepareAlbum(self, album, client):
    if not album.hasLocal():
      CreateDirLocalJob(album.localpath).execute()

    if not album.hasBackupDir():
      CreateDirLocalJob(album.getBackupPath()).execute()

    if not album.hasRemote():
      doCreate = self.ask("Album %s doesn't exist on the remote. Do you want to create it?" % album.remoteName, ["y","n"])
      if "y" not in doCreate:
        self.logger.error("Missing remote album %s." % album.remoteName)
        sys.exit(1)
      CreateAlbumRemoteJob(album).execute(client)

    localPhotos = GetPhotoListLocalJob(album.localPath).execute().data
    remotePhotos = GetPhotoListRemoteJob(album.remoteId).execute(client).data
    album.populatePhotos(localPhotos, remotePhotos)



  def syncFromRemote(self, album):
    """ Delete local onlies and download remote onlies. """
    jobs = []

    for f in album.localonly:
      filePath = path.join(album.localpath, f)
      backupPath = path.join(album.localpath, album.backupDir, f)
      self.logger.debug("move local image "+ filePath + " to backup location "+ backupPath)
      jobs.append(DeletePhotoLocalJob(filePath, backupPath))

    for i in album.remoteonly:
      self.logger.debug("download image"+ i["filenameOriginal"]+ " from "+ i["pathDownload"])
      localFullfile = path.join(album.localpath, i["filenameOriginal"])
      downloadPath = i["pathDownload"]
      fixedDownloadPath = re.sub(r"^http:", "https:", downloadPath)
      if downloadPath != fixedDownloadPath:
        self.logger.warning("fixed protocol in download path to " + fixedDownloadPath)
      size = int(i["size"])*1024
      jobs.append(DownloadPhotoRemoteJob(fixedDownloadPath, localFullfile, size))

      return jobs

  def syncFromLocal(self, album):
    """ Upload local onlies and delete remote onlies. """
    jobs = []

    for f in album.localonly:
      self.logger.debug("upload to remote "+ f)
      fullfile = path.join(album.localpath, f)
      jobs.append(UploadPhotoRemoteJob(fullfile, album))

    for i in album.remoteonly:
      self.logger.debug("tag remote image for deletion " + i["filenameOriginal"])
      jobs.append(DeletePhotoRemoteJob(i["id"]))

    return jobs

  def syncCustom(self, album):
    for f in album.localonly:
      self.logger.info("TODO: give user a choice: delete or upload %s." % f)
    for i in album.remoteonly:
      self.logger.info("TODO: give user a choice: delete or download %s.", i["filenameOriginal"])
    return []

  def ask(self, question, accept):
    """ Ask the user a question and accept an array of answers. 
        Answer is returned. """
    answer = raw_input(question + " " + str(accept))
    while answer not in accept:
      answer = raw_input("  Please choose one of: %s" % accept)
    return answer


