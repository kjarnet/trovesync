import logging
import json

__metaclass__ = type # make sure we use new-style classes

" Globals: "
APPNAME = "trovesync"

class Config:
  """ This is the holder for the data in 
      the cred.json file. It is responsible for
      reading it and alternatively generate it.
  """

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

