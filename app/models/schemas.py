from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    CLEANSING = "cleansing"
    STRUCTURING = "structuring"
    COMPLETED = "completed"
    FAILED = "failed"

class RawExtraction(BaseModel):
    """Output from Phase 1"""
    raw_text: str
    extraction_method: str  # "vlm", "ocr", "fallback"
    confidence_score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    processing_time_ms: float

class CleanedData(BaseModel):
    """Output from Phase 2"""
    normalized_fields: Dict[str, Any]
    original_raw_text: str
    transformations_applied: List[str] = Field(default_factory=list)
    inferred_fields: List[str] = Field(default_factory=list)
    confidence: float

class Invoice(BaseModel):
    """Final structured output schema"""
    invoice_number: str = Field(..., description="Unique invoice identifier")
    date: str = Field(..., description="Invoice date in YYYY-MM-DD format")
    vendor_name: str = Field(..., description="Name of the vendor/supplier")
    total_amount: float = Field(..., description="Total invoice amount")
    currency: str = Field(..., description="Currency code (USD, EUR, GBP, etc.)")
    account_number: Optional[str] = Field(None, description="Customer account number")
    due_date: Optional[str] = Field(None, description="Payment due date")
    line_items: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    tax_amount: Optional[float] = None
    subtotal: Optional[float] = None
    
    @validator('date', 'due_date', pre=True)
    def validate_date_format(cls, v):
        """Ensure date is in YYYY-MM-DD format"""
        if v is None:
            return v
        try:
            # Try to parse various formats
            if isinstance(v, str):
                # Handle common formats
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%b %d, %Y', '%B %d, %Y']:
                    try:
                        parsed = datetime.strptime(v, fmt)
                        return parsed.strftime('%Y-%m-%d')
                    except ValueError:
                        continue
            return str(v)
        except Exception:
            return v
    
    @validator('total_amount', 'tax_amount', 'subtotal')
    def validate_positive_amount(cls, v):
        """Ensure amounts are positive"""
        if v is not None and v < 0:
            raise ValueError(f"Amount must be positive, got {v}")
        return v

class ProcessingResult(BaseModel):
    """Complete pipeline result"""
    request_id: str
    status: ProcessingStatus
    raw_extraction: Optional[RawExtraction] = None
    cleaned_data: Optional[CleanedData] = None
    final_invoice: Optional[Invoice] = None
    error: Optional[str] = None
    processing_stages: Dict[str, float] = Field(default_factory=dict)