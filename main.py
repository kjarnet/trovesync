from openphoto import OpenPhoto
import json
import hashlib
from os import listdir, path
import shutil
import urllib2
import urllib
import oauth2 as oauth
from poster import encode, streaminghttp

# Trovebox service endpoints:
ALBUMS_LIST = "/albums/list.json"
PHOTOS_LIST = "/photos/list.json"
PHOTO_UPLOAD = "/photo/upload.json"
PHOTO_UPDATE = "/photo/%s/update.json"

# Other constants:
DELETE_TAG = "trovesyncDelete"

""" Get Credentials """
with open("./cred.json") as credfile:
  cred = json.load(credfile)
print "cred.json: ", cred

""" Initialize a webservice client """
albumPath = cred["albumPath"]
pageSize = cred["maxPhotos"]
troveboxClient = OpenPhoto(
  cred["host"],
  cred["consumerKey"],
  cred["consumerSecret"],
  cred["token"],
  cred["tokenSecret"]
  )

""" Get list of remote albums """
albresp = json.loads(troveboxClient.get(ALBUMS_LIST)) 
albmessage = albresp["message"]
albcode = albresp["code"]
remoteAlbums = albresp["result"]
print "Response from GET " + ALBUMS_LIST + ":", albmessage
ids = []
print "Remote albums: " 
for a in remoteAlbums:
  print "[" + a["id"] + "] " + a["name"]
  ids.append(a["id"])
ids.append("null")

""" Choose an album to synchronize """
albumId = raw_input("Enter id-number of album to synchronize against the folder " + 
  albumPath + ": ")
while albumId not in ids:
  albumId = raw_input("Please enter a valid album id " + str(ids) + ": ")

""" Get list of remote images """
imgresp = json.loads(troveboxClient.get(PHOTOS_LIST, {"pageSize": pageSize}))
imgmessage = imgresp["message"]
imgcode = imgresp["code"]
imgresult = imgresp["result"]
print "Response from GET " + PHOTOS_LIST + ":", imgmessage
remoteImgs = [i for i in imgresult if albumId in i["albums"]]
print "Remote images:"
for i in remoteImgs:
  print "albums:", i["albums"], "/",  i["filenameOriginal"]
  print "  ", i["hash"]
print "Count: ", len(remoteImgs)
if len(remoteImgs) >= pageSize:
  print ("Capped at " + pageSize + " (maxPhotos option).")

""" Loop through local files and compare against remote images """
localonly = []
print "Local files:"
for f in listdir(albumPath):
  fullfile = path.join(albumPath, f)
  if not path.isfile(fullfile): continue
  print fullfile
  with open(fullfile, "rb") as imgFile:
    sha = hashlib.sha1(imgFile.read()).hexdigest()
    print "  ", sha
  found = False
  for i in remoteImgs:
    if i["hash"] == sha:
      i["inSync"] = True
      found = True
      break
  if not found:
    localonly.append(f)
remoteonly = [i for i in remoteImgs if "inSync" not in i]


print "Local only: ", localonly
print "Remote only: ", [i["filenameOriginal"] for i in remoteonly]

" First, build headers using oauth2 "
def getOauthHeaders(url, method):
  parameters = None
  consumer = oauth.Consumer(troveboxClient.consumer_key, troveboxClient.consumer_secret)
  access_token = oauth.Token(troveboxClient.token, troveboxClient.token_secret)
  sig_method = oauth.SignatureMethod_HMAC_SHA1()

  oauth_request = oauth.Request.from_consumer_and_token(
          consumer, token=access_token, http_method=method, http_url=url, parameters=parameters
      )
  oauth_request.sign_request(sig_method, consumer, access_token)
  headers = oauth_request.to_header()
  headers['User-Agent'] = 'Trovesync'
  return headers


""" Download file (copied from stackoverflow q. 22676) """
def download(url, file_name, file_size):
  print "saving as", file_name
  headers = getOauthHeaders(url, "GET")
  u = urllib2.urlopen(urllib2.Request(url, headers=headers))
  with open(file_name, 'wb') as f:
    meta = u.info()
    print "Response from GET " + url + ":", meta
    print "Downloading: %s Bytes: %s" % (file_name, file_size)

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
      print status
    return meta

def upload(url, file_name, parameters):
  encparams = urllib.urlencode(parameters)
  urlWithParams = url + "?" + encparams
  streaminghttp.register_openers()
  datagen, headers = encode.multipart_encode({"photo": open(file_name, "rb")})
  headers.update(getOauthHeaders(urlWithParams, "POST"))
  request = urllib2.urlopen(urllib2.Request(urlWithParams, datagen, headers))
  response = request.read()
  return response

""" Choose sync direction """
direction = raw_input("Do you want to sync [r]emote changes to local folder, [l]ocal changes to remote album or [c]hoose for each picture [r/l/c]? ")
while direction not in ["r", "l", "c"]:
  direction = raw_input("Please choose r for remote, l for local or c for custom: ")


def syncFromRemote():
  for f in localonly:
    fullfile = path.join(albumPath, f)
    backupPath = cred["backupPath"]
    print "move local image ", fullfile, "to backup location", backupPath
    shutil.move(fullfile, backupPath)
  for i in remoteonly:
    print "download image", i["filenameOriginal"]
    respDownload = json.loads(download(i["pathDownload"], path.join(albumPath, i["filenameOriginal"]), int(i["size"])*1024))
    print "Response from GET " + i["pathDownload"] + ": " + respDownload["message"]

def syncFromLocal():
  for f in localonly:
    print "upload to remote", f
    url = "http://" + cred["host"] + PHOTO_UPLOAD
    fullfile = path.join(albumPath, f)
    respUpload = json.loads(upload(url, fullfile, {"albums": albumId}))
    print "Response from POST " + url + ":", respUpload["message"]

  for i in remoteonly:
    print "tag remote image for deletion", i["filenameOriginal"]
    url = PHOTO_UPDATE % i["id"]
    respTagPhoto = json.loads(troveboxClient.post(url, {"tagsAdd": DELETE_TAG}))
    print "Response from POST " + url + ":", respTagPhoto["message"]

def syncCustom():
  for f in localonly:
    print "give user a choice: delete or upload", f
  for i in remoteonly:
    print "give user a choice: delete or download", i["filenameOriginal"]

""" Synchronize! """
if direction == "r":
  syncFromRemote()
elif direction == "l":
  syncFromLocal()
else:
  syncCustom()
  

