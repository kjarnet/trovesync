
from trovesync import Syncer, Config, BetterClient
from trovesync.client import GetAlbumListRemoteJob, RemoteJob, LocalJob

def ask(question, accept):
  """ Ask the user a question and accept an array of answers. 
      Answer is returned. """
  answer = raw_input(question + " " + str(accept))
  while answer not in accept:
    answer = raw_input("  Please choose one of: %s" % accept)
  return answer

def sync(syncer, client):
  """ Choose albums to synchronize """
  remoteAlbums = GetAlbumListRemoteJob().execute(client).data
  albums  = syncer.createAlbums(syncer.settings.albumMappings, remoteAlbums)

  prepJobs = []
  for album in albums:
    prepJobs += syncer.prepareAlbum(album)

  if prepJobs:
    # q = "Some albums are missing remote or local folders. "
    # q += "Do you want to fix them by executing these tasks:"
    q = "Do you want to execute these tasks to prepare the albums:"
    q += "\n  %s\n?" % "\n  ".join([str(j) for j in prepJobs])
    doPrepare = ask(q, ["y", "n"])
    if doPrepare == "y":
      for j in prepJobs:
        if isinstance(j, RemoteJob):
          j.execute(client)
        elif isinstance(j, LocalJob):
          j.execute()
        else:
          raise Exception()

  direction = ""
  for album in albums:
    if not album.hasRemote()\
          or not album.hasLocal()\
          or not album.hasBackupDir():
      print "Skipping album %s which has not been initialized." % album.remoteName
      continue
    remoteOnlyNames = [p.remoteName for p in album.getRemoteOnly()]
    localOnlyNames = [p.localName for p in album.getLocalOnly()]
    print "Syncing album %s against folder %s." % (
      album.remoteName, album.localPath)
    print "Local only: %s" % localOnlyNames
    print "Remote only: %s" % remoteOnlyNames

    """ Choose sync direction """
    if "a" not in direction:
      syncQuestion = "Do you want to sync " +\
        "[r]emote changes to local folder, " +\
        "[l]ocal changes to remote album or " +\
        "[c]hoose action for each picture [r/l/c]" +\
        "\n  (add \"a\" to apply to all albums, " +\
        "i.e. [ra/la/ca])? "
      direction = ask(syncQuestion, ["r", "l", "c", "ra", "la", "ca"])

    """ Synchronize! """
    if "r" in direction:
      jobs = syncer.syncFromRemote(album)
    elif "l" in direction:
      jobs = syncer.syncFromLocal(album)
    else:
      jobs = syncer.syncCustom(album)

    doContinue = ask("Do you want to execute these jobs %s?" % "\n  ".join([str(j) for j in jobs]),
      ["y", "n"])
    if doContinue != "y":
      print "Skipping album %s" % album.remoteName
      continue

    for j in jobs:
      if isinstance(j, RemoteJob):
        j.execute(client)
      elif isinstance(j, LocalJob):
        j.execute()
      else:
        raise Exception()

if __name__ == "__main__":
  settings = Config.fromFile("./cred.json")
  client = BetterClient(**settings.credentials)
  sync(Syncer(settings), client)

  

