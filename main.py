# main.py

import sys
import logging
import re
from openphoto import OpenPhoto
import json
import hashlib
from os import makedirs, listdir, path, walk
import shutil
import urllib2
import urllib
import oauth2 as oauth
from poster import encode, streaminghttp



__metaclass__ = type # make sure we use new-style classes

APPNAME = "trovesync"

class Picture:
  def __init__(self):
    self.logger = logging.getLogger(APPNAME + ".Picture")
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
      dbgMsg = "Response from POST %s: %s" % (
        BetterClient.PHOTO_UPLOAD , respUpload)
      self.logger.debug(dbgMsg)

    for i in self.remoteonly:
      self.logger.debug("tag remote image for deletion " + i["filenameOriginal"])
      respRaw = client.softDeletePhoto(i["id"])
      # respTagPhoto = json.loads(respRaw)
      respTagPhoto = respRaw.getInfoStr()
      dbgMsg = "Response from POST %s: %s" % (
            BetterClient.PHOTO_UPDATE, respTagPhoto)
      self.logger.debug(dbgMsg)
      self.logger.debug("Image %s tagged with %s." % (
            i["id"], BetterClient.DELETE_TAG))

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

class BetterResponse:
  """ A wrapper for the response from webservice calls,
  to unify output and handle errors """

  def __init__(self):
    self.logger = logging.getLogger(APPNAME + ".BetterResponse")
    self.errors = []
    self.info = {"code": None, "message": None}
    self.data = None

  @classmethod
  def fromString(cls, response):
    newObj = cls()
    newObj.info = {"message": response}
    return newObj

  @classmethod
  def fromDict(cls, response):
    newObj = cls()
    try:
      newObj.info = {"code": response["code"], "message": response["message"]}
      newObj.data = response["result"]
    except TypeError, e:
      msg = "ERROR: response is not a dict: " + str(response)
      newObj.logger.error(msg)
      raise
    return newObj

  @classmethod
  def fromMimeMsg(cls, response):
    newObj = cls()
    newObj.info = {"message": str(response)}
    return newObj

  @classmethod
  def fromJson(cls, response):
    dictResponse = json.loads(response)
    return cls.fromDict(dictResponse)

  def getInfoStr(self):
    return "%s: %s" % (str(self.info.get("code", "msg")), self.info["message"])
    
class BetterClient:
  " A proxy to the OpenPhoto client with added methods for download and upload "

  " Trovebox service endpoints: "
  ALBUMS_LIST = "/albums/list.json"
  ALBUM_CREATE = "/album/create.json"
  PHOTOS_LIST = "/photos/list.json"
  PHOTO_UPLOAD = "/photo/upload.json"
  PHOTO_UPDATE = "/photo/%s/update.json"

  " Other constants: "
  DELETE_TAG = "trovesyncDelete"

  def __init__(
              self, 
              hostName, 
              consumerKey,
              consumerSecret,
              token,
              tokenSecret,
              pageSize):
    " Constructor for proxy-client "
    self.logger = logging.getLogger(APPNAME + ".BetterClient")
    self.hostName = hostName
    self.consumerKey = consumerKey
    self.consumerSecret = consumerSecret
    self.token = token
    self.tokenSecret = tokenSecret
    self.opClient = OpenPhoto(hostName, consumerKey, consumerSecret,
                          token, tokenSecret)
    self.pageSize = pageSize
  
  def getAlbums(self):
    rawresp = self.opClient.get(BetterClient.ALBUMS_LIST)
    #albresp = json.loads(rawresp) # newer op-lib returns ready-parsed response
    albresp = BetterResponse.fromDict(rawresp)
    remoteAlbums = albresp.data
    debugMsg = "Response from GET %s: %s" % (
      BetterClient.ALBUMS_LIST, albresp.getInfoStr())
    self.logger.debug(debugMsg)
    return remoteAlbums

  def createAlbum(self, name):
    rawresp = self.opClient.post(BetterClient.ALBUM_CREATE, name=name)
    albresp = BetterResponse.fromDict(rawresp)
    debugMsg = "Response from POST %s: %s" % (
      BetterClient.ALBUMS_LIST, albresp.getInfoStr())
    self.logger.debug(debugMsg)
    if albresp.info["code"] == 201:
      self.logger.debug("Created album '%s' with id %s." % (
            name, albresp.data["id"]))
    else:
      raise Exception
    return albresp


  def getAlbumPhotos(self, albumId):
    rawresp = self.opClient.get(BetterClient.PHOTOS_LIST, {"pageSize": self.pageSize})
    #imgresp = json.loads(rawresp) #newer op-lib returns ready-parsed response
    imgresp = BetterResponse.fromDict(rawresp)
    imgmessage = imgresp.getInfoStr()
    imgresult = imgresp.data
    debugMsg = "Response from GET %s: %s" % (
      BetterClient.PHOTOS_LIST, imgmessage)
    self.logger.debug(debugMsg)
    remoteImgs = [i for i in imgresult if albumId in i["albums"]]
    return remoteImgs

  def softDeletePhoto(self, photoId):
    url = BetterClient.PHOTO_UPDATE % photoId
    respTagPhoto = self.opClient.post(url, tagsAdd = [BetterClient.DELETE_TAG])
    return BetterResponse.fromDict(respTagPhoto)


  def getOauthHeaders(self, url, method):
    " Build headers using oauth2 "
    parameters = None
    consumer = oauth.Consumer(self.consumerKey, self.consumerSecret)
    access_token = oauth.Token(self.token, self.tokenSecret)
    sig_method = oauth.SignatureMethod_HMAC_SHA1()

    oauth_request = oauth.Request.from_consumer_and_token(
            consumer, token=access_token, http_method=method, 
            http_url=url, parameters=parameters
        )
    oauth_request.sign_request(sig_method, consumer, access_token)
    headers = oauth_request.to_header()
    headers['User-Agent'] = 'Trovesync'
    return headers

  def download(self, url, filename, filesize):
    """ Download file (copied from stackoverflow q. 22676) """
    self.logger.debug("saving as" + filename)
    headers = self.getOauthHeaders(url, "GET")
    requestObject = urllib2.Request(url, headers=headers)
    self.logger.debug("made request"+ requestObject.get_full_url())
    u = urllib2.urlopen(requestObject)
    meta = u.info()
    self.logger.info("Downloading: %s Bytes: %s" % (filename, filesize))
    filesizeDown = 0
    blocksize = 8192
    with open(filename, 'wb') as f:
      while True:
        buffer = u.read(blocksize)
        if not buffer:
          break
        filesizeDown += len(buffer)
        f.write(buffer)
        status = r"%10d  [%3.2f%%]" % (filesizeDown, filesizeDown * 100. / filesize)
        status = status + chr(8)*(len(status)+1)
        self.logger.info(status)
    return BetterResponse.fromMimeMsg(meta)

  def uploadPhoto(self, albumId, fileName):
    url = "http://" + self.hostName + BetterClient.PHOTO_UPLOAD
    return self.upload(url, fileName, {"albums": albumId})
    
  def upload(self, url, fileName, parameters):
    self.logger.debug("Uploading " + fileName + " to " + url)
    encparams = urllib.urlencode(parameters)
    urlWithParams = url + "?" + encparams
    streaminghttp.register_openers()
    with open(fileName, "rb") as localfile:
      datagen, headers = encode.multipart_encode({"photo": localfile})
      headers.update(self.getOauthHeaders(urlWithParams, "POST"))
      request = urllib2.urlopen(urllib2.Request(urlWithParams, datagen, headers))
    response = request.read()
    return BetterResponse.fromJson(response)


class Syncer:
  """ The main class for the application that does all user interaction. """

  def __init__(self):
    " Constructor for Syncer "
    self.logger = logging.getLogger(APPNAME)
    self.initLogging(self.logger)
    self.loadSettings()
    self.initClient(self.cred)
    self.albumsPath = self.cred["albumsPath"]
    

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

  def loadSettings(self):
    " Credentials "
    with open("./cred.json") as credfile:
      self.cred = json.load(credfile)
    self.logger.debug("cred.json: %s" % self.cred)

  def initClient(self, cred):
    """ Initialize a webservice client """
    self.troveboxClient = BetterClient(
      cred["host"],
      cred["consumerKey"],
      cred["consumerSecret"],
      cred["token"],
      cred["tokenSecret"],
      cred["maxPhotos"]
      )

  def sync(self):
    """ Choose albums to synchronize """
    remoteAlbums = self.troveboxClient.getAlbums()
    remoteAlbumNames = [a["name"] for a in remoteAlbums]
    self.logger.info(remoteAlbumNames)
    albumMappings = self.cred["albums"]
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
          doCreate = ask("Do you want to create it?", ["y","n", "ya"])
        if "y" not in doCreate:
          self.logger.error("Missing remote album '%s' - can not continue!" % remoteName)
          sys.exit(1)
      localpath = path.join(self.albumsPath, m["localName"])
      albums.append(
        Album(localpath, remoteId, remoteName, 
          self.cred["backupDirName"], self.troveboxClient), 
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

if __name__ == "__main__": Syncer().sync()

  

