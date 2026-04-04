import io
from typing import Optional
from pathlib import Path
from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes
from loguru import logger
import asyncio

from app.config import settings

class OCRService:
    """OCR fallback service using Tesseract"""
    
    def __init__(self):
        if settings.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_path
    
    async def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF using OCR"""
        try:
            # Convert PDF to images
            images = await asyncio.get_event_loop().run_in_executor(
                None, convert_from_bytes, pdf_bytes, 300
            )
            
            extracted_text = []
            for i, image in enumerate(images):
                text = await self.extract_text_from_image(image)
                extracted_text.append(f"--- Page {i+1} ---\n{text}")
            
            return "\n\n".join(extracted_text)
            
        except Exception as e:
            logger.error(f"PDF OCR failed: {e}")
            raise
    
    async def extract_text_from_image(self, image) -> str:
        """Extract text from PIL Image using Tesseract"""
        try:
            # Preprocess image for better OCR
            processed = self._preprocess_image(image)
            
            # Run OCR
            text = await asyncio.get_event_loop().run_in_executor(
                None, pytesseract.image_to_string, processed
            )
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"Image OCR failed: {e}")
            return ""
    
    def _preprocess_image(self, image):
        """Preprocess image for better OCR results"""
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Increase contrast (simple threshold)
        threshold = 150
        image = image.point(lambda p: p > threshold and 255)
        
        return image
    
    async def extract_text_from_bytes(self, file_bytes: bytes, file_extension: str) -> str:
        """Extract text from file bytes based on type"""
        if file_extension == '.pdf':
            return await self.extract_text_from_pdf(file_bytes)
        else:
            # Assume image
            image = Image.open(io.BytesIO(file_bytes))
            return await self.extract_text_from_image(image)