import os
import pysftp
import paramiko
import subprocess

from googleapiclient.discovery import build

def check_folder_for_files(creds, folder_id):
    try:
        service = build('drive', 'v3', credentials=creds)

        response = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id, name)"
        ).execute()

        folders = response.get('files', [])

        return folders

    except Exception as e:
        print(f"Error: {e}")
        return False

def check_file_in_folder(creds,folder_id,folder_name):
    try:
        service = build('drive', 'v3', credentials=creds)

        response = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false and mimeType!='application/vnd.google-apps.folder'",
            fields="files(id, name)"
        ).execute()

        files = response.get('files', [])

        return files

    except Exception as e:
        print(f"Error: {e}")
        return False


def download_file(creds, file_id, destination_folder):
    # Create the Drive API client
    service = build('drive', 'v3', credentials=creds)

    # Get the file metadata
    file = service.files().get(fileId=file_id).execute()

    # Download the file
    print(f"Start Download File {file['name']} to Disk")
    request = service.files().get_media(fileId=file_id)
    with open(os.path.join(destination_folder, file['name']), 'wb') as f:
        f.write(request.execute())
    print(f"Download File {file['name']} Complete")
    


def send_to_sftp(creds, file_path, remote_path):
    # Replace with your SFTP server details
    SFTP_HOST = '10.184.0.17'
    SFTP_USERNAME = 'root'
    SFTP_PASSWORD = '2wsx1qaz.'
    SFTP_PORT = 22  # Change if your SFTP server uses a different port

    with pysftp.Connection(SFTP_HOST, username=SFTP_USERNAME, password=SFTP_PASSWORD, port=SFTP_PORT) as sftp:
        try:
            sftp.put(file_path, file_path)
            print(f"Successfully copied {file_path} to SFTP server.")
        except Exception as e:
            print(f"Failed to copy {file_path}: {e}")


def get_from_sftp(creds, file_path, remote_path):
    # Replace with your SFTP server details
    SFTP_HOST = '10.184.0.17'
    SFTP_USERNAME = 'root'
    SFTP_PASSWORD = '2wsx1qaz.'
    SFTP_PORT = 22  # Change if your SFTP server uses a different port

    try:
        # Create an SSH client
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to the remote host
        ssh_client.connect(hostname=SFTP_HOST, port=SFTP_PORT, username=SFTP_USERNAME, password=SFTP_PASSWORD)

        # Create an SFTP client
        sftp_client = ssh_client.open_sftp()

        # Download the file from the remote host
        sftp_client.get(file_path, remote_path)
        print(f"Successfully copied {file_path} to SFTP server.")
    except Exception as e:
        print(f"Failed to copy {file_path}: {e}")

def move_file(creds,file_id,folder_id):
    # Create the Drive API client
    service = build('drive', 'v3', credentials=creds)

    # Get the current parents of the file
    file = service.files().get(fileId=file_id, fields='parents').execute()
    previous_parents = ",".join(file.get('parents'))

    # Move the file to the new folder
    try:
        file = service.files().update(
            fileId=file_id,
            addParents=folder_id,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()
        print(f"File with ID '{file_id}' moved to folder with ID '{folder_id}' successfully.")
    except Exception as e:
        print(f"Error: {e}")


def upload_file(creds, file_path, folder_id):
    # Create the Drive API client
    service = build('drive', 'v3', credentials=creds)

    # Set metadata for the file
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [folder_id] if folder_id else None
    }
    
    # Upload the file to Google Drive
    try:
        media = service.files().create(
            body=file_metadata,
            media_body=file_path,
            fields='id'
        ).execute()

        print(f"File ID: {media['id']}")
        print("File uploaded successfully.")

    except Exception as e:
        print(f"Error: {e}")

def run_bash_script_on_remote_host(creds,script_name,file_name):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # Replace with your SFTP server details
    SFTP_HOST = '10.184.0.17'
    SFTP_USERNAME = 'root'
    SFTP_PASSWORD = '2wsx1qaz.'
    SFTP_PORT = 22  # Change if your SFTP server uses a different port
    
    try:
        # Connect to the remote host
        ssh_client.connect(SFTP_HOST, username=SFTP_USERNAME, password=SFTP_PASSWORD)

        # Execute the bash script remotely
        _, stdout, stderr = ssh_client.exec_command(f"bash /home/{script_name}.sh {file_name}")
        # Print the output and error messages (if any)
        print("Script output:")
        for line in stdout:
            print(line.strip())
        for line in stderr:
            print(line.strip())

    except paramiko.AuthenticationException as auth_exc:
        print("Authentication failed. Please check your username and password.")
    except paramiko.SSHException as ssh_exc:
        print("SSH connection failed.")
    finally:
        ssh_client.close()
        