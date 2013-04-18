import logging
from openphoto import OpenPhoto
import json
import urllib2
import urllib
import oauth2 as oauth
import time
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

  def httpGet(self, endpoint, params = {}):
    params['oauth_version'] =  "1.0"
    params['oauth_nonce'] = oauth.generate_nonce()
    params['oauth_timestamp'] = int(time.time())
    otoken = oauth.Token(key=self.token, secret=self.tokenSecret)
    oconsumer = oauth.Consumer(key=self.consumerKey, secret=self.consumerSecret)
    params['oauth_token'] = otoken.key
    params['oauth_consumer_key'] = oconsumer.key
    url = "http://%s%s" % (self.hostName, endpoint)
    req = oauth.Request(method="GET", url=url, parameters=params)
    signature_method = oauth.SignatureMethod_HMAC_SHA1()
    req.sign_request(signature_method, oconsumer, otoken)
    u = self.urlopen(req)
    meta = u.info()
    response = u.read()
    self.logger.info("### response %s" % response)
    return BetterResponse.fromJson(response)

  def urlopen(self, oauthRequest):
    self.logger.info("### %s" % oauthRequest.url)
    request = urllib2.Request(oauthRequest.url)
    for header, value in oauthRequest.to_header().items():
      request.add_header(header, value)
    response = urllib2.urlopen(request)
    return response
  
  def getAlbums(self):
    resp = self.httpGet(BetterClient.ALBUMS_LIST)
    remoteAlbums = resp.data
    debugMsg = "Response from GET %s: %s" % (
      BetterClient.ALBUMS_LIST, resp.getInfoStr())
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
    rawresp = self.httpGet(BetterClient.PHOTOS_LIST, {"pageSize": self.pageSize})
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
  

