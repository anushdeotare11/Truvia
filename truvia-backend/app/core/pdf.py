import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_report_pdf(report_data: dict) -> io.BytesIO:
    """
    Generates a high-quality PDF report for cybercrime evidence submission.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=colors.HexColor('#0B1E39'),
        spaceAfter=15
    )
    
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=colors.HexColor('#1959B8'),
        spaceBefore=15,
        spaceAfter=8,
        borderPadding=2
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#222222'),
        spaceAfter=10
    )

    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.HexColor('#555555')
    )

    code_style = ParagraphStyle(
        'Code',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#111111'),
        backColor=colors.HexColor('#F4F4F5'),
        borderColor=colors.HexColor('#E2E8F0'),
        borderWidth=1,
        borderPadding=10,
        spaceAfter=10
    )

    story = []

    # Title
    story.append(Paragraph("TRUVIA SAFETY REPORT", title_style))
    story.append(Paragraph("Court-Ready Cybercrime Evidence & Threat Assessment", body_style))
    story.append(Spacer(1, 15))

    # Metadata Table
    status_str = report_data.get("status", "N/A").upper()
    metadata = [
        [Paragraph("Ticket ID:", label_style), Paragraph(str(report_data.get("id", "N/A")), body_style)],
        [Paragraph("Source Ingest:", label_style), Paragraph(str(report_data.get("source_type", "N/A")).upper(), body_style)],
        [Paragraph("Detected Language:", label_style), Paragraph(str(report_data.get("detected_language", "N/A")).upper(), body_style)],
        [Paragraph("Ingested At:", label_style), Paragraph(str(report_data.get("created_at", "N/A")), body_style)],
        [Paragraph("Platform Status:", label_style), Paragraph(status_str, body_style)]
    ]
    
    t = Table(metadata, colWidths=[120, 380])
    t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0'))
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    # Threat Score section
    threat_score = report_data.get("threat_score")
    if threat_score is not None:
        story.append(Paragraph("AI Threat Assessment", section_heading))
        severity = report_data.get("severity_band", "low").upper()
        category = report_data.get("scam_category", "Unclassified")
        
        threat_data = [
            [Paragraph("Risk Score Value:", label_style), Paragraph(f"{threat_score} / 100", body_style)],
            [Paragraph("Risk Severity Band:", label_style), Paragraph(severity, body_style)],
            [Paragraph("Scam Pattern Category:", label_style), Paragraph(category, body_style)]
        ]
        tt = Table(threat_data, colWidths=[150, 350])
        tt.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(tt)
        story.append(Spacer(1, 15))

    # Extracted text section
    cleaned_text = report_data.get("cleaned_text", "")
    if cleaned_text:
        story.append(Paragraph("Verbatim Extracted Content", section_heading))
        story.append(Paragraph(cleaned_text, code_style))
        story.append(Spacer(1, 15))

    # Entities section
    entities = report_data.get("entities", [])
    if entities:
        story.append(Paragraph("Identified Threat Entities", section_heading))
        entity_rows = [[Paragraph("Type", label_style), Paragraph("Extracted Value", label_style)]]
        for ent in entities:
            entity_rows.append([
                Paragraph(str(ent.get("type", "")).upper(), body_style),
                Paragraph(str(ent.get("raw_value", "")), body_style)
            ])
        
        et = Table(entity_rows, colWidths=[150, 350])
        et.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F4F4F5')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0'))
        ]))
        story.append(et)
        
    doc.build(story)
    buffer.seek(0)
    return buffer
