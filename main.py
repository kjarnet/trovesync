# main.py
from trovesync import Syncer, Settings

if __name__ == "__main__":
  settings = Settings.fromFile("./cred.json")
  client = BetterClient(**settings.credentials)
  Syncer(settings).sync(client)

  

