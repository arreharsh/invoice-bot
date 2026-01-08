

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from datetime import datetime
import os


def format_indian_currency(amount):
    """
    Format number in Indian numbering system (lakhs, crores)
    Example: 1,23,456.78
    """
    s = f"{amount:,.2f}"
    parts = s.split('.')
    integer_part = parts[0].replace(',', '')
    
    if len(integer_part) > 3:
        last_three = integer_part[-3:]
        rest = integer_part[:-3]
        
        formatted = ''
        for i, digit in enumerate(reversed(rest)):
            if i > 0 and i % 2 == 0:
                formatted = ',' + formatted
            formatted = digit + formatted
        
        result = formatted + ',' + last_three
    else:
        result = integer_part
    
    return f"{result}.{parts[1]}"


def format_currency(amount, currency):
    """Format currency with proper symbol and numbering"""
    if currency == "INR":
        return f"INR {format_indian_currency(amount)}"
    else:
        return f"{currency} {amount:,.2f}"


def format_date(date_str):
    """Format date as DD MMM YYYY"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%d %b %Y')
    except:
        return date_str


def generate_pdf(data):
    """
    Generate invoice PDF from data dictionary
    
    Args:
        data (dict): Dictionary containing all invoice data
            Required keys: invoice_no, currency, invoice_date, due_date,
                          from_name, bill_to_name, items, tax, discount
            Optional keys: from_email, from_address, bill_to_email, 
                          bill_to_address, notes, is_bw
    
    Returns:
        str: Path to generated PDF file
    """
    
    # Create temp directory if it doesn't exist
    os.makedirs('temp', exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"temp/{data['invoice_no']}_{timestamp}.pdf"
    
    # Create PDF document
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    
    # Container for PDF elements
    elements = []
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Determine color scheme
    if data.get('is_bw', False):
        primary_color = colors.black
        bg_color = colors.Color(0.96, 0.96, 0.96)
    else:
        primary_color = colors.Color(0.114, 0.306, 0.847)  # Blue
        bg_color = colors.Color(0.937, 0.965, 1)  # Light blue
    
    # ===== TITLE =====
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=32,
        textColor=primary_color,
        spaceAfter=20,
        fontName='Helvetica-Bold'
    )
    elements.append(Paragraph("INVOICE", title_style))
    elements.append(Spacer(1, 10*mm))
    
    # ===== INVOICE INFO (Number, Date, Due Date) =====
    meta_data = [
        ['INVOICE NO.', '', 'DATE'],
        [data['invoice_no'], '', format_date(data['invoice_date'])],
        ['', '', ''],
        ['', '', 'DUE DATE'],
        ['', '', format_date(data['due_date'])]
    ]
    
    meta_table = Table(meta_data, colWidths=[60*mm, 50*mm, 60*mm])
    meta_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, 0), 'Helvetica-Bold'),
        ('FONTNAME', (2, 3), (2, 3), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (2, 3), (2, 3), 9),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.Color(0.4, 0.4, 0.4)),
        ('TEXTCOLOR', (2, 0), (2, 0), colors.Color(0.4, 0.4, 0.4)),
        ('TEXTCOLOR', (2, 3), (2, 3), colors.Color(0.4, 0.4, 0.4)),
        ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 1), (2, 1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 4), (2, 4), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
    ]))
    
    elements.append(meta_table)
    elements.append(Spacer(1, 10*mm))
    
    # ===== FROM & BILL TO =====
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4
    )
    
    # Build FROM text
    from_text = f"<b>FROM</b><br/><font size=12>{data['from_name']}</font>"
    if data.get('from_email'):
        from_text += f"<br/>{data['from_email']}"
    if data.get('from_address'):
        from_text += f"<br/>{data['from_address']}"
    
    # Build BILL TO text
    bill_to_text = f"<b>BILL TO</b><br/><font size=12>{data['bill_to_name']}</font>"
    if data.get('bill_to_email'):
        bill_to_text += f"<br/>{data['bill_to_email']}"
    if data.get('bill_to_address'):
        bill_to_text += f"<br/>{data['bill_to_address']}"
    
    contact_data = [[
        Paragraph(from_text, normal_style),
        Paragraph(bill_to_text, normal_style)
    ]]
    
    contact_table = Table(contact_data, colWidths=[85*mm, 85*mm])
    contact_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    elements.append(contact_table)
    elements.append(Spacer(1, 10*mm))
    
    # ===== ITEMS TABLE =====
    items_data = [['Description', 'Qty', 'Rate', 'Amount']]
    
    for item in data['items']:
        amount = item['qty'] * item['rate']
        items_data.append([
            item['description'],
            str(item['qty']),
            format_currency(item['rate'], data['currency']),
            format_currency(amount, data['currency'])
        ])
    
    items_table = Table(items_data, colWidths=[80*mm, 30*mm, 30*mm, 30*mm])
    items_table.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), bg_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        
        # Alignment
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        
        # Borders
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.Color(0.89, 0.91, 0.94)),
        ('LINEBELOW', (0, 1), (-1, -2), 0.5, colors.Color(0.89, 0.91, 0.94)),
    ]))
    
    elements.append(items_table)
    elements.append(Spacer(1, 8*mm))
    
    # ===== CALCULATIONS =====
    subtotal = sum(item['qty'] * item['rate'] for item in data['items'])
    discount_amount = subtotal * data['discount'] / 100
    tax_amount = (subtotal - discount_amount) * data['tax'] / 100
    total = subtotal - discount_amount + tax_amount
    
    # ===== TOTALS TABLE =====
    totals_data = [
        ['', '', 'Subtotal', format_currency(subtotal, data['currency'])],
    ]
    
    if data['discount'] > 0:
        totals_data.append([
            '', '', 
            f"Discount ({data['discount']}%)", 
            f"-{format_currency(discount_amount, data['currency'])}"
        ])
    
    totals_data.append([
        '', '', 
        f"Tax ({data['tax']}%)", 
        f"+{format_currency(tax_amount, data['currency'])}"
    ])
    
    totals_table = Table(totals_data, colWidths=[50*mm, 50*mm, 35*mm, 35*mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    
    elements.append(totals_table)
    elements.append(Spacer(1, 2*mm))
    
    # ===== TOTAL (Bold and highlighted) =====
    total_data = [['', '', 'Total', format_currency(total, data['currency'])]]
    total_table = Table(total_data, colWidths=[50*mm, 50*mm, 35*mm, 35*mm])
    total_table.setStyle(TableStyle([
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (2, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (2, 0), (-1, -1), 14),
        ('TEXTCOLOR', (2, 0), (-1, -1), primary_color),
        ('LINEABOVE', (2, 0), (-1, 0), 2, primary_color),
        ('TOPPADDING', (2, 0), (-1, -1), 8),
    ]))
    
    elements.append(total_table)
    
    # ===== NOTES (if provided) =====
    if data.get('notes'):
        elements.append(Spacer(1, 10*mm))
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Normal'],
            fontSize=9,
            fontName='Helvetica-Bold',
            spaceAfter=2
        )
        
        elements.append(Paragraph("<b>Notes</b>", heading_style))
        
        notes_style = ParagraphStyle(
            'NotesStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.Color(0.33, 0.33, 0.33)
        )
        
        elements.append(Paragraph(data['notes'], notes_style))
    
    # ===== BUILD PDF =====
    doc.build(elements)
    
    return filename


# For testing purposes
if __name__ == '__main__':
    # Test data
    test_data = {
        'invoice_no': 'INV-001',
        'currency': 'INR',
        'invoice_date': '2024-01-15',
        'due_date': '2024-02-15',
        'from_name': 'Test Company Pvt Ltd',
        'from_email': 'contact@testcompany.com',
        'from_address': 'Mumbai, Maharashtra, India',
        'bill_to_name': 'Client Corporation',
        'bill_to_email': 'client@example.com',
        'bill_to_address': 'Delhi, India',
        'items': [
            {'description': 'Web Development', 'qty': 1, 'rate': 50000},
            {'description': 'Logo Design', 'qty': 2, 'rate': 5000},
        ],
        'tax': 18,
        'discount': 10,
        'notes': 'Thank you for your business!',
        'is_bw': False
    }
    
    print("Generating test PDF...")
    pdf_path = generate_pdf(test_data)
    print(f"PDF generated: {pdf_path}")