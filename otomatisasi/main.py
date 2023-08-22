from __future__ import print_function

import re
import sys
from typing import Any
import warnings
import os
import os.path
import time
import subprocess
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from gcp.var import *
from gcp.compute import *
from drive.folder import *

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive']
CREDENTIALS_FILE = 'omics_training.json'
FOLDER_ID = '1xgSB5kSILFeY940XkqH7pO5QKRxHr3om'

def main():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds

def start_pipeline(creds, folder_id):
    while True:
        folders = check_folder_for_files(creds, folder_id)      
        if folders:
            print("Folders found with the specified parent folder ID:")
            for folder in folders:
                print(f"Folder ID: {folder['id']}, Folder Name: {folder['name']}")
                files = check_file_in_folder(creds,folder['id'],folder['name'])
                if files:
                    print("files found with the specified parent folder ID:")
                    for file in files:
                        print("Start Time : ", datetime.now())

                        print(f"file ID: {file['id']}, file Name: {file['name']}")
                        download_file(creds,file['id'],f"/home/{folder['name']}")
                        time.sleep(5)
                        
                        send_to_sftp(creds, f"/home/{folder['name']}/{file['name']}", f"/home/{folder['name']}/{file['name']}")
                        time.sleep(5)

                        upgrade_instance()
                        time.sleep(30)
                        
                        name, extension = os.path.splitext(file['name'])
                        run_bash_script_on_remote_host(creds,folder['name'],name)
                        time.sleep(5)
                        
                        get_from_sftp(creds,f"/home/{folder['name']}/output/{name}.zip",f"/home/{folder['name']}/output/{name}.zip")
                        time.sleep(5)
                        
                        upload_file(creds,f"/home/{folder['name']}/output/{name}.zip",'1P1u6zm4ijl8DIbplFpyAC3BFTqQvo4U_')
                        time.sleep(5)

                        downgrade_instance()
                        time.sleep(30)
                        
                        run_bash_script_on_remote_host(creds,f"rm_{folder['name']}",name)
                        move_file(creds, file['id'], '1CtZzLvgAd2RhMohITmg7GYT9Wwntx3kW')
                        os.remove(f"/home/{folder['name']}/{file['name']}")
                        os.remove(f"/home/{folder['name']}/output/{name}.zip")
                        time.sleep(10)
                        print("End Time : ",datetime.now())
                        print("Done")
                else:
                    print("No files found.")
        else:
            print("No folders found.")
            print("Waiting for folders and files")

        time.sleep(60)


def downgrade_instance():
    machine_type='e2-micro'
    update_instance_machine_type(project,zone,instance_name,machine_type)

def upgrade_instance():
    machine_type='e2-highcpu-8'
    update_instance_machine_type(project,zone,instance_name,machine_type)

if __name__ == '__main__':
    creds = main()
    start_pipeline(creds,FOLDER_ID)
    