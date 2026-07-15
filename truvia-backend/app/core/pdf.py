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


def generate_case_pdf(case_data: dict) -> io.BytesIO:
    """
    Generates a comprehensive court-ready PDF package for a case.
    Includes 10 sections: Case Header, Timeline, Evidence, Extracted Entities,
    Threat Analysis, AI Explanation, Confidence Score, Linked Complaints,
    Related Fraud Ring, and Officer Notes.
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

    # Custom Styles (matching generate_report_pdf)
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

    # ─── Section 1: Case Header ───────────────────────────────────────
    story.append(Paragraph("TRUVIA COURT-READY CASE PACKAGE", title_style))
    story.append(Paragraph("Comprehensive Intelligence & Evidence Dossier", body_style))
    story.append(Spacer(1, 15))

    story.append(Paragraph("1. Case Header", section_heading))
    header_data = [
        [Paragraph("Case Number:", label_style), Paragraph(str(case_data.get("case_number", "N/A")), body_style)],
        [Paragraph("Priority:", label_style), Paragraph(str(case_data.get("priority", "N/A")).upper(), body_style)],
        [Paragraph("Case Type:", label_style), Paragraph(str(case_data.get("case_type", "N/A")), body_style)],
        [Paragraph("Created At:", label_style), Paragraph(str(case_data.get("created_at", "N/A")), body_style)],
        [Paragraph("Status:", label_style), Paragraph(str(case_data.get("status", "N/A")).upper(), body_style)],
        [Paragraph("Assigned Officer:", label_style), Paragraph(str(case_data.get("assigned_officer_name", "N/A")), body_style)],
    ]
    ht = Table(header_data, colWidths=[130, 370])
    ht.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0'))
    ]))
    story.append(ht)
    story.append(Spacer(1, 15))

    # ─── Section 2: Timeline ──────────────────────────────────────────
    story.append(Paragraph("2. Timeline", section_heading))
    timeline = case_data.get("timeline", [])
    if timeline:
        tl_rows = [[
            Paragraph("Timestamp", label_style),
            Paragraph("Event Type", label_style),
            Paragraph("Description", label_style),
        ]]
        for event in timeline:
            tl_rows.append([
                Paragraph(str(event.get("timestamp", "")), body_style),
                Paragraph(str(event.get("event_type", "")), body_style),
                Paragraph(str(event.get("description", "")), body_style),
            ])
        tl_table = Table(tl_rows, colWidths=[120, 100, 280])
        tl_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F4F4F5')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0'))
        ]))
        story.append(tl_table)
    else:
        story.append(Paragraph("No timeline events recorded.", body_style))
    story.append(Spacer(1, 15))

    # ─── Section 3: Evidence ──────────────────────────────────────────
    story.append(Paragraph("3. Evidence", section_heading))
    reports = case_data.get("reports", [])
    if reports:
        for i, report in enumerate(reports, 1):
            story.append(Paragraph(
                f"Evidence {i} — Report {report.get('id', 'N/A')} "
                f"[{str(report.get('source_type', 'unknown')).upper()}] "
                f"({report.get('created_at', 'N/A')})",
                label_style
            ))
            story.append(Spacer(1, 4))
            cleaned_text = report.get("cleaned_text", "No transcript available.")
            story.append(Paragraph(cleaned_text, code_style))
            story.append(Spacer(1, 8))
    else:
        story.append(Paragraph("No evidence reports linked to this case.", body_style))
    story.append(Spacer(1, 15))

    # ─── Section 4: Extracted Entities ────────────────────────────────
    story.append(Paragraph("4. Extracted Entities", section_heading))
    entities = case_data.get("entities", [])
    if entities:
        ent_rows = [[
            Paragraph("Type", label_style),
            Paragraph("Value", label_style),
            Paragraph("Risk Score", label_style),
            Paragraph("Risk Tier", label_style),
        ]]
        for ent in entities:
            ent_rows.append([
                Paragraph(str(ent.get("type", "")).upper(), body_style),
                Paragraph(str(ent.get("raw_value", "")), body_style),
                Paragraph(str(ent.get("risk_score", "N/A")), body_style),
                Paragraph(str(ent.get("risk_tier", "N/A")), body_style),
            ])
        ent_table = Table(ent_rows, colWidths=[80, 200, 80, 80])
        ent_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F4F4F5')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0'))
        ]))
        story.append(ent_table)
    else:
        story.append(Paragraph("No entities extracted.", body_style))
    story.append(Spacer(1, 15))

    # ─── Section 5: Threat Analysis ───────────────────────────────────
    story.append(Paragraph("5. Threat Analysis", section_heading))
    threat_scores = case_data.get("threat_scores", [])
    if threat_scores:
        ts_rows = [[
            Paragraph("Report ID", label_style),
            Paragraph("Threat Score", label_style),
            Paragraph("Severity", label_style),
            Paragraph("Scam Category", label_style),
        ]]
        for ts in threat_scores:
            ts_rows.append([
                Paragraph(str(ts.get("report_id", "N/A")), body_style),
                Paragraph(f"{ts.get('threat_score', 'N/A')} / 100", body_style),
                Paragraph(str(ts.get("severity_band", "N/A")).upper(), body_style),
                Paragraph(str(ts.get("scam_category", "N/A")), body_style),
            ])
        ts_table = Table(ts_rows, colWidths=[130, 90, 90, 190])
        ts_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F4F4F5')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0'))
        ]))
        story.append(ts_table)
    else:
        story.append(Paragraph("No threat scores available.", body_style))
    story.append(Spacer(1, 15))

    # ─── Section 6: AI Explanation ────────────────────────────────────
    story.append(Paragraph("6. AI Explanation", section_heading))
    if threat_scores:
        for ts in threat_scores:
            reasoning = ts.get("reasoning_json", {})
            if reasoning:
                report_id = ts.get("report_id", "N/A")
                story.append(Paragraph(f"Report: {report_id}", label_style))
                story.append(Spacer(1, 4))

                # Key Indicators
                key_indicators = reasoning.get("key_indicators", [])
                if key_indicators:
                    story.append(Paragraph("Key Indicators:", label_style))
                    for indicator in key_indicators:
                        story.append(Paragraph(f"  • {indicator}", body_style))

                # Risk Explanation
                risk_explanation = reasoning.get("risk_explanation", "")
                if risk_explanation:
                    story.append(Paragraph("Risk Explanation:", label_style))
                    story.append(Paragraph(risk_explanation, body_style))

                story.append(Spacer(1, 8))
    else:
        story.append(Paragraph("No AI reasoning data available.", body_style))
    story.append(Spacer(1, 15))

    # ─── Section 7: Confidence Score ──────────────────────────────────
    story.append(Paragraph("7. Confidence Score", section_heading))
    if threat_scores:
        conf_rows = [[
            Paragraph("Report ID", label_style),
            Paragraph("Confidence", label_style),
            Paragraph("Degraded Mode", label_style),
        ]]
        for ts in threat_scores:
            confidence = ts.get("confidence_score", "N/A")
            if isinstance(confidence, float):
                confidence_str = f"{confidence:.2f}"
            else:
                confidence_str = str(confidence)
            degraded = "Yes" if ts.get("degraded_mode", False) else "No"
            conf_rows.append([
                Paragraph(str(ts.get("report_id", "N/A")), body_style),
                Paragraph(confidence_str, body_style),
                Paragraph(degraded, body_style),
            ])
        conf_table = Table(conf_rows, colWidths=[200, 150, 150])
        conf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F4F4F5')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0'))
        ]))
        story.append(conf_table)
    else:
        story.append(Paragraph("No confidence scores available.", body_style))
    story.append(Spacer(1, 15))

    # ─── Section 8: Linked Complaints ─────────────────────────────────
    story.append(Paragraph("8. Linked Complaints", section_heading))
    linked_reports = case_data.get("linked_reports", [])
    if linked_reports:
        lr_rows = [[
            Paragraph("Report ID", label_style),
            Paragraph("Source Type", label_style),
            Paragraph("Created At", label_style),
        ]]
        for lr in linked_reports:
            lr_rows.append([
                Paragraph(str(lr.get("id", "N/A")), body_style),
                Paragraph(str(lr.get("source_type", "N/A")).upper(), body_style),
                Paragraph(str(lr.get("created_at", "N/A")), body_style),
            ])
        lr_table = Table(lr_rows, colWidths=[200, 130, 170])
        lr_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F4F4F5')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0'))
        ]))
        story.append(lr_table)
    else:
        story.append(Paragraph("No linked complaints.", body_style))
    story.append(Spacer(1, 15))

    # ─── Section 9: Related Fraud Ring ────────────────────────────────
    story.append(Paragraph("9. Related Fraud Ring", section_heading))
    fraud_ring = case_data.get("fraud_ring")
    if fraud_ring:
        story.append(Paragraph(f"Ring ID: {fraud_ring.get('ring_id', 'N/A')}", body_style))
        story.append(Paragraph(f"Member Count: {fraud_ring.get('member_count', 'N/A')}", body_style))
        story.append(Spacer(1, 6))

        ring_entities = fraud_ring.get("entities", [])
        if ring_entities:
            re_rows = [[
                Paragraph("Type", label_style),
                Paragraph("Value", label_style),
            ]]
            for re_ent in ring_entities:
                re_rows.append([
                    Paragraph(str(re_ent.get("type", "")).upper(), body_style),
                    Paragraph(str(re_ent.get("value", "")), body_style),
                ])
            re_table = Table(re_rows, colWidths=[150, 350])
            re_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F4F4F5')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0'))
            ]))
            story.append(re_table)
    else:
        story.append(Paragraph("None detected.", body_style))
    story.append(Spacer(1, 15))

    # ─── Section 10: Officer Notes ────────────────────────────────────
    story.append(Paragraph("10. Officer Notes", section_heading))
    story.append(Paragraph("(Space reserved for handwritten officer observations and notes)", body_style))
    story.append(Spacer(1, 10))
    # Draw horizontal lines as placeholders for handwritten notes
    for _ in range(8):
        note_line = Table([[""]],  colWidths=[500])
        note_line.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 18),
        ]))
        story.append(note_line)

    # AI Summary at the end (if available)
    ai_summary = case_data.get("ai_summary")
    if ai_summary:
        story.append(Spacer(1, 20))
        story.append(Paragraph("AI Case Summary", section_heading))
        story.append(Paragraph(ai_summary, body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer
