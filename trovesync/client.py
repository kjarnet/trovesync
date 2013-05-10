import logging
import json
import urllib2
import urllib
import oauth2 as oauth
from poster import encode, streaminghttp
import shutil
from os import makedirs, path, walk
import re
import hashlib

from config import APPNAME
from models import Photo

__metaclass__ = type # make sure we use new-style classes



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
    # TODO: Handle error responses
    return newObj

  @classmethod
  def fromDict(cls, response):
    newObj = cls()
    try:
      newObj.info = {"code": response["code"], "message": response["message"]}
      newObj.data = response["result"]
      # TODO: Handle error responses
    except TypeError, e:
      msg = "ERROR: response is not a dict: %s. Error: %s" % (response, e)
      newObj.logger.error(msg)
      raise
    return newObj

  @classmethod
  def fromMimeMsg(cls, response):
    newObj = cls()
    newObj.info = {"message": str(response)}
      # TODO: Handle error responses
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

  METHOD_GET = "GET"
  METHOD_POST = "POST"

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
    self.pageSize = pageSize

  def getUrl(self, endpoint, parameters={}):
    url = "http://%s%s" % (self.hostName, endpoint)
    encparams = urllib.urlencode(parameters)
    urlWithParams = url + "?" + encparams
    return urlWithParams

  def httpPost(self, endpoint, params = {}):
    url = self.getUrl(endpoint)
    headers = self.getOauthHeaders(
        url, BetterClient.METHOD_POST, params)
    paramString = urllib.urlencode(params)
    self.logger.debug("### POSTing to %s with data %s" % (url, paramString))
    requestObject = urllib2.Request(url, data=paramString, headers=headers)
    u = urllib2.urlopen(requestObject)
    #meta = u.info()
    response = u.read()
    return BetterResponse.fromJson(response)

  def httpGet(self, endpoint, params = {}):
    url = self.getUrl(endpoint)
    urlWithParams = self.getUrl(endpoint, params)
    headers = self.getOauthHeaders(url, BetterClient.METHOD_GET, params)
    requestObject = urllib2.Request(urlWithParams, headers=headers)
    u = urllib2.urlopen(requestObject)
    #meta = u.info()
    response = u.read()
    return BetterResponse.fromJson(response)

  def getOauthHeaders(self, url, method, params = {}):
    " Build headers using oauth2 "
    otoken = oauth.Token(self.token, self.tokenSecret)
    oconsumer = oauth.Consumer(self.consumerKey, self.consumerSecret)
    req = oauth.Request.from_consumer_and_token(
            oconsumer, token=otoken, http_method=method, 
            http_url=url, parameters=params
        )
    signature_method = oauth.SignatureMethod_HMAC_SHA1()
    req.sign_request(signature_method, oconsumer, otoken)
    headers = req.to_header()
    #headers['User-Agent'] = 'Trovesync'
    return headers

  def download(self, url, filename, filesize):
    """ Download file (copied from stackoverflow q. 22676) """
    self.logger.debug("saving as" + filename)
    headers = self.getOauthHeaders(url, BetterClient.METHOD_GET)
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

  def upload(self, endpoint, filePath, parameters):
    #endpWithParams = endpoint + "?" + urllib.urlencode(parameters) # Multipart post requests needs to pass parameters in url due to a bug on server.
    self.logger.debug("Uploading " + filePath + " to " + self.getUrl(endpoint, parameters))
    streaminghttp.register_openers()
    with open(filePath, "rb") as localfile:
      datagen, headers = encode.multipart_encode({"photo": localfile})
      oheaders = self.getOauthHeaders(self.getUrl(endpoint), BetterClient.METHOD_POST, parameters) #, headers)) # TODO: should I pass in headers here?
      headers.update(oheaders)
      request = urllib2.Request(self.getUrl(endpoint, parameters), datagen, headers)
      resource = urllib2.urlopen(request)
    response = resource.read()
    return BetterResponse.fromJson(response)
  

class RemoteJob:

  def __init__(self):
    pass

  def execute(self, client):
    pass


class DeletePhotoRemoteJob(RemoteJob):

  def __init__(self, photoId):
    self.photoId = photoId

  def execute(self, client):
    url = BetterClient.PHOTO_UPDATE % self.photoId
    respTagPhoto = client.httpPost(url, tagsAdd = [BetterClient.DELETE_TAG])
    return BetterResponse.fromDict(respTagPhoto)

  def __str__(self):
    return "Delete remote photo %s (soft deletion)" % self.photoId

class CreateAlbumRemoteJob(RemoteJob):

  def __init__(self, album):
    self.album = album

  def execute(self, client):
    self.logger.debug("Creating album with name '%s'" % self.album.remoteName)
    albresp = client.httpPost(BetterClient.ALBUM_CREATE, {"name": self.album.remoteName})
    debugMsg = "Response from POST %s: %s" % (
      BetterClient.ALBUMS_LIST, albresp.getInfoStr())
    self.logger.debug(debugMsg)
    if albresp.info["code"] == 201:
      self.logger.debug("Created album '%s' with id %s." % (
            self.album.remoteName, albresp.data["id"]))
    else:
      raise Exception
    self.album.remoteId = albresp.data["id"] # TODO: This deviates from the convention in the rest of the remote jobs
    return albresp

  def __str__(self):
    return "Job: Create remote album %s" % self.album.remoteName


class DownloadPhotoRemoteJob(RemoteJob):

  def __init__(self, url, filePath, fileSize):
    self.url = url
    self.filePath = filePath
    self.fileSize = fileSize

  def execute(self, client):
    return client.download(self.url, self.filePath, self.fileSize)

  def __str__(self):
    return "Job: Download remote photo (%d KB) from %s to %s" % (
      self.fileSize/1000, self.url, self.filePath)

class GetPhotoListRemoteJob(RemoteJob):

  def __init__(self, album):
    self.album= album

  def execute(self, client):
    # TODO: Check if there is a service to get photos on an album
    imgresp  = client.httpGet(
        BetterClient.PHOTOS_LIST, {"pageSize": self.pageSize})
    imgmessage = imgresp.getInfoStr()
    imgresult = imgresp.data
    debugMsg = "Response from GET %s: %s" % (
      BetterClient.PHOTOS_LIST, imgmessage)
    self.logger.debug(debugMsg)
    remotePhotos = [Photo(None, None, i["name"], i["hash"])
        for i in imgresult if self.albumId in i["albums"]]

    numPhotos = len(remotePhotos)
    if numPhotos >= self.wsClient.pageSize:
      self.logger.warn("Capped at %s (maxPhotos option)." %\
            self.wsClient.pageSize)
    self.logger.debug("Remote photos (%d):" % numPhotos)
    debugFormat = "album(s):%s/%s\n  %s"
    imgDebugInfo = [debugFormat %\
      ( i["albums"], i["filenameOriginal"], i["hash"])\
      for i in remotePhotos]
    self.logger.debug(imgDebugInfo.join("\n"))

    self.album.setRemotePhotos(remotePhotos)
    return imgresp

  def __str__(self):
    return "Job: Get list of remote photos in album %s." % self.albumId

class GetAlbumListRemoteJob(RemoteJob):

  def __init__(self):
    pass

  def execute(self, client):
    return client.httpGet(BetterClient.ALBUMS_LIST)

  def __str__(self):
    return "Job: Get list of remote albums."

class UploadPhotoRemoteJob(RemoteJob):

  def __init__(self, filePath, album):
    # NB: Album may not have albumId set yet (see CreateAlbumJob)
    self.filePath = filePath
    self.album = album

  def execute(self, client):
    if self.album.remoteId is None:
      raise
    return client.upload(
      BetterClient.PHOTO_UPLOAD, self.filePath, {"albums": self.album.remoteId})

  def __str__(self):
    return "Job: Upload photo %s to remote album %s (id: %s)" % (
      self.filePath, self.album.remoteName, self.album.remoteId)


# TODO: This is supposed to be an interface to all filesystem-touching jobs
class FileSystem:

  " Constants "
  PHOTO_FILEPATTERN = ".*\\.jpg$"

  def __init__(self):
    pass

# TODO: Local jobs doesn't really belong in client.py
class LocalJob:
  def __init__(self):
    pass

  def execute(self):
    pass

class DeletePhotoLocalJob(LocalJob):

  def __init__(self, filePath, backupPath):
    self.filePath = filePath
    self.backupPath = backupPath

  def execute(self):
    shutil.move(self.filePath, self.backupPath)

  def __str__(self):
    return "Job: Delete local photo %s (backup to %s)" % (
      self.filePath, self.backupPath)

class CreateDirLocalJob(LocalJob):

  def __init__(self, fullPath):
    self.fullPath = fullPath

  def execute(self):
    makedirs(self.fullpath)

  def __str__(self):
    return "Job: Create local directory %s." % self.fullPath

class GetPhotoListLocalJob(LocalJob):

  def __init__(self, album):
    self.album= album

  def execute(self):
    localPhotos = []
    rePhotoPattern = re.compile(FileSystem.PHOTO_FILEPATTERN, re.IGNORECASE)
    absLocalPath = path.abspath(self.albumPath)
    for currentPath, subFolders, files in walk(absLocalPath):
      if self.backupDir in subFolders:
        subFolders.remove(self.backupDir)
      relativePath = path.relpath(currentPath, absLocalPath)
      photoFiles = filter(rePhotoPattern.search, files)
      for filename in photoFiles:
        fullfile = path.join(absLocalPath, relativePath, filename)
        self.logger.debug(fullfile)
        with open(fullfile, "rb") as imgFile:
          sha = hashlib.sha1(imgFile.read()).hexdigest()
          self.logger.debug("  "+ sha)
        localPhotos.append(Photo(filename, relativePath, None, sha))
    self.album.setLocalPhotos(localPhotos)
    return

  def __str__(self):
    return "Job: Get list of local photos in album %s." % self.album.localName
    
