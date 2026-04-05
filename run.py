#!/usr/bin/env python3
"""
Entry point for the Invoice Processing System
"""

import uvicorn
import os
from app.config import settings

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║     Intelligent Document Processing Pipeline - v1.0.0       ║
    ║                                                              ║
    ║  Processing invoices, PDFs, and scanned documents with AI   ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    port = int(os.environ.get("PORT", 8000))
    is_production = os.environ.get("RENDER") == "true" or os.environ.get("ENVIRONMENT") == "production"
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=not is_production,
        log_level=settings.log_level.lower()
    )