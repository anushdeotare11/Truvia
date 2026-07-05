import os
import shutil
import uuid
import logging
from app.config import settings

logger = logging.getLogger("truvia.storage")

class StorageClient:
    def __init__(self):
        self.storage_type = settings.STORAGE_TYPE
        if self.storage_type == "local":
            self.base_dir = settings.LOCAL_STORAGE_DIR
            os.makedirs(self.base_dir, exist_ok=True)
            logger.info(f"Initialized local storage directory at {self.base_dir}")
        else:
            # Placeholder for S3 storage configuration
            # In production, initialize boto3 client
            self.bucket_name = settings.STORAGE_BUCKET_NAME
            logger.info(f"Initialized S3 storage bucket reference for {self.bucket_name}")

    async def save_file(self, file_content: bytes, filename: str, content_type: str = None) -> str:
        """
        Saves file contents and returns a reference string (file_ref).
        """
        # Generate unique key to avoid collision
        file_ext = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"

        if self.storage_type == "local":
            file_path = os.path.join(self.base_dir, unique_filename)
            try:
                # Write file synchronously (standard for small files in threads)
                with open(file_path, "wb") as buffer:
                    buffer.write(file_content)
                logger.info(f"Saved file locally: {file_path}")
                return unique_filename
            except Exception as e:
                logger.error(f"Failed to save file locally: {str(e)}")
                raise
        else:
            # S3 client upload implementation placeholder
            logger.info(f"Simulating S3 upload for {unique_filename} to bucket {self.bucket_name}")
            return f"s3://{self.bucket_name}/{unique_filename}"

    async def get_file(self, file_ref: str) -> bytes:
        """
        Retrieves file contents by reference.
        """
        if self.storage_type == "local":
            file_path = os.path.join(self.base_dir, file_ref)
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_ref}")
            with open(file_path, "rb") as file:
                return file.read()
        else:
            # S3 client download implementation placeholder
            logger.info(f"Simulating S3 download for {file_ref}")
            return b"dummy file contents"

    async def get_file_url(self, file_ref: str) -> str:
        """
        Returns accessible URL or path for the file.
        """
        if self.storage_type == "local":
            # Return relative API URL path for dev serving
            return f"/api/v1/evidence/view/{file_ref}"
        else:
            # Generate pre-signed URL
            return f"https://s3.amazonaws.com/{self.bucket_name}/{file_ref}"

storage_client = StorageClient()
