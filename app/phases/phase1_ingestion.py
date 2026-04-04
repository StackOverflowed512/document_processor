import time
from typing import Dict, Any
import io
from pathlib import Path
import base64
from loguru import logger

from app.models.schemas import RawExtraction
from app.services.llm_service import VisionService
from app.services.ocr_service import OCRService
from app.prompts.templates import VISION_EXTRACTION_PROMPT
from app.config import settings

class IngestionPhase:
    """Phase 1: Extract raw text from documents"""
    
    def __init__(self):
        self.vision_service = VisionService()
        self.ocr_service = OCRService()
        
    async def process(self, file_content: bytes, filename: str, file_type: str) -> RawExtraction:
        """
        Process file and extract raw text
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            file_type: MIME type or extension
        
        Returns:
            RawExtraction object with extracted text
        """
        start_time = time.time()
        extraction_method = "unknown"
        raw_text = ""
        confidence = None
        
        try:
            # Determine file extension
            ext = Path(filename).suffix.lower()
            
            # Try VLM first for images
            if ext in ['.png', '.jpg', '.jpeg', '.tiff']:
                logger.info(f"Processing image {filename} with VLM")
                # Convert image to base64 for VLM
                image_b64 = base64.b64encode(file_content).decode('utf-8')
                raw_text = await self.vision_service.extract_text_from_image(
                    image_b64, VISION_EXTRACTION_PROMPT
                )
                extraction_method = "vlm"
                confidence = 0.9
                
                # If VLM extraction is empty, fallback to OCR
                if not raw_text or len(raw_text.strip()) < 50:
                    logger.warning("VLM extraction returned little text, falling back to OCR")
                    raw_text = await self.ocr_service.extract_text_from_bytes(file_content, ext)
                    extraction_method = "ocr_fallback"
                    confidence = 0.7
            
            # For PDFs, try direct text extraction first, then OCR
            elif ext == '.pdf':
                logger.info(f"Processing PDF {filename}")
                # Try direct text extraction
                raw_text = await self._extract_pdf_text(file_content)
                
                if not raw_text or len(raw_text.strip()) < 100:
                    logger.warning("Direct PDF text extraction failed, using OCR")
                    raw_text = await self.ocr_service.extract_text_from_bytes(file_content, ext)
                    extraction_method = "ocr"
                    confidence = 0.75
                else:
                    extraction_method = "pdf_text_extraction"
                    confidence = 0.85
            
            # For text files, direct read
            elif ext == '.txt':
                raw_text = file_content.decode('utf-8', errors='ignore')
                extraction_method = "direct_text"
                confidence = 0.99
            
            # For email files
            elif ext == '.eml':
                raw_text = file_content.decode('utf-8', errors='ignore')
                extraction_method = "email_text"
                confidence = 0.95
            
            else:
                raise ValueError(f"Unsupported file type: {ext}")
            
            # Validate extraction
            if not raw_text or len(raw_text.strip()) == 0:
                raise ValueError("No text extracted from document")
            
            processing_time = (time.time() - start_time) * 1000
            
            logger.info(f"Extraction complete: {len(raw_text)} characters using {extraction_method}")
            
            return RawExtraction(
                raw_text=raw_text,
                extraction_method=extraction_method,
                confidence_score=confidence,
                metadata={
                    "filename": filename,
                    "file_type": file_type,
                    "file_size": len(file_content)
                },
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Extraction failed for {filename}: {str(e)}")
            processing_time = (time.time() - start_time) * 1000
            raise
    
    async def _extract_pdf_text(self, pdf_bytes: bytes) -> str:
        """Extract text directly from PDF using PyPDF"""
        try:
            from pypdf import PdfReader
            import io
            
            pdf_file = io.BytesIO(pdf_bytes)
            reader = PdfReader(pdf_file)
            
            text = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
            
            return "\n".join(text)
            
        except Exception as e:
            logger.warning(f"PyPDF extraction failed: {e}")
            return ""