import time
import json
from typing import Dict, Any
from loguru import logger
from pydantic import ValidationError

from app.models.schemas import Invoice, CleanedData
from app.services.llm_service import LLMService
from app.prompts.templates import STRUCTURING_PROMPT

class StructuringPhase:
    """Phase 3: Convert cleaned data to strict JSON schema"""
    
    def __init__(self):
        self.llm_service = LLMService()
    
    async def process(self, cleaned_data: CleanedData) -> Invoice:
        """
        Convert cleaned data to Invoice schema
        
        Args:
            cleaned_data: Output from Phase 2
        
        Returns:
            Validated Invoice object
        """
        start_time = time.time()
        
        try:
            # Try direct mapping if confidence is high
            if cleaned_data.confidence > 0.85:
                try:
                    invoice = self._direct_mapping(cleaned_data.normalized_fields)
                    if invoice:
                        logger.info("Direct mapping successful")
                        return invoice
                except Exception as e:
                    logger.warning(f"Direct mapping failed: {e}")
            
            # Use LLM for structuring
            prompt = STRUCTURING_PROMPT.format(
                cleaned_data=json.dumps(cleaned_data.normalized_fields, indent=2)
            )
            
            response_text = await self.llm_service.complete(
                prompt=prompt,
                system_prompt="You are a data structuring expert. Return ONLY valid JSON matching the schema.",
                temperature=0.1
            )
            
            # Parse and validate
            invoice_data = self._parse_llm_response(response_text)
            invoice = Invoice(**invoice_data)
            
            processing_time = (time.time() - start_time) * 1000
            logger.info(f"Structuring complete in {processing_time:.2f}ms")
            
            return invoice
            
        except ValidationError as e:
            logger.error(f"Validation failed: {e}")
            # Try to fix common validation errors
            return self._fix_validation_errors(cleaned_data.normalized_fields, e)
            
        except Exception as e:
            logger.error(f"Structuring failed: {e}")
            # Return minimal valid invoice
            return self._create_minimal_invoice(cleaned_data.normalized_fields)
    
    def _direct_mapping(self, normalized_fields: Dict[str, Any]) -> Invoice:
        """Directly map fields to Invoice without LLM"""
        # Ensure all required fields are present
        required_fields = ["invoice_number", "date", "vendor_name", "total_amount", "currency"]
        
        for field in required_fields:
            if field not in normalized_fields or normalized_fields[field] is None:
                raise ValueError(f"Missing required field: {field}")
        
        return Invoice(**normalized_fields)
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM JSON response"""
        response_text = response_text.strip()
        
        # Remove markdown if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        return json.loads(response_text.strip())
    
    def _fix_validation_errors(self, normalized: Dict[str, Any], validation_error: ValidationError) -> Invoice:
        """Attempt to fix common validation errors"""
        logger.info("Attempting to fix validation errors")
        
        # Set defaults for missing required fields
        invoice_data = normalized.copy()
        
        if "invoice_number" not in invoice_data or not invoice_data["invoice_number"]:
            invoice_data["invoice_number"] = "UNKNOWN"
            
        if "date" not in invoice_data or not invoice_data["date"]:
            from datetime import date
            invoice_data["date"] = date.today().isoformat()
            
        if "vendor_name" not in invoice_data or not invoice_data["vendor_name"]:
            invoice_data["vendor_name"] = "Unknown Vendor"
            
        if "total_amount" not in invoice_data or invoice_data["total_amount"] is None:
            invoice_data["total_amount"] = 0.0
            
        if "currency" not in invoice_data or not invoice_data["currency"]:
            invoice_data["currency"] = "USD"
        
        return Invoice(**invoice_data)
    
    def _create_minimal_invoice(self, normalized: Dict[str, Any]) -> Invoice:
        """Create minimal valid invoice as last resort"""
        from datetime import date
        
        return Invoice(
            invoice_number=normalized.get("invoice_number", "UNKNOWN"),
            date=normalized.get("date", date.today().isoformat()),
            vendor_name=normalized.get("vendor_name", "Unknown Vendor"),
            total_amount=float(normalized.get("total_amount", 0.0)),
            currency=normalized.get("currency", "USD"),
            account_number=normalized.get("account_number")
        )