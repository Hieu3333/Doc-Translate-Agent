"""
Supabase file storage service for handling file uploads and downloads.
"""

from core.database import get_supabase_client
from typing import Optional, Tuple
import io
import os
from dotenv import load_dotenv

load_dotenv()

class FileStorageService:
    """Service for managing file operations with Supabase Storage"""

    BUCKET_NAME = os.getenv("SUPABASE_STORAGE_BUCKET")
    
    @staticmethod
    def upload_file(file_path: str, file_content: bytes) -> str:
        """
        Upload a file to Supabase storage.
        
        Args:
            file_path: The path where the file will be stored (e.g., "session_id/filename.pdf")
            file_content: The file content as bytes
        
        Returns:
            The public URL of the uploaded file
        """
        supabase = get_supabase_client()
        
        try:
            response = supabase.storage.from_(FileStorageService.BUCKET_NAME).upload(
                file_path,
                file_content
            )
            
            # Get public URL
            public_url = supabase.storage.from_(FileStorageService.BUCKET_NAME).get_public_url(file_path)
            
            return public_url
        except Exception as e:
            raise Exception(f"Error uploading file: {str(e)}")
    
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
