"""Export utilities for generating reports in various formats."""
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image, HRFlowable
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from config.settings import EXPORT_DIR


class ReportExporter:
    """Handle exporting validation results in various formats."""
    
    def __init__(self):
        """Initialize exporter."""
        self.export_dir = EXPORT_DIR
        self.export_dir.mkdir(exist_ok=True)
    
    def export_to_pdf(
        self,
        results: Dict[str, Any],
        filename: str = None
    ) -> Path:
        """Export results to PDF format."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"validation_report_{timestamp}.pdf"
        
        filepath = self.export_dir / filename
        
        # Create PDF document with better formatting
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=36,
            title="Business Idea Validation Report",
            author="AI-Powered Kill Switch"
        )
        
        # Container for flowable objects
        elements = []
        styles = self._get_custom_styles()
        
        # Add title page
        self._add_title_page(elements, results, styles)
        
        # Add executive summary with metrics dashboard
        self._add_executive_summary(elements, results, styles)
        
        # Add table of contents
        elements.append(PageBreak())
        self._add_table_of_contents(elements, styles)
        
        # Pain Research Results
        if "pain_research" in results:
            elements.append(PageBreak())
            self._add_pain_research_section(elements, results["pain_research"], styles)
        
        # Market Analysis Results
        if "market_analysis" in results:
            elements.append(PageBreak())
            self._add_market_analysis_section(elements, results["market_analysis"], styles)
        
        # Content Generation Results
        if "content_generation" in results:
            elements.append(PageBreak())
            self._add_content_generation_section(elements, results["content_generation"], styles)
        
        # Survey Analysis Results
        if "survey_analysis" in results:
            elements.append(PageBreak())
            self._add_survey_analysis_section(elements, results["survey_analysis"], styles)
        
        # Final Recommendation
        elements.append(PageBreak())
        self._add_final_recommendation(elements, results, styles)
        
        # Build PDF
        doc.build(elements)
        
        return filepath
    
    def _get_custom_styles(self):
        """Create custom styles for the PDF."""
        styles = getSampleStyleSheet()
        
        # Title style
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Title'],
            fontSize=32,
            textColor=colors.HexColor('#FF4B4B'),
            spaceAfter=40,
            alignment=TA_CENTER
        ))
        
        # Subtitle style
        styles.add(ParagraphStyle(
            name='Subtitle',
            parent=styles['Heading2'],
            fontSize=18,
            textColor=colors.HexColor('#666666'),
            spaceAfter=20,
            alignment=TA_CENTER
        ))
        
        # Section header style
        styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#333333'),
            spaceAfter=20,
            borderWidth=0,
            borderPadding=0,
            borderColor=colors.HexColor('#FF4B4B'),
            borderRadius=0
        ))
        
        # Subsection style
        styles.add(ParagraphStyle(
            name='Subsection',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#444444'),
            spaceAfter=12,
            spaceBefore=12
        ))
        
        # Metric style
        styles.add(ParagraphStyle(
            name='Metric',
            parent=styles['Normal'],
            fontSize=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#333333')
        ))
        
        # Score style
        styles.add(ParagraphStyle(
            name='Score',
            parent=styles['Normal'],
            fontSize=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#FF4B4B'),
            fontName='Helvetica-Bold'
        ))
        
        return styles
    
    def _add_title_page(self, elements: List, results: Dict[str, Any], styles):
        """Add a professional title page."""
        # Add spacing
        elements.append(Spacer(1, 2*inch))
        
        # Title
        elements.append(Paragraph("Business Idea Validation Report", styles['CustomTitle']))
        elements.append(Spacer(1, 0.5*inch))
        
        # Problem statement
        problem = results.get("problem", "")
        if problem:
            elements.append(Paragraph(f"<i>{problem}</i>", styles['Subtitle']))
            elements.append(Spacer(1, 0.3*inch))
        
        # Target audience
        audience = results.get("target_audience", "")
        if audience:
            elements.append(Paragraph(f"Target Audience: {audience}", styles['Normal']))
            elements.append(Spacer(1, 1*inch))
        
        # Report metadata
        elements.append(HRFlowable(width="80%", thickness=1, color=colors.HexColor('#CCCCCC'), spaceBefore=10, spaceAfter=10))
        
        # Date
        elements.append(Paragraph(f"Report Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
        elements.append(Paragraph("Powered by AI-Powered Kill Switch", styles['Normal']))
    
    def _add_executive_summary(self, elements: List, results: Dict[str, Any], styles):
        """Add executive summary with metrics dashboard."""
        elements.append(PageBreak())
        elements.append(Paragraph("Executive Summary", styles['SectionHeader']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Overall recommendation
        summary = results.get("summary", {})
        recommendation = summary.get("recommendation", "UNKNOWN")
        
        if recommendation == "GO":
            rec_color = colors.green
            rec_text = "✅ GO - This idea shows strong potential"
        else:
            rec_color = colors.red
            rec_text = "❌ NO-GO - This idea needs significant refinement"
        
        rec_style = ParagraphStyle(
            'RecStyle',
            parent=styles['Normal'],
            fontSize=18,
            textColor=rec_color,
            alignment=TA_CENTER,
            spaceAfter=20
        )
        elements.append(Paragraph(rec_text, rec_style))
        
        # Reasoning
        if summary.get("reasoning"):
            elements.append(Paragraph(summary["reasoning"], styles['Normal']))
            elements.append(Spacer(1, 0.3*inch))
        
        # Metrics Dashboard
        elements.append(Paragraph("Key Metrics", styles['Subsection']))
        
        # Create metrics table
        metrics_data = []
        
        # Header row
        metrics_data.append(['Metric', 'Score', 'Status', 'Threshold'])
        
        # Viability Score
        viability = summary.get('viability_score', 0)
        metrics_data.append([
            'Overall Viability',
            f'{viability}/10',
            '✅ Pass' if viability >= 7 else '❌ Fail',
            '≥ 7/10'
        ])
        
        # Pain Score
        pain_score = results.get("pain_research", {}).get("pain_score", 0)
        metrics_data.append([
            'Pain Score',
            f'{pain_score}/10',
            '✅ Pass' if pain_score >= 7 else '❌ Fail',
            '≥ 7/10'
        ])
        
        # Market Opportunity
        opp_score = results.get("market_analysis", {}).get("opportunity_score", 0)
        metrics_data.append([
            'Market Opportunity',
            f'{opp_score}/10',
            '✅ Pass' if opp_score >= 6 else '❌ Fail',
            '≥ 6/10'
        ])
        
        # Conversion Rate
        conv_rate = results.get("content_generation", {}).get("predicted_conversion", 0) * 100
        metrics_data.append([
            'Predicted Conversion',
            f'{conv_rate:.1f}%',
            '✅ Pass' if conv_rate >= 2 else '❌ Fail',
            '≥ 2%'
        ])
        
        # Average WTP
        avg_wtp = results.get("survey_analysis", {}).get("avg_wtp", 0)
        metrics_data.append([
            'Average WTP',
            f'${avg_wtp}/mo',
            '✅ Pass' if avg_wtp >= 50 else '❌ Fail',
            '≥ $50/mo'
        ])
        
        # Create and style the table
        metrics_table = Table(metrics_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        metrics_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FF4B4B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data rows
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F8F8')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            
            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(metrics_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Strengths and Risks side by side
        if summary.get("strengths") or summary.get("risks"):
            strengths_risks_data = []
            strengths = summary.get("strengths", [])
            risks = summary.get("risks", [])
            
            # Create two columns
            strengths_text = "<b>✅ Strengths</b><br/><br/>"
            for strength in strengths[:5]:
                strengths_text += f"• {strength}<br/>"
            
            risks_text = "<b>⚠️ Risks</b><br/><br/>"
            for risk in risks[:5]:
                risks_text += f"• {risk}<br/>"
            
            sr_table = Table([[Paragraph(strengths_text, styles['Normal']), 
                             Paragraph(risks_text, styles['Normal'])]], 
                           colWidths=[3.5*inch, 3.5*inch])
            sr_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ]))
            
            elements.append(sr_table)
    
    def _add_table_of_contents(self, elements: List, styles):
        """Add table of contents."""
        elements.append(Paragraph("Table of Contents", styles['SectionHeader']))
        elements.append(Spacer(1, 0.3*inch))
        
        toc_items = [
            ("Executive Summary", "2"),
            ("Pain Research Analysis", "4"),
            ("Market Analysis", "5"),
            ("Content & Messaging", "6"),
            ("Survey Analysis", "7"),
            ("Final Recommendation", "8")
        ]
        
        for item, page in toc_items:
            toc_line = f'<para>{item}{"." * 50}{page}</para>'
            elements.append(Paragraph(toc_line, styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))
    
    def _add_pain_research_section(self, elements: List, data: Dict[str, Any], styles):
        """Add pain research section with better formatting."""
        elements.append(Paragraph("Pain Research Analysis", styles['SectionHeader']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Three-tier threshold evaluation if available
        if data.get('threshold_evaluations'):
            elements.append(Paragraph("Threshold Evaluation Results", styles['Subsection']))
            
            threshold_data = [['Threshold Level', 'Status', 'Complaints', 'Pain Score', 'Details']]
            
            for level in ['easy', 'medium', 'difficult']:
                eval_data = data['threshold_evaluations'].get(level, {})
                criteria = eval_data.get('criteria', {})
                
                level_names = {
                    'easy': '🟢 Easy (Market Exists)',
                    'medium': '🟡 Medium (Strong Opportunity)',
                    'difficult': '🔴 Difficult (Exceptional Problem)'
                }
                
                status = "✅ PASS" if eval_data.get('passed') else "❌ FAIL"
                complaints = f"{criteria.get('actual_complaints', 0)}/{criteria.get('complaints_required', 0)}"
                pain_score = f"{criteria.get('actual_pain_score', 0):.1f}/{criteria.get('pain_score_required', 0)}"
                
                details = ""
                if level == 'difficult':
                    details = f"Urgency: {criteria.get('actual_urgency', 0):.0f}%, Emotional: {criteria.get('actual_emotional', 0):.0f}%"
                
                threshold_data.append([level_names[level], status, complaints, pain_score, details])
            
            threshold_table = Table(threshold_data, colWidths=[2.2*inch, 0.8*inch, 1.2*inch, 1.2*inch, 2.1*inch])
            threshold_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            
            elements.append(threshold_table)
            elements.append(Spacer(1, 0.3*inch))
        
        # Complaint breakdown if available
        if data.get('complaint_breakdown'):
            elements.append(Paragraph("Complaint Quality Analysis", styles['Subsection']))
            
            breakdown = data['complaint_breakdown']
            quality_data = [
                ['Category', 'Count', 'Percentage'],
                ['🔴 High-Impact Complaints', str(breakdown.get('tier_3_high_impact', 0)), 
                 f"{(breakdown.get('tier_3_high_impact', 0) / max(breakdown.get('total_analyzed', 1), 1)) * 100:.1f}%"],
                ['🟡 Moderate Complaints', str(breakdown.get('tier_2_moderate', 0)),
                 f"{(breakdown.get('tier_2_moderate', 0) / max(breakdown.get('total_analyzed', 1), 1)) * 100:.1f}%"],
                ['🟢 Low-Value Signals', str(breakdown.get('tier_1_low_value', 0)),
                 f"{(breakdown.get('tier_1_low_value', 0) / max(breakdown.get('total_analyzed', 1), 1)) * 100:.1f}%"],
                ['⚪ Not Complaints', str(breakdown.get('tier_0_not_complaints', 0)),
                 f"{(breakdown.get('tier_0_not_complaints', 0) / max(breakdown.get('total_analyzed', 1), 1)) * 100:.1f}%"]
            ]
            
            quality_table = Table(quality_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
            quality_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F0F0')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            elements.append(quality_table)
            elements.append(Spacer(1, 0.3*inch))
        
        # Summary metrics
        metrics_table_data = [
            ['Pain Score', f"{data.get('pain_score', 0)}/10"],
            ['Weighted Complaints', str(data.get('weighted_complaint_score', 0))],
            ['Quality Rating', data.get('quality_metrics', {}).get('quality_rating', 'Unknown').upper()],
            ['Kill Decision', "Yes" if data.get('kill_decision') else "No"]
        ]
        
        metrics_table = Table(metrics_table_data, colWidths=[2*inch, 2*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F0F0F0')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(metrics_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Key themes
        if data.get('themes'):
            elements.append(Paragraph("Key Pain Themes", styles['Subsection']))
            for i, theme in enumerate(data['themes'][:5], 1):
                elements.append(Paragraph(f"{i}. {theme}", styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
        
        # Key quotes
        if data.get('key_quotes'):
            elements.append(Paragraph("Representative Quotes", styles['Subsection']))
            for quote in data['key_quotes'][:3]:
                quote_style = ParagraphStyle(
                    'Quote',
                    parent=styles['Normal'],
                    leftIndent=20,
                    rightIndent=20,
                    textColor=colors.HexColor('#555555'),
                    fontSize=10,
                    leading=14
                )
                # Handle both string quotes and dict quotes
                if isinstance(quote, dict):
                    quote_text = quote.get('text', quote.get('quote', str(quote)))
                    quote_source = quote.get('source', 'User')
                else:
                    quote_text = str(quote)
                    quote_source = 'User'
                
                elements.append(Paragraph(f'"{quote_text}"', quote_style))
                elements.append(Paragraph(f'<i>- {quote_source}</i>', quote_style))
                elements.append(Spacer(1, 0.1*inch))
    
    def _add_market_analysis_section(self, elements: List, data: Dict[str, Any], styles):
        """Add market analysis section with better formatting."""
        elements.append(Paragraph("Market Analysis", styles['SectionHeader']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Summary metrics
        avg_pricing = data.get('avg_pricing', {})
        metrics_table_data = [
            ['Opportunity Score', f"{data.get('opportunity_score', 0)}/10"],
            ['Competitors Found', str(data.get('competitors_found', 0))],
            ['Avg Monthly Price', f"${avg_pricing.get('monthly_average', 0)}"],
            ['Price Range', f"${avg_pricing.get('monthly_low', 0)} - ${avg_pricing.get('monthly_high', 0)}"]
        ]
        
        metrics_table = Table(metrics_table_data, colWidths=[2*inch, 2*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F0F0F0')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(metrics_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Top competitors
        if data.get('competitors'):
            elements.append(Paragraph("Top Competitors", styles['Subsection']))
            
            comp_data = [['Company', 'Pricing', 'Key Features']]
            for comp in data['competitors'][:5]:
                # Handle different competitor data formats
                if isinstance(comp, dict):
                    name = comp.get('name', 'Unknown')
                    pricing = comp.get('pricing', comp.get('price', 'N/A'))
                    features = comp.get('features', [])
                    if not isinstance(features, list):
                        features = [str(features)] if features else []
                else:
                    name = str(comp)
                    pricing = 'N/A'
                    features = []
                
                # Format pricing
                if pricing and pricing != 'N/A':
                    if isinstance(pricing, (int, float)):
                        pricing_str = f"${pricing}/mo"
                    else:
                        pricing_str = str(pricing)
                        if not pricing_str.startswith('$'):
                            pricing_str = f"${pricing_str}"
                else:
                    pricing_str = 'N/A'
                
                comp_data.append([
                    name,
                    pricing_str,
                    ', '.join(features[:3]) or 'N/A'
                ])
            
            comp_table = Table(comp_data, colWidths=[2*inch, 1.5*inch, 3.5*inch])
            comp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FF4B4B')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F8F8')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            elements.append(comp_table)
            elements.append(Spacer(1, 0.2*inch))
        
        # Market gaps
        if data.get('gaps'):
            elements.append(Paragraph("Market Gaps & Opportunities", styles['Subsection']))
            for gap in data['gaps'][:5]:
                elements.append(Paragraph(f"• {gap}", styles['Normal']))
    
    def _add_content_generation_section(self, elements: List, data: Dict[str, Any], styles):
        """Add content generation section."""
        elements.append(Paragraph("Content & Messaging", styles['SectionHeader']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Metrics
        conv_rate = data.get('predicted_conversion', 0) * 100
        metrics_table_data = [
            ['Predicted Conversion', f"{conv_rate:.1f}%"],
            ['Messaging Score', f"{data.get('messaging_score', 0)}/10"],
            ['Kill Decision', "Yes" if data.get('kill_decision') else "No"]
        ]
        
        metrics_table = Table(metrics_table_data, colWidths=[2*inch, 2*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F0F0F0')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(metrics_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Landing page preview
        landing_page = data.get('landing_page', {})
        if landing_page:
            elements.append(Paragraph("Landing Page Copy", styles['Subsection']))
            
            # Headline and subheadline
            if landing_page.get('headline'):
                headline_style = ParagraphStyle(
                    'Headline',
                    parent=styles['Normal'],
                    fontSize=16,
                    fontName='Helvetica-Bold',
                    spaceAfter=10
                )
                elements.append(Paragraph(landing_page['headline'], headline_style))
            
            if landing_page.get('subheadline'):
                elements.append(Paragraph(landing_page['subheadline'], styles['Normal']))
                elements.append(Spacer(1, 0.2*inch))
            
            # Benefits
            if landing_page.get('benefits'):
                elements.append(Paragraph("Key Benefits:", styles['Normal']))
                benefits = landing_page['benefits']
                if isinstance(benefits, list):
                    for benefit in benefits:
                        elements.append(Paragraph(f"✓ {benefit}", styles['Normal']))
                else:
                    elements.append(Paragraph(f"✓ {benefits}", styles['Normal']))
                elements.append(Spacer(1, 0.2*inch))
        
        # Improvement suggestions
        if data.get('improvement_suggestions'):
            elements.append(Paragraph("Improvement Suggestions", styles['Subsection']))
            for suggestion in data['improvement_suggestions'][:3]:
                elements.append(Paragraph(f"• {suggestion}", styles['Normal']))
    
    def _add_survey_analysis_section(self, elements: List, data: Dict[str, Any], styles):
        """Add survey analysis section."""
        elements.append(Paragraph("Survey Analysis", styles['SectionHeader']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Summary metrics
        metrics_table_data = [
            ['Average WTP', f"${data.get('avg_wtp', 0)}/month"],
            ['% Willing to Pay $50+', f"{data.get('percent_over_50', 0)}%"],
            ['Recommended Price', f"${data.get('recommended_price', 0)}/month"],
            ['Sample Size', str(data.get('sample_size', 0))]
        ]
        
        metrics_table = Table(metrics_table_data, colWidths=[2*inch, 2*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F0F0F0')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(metrics_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Price distribution
        if data.get('price_distribution'):
            elements.append(Paragraph("Price Point Distribution", styles['Subsection']))
            
            dist_data = [['Price Range', 'Percentage']]
            for range_name, percentage in data['price_distribution'].items():
                dist_data.append([range_name, f"{percentage}%"])
            
            dist_table = Table(dist_data, colWidths=[3*inch, 1.5*inch])
            dist_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FF4B4B')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F8F8')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            elements.append(dist_table)
            elements.append(Spacer(1, 0.2*inch))
        
        # Top requested features
        if data.get('top_features'):
            elements.append(Paragraph("Most Requested Features", styles['Subsection']))
            for i, feature in enumerate(data['top_features'][:5], 1):
                elements.append(Paragraph(f"{i}. {feature}", styles['Normal']))
    
    def _add_final_recommendation(self, elements: List, results: Dict[str, Any], styles):
        """Add final recommendation section."""
        elements.append(Paragraph("Final Recommendation", styles['SectionHeader']))
        elements.append(Spacer(1, 0.3*inch))
        
        summary = results.get('summary', {})
        recommendation = summary.get('recommendation', 'UNKNOWN')
        
        # Big decision box
        if recommendation == "GO":
            rec_bg_color = colors.HexColor('#E8F5E9')
            rec_border_color = colors.green
            rec_text = "✅ GO"
            rec_subtitle = "This idea shows strong potential and is worth pursuing"
        else:
            rec_bg_color = colors.HexColor('#FFEBEE')
            rec_border_color = colors.red
            rec_text = "❌ NO-GO"
            rec_subtitle = "This idea needs significant refinement before proceeding"
        
        # Create recommendation box
        rec_data = [[Paragraph(rec_text, ParagraphStyle(
            'RecText',
            fontSize=28,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            textColor=rec_border_color
        ))], [Paragraph(rec_subtitle, ParagraphStyle(
            'RecSub',
            fontSize=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#555555')
        ))]]
        
        rec_table = Table(rec_data, colWidths=[6*inch])
        rec_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), rec_bg_color),
            ('BOX', (0, 0), (-1, -1), 2, rec_border_color),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 20),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
        ]))
        
        elements.append(rec_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Detailed reasoning
        if summary.get('reasoning'):
            elements.append(Paragraph("Reasoning", styles['Subsection']))
            elements.append(Paragraph(summary['reasoning'], styles['Normal']))
            elements.append(Spacer(1, 0.3*inch))
        
        # Next steps
        if summary.get('next_steps'):
            elements.append(Paragraph("Recommended Next Steps", styles['Subsection']))
            for i, step in enumerate(summary['next_steps'], 1):
                elements.append(Paragraph(f"{i}. {step}", styles['Normal']))
                elements.append(Spacer(1, 0.05*inch))
    
    def export_to_csv(
        self,
        results: Dict[str, Any],
        filename: str = None
    ) -> Path:
        """Export results to CSV format."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"validation_data_{timestamp}.csv"
        
        filepath = self.export_dir / filename
        
        # Flatten the results for CSV format
        rows = []
        
        # Add summary row
        summary = results.get("summary", {})
        rows.append({
            "Section": "Summary",
            "Metric": "Overall Score",
            "Value": summary.get("viability_score", "N/A"),
            "Details": summary.get("recommendation", "")
        })
        
        # Add pain research metrics
        if "pain_research" in results:
            pain_data = results["pain_research"]
            rows.append({
                "Section": "Pain Research",
                "Metric": "Pain Score",
                "Value": pain_data.get("pain_score", "N/A"),
                "Details": f"Based on {pain_data.get('complaints_analyzed', 0)} complaints"
            })
            rows.append({
                "Section": "Pain Research",
                "Metric": "Is Urgent Problem",
                "Value": "Yes" if pain_data.get("is_urgent_problem") else "No",
                "Details": pain_data.get("analysis_summary", "")
            })
        
        # Add market analysis metrics
        if "market_analysis" in results:
            market_data = results["market_analysis"]
            rows.append({
                "Section": "Market Analysis",
                "Metric": "Average Pricing",
                "Value": f"${market_data.get('avg_pricing', {}).get('monthly_average', 0)}",
                "Details": f"Range: ${market_data.get('avg_pricing', {}).get('monthly_low', 0)}-${market_data.get('avg_pricing', {}).get('monthly_high', 0)}"
            })
            rows.append({
                "Section": "Market Analysis",
                "Metric": "Opportunity Score",
                "Value": market_data.get("opportunity_score", "N/A"),
                "Details": market_data.get("insights", "")
            })
        
        # Add survey metrics
        if "survey_analysis" in results:
            survey_data = results["survey_analysis"]
            rows.append({
                "Section": "Survey Analysis",
                "Metric": "Average WTP",
                "Value": f"${survey_data.get('avg_wtp', 0)}",
                "Details": f"{survey_data.get('percent_over_50', 0)}% willing to pay $50+"
            })
        
        # Write to CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ["Section", "Metric", "Value", "Details"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        return filepath
    
    def export_to_json(
        self,
        results: Dict[str, Any],
        filename: str = None
    ) -> Path:
        """Export results to JSON format."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"validation_results_{timestamp}.json"
        
        filepath = self.export_dir / filename
        
        # Add metadata
        export_data = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "version": "1.0"
            },
            "results": results
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return filepath


def create_summary_dataframe(results: Dict[str, Any]) -> pd.DataFrame:
    """Create a pandas DataFrame from validation results for analysis."""
    data = []
    
    # Extract key metrics
    if "pain_research" in results:
        pain = results["pain_research"]
        data.append({
            "Stage": "Pain Research",
            "Score": pain.get("pain_score", 0),
            "Pass/Fail": "Pass" if pain.get("is_urgent_problem") else "Fail",
            "Key Insight": pain.get("analysis_summary", "")[:100]
        })
    
    if "market_analysis" in results:
        market = results["market_analysis"]
        data.append({
            "Stage": "Market Analysis", 
            "Score": market.get("opportunity_score", 0),
            "Pass/Fail": "Pass" if market.get("opportunity_score", 0) >= 7 else "Fail",
            "Key Insight": market.get("insights", "")[:100]
        })
    
    if "content_generation" in results:
        content = results["content_generation"]
        data.append({
            "Stage": "Content Testing",
            "Score": content.get("predicted_conversion", 0) * 10,  # Convert percentage to score
            "Pass/Fail": "Pass" if content.get("predicted_conversion", 0) >= 0.02 else "Fail",
            "Key Insight": f"Predicted {content.get('predicted_conversion', 0)*100:.1f}% conversion"
        })
    
    if "survey_analysis" in results:
        survey = results["survey_analysis"]
        data.append({
            "Stage": "Survey Analysis",
            "Score": min(survey.get("avg_wtp", 0) / 10, 10),  # Convert WTP to score
            "Pass/Fail": "Pass" if survey.get("avg_wtp", 0) >= 50 else "Fail",
            "Key Insight": f"Avg WTP: ${survey.get('avg_wtp', 0)}"
        })
    
    return pd.DataFrame(data)