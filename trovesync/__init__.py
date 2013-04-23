# __init__.py

import sys
import logging
import json
from os import path

from config import APPNAME
from client import BetterClient
from models import Album

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
    self.initClient()
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


  def initClient(self):
    """ Initialize a webservice client """
    self.troveboxClient = BetterClient(**self.settings.credentials)

  def sync(self):
    """ Choose albums to synchronize """
    remoteAlbums = self.troveboxClient.getAlbums()
    remoteAlbumNames = [a["name"] for a in remoteAlbums]
    self.logger.info(remoteAlbumNames)
    albumMappings = self.settings.albumMappings
    albums = []
    self.logger.info("Remote albums: " )
    doCreate = ""
    for m in albumMappings:
      remoteId = None
      remoteName = m["remoteName"]
      for a in remoteAlbums:
        if remoteName == a["name"]:
          remoteId = a["id"]
          break
      else: # looped through remote albums without finding m.
        self.logger.info("Album '%s' doesn't exist on the remote." % remoteName)
        if "a" not in doCreate:
          doCreate = self.ask("Do you want to create it?", ["y","n", "ya"])
        if "y" not in doCreate:
          self.logger.error("Missing remote album '%s' - can not continue!" % remoteName)
          sys.exit(1)
      localpath = path.join(self.albumsPath, m["localName"])
      albums.append(
        Album(localpath, remoteId, remoteName, 
          self.settings.backupDirName, self.troveboxClient), 
        )

    direction = ""
    for album in albums:
      remoteOnlyNames = [i["filenameOriginal"] for i in album.remoteonly]
      self.logger.info("Syncing album %s against folder %s." % (
        album.remoteName, album.localpath))
      self.logger.info("Local only: %s" % album.localonly)
      self.logger.info("Remote only: %s" % remoteOnlyNames)

      if "a" not in direction:
        """ Choose sync direction """
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
        album.syncFromRemote(self.troveboxClient)
      elif "l" in direction:
        self.logger.info("Syncing local changes to remote album.")
        album.syncFromLocal(self.troveboxClient)
      else:
        self.logger.info("Custom syncing.")
        album.syncCustom(self.troveboxClient)

  def ask(self, question, accept):
    """ Ask the user a question and accept an array of answers. 
        Answer is returned. """
    answer = raw_input(question + " " + str(accept))
    while answer not in accept:
      answer = raw_input("  Please choose one of: %s" % accept)
    return answer


