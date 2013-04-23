# main.py
from trovesync import Syncer, Settings

if __name__ == "__main__": Syncer(Settings.fromFile("./cred.json")).sync()

  

