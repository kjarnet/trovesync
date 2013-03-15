# main.py

import logging
import re
from openphoto import OpenPhoto
import json
import hashlib
from os import listdir, path
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
  def __init__(self, localpath, remoteId, backupPath):
    self.logger = logging.getLogger(APPNAME + ".Album")
    self.localonly = []
    self.remoteonly = []
    self.localpath = localpath
    self.remoteId = remoteId
    self.backupPath = backupPath

  def syncFromRemote(self, client):
    for f in self.localonly:
      fullfile = path.join(self.localpath, f)
      self.logger.info("move local image "+ fullfile+ "to backup location"+ self.backupPath)
      shutil.move(fullfile, self.backupPath)
    for i in self.remoteonly:
      self.logger.info("download image"+ i["filenameOriginal"]+ " from "+ i["pathDownload"])
      localFullfile = path.join(self.localpath, i["filenameOriginal"])
      downloadPath = i["pathDownload"]
      fixedDownloadPath = re.sub(r"^http:", "https:", downloadPath)
      self.logger.info("fixed download path is"+ fixedDownloadPath)
      respDownload = str(
        client.download(fixedDownloadPath, localFullfile, int(i["size"])*1024))
      self.logger.info("Response from GET " + i["pathDownload"] + ": " + respDownload)

  def syncFromLocal(self, client):
    for f in self.localonly:
      self.logger.info("upload to remote"+ f)
      fullfile = path.join(self.localpath, f)
      respUpload = json.loads(client.uploadPhoto(self.remoteId, fullfile))
      self.logger.info("Response from POST " +  BetterClient.PHOTO_UPLOAD + ":"+ respUpload["message"])

    for i in self.remoteonly:
      self.logger.info("tag remote image for deletion"+ i["filenameOriginal"])
      respTagPhoto = json.loads(client.softDeletePhoto(i["id"]))
      self.logger.info("Response from POST " + url + ":"+ respTagPhoto["message"])

  def syncCustom(self, client):
    for f in self.localonly:
      self.logger.info("give user a choice: delete or upload"+ f)
    for i in self.remoteonly:
      self.logger.info("give user a choice: delete or download"+ i["filenameOriginal"])

class BetterClient:
  " A proxy to the OpenPhoto client with added methods for download and upload "

# Trovebox service endpoints:
  ALBUMS_LIST = "/albums/list.json"
  PHOTOS_LIST = "/photos/list.json"
  PHOTO_UPLOAD = "/photo/upload.json"
  PHOTO_UPDATE = "/photo/%s/update.json"

# Other constants:
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
    albresp = json.loads(self.opClient.get(BetterClient.ALBUMS_LIST)) 
    albmessage = albresp["message"]
    albcode = albresp["code"]
    remoteAlbums = albresp["result"]
    self.logger.info("Response from GET " + BetterClient.ALBUMS_LIST + ":"+ albmessage)
    return remoteAlbums

  def getAlbumPhotos(self, albumId):
    imgresp = json.loads(self.opClient.get(BetterClient.PHOTOS_LIST, {"pageSize": self.pageSize}))
    imgmessage = imgresp["message"]
    imgcode = imgresp["code"]
    imgresult = imgresp["result"]
    self.logger.info("Response from GET " + BetterClient.PHOTOS_LIST + ":"+ imgmessage)
    remoteImgs = [i for i in imgresult if albumId in i["albums"]]
    return remoteImgs

  def softDeletePhoto(self, photoId):
    url = BetterClient.PHOTO_UPDATE % photoId
    respTagPhoto = self.opClient.post(url, {"tagsAdd": DELETE_TAG})
    return respTagPhoto


  " First, build headers using oauth2 "
  def getOauthHeaders(self, url, method):
    parameters = None
    consumer = oauth.Consumer(self.consumerKey, self.consumerSecret)
    access_token = oauth.Token(self.token, self.tokenSecret)
    sig_method = oauth.SignatureMethod_HMAC_SHA1()

    oauth_request = oauth.Request.from_consumer_and_token(
            consumer, token=access_token, http_method=method, http_url=url, parameters=parameters
        )
    oauth_request.sign_request(sig_method, consumer, access_token)
    headers = oauth_request.to_header()
    headers['User-Agent'] = 'Trovesync'
    return headers

  """ Download file (copied from stackoverflow q. 22676) """
  def download(self, url, file_name, file_size):
    self.logger.info("saving as"+ file_name)
    headers = self.getOauthHeaders(url, "GET")
    requestObject = urllib2.Request(url, headers=headers)
    self.logger.info("made request"+ requestObject.get_full_url())
    u = urllib2.urlopen(requestObject)
    with open(file_name, 'wb') as f:
      meta = u.info()
      self.logger.info("Response from GET " + url + ":"+ meta)
      self.logger.info("Downloading: %s Bytes: %s" % (file_name+ file_size))

      file_size_dl = 0
      block_sz = 8192
      while True:
        buffer = u.read(block_sz)
        if not buffer:
          break
        file_size_dl += len(buffer)
        f.write(buffer)
        status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
        status = status + chr(8)*(len(status)+1)
        self.logger.info(status)
    return meta

  def uploadPhoto(self, albumId, fileName):
    url = "http://" + self.hostName + BetterClient.PHOTO_UPLOAD
    return self.upload(url, fileName, {"albums": albumId})
    
  def upload(self, url, file_name, parameters):
    encparams = urllib.urlencode(parameters)
    urlWithParams = url + "?" + encparams
    streaminghttp.register_openers()
    with open(file_name, "rb") as localfile:
      datagen, headers = encode.multipart_encode({"photo": localfile})
      headers.update(self.getOauthHeaders(urlWithParams, "POST"))
      request = urllib2.urlopen(urllib2.Request(urlWithParams, datagen, headers))
    response = request.read()
    return response


def setup():
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

  " Credentials "
  with open("./cred.json") as credfile:
    cred = json.load(credfile)
  logger.info("cred.json: "+ str(cred))
  return cred

def sync(cred):

  logger = logging.getLogger(APPNAME)
  """ Initialize a webservice client """
  albumsPath = cred["albumsPath"]
  troveboxClient = BetterClient(
    cred["host"],
    cred["consumerKey"],
    cred["consumerSecret"],
    cred["token"],
    cred["tokenSecret"],
    cred["maxPhotos"]
    )

  """ Choose albums to synchronize """
  remoteAlbums = troveboxClient.getAlbums()
  albumMappings = cred["albums"]
  albums = []
  logger.info("Remote albums: " )
  for m in albumMappings:
    for a in remoteAlbums:
      found = False
      if m["remoteName"] == a["name"]:
        localPath = path.join(albumsPath, m["localName"])
        backupPath = path.join(localPath, cred["backupDirName"])
        albums.append(Album(localPath, a["id"], backupPath))
        found = True
        break
    if not found:
      remoteAlbumNames = [a["name"] for a in remoteAlbums]
      raise Exception("Found no remote album named " + m["remoteName"] +" in " + str(remoteAlbumNames))
  logger.info([a["name"] for a in remoteAlbums])

  for album in albums:
    """ Get list of remote images """
    remoteImgs = troveboxClient.getAlbumPhotos(album.remoteId)
    logger.info("Remote images:")
    for i in remoteImgs:
      logger.info("albums:"+ str(i["albums"])+ "/"+  i["filenameOriginal"])
      logger.info("  "+ i["hash"])
    logger.info("Count: "+ str(len(remoteImgs)))
    if len(remoteImgs) >= troveboxClient.pageSize:
      logger.info(("Capped at " + troveboxClient.pageSize + " (maxPhotos option)."))

    """ Loop through local files and compare against remote images """
    logger.info("Local files:")
    for f in listdir(album.localpath):
      fullfile = path.join(album.localpath, f)
      if not path.isfile(fullfile):
        logger.info("Skipping"+ fullfile+ "(is not a file).")
        continue
      logger.info(fullfile)
      with open(fullfile, "rb") as imgFile:
        sha = hashlib.sha1(imgFile.read()).hexdigest()
        logger.info("  "+ sha)
      found = False
      for i in remoteImgs:
        if i["hash"] == sha:
          i["inSync"] = True
          found = True
          break
      if not found:
        album.localonly.append(f)
    album.remoteonly = [i for i in remoteImgs if "inSync" not in i]

    logger.info("Local only: "+ str(album.localonly))
    logger.info("Remote only: "+ str([i["filenameOriginal"] for i in album.remoteonly]))

    """ Choose sync direction """
    direction = raw_input("Do you want to sync [r]emote changes to local folder, [l]ocal changes to remote album or [c]hoose for each picture [r/l/c]? ")
    while direction not in ["r", "l", "c"]:
      direction = raw_input("Please choose r for remote, l for local or c for custom: ")

    """ Synchronize! """
    if direction == "r":
      album.syncFromRemote(troveboxClient)
    elif direction == "l":
      album.syncFromLocal(troveboxClient)
    else:
      album.syncCustom(troveboxClient)

def goGoGadget():
  cred = setup()
  sync(cred)

if __name__ == "__main__": goGoGadget()

  

