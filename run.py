#!/usr/bin/env python3
"""
Entry point for the Invoice Processing System
"""

import uvicorn
from app.config import settings

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║     Intelligent Document Processing Pipeline - v1.0.0       ║
    ║                                                              ║
    ║  Processing invoices, PDFs, and scanned documents with AI   ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower()
    )