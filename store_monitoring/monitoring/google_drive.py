import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

class GoogleDriveClient:
    """A client for interacting with Google Drive API."""
    
    def __init__(self, credentials_file=None):
        """Initialize the Google Drive client."""
        self.credentials_file = credentials_file or os.environ.get('GOOGLE_DRIVE_CREDENTIALS_JSON') or 'service_account.json'
        self.drive_service = None
    
    def initialize(self):
        """Initialize the Google Drive service."""  
        if not os.path.exists(self.credentials_file):
            raise FileNotFoundError(f"Google Drive credentials file not found: {self.credentials_file}")
        
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_file, scopes=['https://www.googleapis.com/auth/drive'])
            self.drive_service = build('drive', 'v3', credentials=credentials)
            return True
        except Exception as e:
            print(f"Error initializing Google Drive client: {e}")
            return False
    
    def upload_file(self, file_path, file_name=None, mime_type=None, folder_id=None):
        """
        Upload a file to Google Drive.
        
        Arguments:
            file_path: Path to the file to upload
            file_name: Name to use for the file in Google Drive (defaults to basename of file_path)
            mime_type: MIME type of the file (auto-detected if not provided)
            folder_id: ID of the folder to upload to (root if not provided)
            
        Returns:
            Dictionary with file ID and webViewLink if successful, None if failed
        """
        if not self.drive_service:
            if not self.initialize():
                return None
        
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None
        
        try:
            if not file_name:
                file_name = os.path.basename(file_path)
            
            if not mime_type:
                # Try to guess MIME type or default to text/plain
                import mimetypes
                mime_type = mimetypes.guess_type(file_path)[0] or 'text/plain'
            
            file_metadata = {
                'name': file_name,
                'mimeType': mime_type
            }
            
            # If folder_id is provided, set parent folder
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            
            # Create the file
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink'
            ).execute()
            
            # Make the file viewable by anyone with the link
            self.drive_service.permissions().create(
                fileId=file.get('id'),
                body={'type': 'anyone', 'role': 'reader'},
                fields='id'
            ).execute()
            
            return {
                'id': file.get('id'),
                'link': file.get('webViewLink')
            }
        
        except HttpError as e:
            print(f"Google Drive API error: {e}")
            return None
        except Exception as e:
            print(f"Error uploading file to Google Drive: {e}")
            return None
    
    def create_folder(self, folder_name, parent_folder_id=None):
        """
        Create a folder in Google Drive.
        
        Arguments:
            folder_name: Name of the folder to create
            parent_folder_id: ID of the parent folder (root if not provided)
            
        Returns:
            Folder ID if successful, None if failed
        """
        if not self.drive_service:
            if not self.initialize():
                return None
        
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            folder = self.drive_service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            return folder.get('id')
        
        except Exception as e:
            print(f"Error creating folder in Google Drive: {e}")
            return None