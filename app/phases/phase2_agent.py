import json
import time
from typing import Dict, Any
from loguru import logger

from app.models.schemas import CleanedData, RawExtraction
from app.services.llm_service import LLMService
from app.prompts.templates import CLEANSING_AGENT_PROMPT

class AgenticCleansingPhase:
    """Phase 2: Agent-based reasoning for data cleansing"""
    
    def __init__(self):
        self.llm_service = LLMService()
    
    async def process(self, raw_extraction: RawExtraction) -> CleanedData:
        """
        Clean and normalize raw extracted text using LLM agent
        
        Args:
            raw_extraction: Output from Phase 1
        
        Returns:
            CleanedData with normalized fields
        """
        start_time = time.time()
        
        try:
            # Prepare prompt with raw text
            prompt = CLEANSING_AGENT_PROMPT.format(raw_text=raw_extraction.raw_text[:8000])  # Limit token size
            
            # Get LLM response
            response_text = await self.llm_service.complete(
                prompt=prompt,
                system_prompt="You are a data cleansing expert. Return ONLY valid JSON.",
                temperature=0.1
            )
            
            # Parse JSON response
            cleaned_data = self._parse_llm_response(response_text)
            
            # Additional post-processing
            cleaned_data = self._post_process(cleaned_data)
            
            processing_time = (time.time() - start_time) * 1000
            
            logger.info(f"Cleansing complete in {processing_time:.2f}ms")
            
            return CleanedData(
                normalized_fields=cleaned_data.get("normalized_fields", {}),
                original_raw_text=raw_extraction.raw_text[:500],  # Store sample
                transformations_applied=cleaned_data.get("transformations_applied", []),
                inferred_fields=cleaned_data.get("inferred_fields", []),
                confidence=cleaned_data.get("confidence", 0.5)
            )
            
        except Exception as e:
            logger.error(f"Cleansing failed: {str(e)}")
            # Return fallback cleaned data
            return self._fallback_cleaning(raw_extraction.raw_text)
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response, handling common issues"""
        try:
            # Try to find JSON in response
            response_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            # Parse JSON
            data = json.loads(response_text.strip())
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.debug(f"Raw response: {response_text[:500]}")
            return {
                "normalized_fields": {},
                "transformations_applied": ["json_parse_failed"],
                "inferred_fields": [],
                "confidence": 0.3
            }
    
    def _post_process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Additional post-processing of cleaned data"""
        normalized = data.get("normalized_fields", {})
        
        # Ensure currency is uppercase
        if "currency" in normalized and normalized["currency"]:
            normalized["currency"] = normalized["currency"].upper()
        
        # Convert total_amount to float if it's string
        if "total_amount" in normalized and isinstance(normalized["total_amount"], str):
            try:
                # Remove currency symbols and commas
                cleaned = normalized["total_amount"].replace("$", "").replace(",", "").strip()
                normalized["total_amount"] = float(cleaned)
            except:
                pass
        
        data["normalized_fields"] = normalized
        return data
    
    def _fallback_cleaning(self, raw_text: str) -> CleanedData:
        """Fallback cleaning when LLM fails"""
        logger.warning("Using fallback cleaning method")
        
        # Simple regex-based fallback (basic extraction)
        import re
        
        normalized = {}
        
        # Try to find invoice number
        inv_match = re.search(r'(?:invoice|inv|#)[\s:]*([A-Z0-9\-]+)', raw_text, re.IGNORECASE)
        if inv_match:
            normalized["invoice_number"] = inv_match.group(1)
        
        # Try to find date
        date_match = re.search(r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})', raw_text)
        if date_match:
            normalized["date"] = date_match.group(1)
        
        # Try to find amount
        amount_match = re.search(r'(?:total|amount|sum)[\s:]*\$?([\d,]+\.?\d*)', raw_text, re.IGNORECASE)
        if amount_match:
            try:
                normalized["total_amount"] = float(amount_match.group(1).replace(",", ""))
            except:
                pass
        
        return CleanedData(
            normalized_fields=normalized,
            original_raw_text=raw_text[:500],
            transformations_applied=["fallback_regex_cleaning"],
            inferred_fields=[],
            confidence=0.4
        )