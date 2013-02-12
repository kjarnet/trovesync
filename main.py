from openphoto import OpenPhoto
import json
import hashlib
from os import listdir
from os.path import isfile, join
with open("./cred.json") as credfile:
  cred = json.load(credfile)
print cred
client = OpenPhoto(cred["host"], cred["consumerKey"], cred["consumerSecret"], cred["token"], cred["tokenSecret"])
resp = json.loads(client.get('/photos/list.json'))
message = resp["message"]
code = resp["code"]
result = resp["result"]
print message
for i in result:
  print i["albums"]
  print i["filenameOriginal"]
  print i["hash"]

for f in listdir(cred["albumPath"]):
  fullfile = join(cred["albumPath"], f)
  print fullfile
  with open(fullfile, "rb") as imgFile:
    sha = hashlib.sha1(imgFile.read()).hexdigest()
    print sha


