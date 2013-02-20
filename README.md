TroveSync
=========

Application for synchronizing a local folder with a trovebox.com album

Dependencies
------------

* python-oauth2
* [openphoto-python](https://github.com/photo/openphoto-python)
* [poster](http://atlee.ca/software/poster/)

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

Known Issues
------------
Because Trovebox currently autorotate all uploaded images
with exiftran
_before_ storing the original
and exiftran (for reasons unknown) adds some bytes to the file
irrespective of whether the image needs rotation or not
the actual _original_ version of the file is not available
for downloading from trovebox (see [issue at github]
(https://github.com/photo/frontend/issues/1149)).
Furthermore, because the hash stored with the image on Trovebox
is generated from the _actual original_,
and as trovesync uses this hash to compare files
syncing from Trovebox will be faulty.
There are two ways to work around this problem
(until Trovebox hopefully changes this behaviour):

1. Run all your images through exiftran autorotation locally
_before_ uploading to Trovebox.
2. Ask Trovebox support kindly to disable exiftran for your account.

License
-------
Released under the MIT License as stated in the file LICENSE.

