import logging
import json
import urllib2
import urllib
import oauth2 as oauth
from poster import encode, streaminghttp

from config import APPNAME

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
      msg = "ERROR: response is not a dict: %s" % response
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
    meta = u.info()
    response = u.read()
    return BetterResponse.fromJson(response)

  def httpGet(self, endpoint, params = {}):
    url = self.getUrl(endpoint)
    urlWithParams = self.getUrl(endpoint, params)
    headers = self.getOauthHeaders(url, BetterClient.METHOD_GET, params)
    requestObject = urllib2.Request(urlWithParams, headers=headers)
    u = urllib2.urlopen(requestObject)
    meta = u.info()
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

  def upload(self, endpoint, fileName, parameters):
    #endpWithParams = endpoint + "?" + urllib.urlencode(parameters) # Multipart post requests needs to pass parameters in url due to a bug on server.
    self.logger.debug("Uploading " + fileName + " to " + self.getUrl(endpoint, parameters))
    streaminghttp.register_openers()
    with open(fileName, "rb") as localfile:
      datagen, headers = encode.multipart_encode({"photo": localfile})
      oheaders = self.getOauthHeaders(self.getUrl(endpoint), BetterClient.METHOD_POST, parameters) #, headers)) # TODO: should I pass in headers here?
      headers.update(oheaders)
      request = urllib2.Request(self.getUrl(endpoint, parameters), datagen, headers)
      resource = urllib2.urlopen(request)
    response = resource.read()
    return BetterResponse.fromJson(response)
  
  def uploadPhoto(self, albumId, fileName):
    return self.upload(BetterClient.PHOTO_UPLOAD, fileName, {"albums": albumId})
    
  def getAlbums(self):
    resp = self.httpGet(BetterClient.ALBUMS_LIST)
    remoteAlbums = resp.data
    debugMsg = "Response from GET %s: %s" % (
      BetterClient.ALBUMS_LIST, resp.getInfoStr())
    self.logger.debug(debugMsg)
    return remoteAlbums

  def createAlbum(self, name):
    self.logger.debug("Creating album with name '%s'" % name)
    albresp = self.httpPost(BetterClient.ALBUM_CREATE, {"name": name})
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
    imgresp  = self.httpGet(
        BetterClient.PHOTOS_LIST, {"pageSize": self.pageSize})
    imgmessage = imgresp.getInfoStr()
    imgresult = imgresp.data
    debugMsg = "Response from GET %s: %s" % (
      BetterClient.PHOTOS_LIST, imgmessage)
    self.logger.debug(debugMsg)
    remoteImgs = [i for i in imgresult if albumId in i["albums"]]
    return remoteImgs

  def softDeletePhoto(self, photoId):
    url = BetterClient.PHOTO_UPDATE % photoId
    respTagPhoto = self.httpPost(url, tagsAdd = [BetterClient.DELETE_TAG])
    return BetterResponse.fromDict(respTagPhoto)




