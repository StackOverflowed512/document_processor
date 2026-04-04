"""
File handling utilities for document processing
"""

import os
import hashlib
import mimetypes
from pathlib import Path
from typing import Tuple, Optional, BinaryIO
from datetime import datetime
import aiofiles
from loguru import logger
from fastapi import UploadFile


class FileValidator:
    """Validate uploaded files for security and compatibility"""
    
    # Common malicious patterns
    MALICIOUS_PATTERNS = [
        b'<?php',
        b'<script',
        b'javascript:',
        b'vbscript:',
        b'exec(',
        b'eval(',
        b'system(',
        b'passthru(',
        b'shell_exec('
    ]
    
    @classmethod
    def validate_file_size(cls, file_content: bytes, max_size: int) -> bool:
        """Check if file size is within limits"""
        return len(file_content) <= max_size
    
    @classmethod
    def validate_extension(cls, filename: str, allowed_extensions: list) -> bool:
        """Check if file extension is allowed"""
        ext = Path(filename).suffix.lower()
        return ext in allowed_extensions
    
    @classmethod
    def validate_mime_type(cls, file_content: bytes, expected_types: list) -> bool:
        """Validate MIME type of file content"""
        mime_type = mimetypes.guess_type("")[0]
        
        # Check magic bytes for common file types
        if file_content.startswith(b'%PDF'):
            mime_type = 'application/pdf'
        elif file_content.startswith(b'\x89PNG\r\n\x1a\n'):
            mime_type = 'image/png'
        elif file_content.startswith(b'\xff\xd8\xff'):
            mime_type = 'image/jpeg'
        elif file_content.startswith(b'From:') or b'Content-Type:' in file_content[:1000]:
            mime_type = 'message/rfc822'
        
        return mime_type in expected_types if expected_types else True
    
    @classmethod
    def scan_for_malicious_content(cls, file_content: bytes) -> bool:
        """Scan file for malicious patterns"""
        content_lower = file_content.lower()
        
        for pattern in cls.MALICIOUS_PATTERNS:
            if pattern in content_lower:
                logger.warning(f"Malicious pattern detected: {pattern[:20]}")
                return True
        
        return False


class FileProcessor:
    """Process and manage uploaded files"""
    
    def __init__(self, temp_dir: Path):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_upload_file(self, file: UploadFile, request_id: str) -> Path:
        """
        Save uploaded file to temporary storage
        
        Args:
            file: Uploaded file object
            request_id: Unique request identifier
        
        Returns:
            Path to saved file
        """
        # Generate safe filename
        original_name = file.filename
        safe_name = self._sanitize_filename(original_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{request_id}_{timestamp}_{safe_name}"
        file_path = self.temp_dir / unique_filename
        
        # Save file asynchronously
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        logger.info(f"Saved uploaded file to {file_path}")
        return file_path
    
    async def read_file_content(self, file_path: Path) -> bytes:
        """Read file content as bytes"""
        async with aiofiles.open(file_path, 'rb') as f:
            return await f.read()
    
    async def delete_temp_file(self, file_path: Path):
        """Delete temporary file after processing"""
        try:
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Deleted temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete temporary file {file_path}: {e}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal"""
        # Remove path components
        filename = os.path.basename(filename)
        
        # Remove special characters
        safe_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_')
        sanitized = ''.join(c for c in filename if c in safe_chars)
        
        # Ensure we have a valid name
        if not sanitized:
            sanitized = "unnamed_file"
        
        return sanitized
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """Delete temporary files older than specified age"""
        try:
            current_time = datetime.now()
            deleted_count = 0
            
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if file_age.total_seconds() > max_age_hours * 3600:
                        file_path.unlink()
                        deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old temporary files")
                
        except Exception as e:
            logger.error(f"Error during temp file cleanup: {e}")


def calculate_file_hash(file_content: bytes, algorithm: str = 'sha256') -> str:
    """
    Calculate hash of file content for deduplication
    
    Args:
        file_content: File content as bytes
        algorithm: Hash algorithm (md5, sha1, sha256)
    
    Returns:
        Hexadecimal hash string
    """
    if algorithm == 'md5':
        hash_obj = hashlib.md5()
    elif algorithm == 'sha1':
        hash_obj = hashlib.sha1()
    else:
        hash_obj = hashlib.sha256()
    
    hash_obj.update(file_content)
    return hash_obj.hexdigest()


def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return Path(filename).suffix.lower()


def is_image_file(filename: str) -> bool:
    """Check if file is an image"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    return get_file_extension(filename) in image_extensions


def is_pdf_file(filename: str) -> bool:
    """Check if file is a PDF"""
    return get_file_extension(filename) == '.pdf'


def is_text_file(filename: str) -> bool:
    """Check if file is a text file"""
    text_extensions = {'.txt', '.csv', '.json', '.xml', '.eml', '.msg'}
    return get_file_extension(filename) in text_extensions