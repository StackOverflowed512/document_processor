"""Prompt templates for all pipeline phases"""

# Phase 2: Agentic Cleansing Prompt
CLEANSING_AGENT_PROMPT = """You are an intelligent data cleansing agent. Your task is to normalize raw extracted text into clean, structured business data.

## RAW EXTRACTED TEXT:
{raw_text}

## TASK:
1. Normalize field names to standard format:
   - "Acct #", "Account No.", "A/C Number" → "account_number"
   - "Inv #", "Invoice ID", "Invoice No." → "invoice_number"
   - "Vendor", "Supplier", "Seller" → "vendor_name"
   - "Total", "Amount Due", "Grand Total" → "total_amount"
   - "Date", "Invoice Date", "Issue Date" → "date"

2. Fix formatting:
   - Convert ALL dates to YYYY-MM-DD format
   - Convert currency values to float (remove $, commas)
   - Standardize currency codes (USD, EUR, GBP, etc.)

3. Remove noise and OCR errors:
   - Remove artifacts like "|", special characters
   - Fix common OCR mistakes (e.g., "0" vs "O", "1" vs "l")
   - Remove page headers/footers

4. Infer missing values if possible:
   - If currency missing, infer from context or default to USD
   - If account number missing, set to null (not placeholder)

## OUTPUT FORMAT (JSON only):
{{
  "normalized_fields": {{
    "invoice_number": "string or null",
    "date": "YYYY-MM-DD or null",
    "vendor_name": "string or null",
    "total_amount": float or null,
    "currency": "string or null",
    "account_number": "string or null",
    "due_date": "YYYY-MM-DD or null",
    "tax_amount": float or null,
    "subtotal": float or null
  }},
  "transformations_applied": ["list of changes made"],
  "inferred_fields": ["fields that were inferred"],
  "confidence": 0.95
}}

Return ONLY valid JSON, no other text."""

# Phase 3: JSON Structuring Prompt
STRUCTURING_PROMPT = """Convert the following cleaned business data into a strict JSON schema.

## CLEANED DATA:
{cleaned_data}

## REQUIRED SCHEMA:
{{
  "invoice_number": "string (required)",
  "date": "YYYY-MM-DD format (required)",
  "vendor_name": "string (required)",
  "total_amount": "float (required, positive)",
  "currency": "3-letter currency code (required)",
  "account_number": "string or null (optional)",
  "due_date": "YYYY-MM-DD or null",
  "line_items": "array of items or empty array",
  "tax_amount": "float or null",
  "subtotal": "float or null"
}}

## RULES:
1. All required fields must be present
2. Validate data types strictly
3. Ensure dates are in YYYY-MM-DD
4. Return ONLY valid JSON
5. Do not add extra fields not in schema

OUTPUT JSON:"""

# Vision Extraction Prompt (for VLM)
VISION_EXTRACTION_PROMPT = """Extract all visible text from this invoice document. 
Focus on:
- Invoice numbers
- Dates
- Vendor/customer names
- Amounts and currencies
- Account numbers
- Line items

Return the text exactly as you see it, preserving structure."""

# Fallback Extraction Instruction
OCR_FALLBACK_INSTRUCTION = "Extract text from image using OCR engine"