#!/usr/bin/env python3
"""
Generate test invoice PDFs for testing the document processor
"""

from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from pathlib import Path
import sys


def create_invoice_pdf(filename: str, invoice_number: str = None):
    """
    Create a sample invoice PDF
    
    Args:
        filename: Output PDF filename
        invoice_number: Optional invoice number (auto-generated if not provided)
    """
    
    if invoice_number is None:
        invoice_number = f"INV-2026-{datetime.now().strftime('%m%d%H%M%S')}"
    
    # Create PDF document
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch,
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=6,
        alignment=1  # Center
    )
    elements.append(Paragraph("INVOICE", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Header Info
    header_data = [
        [f"Invoice #: {invoice_number}", f"Date: {datetime.now().strftime('%B %d, %Y')}"],
        [f"Due Date: {(datetime.now() + timedelta(days=30)).strftime('%B %d, %Y')}", "Account No: ACCT-2024-789"],
        [f"PO Number: PO-2024-5632", ""]
    ]
    
    header_table = Table(header_data, colWidths=[3.5*inch, 3.5*inch])
    header_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('LINEBELOW', (0, 0), (-1, -1), 1, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Vendor and Customer Info
    vendor_customer_data = [
        [
            Paragraph("<b>VENDOR</b><br/>TechCore Solutions Inc.<br/>456 Innovation Drive<br/>Suite 300<br/>San Jose, CA 95110<br/>Tax ID: 45-1234567<br/>contact@techcore.com", styles['Normal']),
            Paragraph("<b>CUSTOMER</b><br/>Global Industries Corp<br/>789 Enterprise Blvd<br/>Suite 200<br/>New York, NY 10001<br/>Tax ID: 12-9876543<br/>ap@globalind.com", styles['Normal'])
        ]
    ]
    
    vendor_table = Table(vendor_customer_data, colWidths=[3.5*inch, 3.5*inch])
    vendor_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, -1), 1, colors.lightgrey),
    ]))
    elements.append(vendor_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Line Items
    items_data = [
        ['Item #', 'Description', 'Quantity', 'Unit Price', 'Total'],
        ['1', 'Enterprise Cloud Platform - Annual License', '1', '$4,999.00', '$4,999.00'],
        ['2', 'Implementation & Training Services', '40', '$150.00', '$6,000.00'],
        ['3', 'Premium Support Package (12 months)', '1', '$2,500.00', '$2,500.00'],
        ['4', 'Data Migration & Integration', '80', '$200.00', '$16,000.00'],
        ['5', 'Security Audit & Compliance Report', '1', '$1,200.00', '$1,200.00'],
    ]
    
    items_table = Table(items_data, colWidths=[0.6*inch, 3*inch, 1*inch, 1.2*inch, 1.2*inch])
    items_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1f4788')),
        ('LINEBELOW', (0, -1), (-1, -1), 2, colors.HexColor('#1f4788')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Totals
    totals_data = [
        ['', '', 'Subtotal:', '$30,699.00'],
        ['', '', 'Tax (8.5%):', '$2,609.42'],
        ['', '', 'Shipping:', '$50.00'],
        ['', '', 'Discount (5%):', '-$1,535.00'],
        ['', '', 'GRAND TOTAL:', '$31,823.42'],
    ]
    
    totals_table = Table(totals_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    totals_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (2, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTSIZE', (2, -1), (-1, -1), 12),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (1, -1), 'RIGHT'),
        ('LINEABOVE', (2, -1), (-1, -1), 2, colors.HexColor('#1f4788')),
        ('LINEBELOW', (2, -1), (-1, -1), 2, colors.HexColor('#1f4788')),
        ('ROWBACKGROUNDS', (2, -1), (-1, -1), [colors.HexColor('#e8f0f8')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    elements.append(totals_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Terms
    terms_style = ParagraphStyle(
        'Terms',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=0
    )
    elements.append(Paragraph("<b>Payment Terms:</b> Net 30 days from invoice date", terms_style))
    elements.append(Paragraph("<b>Payment Method:</b> Bank Transfer or Credit Card", terms_style))
    elements.append(Paragraph("<b>Bank Details:</b> Chase Bank - Account: 9876543210 - Routing: 021000021", terms_style))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("<b>Notes:</b> Thank you for your business. Please contact us with any questions regarding this invoice.", terms_style))
    
    # Build PDF
    doc.build(elements)
    print(f"✓ PDF created: {filename}")


if __name__ == "__main__":
    # Create output directory if it doesn't exist
    test_dir = Path("tests")
    test_dir.mkdir(exist_ok=True)
    
    # Generate test PDFs
    try:
        create_invoice_pdf(str(test_dir / "test_invoice_1.pdf"), "INV-2026-0001")
        create_invoice_pdf(str(test_dir / "test_invoice_2.pdf"), "INV-2026-0002")
        create_invoice_pdf(str(test_dir / "test_invoice_3.pdf"), "INV-2026-0003")
        
        print("\n✓ All test PDFs generated successfully!")
        print(f"  Location: {test_dir.resolve()}")
        print("\nTo test the document processor:")
        print(f"  curl.exe -X POST \"http://localhost:8000/process\" -F \"file=@tests/test_invoice_1.pdf\"")
        
    except ImportError:
        print("ERROR: reportlab library not found!")
        print("\nInstall it with:")
        print("  pip install reportlab")
        sys.exit(1)
