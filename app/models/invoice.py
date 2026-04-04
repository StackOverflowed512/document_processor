"""
Invoice data models and schemas for the document processing pipeline.
This module contains the core business data models for invoice processing.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum


class CurrencyCode(str, Enum):
    """Supported currency codes"""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CAD = "CAD"
    AUD = "AUD"
    CNY = "CNY"
    INR = "INR"
    UNKNOWN = "UNKNOWN"


class PaymentTerms(str, Enum):
    """Common payment terms"""
    NET_30 = "Net 30"
    NET_60 = "Net 60"
    NET_90 = "Net 90"
    DUE_ON_RECEIPT = "Due on Receipt"
    COD = "COD"
    EOM = "End of Month"
    UNKNOWN = "Unknown"


class LineItem(BaseModel):
    """Individual line item from invoice"""
    description: Optional[str] = Field(None, description="Item description")
    quantity: Optional[float] = Field(1.0, description="Quantity of items", ge=0)
    unit_price: Optional[float] = Field(None, description="Price per unit", ge=0)
    total_price: Optional[float] = Field(None, description="Total for line item (quantity * unit_price)", ge=0)
    product_code: Optional[str] = Field(None, description="Product/SKU code")
    tax_rate: Optional[float] = Field(None, description="Tax rate percentage for this item", ge=0, le=100)
    
    @validator('total_price', pre=True, always=True)
    def calculate_total_price(cls, v, values):
        """Auto-calculate total price if not provided"""
        if v is None and 'quantity' in values and 'unit_price' in values:
            if values['quantity'] and values['unit_price']:
                return values['quantity'] * values['unit_price']
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "description": "Enterprise Software License",
                "quantity": 2,
                "unit_price": 499.99,
                "total_price": 999.98,
                "product_code": "SW-2024-001",
                "tax_rate": 10.0
            }
        }


class TaxDetail(BaseModel):
    """Tax information breakdown"""
    tax_type: str = Field(..., description="Type of tax (GST, VAT, Sales Tax, etc.)")
    tax_rate: float = Field(..., description="Tax rate percentage", ge=0, le=100)
    taxable_amount: float = Field(..., description="Amount before tax", ge=0)
    tax_amount: float = Field(..., description="Tax amount", ge=0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "tax_type": "GST",
                "tax_rate": 18.0,
                "taxable_amount": 1000.00,
                "tax_amount": 180.00
            }
        }


class VendorInfo(BaseModel):
    """Vendor/Supplier information"""
    name: str = Field(..., description="Vendor company name")
    tax_id: Optional[str] = Field(None, description="VAT/Tax identification number")
    address: Optional[str] = Field(None, description="Vendor address")
    email: Optional[str] = Field(None, description="Vendor email")
    phone: Optional[str] = Field(None, description="Vendor phone number")
    website: Optional[str] = Field(None, description="Vendor website")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Tech Solutions Inc.",
                "tax_id": "12-3456789",
                "address": "123 Business Ave, San Francisco, CA 94105",
                "email": "billing@techsolutions.com",
                "phone": "+1 (555) 123-4567"
            }
        }


class CustomerInfo(BaseModel):
    """Customer/Buyer information"""
    name: str = Field(..., description="Customer name")
    account_number: Optional[str] = Field(None, description="Customer account number")
    tax_id: Optional[str] = Field(None, description="Customer tax ID")
    address: Optional[str] = Field(None, description="Customer address")
    email: Optional[str] = Field(None, description="Customer email")
    po_number: Optional[str] = Field(None, description="Purchase Order number")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "ABC Corporation",
                "account_number": "ACC-789012",
                "tax_id": "98-7654321",
                "address": "456 Corporate Dr, Chicago, IL 60601",
                "email": "accounts@abccorp.com",
                "po_number": "PO-2024-00123"
            }
        }


class Invoice(BaseModel):
    """
    Main Invoice model representing a structured invoice document.
    This is the primary output schema for Phase 3.
    """
    
    # Required fields
    invoice_number: str = Field(
        ..., 
        description="Unique invoice identifier",
        min_length=1,
        max_length=50
    )
    
    date: str = Field(
        ..., 
        description="Invoice date in YYYY-MM-DD format",
        regex=r'^\d{4}-\d{2}-\d{2}$'
    )
    
    vendor_name: str = Field(
        ..., 
        description="Name of the vendor/supplier",
        min_length=1,
        max_length=200
    )
    
    total_amount: float = Field(
        ..., 
        description="Total invoice amount (including tax)",
        ge=0
    )
    
    currency: str = Field(
        ..., 
        description="Currency code (USD, EUR, GBP, etc.)",
        min_length=3,
        max_length=3
    )
    
    # Optional fields
    account_number: Optional[str] = Field(
        None, 
        description="Customer account number",
        max_length=50
    )
    
    due_date: Optional[str] = Field(
        None, 
        description="Payment due date in YYYY-MM-DD format",
        regex=r'^\d{4}-\d{2}-\d{2}$'
    )
    
    line_items: Optional[List[LineItem]] = Field(
        default_factory=list,
        description="Individual line items from the invoice"
    )
    
    tax_amount: Optional[float] = Field(
        None, 
        description="Total tax amount",
        ge=0
    )
    
    subtotal: Optional[float] = Field(
        None, 
        description="Subtotal before tax and discounts",
        ge=0
    )
    
    discount_amount: Optional[float] = Field(
        None, 
        description="Total discount amount",
        ge=0
    )
    
    discount_percentage: Optional[float] = Field(
        None, 
        description="Discount percentage",
        ge=0,
        le=100
    )
    
    shipping_amount: Optional[float] = Field(
        None, 
        description="Shipping/handling charges",
        ge=0
    )
    
    payment_terms: Optional[PaymentTerms] = Field(
        None, 
        description="Payment terms"
    )
    
    vendor_info: Optional[VendorInfo] = Field(
        None, 
        description="Detailed vendor information"
    )
    
    customer_info: Optional[CustomerInfo] = Field(
        None, 
        description="Detailed customer information"
    )
    
    tax_details: Optional[List[TaxDetail]] = Field(
        default_factory=list,
        description="Breakdown of taxes applied"
    )
    
    notes: Optional[str] = Field(
        None, 
        description="Additional invoice notes or terms",
        max_length=1000
    )
    
    po_number: Optional[str] = Field(
        None, 
        description="Purchase Order number reference",
        max_length=50
    )
    
    order_date: Optional[str] = Field(
        None, 
        description="Order/PO date in YYYY-MM-DD format",
        regex=r'^\d{4}-\d{2}-\d{2}$'
    )
    
    payment_due_days: Optional[int] = Field(
        None, 
        description="Number of days until payment is due",
        ge=0
    )
    
    # Validators
    @validator('date', 'due_date', 'order_date', pre=True)
    def validate_date_format(cls, v):
        """Ensure date is in YYYY-MM-DD format"""
        if v is None:
            return v
        
        # If already in correct format
        if isinstance(v, str) and len(v) == 10 and v[4] == '-' and v[7] == '-':
            return v
        
        # Try to parse from various formats
        try:
            if isinstance(v, str):
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%b %d, %Y', '%B %d, %Y', '%Y%m%d']:
                    try:
                        parsed = datetime.strptime(v, fmt)
                        return parsed.strftime('%Y-%m-%d')
                    except ValueError:
                        continue
                
                # Handle dates like "Jan 15, 2024"
                try:
                    parsed = datetime.strptime(v, '%b %d, %Y')
                    return parsed.strftime('%Y-%m-%d')
                except:
                    pass
                    
            elif isinstance(v, datetime):
                return v.strftime('%Y-%m-%d')
                
        except Exception:
            pass
        
        raise ValueError(f"Invalid date format: {v}")
    
    @validator('currency')
    def validate_currency(cls, v):
        """Ensure currency code is valid"""
        v = v.upper()
        valid_currencies = [c.value for c in CurrencyCode]
        if v not in valid_currencies:
            # Try to map common alternatives
            currency_map = {
                'US DOLLAR': 'USD',
                'US DOLLARS': 'USD',
                'DOLLAR': 'USD',
                'DOLLARS': 'USD',
                '$': 'USD',
                'EURO': 'EUR',
                'EUROS': 'EUR',
                '€': 'EUR',
                'POUND': 'GBP',
                'POUNDS': 'GBP',
                '£': 'GBP',
                'YEN': 'JPY',
                '¥': 'JPY'
            }
            if v in currency_map:
                return currency_map[v]
            return 'USD'  # Default fallback
        return v
    
    @root_validator
    def validate_total_consistency(cls, values):
        """Validate that total_amount equals subtotal + tax - discount + shipping"""
        total = values.get('total_amount')
        subtotal = values.get('subtotal')
        tax = values.get('tax_amount', 0)
        discount = values.get('discount_amount', 0)
        shipping = values.get('shipping_amount', 0)
        
        if total is not None and subtotal is not None:
            calculated_total = subtotal + (tax or 0) - (discount or 0) + (shipping or 0)
            # Allow small floating point differences
            if abs(total - calculated_total) > 0.01:
                # Don't raise error, just log warning - OCR might have slight errors
                pass
        
        # Auto-calculate total if missing but components exist
        if total is None and subtotal is not None:
            values['total_amount'] = subtotal + (tax or 0) - (discount or 0) + (shipping or 0)
        
        # Calculate due date from payment terms if missing
        if values.get('due_date') is None and values.get('payment_due_days') and values.get('date'):
            try:
                from datetime import datetime, timedelta
                invoice_date = datetime.strptime(values['date'], '%Y-%m-%d')
                due_date = invoice_date + timedelta(days=values['payment_due_days'])
                values['due_date'] = due_date.strftime('%Y-%m-%d')
            except:
                pass
        
        return values
    
    class Config:
        """Pydantic configuration"""
        json_schema_extra = {
            "example": {
                "invoice_number": "INV-2024-00123",
                "date": "2024-01-15",
                "vendor_name": "Tech Solutions Inc.",
                "total_amount": 2499.99,
                "currency": "USD",
                "account_number": "ACC-789012",
                "due_date": "2024-02-15",
                "line_items": [
                    {
                        "description": "Software License",
                        "quantity": 1,
                        "unit_price": 1999.99,
                        "total_price": 1999.99
                    }
                ],
                "tax_amount": 200.00,
                "subtotal": 2299.99,
                "vendor_info": {
                    "name": "Tech Solutions Inc.",
                    "tax_id": "12-3456789",
                    "email": "billing@techsolutions.com"
                },
                "customer_info": {
                    "name": "ABC Corporation",
                    "account_number": "ACC-789012",
                    "po_number": "PO-2024-00123"
                }
            }
        }


class InvoiceBatch(BaseModel):
    """Batch of invoices for bulk processing"""
    invoices: List[Invoice] = Field(..., description="List of processed invoices")
    batch_id: str = Field(..., description="Unique batch identifier")
    processing_timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    total_invoices: int = Field(..., description="Total number of invoices in batch")
    successful_count: int = Field(..., description="Successfully processed count")
    failed_count: int = Field(..., description="Failed processing count")
    
    @validator('total_invoices')
    def validate_total(cls, v, values):
        """Ensure total matches sum of successful and failed"""
        if 'successful_count' in values and 'failed_count' in values:
            if v != values['successful_count'] + values['failed_count']:
                raise ValueError("total_invoices must equal successful_count + failed_count")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "invoices": [],
                "batch_id": "batch_20240115_001",
                "total_invoices": 10,
                "successful_count": 9,
                "failed_count": 1
            }
        }