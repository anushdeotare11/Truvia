import os
import shutil
import uuid
import logging
import io
import httpx
import cloudinary
import cloudinary.uploader
from app.config import settings

logger = logging.getLogger("truvia.storage")

class StorageClient:
    def __init__(self):
        self.storage_type = settings.STORAGE_TYPE
        if self.storage_type == "local":
            self.base_dir = settings.LOCAL_STORAGE_DIR
            os.makedirs(self.base_dir, exist_ok=True)
            logger.info(f"Initialized local storage directory at {self.base_dir}")
        elif self.storage_type == "cloudinary":
            # Cloudinary can be configured either via CLOUDINARY_URL or via explicit credentials
            if settings.CLOUDINARY_URL:
                cloudinary.config(cloudinary_url=settings.CLOUDINARY_URL)
                logger.info("Initialized Cloudinary client via CLOUDINARY_URL")
            elif settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
                cloudinary.config(
                    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                    api_key=settings.CLOUDINARY_API_KEY,
                    api_secret=settings.CLOUDINARY_API_SECRET
                )
                logger.info("Initialized Cloudinary client via explicit API credentials")
            else:
                logger.warning("Cloudinary storage requested but no credentials configured. Uploads may fail.")
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
        elif self.storage_type == "cloudinary":
            # Determine folder name based on file extension / content type
            # The prompt requested: "Organize uploads into folders based on file type (reports, evidence, profile-images, etc.)"
            file_ext_lower = file_ext.lower()
            if content_type:
                content_type_lower = content_type.lower()
                if "image" in content_type_lower:
                    folder = "evidence/images"
                elif "audio" in content_type_lower:
                    folder = "evidence/audio"
                elif "video" in content_type_lower:
                    folder = "evidence/videos"
                elif "pdf" in content_type_lower or "document" in content_type_lower:
                    folder = "evidence/documents"
                else:
                    folder = "evidence/others"
            else:
                if file_ext_lower in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
                    folder = "evidence/images"
                elif file_ext_lower in [".mp3", ".wav", ".m4a", ".ogg", ".aac", ".flac"]:
                    folder = "evidence/audio"
                elif file_ext_lower in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
                    folder = "evidence/videos"
                elif file_ext_lower in [".pdf", ".doc", ".docx", ".txt", ".csv"]:
                    folder = "evidence/documents"
                else:
                    folder = "evidence/others"

            try:
                # Generate unique public_id without the extension
                public_id = os.path.splitext(unique_filename)[0]
                
                # Cloudinary uploader takes bytes-like objects via BytesIO
                file_io = io.BytesIO(file_content)
                
                # Upload using auto resource type to handle audio/video/images correctly
                upload_result = cloudinary.uploader.upload(
                    file_io,
                    public_id=public_id,
                    folder=folder,
                    resource_type="auto"
                )
                secure_url = upload_result.get("secure_url")
                if not secure_url:
                    raise ValueError("Cloudinary response did not contain a secure_url")
                logger.info(f"Saved file to Cloudinary: {secure_url} in folder {folder}")
                return secure_url
            except Exception as e:
                logger.error(f"Failed to save file to Cloudinary: {str(e)}")
                raise
        else:
            # S3 client upload implementation placeholder
            logger.info(f"Simulating S3 upload for {unique_filename} to bucket {self.bucket_name}")
            return f"s3://{self.bucket_name}/{unique_filename}"

    async def get_file(self, file_ref: str) -> bytes:
        """
        Retrieves file contents by reference.
        """
        if file_ref.startswith("http://") or file_ref.startswith("https://"):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(file_ref)
                    response.raise_for_status()
                    return response.content
            except Exception as e:
                logger.error(f"Failed to fetch file from URL reference {file_ref}: {str(e)}")
                raise

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
        if file_ref.startswith("http://") or file_ref.startswith("https://"):
            return file_ref
        if self.storage_type == "local":
            # Return relative API URL path for dev serving
            return f"/api/v1/evidence/view/{file_ref}"
        else:
            # Generate pre-signed URL
            return f"https://s3.amazonaws.com/{self.bucket_name}/{file_ref}"

storage_client = StorageClient()

