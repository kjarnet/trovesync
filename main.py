from openphoto import OpenPhoto
import json
import hashlib
from os import listdir
from os.path import isfile, join

# Trovebox service endpoints:
PHOTOS_LIST = "/photos/list.json"
ALBUMS_LIST = "/albums/list.json"

""" Get Credentials """
with open("./cred.json") as credfile:
  cred = json.load(credfile)
print "cred.json: ", cred

""" Initialize a webservice client """
albumPath = cred["albumPath"]
pageSize = cred["maxPhotos"]
client = OpenPhoto(
  cred["host"],
  cred["consumerKey"],
  cred["consumerSecret"],
  cred["token"],
  cred["tokenSecret"]
  )

""" Get list of remote albums """
albresp = json.loads(client.get(ALBUMS_LIST)) 
albmessage = albresp["message"]
albcode = albresp["code"]
remoteAlbums = albresp["result"]
ids = []
print albmessage, "Remote albums: " 
for a in remoteAlbums:
  print a["id"]
  print a["name"]
  ids.append(a["id"])
ids.append("null")

""" Choose an album to synchronize """
albumId = raw_input("Enter id-number of album to synchronize against the folder " + 
  albumPath + ": ")
while albumId not in ids:
  albumId = raw_input("Please enter a valid album id " + str(ids) + ": ")

""" Get list of remote images """
imgresp = json.loads(client.get(PHOTOS_LIST, {"pageSize": pageSize}))
imgmessage = imgresp["message"]
imgcode = imgresp["code"]
imgresult = imgresp["result"]
remoteImgs = [i for i in imgresult if albumId in i["albums"]]
# remoteImgs = imgresult
print imgmessage
for i in remoteImgs:
  print i["albums"]
  print i["filenameOriginal"]
  print i["hash"]
print "Count: ", len(remoteImgs)
if len(remoteImgs) >= pageSize:
  print ("Capped at " + pageSize + " (maxPhotos option).")

""" Loop through local files and compare against remote images """
localonly = []
for f in listdir(albumPath):
  fullfile = join(albumPath, f)
  print fullfile
  with open(fullfile, "rb") as imgFile:
    sha = hashlib.sha1(imgFile.read()).hexdigest()
    print sha
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
print "Remote only: ", remoteonly

""" Choose sync direction """
direction = raw_input("Do you want to sync [r]emote changes to local folder, [l]ocal changes to remote album or [c]hoose for each picture [r/l/c]? ")
while direction not in ["r", "l", "c"]:
  direction = raw_input("Please choose r for remote, l for local or c for custom: ")

""" Synchronize! """
if direction == "r":
  for i in localonly:
    print "move local image to backup location", i
  for i in remoteonly:
    print "download image", i["filenameOriginal"]
elif direction == "l":
  for i in localonly:
    print "upload to remote", i
  for i in remoteonly:
    print "tag remote image for deletion", i["filenameOriginal"]
else:
  for i in localonly:
    print "give user a choice: delete or upload", i
  for i in remoteonly:
    print "give user a choice: delete or download", i["filenameOriginal"]
  

