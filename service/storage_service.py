"""
File storage service for handling file uploads and downloads.
"""

from core.database import get_supabase_client
from typing import Optional, Tuple
import io
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()

class FileStorageService:
    """Service for managing file operations - Supabase as main storage, local for processing"""

    BUCKET_NAME = os.getenv("SUPABASE_STORAGE_BUCKET")
    LOCAL_UPLOAD_DIR = "uploads"  # Local directory for file processing
    
    @staticmethod
    def upload_file(file_path: str, file_content: bytes) -> str:
        """
        Upload a file to Supabase storage.
        
        Args:
            file_path: The desired path (e.g., "user_id/session_id/filename.pdf")
            file_content: The file content as bytes
        
        Returns:
            Supabase path (not URL, just the path)
        """
        supabase = get_supabase_client()
        
        try:
            logger.info(f"Uploading file to Supabase at path: {file_path} (size: {len(file_content)} bytes)")
            
            supabase.storage.from_(FileStorageService.BUCKET_NAME).upload(
                file_path,
                file_content
            )
            
            logger.info(f"File successfully uploaded to Supabase: {file_path}")
            # Return the Supabase path
            return file_path
        except Exception as e:
            logger.error(f"Error uploading file to Supabase at path '{file_path}': {str(e)}", exc_info=True)
            raise Exception(f"Error uploading file to Supabase: {str(e)}")
    
    @staticmethod
    def download_and_save_locally(supabase_path: str) -> str:
        """
        Download a file from Supabase and save it locally for processing.
        
        Args:
            supabase_path: The Supabase storage path (e.g., "user_id/session_id/filename.pdf")
        
        Returns:
            The local file path where the file was saved
        """
        supabase = get_supabase_client()
        
        try:
            logger.info(f"Downloading file from Supabase: {supabase_path}")
            
            # Download from Supabase
            file_content = supabase.storage.from_(FileStorageService.BUCKET_NAME).download(supabase_path)
            
            # Save to local storage
            local_path = Path(FileStorageService.LOCAL_UPLOAD_DIR) / supabase_path
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(local_path, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"File saved locally at: {local_path}")
            # Return the local path as a string
            return str(local_path)
        except Exception as e:
            logger.error(f"Error downloading file from Supabase at path '{supabase_path}': {str(e)}", exc_info=True)
            raise Exception(f"Error downloading and saving file locally from path '{supabase_path}': {str(e)}")
    
    @staticmethod
    def upload_local_file_to_supabase(local_file_path: str, supabase_path: str) -> str:
        """
        Upload a local file to Supabase storage.
        
        Args:
            local_file_path: The local file path to upload (e.g., "uploads/user_id/session_id/output.xlsx")
            supabase_path: The desired Supabase path for the file
        
        Returns:
            The Supabase path where the file was saved
        """
        supabase = get_supabase_client()
        
        try:
            logger.info(f"Reading local file from: {local_file_path}")
            
            # Read local file
            with open(local_file_path, 'rb') as f:
                file_content = f.read()
            
            logger.info(f"Uploading output file to Supabase at path: {supabase_path} (size: {len(file_content)} bytes)")
            
            # Upload to Supabase
            supabase.storage.from_(FileStorageService.BUCKET_NAME).upload(
                supabase_path,
                file_content
            )
            
            logger.info(f"Output file successfully uploaded to Supabase: {supabase_path}")
            # Return the Supabase path
            return supabase_path
        except Exception as e:
            logger.error(f"Error uploading local file to Supabase: local_path='{local_file_path}', supabase_path='{supabase_path}', error={str(e)}", exc_info=True)
            raise Exception(f"Error uploading local file to Supabase: {str(e)}")
    
    @staticmethod
    def download_file(file_path: str) -> Tuple[bytes, str]:
        """
        Download a file from Supabase storage.
        
        Args:
            file_path: The path of the file to download (e.g., "session_id/filename.pdf")
        
        Returns:
            Tuple of (file_content: bytes, content_type: str)
        """
        supabase = get_supabase_client()
        
        try:
            response = supabase.storage.from_(FileStorageService.BUCKET_NAME).download(file_path)
            
            # Determine content type based on file extension
            content_type = FileStorageService._get_content_type(file_path)
            
            return response, content_type
        except Exception as e:
            raise Exception(f"Error downloading file: {str(e)}")
    
    @staticmethod
    def delete_file(file_path: str) -> bool:
        """
        Delete a file from Supabase storage.
        
        Args:
            file_path: The path of the file to delete
        
        Returns:
            True if successful
        """
        supabase = get_supabase_client()
        
        try:
            supabase.storage.from_(FileStorageService.BUCKET_NAME).remove([file_path])
            return True
        except Exception as e:
            raise Exception(f"Error deleting file: {str(e)}")
    
    @staticmethod
    def list_files(folder_path: str) -> list:
        """
        List all files in a folder in Supabase storage.
        
        Args:
            folder_path: The folder path (e.g., "session_id/")
        
        Returns:
            List of file metadata
        """
        supabase = get_supabase_client()
        
        try:
            response = supabase.storage.from_(FileStorageService.BUCKET_NAME).list(folder_path)
            return response
        except Exception as e:
            raise Exception(f"Error listing files: {str(e)}")
    
    @staticmethod
    def _get_content_type(file_path: str) -> str:
        """Get content type based on file extension"""
        extension_map = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
            ".html": "text/html",
            ".htm": "text/html",
            ".json": "application/json",
            ".xml": "application/xml",
            ".csv": "text/csv",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".zip": "application/zip",
            ".tar": "application/x-tar",
            ".gz": "application/gzip",
        }
        
        file_lower = file_path.lower()
        for ext, content_type in extension_map.items():
            if file_lower.endswith(ext):
                return content_type
        
        # Default to binary/octet-stream if extension not found
        return "application/octet-stream"
    
    @staticmethod
    def get_file_extension(file_path: str) -> str:
        """Extract file extension from path"""
        return file_path.split(".")[-1] if "." in file_path else ""
