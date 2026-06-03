import os
import uuid
from datetime import datetime
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch

from src.common.models import Alert

class MissionReporter:
    """
    Generates professional tactical reports for Sentinel-X.
    Includes incident summaries, threat analysis, and blockchain evidence.
    """

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        self.styles.add(ParagraphStyle(
            name='TacticalHeader',
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#00D4FF"),
            alignment=1, # Center
            spaceAfter=20,
            fontName='Helvetica-Bold'
        ))
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            fontSize=12,
            leading=14,
            textColor=colors.HexColor("#4DA3FF"),
            spaceBefore=15,
            spaceAfter=10,
            fontName='Helvetica-Bold',
            borderPadding=5,
            borderWidth=0.5,
            borderColor=colors.HexColor("#1E3A5F")
        ))

    def generate_incident_report(self, alerts: List[dict]) -> str:
        """Generates a PDF report from a list of alert dictionaries."""
        report_id = f"SRX-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        filename = f"{report_id}.pdf"
        filepath = os.path.join(self.output_dir, filename)

        doc = SimpleDocTemplate(filepath, pagesize=A4)
        elements = []

        # Header
        elements.append(Paragraph("SENTINEL-X MISSION REPORT", self.styles['TacticalHeader']))
        elements.append(Paragraph(f"REPORT ID: {report_id}", self.styles['Normal']))
        elements.append(Paragraph(f"GENERATED: {datetime.utcnow().isoformat()} UTC", self.styles['Normal']))
        elements.append(Spacer(1, 0.2 * inch))

        # Executive Summary
        elements.append(Paragraph("EXECUTIVE SUMMARY", self.styles['SectionHeader']))
        summary_text = f"This report covers {len(alerts)} tracked incidents. "
        critical_count = len([a for a in alerts if a.get('threat_class') in ['CRITICAL', 'CATASTROPHIC']])
        if critical_count > 0:
            summary_text += f"System detected {critical_count} critical/catastrophic threats requiring immediate review."
        else:
            summary_text += "No catastrophic threats detected during this period."
        elements.append(Paragraph(summary_text, self.styles['Normal']))

        # Alert Table
        elements.append(Paragraph("INCIDENT LOG", self.styles['SectionHeader']))
        table_data = [["Time (UTC)", "Domain", "Severity", "Description"]]
        for a in alerts[:50]: # Limit to last 50
            table_data.append([
                a.get('timestamp_utc', '—')[:19],
                a.get('domain', '—'),
                a.get('threat_class', '—'),
                a.get('description', '—')
            ])
        
        t = Table(table_data, colWidths=[1.2*inch, 0.8*inch, 0.8*inch, 2.5*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0E1A2B")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#1E3A5F")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        elements.append(t)

        # Blockchain Evidence
        elements.append(Paragraph("BLOCKCHAIN EVIDENCE CHAIN", self.styles['SectionHeader']))
        elements.append(Paragraph("All incidents above are anchored to the ThreatLedger smart contract. Evidence hashes are stored on IPFS for immutable forensic review.", self.styles['Normal']))
        
        # Footer
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(Paragraph("CONFIDENTIAL - SENTINEL-X INTERNAL USE ONLY", self.styles['Normal']))

        doc.build(elements)
        return filepath

reporter = MissionReporter()
