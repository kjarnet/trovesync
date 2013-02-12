TroveSync
=========

Application for synchronizing a local folder with a trovebox.com album

Dependencies
------------

* python-oauth2
* [openphoto-python](https://github.com/photo/openphoto-python)

Usage
-----

1. Get your OAuth credentials from Site Settings 
on your Trovebox site 
by creating a new app.
2. Copy sample.cred.json to cred.json
and replace with your credentials
and album path.
3. Run `python main.py`.
4. When prompted,
open the folders "localonly" and "remoteonly".
Files in the localonly folder
are copies of files that exist in you local album
but are not in Trovebox.
Files in the remoteonly folder
are files you have stored in Trovebox
but are not in your local album.
5. You now get three choices:
   1. "Sync from Trovebox":
   Choose this to make your local folder
   an exact copy of the Trovebox album.
   For each file in the localonly folder
   the corresponding file in your local folder will be deleted.
   For each file in the remoteonly folder
   the corresponding file will be downloaded from Trovebox
   to your local folder.
   2. "Sync to Trovebox":
   This will make the Trovebox album
   an exact copy of your local folder.
   Each file in the localonly folder
   will be uploaded to the Trovebox album.
   For each file in the remoteonly folder
   the corresponding file will be deleted from Trovebox.
   3. "Manual":
   This will go through each file in both folders
   and prompt you to choose whether to
   upload the file to Trovebox,
   download the file to your local album,
   delete the file from Trovebox,
   delete the file from your local album
   or ignore the file.

