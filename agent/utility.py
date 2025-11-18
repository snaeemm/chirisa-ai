# utility.py - Report Generation and File Management Tools
import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Union, Dict, Any, List
from google.adk.tools import FunctionTool
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.colors import HexColor

from .models import ReportSchema, LocationContext
from .domain_models import (
    PowerInfrastructureOutput, NetworkConnectivityOutput, ClimateAnalysisOutput,
    SiteCivilInfrastructureOutput, MechanicalThermalOutput,
    RegulatoryESGOutput, MarketCompetitionOutput,
    RichSection, extract_metrics_for_tables
)

# ================================================================================================
# TEXT PROCESSING UTILITIES
# ================================================================================================

def _get_verification_badge_text(verification_level: str) -> str:
    """Get text representation of verification level for PDF"""
    badge_text = {
        "verified_by_public_source": "✓ Verified by Public Source",
        "verified_by_transactional": "✓✓ Investment-Grade",
        "model_inference": "⚠ Model Inference - Needs Validation",
        "unknown_requires_utility_letter": "⚠ Unknown - Requires Utility Letter",
        "assumption_based_on_region": "~ Regional Assumption"
    }
    return badge_text.get(verification_level, verification_level)

def clean_markdown_text(text: str) -> str:
    """Remove markdown formatting artifacts from text"""
    if not text:
        return text

    # Remove bold markdown (**text** or __text__) - handle edge cases
    text = re.sub(r'\*\*([^*]*?)\*\*', r'\1', text)
    text = re.sub(r'__([^_]*?)__', r'\1', text)

    # Handle incomplete bold markdown (e.g., "**text:" without closing **)
    text = re.sub(r'\*\*([^*]+):', r'\1:', text)
    text = re.sub(r'__([^_]+):', r'\1:', text)

    # Remove italic markdown (*text* or _text_)
    text = re.sub(r'\*([^*]*?)\*', r'\1', text)
    text = re.sub(r'_([^_]*?)_', r'\1', text)

    # Remove code markdown (`text`)
    text = re.sub(r'`([^`]*?)`', r'\1', text)

    # Remove header markdown (# ## ###)
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)

    # Remove remaining stray markdown characters
    text = re.sub(r'[*_`#]+', '', text)

    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def format_section_name(section_name: str) -> str:
    """Convert snake_case section names to proper Title Case"""
    if not section_name:
        return section_name

    # Convert snake_case to Title Case
    formatted = section_name.replace('_', ' ').title()

    # Handle special cases
    replacements = {
        'Esg': 'ESG',
        'Ai': 'AI',
        'Ml': 'ML',
        'Ai Ml': 'AI/ML',
        'Eia': 'EIA',
        'Pue': 'PUE',
        'Saidi': 'SAIDI',
        'Saifi': 'SAIFI',
        'Ppa': 'PPA',
        'Ixp': 'IXP',
        'Cdn': 'CDN',
        'Gdpr': 'GDPR',
        'Sez': 'SEZ',
        'Co2': 'CO2',
        'Ghg': 'GHG'
    }

    for old, new in replacements.items():
        formatted = formatted.replace(old, new)

    return formatted

def round_numeric_value(value: Union[float, int, str]) -> Union[float, int, str]:
    """Round numeric values to appropriate decimal places"""
    if isinstance(value, (int, float)):
        # Round scores and percentages to 1 decimal place
        if 0 <= value <= 5 or 0 <= value <= 100:
            return round(value, 1)
        # Round large numbers to whole numbers
        elif value >= 1000:
            return round(value)
        # Round small decimals to 2 decimal places
        else:
            return round(value, 2)
    return value


def calculate_optimal_cell_width(content: str, base_width: float, max_width: float) -> float:
    """Calculate optimal cell width based on content length"""
    if not content:
        return base_width

    content_length = len(str(content))
    # Use character count to estimate width (rough approximation)
    estimated_width = content_length * 6  # pixels per character

    # Convert to inches (approximate)
    estimated_inches = estimated_width / 72.0

    # Return width within bounds
    return min(max(base_width, estimated_inches), max_width)

def format_table_cell_content(content: str, max_width_chars: int = 25) -> str:
    """Format table cell content with simple character-based line breaking"""
    if not content:
        return content

    # Ensure content is string and properly encoded
    content = str(content)

    # Remove any non-printable characters that could cause display issues
    import re
    content = re.sub(r'[^\x20-\x7E\n\r\t]', '', content)

    # Clean markdown first
    content = clean_markdown_text(content)

    # Simple approach: if text is longer than threshold, break at word boundaries
    if len(content) <= max_width_chars:
        return content

    # Break at word boundaries
    words = content.split()
    lines = []
    current_line = ""

    for word in words:
        # If adding this word would exceed width, start new line
        if current_line and len(current_line + " " + word) > max_width_chars:
            lines.append(current_line)
            current_line = word
        else:
            current_line = (current_line + " " + word) if current_line else word

    # Add remaining content
    if current_line:
        lines.append(current_line)

    return "\n".join(lines)


# Report directory path - using pathlib and environment variable
REPORTS_DIR = Path(os.getenv('REPORTS_OUTPUT_DIR', 'agent/Reports')).resolve()

# ================================================================================================
# DYNAMIC PHASE 1 DEPLOYMENT PLAN GENERATOR
# ================================================================================================

def generate_dynamic_phase1_plan(location_context: LocationContext, power_result: PowerInfrastructureOutput, network_result: NetworkConnectivityOutput, climate_result: ClimateAnalysisOutput,
                                regulatory_esg_result: RegulatoryESGOutput, site_civil_result=None, mechanical_thermal_result=None, market_competition_result=None, composite_score: float = 3.0):
    """Simple fallback Phase 1 plan - will be replaced by insights_agent.py"""
    from .models import Phase1Deployment

    try:
        # Simple capacity determination
        if composite_score >= 4.0:
            capacity = "100-150 MW initial deployment with campus expansion potential"
            investment = "$400-600 million USD Phase 1"
            timeline = "18-24 months for Phase 1"
        elif composite_score >= 3.0:
            capacity = "50-100 MW initial deployment with scalability planning"
            investment = "$200-400 million USD Phase 1"
            timeline = "24-30 months for Phase 1"
        else:
            capacity = "25-50 MW pilot deployment with assessment period"
            investment = "$100-200 million USD pilot phase"
            timeline = "30-36 months for Phase 1"

        return Phase1Deployment(
            recommended_capacity=capacity,
            timeline=timeline,
            priority_actions=[
                "Site acquisition and grid interconnection planning",
                "Comprehensive permitting and regulatory approvals",
                "Detailed engineering design and equipment procurement",
                "Construction management and infrastructure development",
                "Installation, testing, and commissioning of critical systems"
            ],
            estimated_investment=investment,
            risk_mitigation=[
                "Power resilience with redundant systems",
                "Network redundancy with multiple carriers",
                "Phased deployment with milestone gates",
                "Comprehensive insurance coverage",
                "Supply chain risk management"
            ]
        )

    except Exception as e:
        print(f"⚠️ Error in fallback Phase 1 plan: {e}")
        return Phase1Deployment(
            recommended_capacity="50-100 MW initial deployment",
            timeline="24-30 months for Phase 1",
            priority_actions=["Site planning", "Permitting", "Design", "Construction", "Commissioning"],
            estimated_investment="$200-400 million USD",
            risk_mitigation=["Power backup", "Network redundancy", "Phased approach", "Insurance", "Risk monitoring"]
        )

def save_report_schema(report: ReportSchema) -> dict:
    """Save ReportSchema to JSON file using Pydantic model.

    Args:
        report: ReportSchema Pydantic model instance

    Returns:
        dict: Contains status and file_path
    """
    try:
        print(f"🔧 DEBUG: save_report_schema called with location='{report.location}'")

        # Ensure reports directory exists using pathlib
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_location = "".join(c for c in report.location if c.isalnum() or c in (' ', '_', '-')).strip()
        safe_location = safe_location.replace(' ', '_')
        filename = f"datacenter_analysis_{safe_location}_{timestamp}.json"
        file_path = REPORTS_DIR / filename

        # Use Pydantic's model_dump for JSON serialization
        report_dict = report.model_dump()

        # Save JSON file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        print(f"✅ JSON report saved successfully: {file_path}")


        return {
            "status": "success",
            "message": f"JSON report saved successfully",
            "file_path": str(file_path)
        }

    except Exception as e:
        print(f"❌ Error saving JSON report: {e}")
        return {
            "status": "error",
            "message": f"Failed to save JSON report: {str(e)}"
        }

def save_json_report(report: ReportSchema, location_name: str) -> dict:
    """Save JSON report from ReportSchema Pydantic model.

    Args:
        report: The ReportSchema Pydantic model instance
        location_name: Name of the location for file naming

    Returns:
        dict: Contains status and file_path
    """
    print(f"🔧 DEBUG: save_json_report called with location_name='{location_name}'")
    print(f"🔧 DEBUG: report type: {type(report)} (ReportSchema Pydantic model)")

    # Validation is handled by Pydantic model - no manual validation needed
    report_data = report.model_dump()  # Convert to dict for JSON serialization
    print(f"🔧 DEBUG: report_data keys: {list(report_data.keys())}")

    try:
        print(f"🔧 DEBUG: Starting file save process...")
        print(f"🔧 DEBUG: Reports directory: {REPORTS_DIR}")

        # Ensure reports directory exists using pathlib
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"🔧 DEBUG: Reports directory created/verified: {REPORTS_DIR.exists()}")

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_location = "".join(c for c in location_name if c.isalnum() or c in (' ', '-', '_')).replace(' ', '_')
        filename = f"{clean_location}_{timestamp}.json"
        file_path = REPORTS_DIR / filename
        print(f"🔧 DEBUG: Attempting to save to: {file_path}")

        # Save JSON report using Pydantic's model_dump
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        print(f"🔧 DEBUG: JSON data written to file")

        # Verify file was created
        if not file_path.exists():
            raise Exception(f"File was not created at {file_path}")

        file_size = file_path.stat().st_size
        print(f"🔧 DEBUG: File verification successful - size: {file_size} bytes")

        result = {
            "status": "success",
            "file_path": str(file_path),
            "filename": filename,
            "message": f"JSON report saved successfully to {file_path}"
        }
        print(f"✅ DEBUG: JSON save completed successfully: {filename}")



        return result
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"Failed to save JSON report: {str(e)}"
        }
        print(f"⚠️  Error saving JSON report: {str(e)}")
        return error_result

# ================================================================================================
# ENHANCED REPORT GENERATION WITH DOMAIN-SPECIFIC DATA SUPPORT
# ================================================================================================

def create_metrics_table(rich_section: RichSection, section_name: str) -> Union[Table, None]:
    """Create a formatted table from RichSection metrics data with simple fixed column widths"""
    try:
        metrics_data = extract_metrics_for_tables(rich_section)
        if not metrics_data:
            return None

        # Create table data with metric names and values
        table_data = [['Metric', 'Value']]  # Header row

        for metric_name, metric_value in metrics_data.items():
            # Format metric name using utility function and simple line breaking
            formatted_name = format_section_name(metric_name)
            wrapped_name = format_table_cell_content(formatted_name, max_width_chars=25)

            # Format metric value - handle numbers and clean text
            if isinstance(metric_value, (int, float)):
                formatted_value = str(round_numeric_value(metric_value))
            else:
                formatted_value = format_table_cell_content(str(metric_value), max_width_chars=50)

            table_data.append([wrapped_name, formatted_value])

        if len(table_data) <= 1:  # Only header row
            return None

        # Simple fixed column widths - no complex calculations
        col1_width = 2.2 * inch  # Fixed width for metric names
        col2_width = 3.3 * inch  # Fixed width for values

        metrics_table = Table(table_data, colWidths=[col1_width, col2_width])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#4a90e2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), HexColor('#f9f9f9')),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('WORDWRAP', (0, 0), (-1, -1), True),
            ('ROWHEIGHT', (0, 0), (-1, -1), None),  # Allow auto row height
            ('SPLITLONGWORDS', (0, 0), (-1, -1), True),
            ('LEADING', (0, 1), (-1, -1), 10)
        ]))

        return metrics_table

    except Exception as e:
        print(f"⚠️ Error creating metrics table for {section_name}: {e}")
        return None

def render_rich_section(rich_section: RichSection, story: List, styles: Dict, section_name: str):
    """Render a RichSection with enhanced formatting and metrics tables"""
    try:
        # Section title with proper formatting
        if rich_section.name:
            clean_name = clean_markdown_text(rich_section.name)
            story.append(Paragraph(f"<b>{clean_name}:</b>", styles['Normal']))

        # Section content with markdown cleaning
        if rich_section.content and rich_section.content.strip():
            clean_content = clean_markdown_text(rich_section.content)
            story.append(Paragraph(clean_content, styles['Normal']))
            story.append(Spacer(1, 8))

        # Key points if available
        if rich_section.key_points:
            story.append(Paragraph("<b>Key Points:</b>", styles['Normal']))
            for point in rich_section.key_points:
                clean_point = clean_markdown_text(point)
                story.append(Paragraph(f"• {clean_point}", styles['Normal']))
            story.append(Spacer(1, 8))

        # Verification metadata if available
        if hasattr(rich_section, 'verification_metadata') and rich_section.verification_metadata:
            story.append(Paragraph("<b>Verification Status:</b>", styles['Normal']))
            for claim, verification_level in rich_section.verification_metadata.items():
                badge_text = _get_verification_badge_text(verification_level)
                claim_display = claim.replace("_", " ").title()
                story.append(Paragraph(f"• <b>{claim_display}:</b> {badge_text}", styles['Normal']))
            story.append(Spacer(1, 8))

        # Metrics table if available
        metrics_table = create_metrics_table(rich_section, section_name)
        if metrics_table:
            formatted_section_name = format_section_name(section_name)
            story.append(Paragraph(f"<b>{formatted_section_name} Metrics:</b>", styles['Normal']))
            story.append(Spacer(1, 4))
            story.append(metrics_table)
            story.append(Spacer(1, 8))

        # Custom tables if available
        if rich_section.tables:
            for table_data in rich_section.tables:
                if isinstance(table_data, dict) and 'data' in table_data:
                    table_title = clean_markdown_text(table_data.get('title', 'Data Table'))
                    story.append(Paragraph(f"<b>{table_title}:</b>", styles['Normal']))
                    # Create table from nested data structure
                    # This would need to be customized based on specific table formats
                    story.append(Spacer(1, 8))

        # Sub-score with proper rounding
        if rich_section.sub_score > 0:
            rounded_score = round_numeric_value(rich_section.sub_score)
            story.append(Paragraph(f"<i>Section Score: {rounded_score}/5.0</i>", styles['Normal']))

        story.append(Spacer(1, 12))

    except Exception as e:
        print(f"⚠️ Error rendering rich section {section_name}: {e}")
        # Fallback to basic rendering
        if rich_section.content:
            clean_content = clean_markdown_text(rich_section.content)
            story.append(Paragraph(clean_content, styles['Normal']))
            story.append(Spacer(1, 8))

def render_domain_specific_analysis(domain_output: Union[
    PowerInfrastructureOutput, NetworkConnectivityOutput, ClimateAnalysisOutput,
    SiteCivilInfrastructureOutput, MechanicalThermalOutput,
    RegulatoryESGOutput, MarketCompetitionOutput
], story: List, styles: Dict, domain_name: str):
    """Render domain-specific analysis with rich structured data"""

    try:
        # Executive summary
        if domain_output.executive_summary and domain_output.executive_summary.strip():
            story.append(Paragraph(domain_output.executive_summary, styles['Normal']))
            story.append(Spacer(1, 10))

        # Render all RichSection attributes
        for attr_name in dir(domain_output):
            attr_value = getattr(domain_output, attr_name)
            if isinstance(attr_value, RichSection):
                render_rich_section(attr_value, story, styles, attr_name)

        # Key Assumptions
        if domain_output.assumptions:
            story.append(Paragraph("<b>Key Assumptions:</b>", styles['Normal']))
            for assumption in domain_output.assumptions:
                story.append(Paragraph(f"• {assumption}", styles['Normal']))
            story.append(Spacer(1, 10))

        # Key Insights
        if domain_output.key_insights:
            story.append(Paragraph("<b>Key Insights:</b>", styles['Normal']))
            for insight in domain_output.key_insights:
                clean_insight = clean_markdown_text(insight)
                story.append(Paragraph(f"• {clean_insight}", styles['Normal']))
            story.append(Spacer(1, 10))

    except Exception as e:
        print(f"⚠️ Error rendering domain-specific analysis for {domain_name}: {e}")
        # Fallback to executive summary only
        if hasattr(domain_output, 'executive_summary') and domain_output.executive_summary:
            story.append(Paragraph(domain_output.executive_summary, styles['Normal']))
            story.append(Spacer(1, 10))

def render_domain_specific_rich_sections(domain_output: Any, story: List, styles: Dict, domain_name: str, rich_section_attributes: List):
    """Render domain-specific analysis using detected RichSection attributes from JSON"""

    try:
        # Executive summary
        if hasattr(domain_output, 'executive_summary') and domain_output.executive_summary and domain_output.executive_summary.strip():
            story.append(Paragraph(domain_output.executive_summary, styles['Normal']))
            story.append(Spacer(1, 10))

        # Render each detected RichSection
        for section_name, section_obj in rich_section_attributes:
            print(f"  📋 Rendering RichSection: {section_name}")
            render_rich_section(section_obj, story, styles, section_name)

        # Key Assumptions
        if hasattr(domain_output, 'assumptions') and domain_output.assumptions:
            story.append(Paragraph("<b>Key Assumptions:</b>", styles['Normal']))
            for assumption in domain_output.assumptions:
                story.append(Paragraph(f"• {assumption}", styles['Normal']))
            story.append(Spacer(1, 10))

        # Key Insights
        if hasattr(domain_output, 'key_insights') and domain_output.key_insights:
            story.append(Paragraph("<b>Key Insights:</b>", styles['Normal']))
            for insight in domain_output.key_insights:
                clean_insight = clean_markdown_text(insight)
                story.append(Paragraph(f"• {clean_insight}", styles['Normal']))
            story.append(Spacer(1, 10))

    except Exception as e:
        print(f"⚠️ Error rendering domain-specific rich sections for {domain_name}: {e}")
        print(f"   Available attributes: {[attr for attr, _ in rich_section_attributes]}")
        # Fallback to executive summary only
        if hasattr(domain_output, 'executive_summary') and domain_output.executive_summary:
            story.append(Paragraph(domain_output.executive_summary, styles['Normal']))
            story.append(Spacer(1, 10))


def generate_pdf_report(report: ReportSchema, location_name: str) -> dict:
    """Generate PDF report from ReportSchema Pydantic model.

    Args:
        report: The ReportSchema Pydantic model instance
        location_name: Name of the location for file naming

    Returns:
        dict: Contains status and file_path
    """
    print(f"🔧 DEBUG: generate_pdf_report called with location_name='{location_name}'")
    print(f"🔧 DEBUG: report type: {type(report)} (ReportSchema Pydantic model)")

    # Validation is handled by Pydantic model - no manual validation needed
    report_data = report.model_dump()  # Convert to dict for PDF generation
    print(f"🔧 DEBUG: report_data keys: {list(report_data.keys())}")

    try:
        print(f"🔧 DEBUG: Starting PDF generation process...")
        print(f"🔧 DEBUG: Reports directory: {REPORTS_DIR}")

        # Ensure reports directory exists using pathlib
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"🔧 DEBUG: Reports directory created/verified: {REPORTS_DIR.exists()}")

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_location = "".join(c for c in location_name if c.isalnum() or c in (' ', '-', '_')).replace(' ', '_')
        filename = f"{clean_location}_{timestamp}.pdf"
        file_path = REPORTS_DIR / filename
        print(f"🔧 DEBUG: Attempting to save PDF to: {file_path}")

        # Create PDF document
        doc = SimpleDocTemplate(str(file_path), pagesize=A4, topMargin=0.8*inch)
        print(f"🔧 DEBUG: PDF document object created")
        story = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=HexColor('#1f4e79'),
            alignment=1,  # Center
            spaceAfter=30
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=HexColor('#2e75b6'),
            spaceBefore=20,
            spaceAfter=10
        )

        # Domain subsection style (defined once)
        domain_subsection_style = ParagraphStyle(
            'DomainSubsection',
            parent=styles['Heading3'],
            fontSize=14,
            textColor=HexColor('#2e75b6'),
            spaceBefore=15,
            spaceAfter=8
        )

        # Title
        title = f"Data Center Site Analysis Report"
        story.append(Paragraph(title, title_style))

        # Location info - direct access to Pydantic model attributes
        location_text = f"<b>Location:</b> {report.location}<br/>"
        location_text += f"<b>Coordinates:</b> {report.coordinates.get('lat', 'N/A')}, {report.coordinates.get('lng', 'N/A')}<br/>"
        location_text += f"<b>Country:</b> {report.country}<br/>"
        location_text += f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        story.append(Paragraph(location_text, styles['Normal']))
        story.append(Spacer(1, 20))

        # Executive Summary
        story.append(Paragraph("Executive Summary", heading_style))

        # Use the insights agent's location_overview directly
        if hasattr(report.executive_summary, 'location_overview') and report.executive_summary.location_overview:
            exec_summary = report.executive_summary.location_overview
        else:
            exec_summary = f"Analysis for {report.location} data center deployment."

        story.append(Paragraph(exec_summary, styles['Normal']))
        story.append(Spacer(1, 20))

        # Overall Suitability
        story.append(Paragraph("Overall Suitability Assessment", heading_style))

        # Round the composite score for display
        rounded_score = round_numeric_value(report.overall_suitability.composite_score)

        overall_data = [
            ['Metric', 'Value'],
            ['Composite Score', f"{rounded_score}/5.0"],
            ['Rating', report.overall_suitability.rating],
            ['Recommendation', format_table_cell_content(report.overall_suitability.recommendation, max_width_chars=80)]
        ]

        # Adaptive column sizing for overall table
        total_width = 5.5 * inch
        # Calculate optimal widths based on content
        max_metric_width = max(len(row[0]) for row in overall_data) * 8  # Rough character width estimation

        col1_width = min(max(total_width * 0.3, max_metric_width / 72), total_width * 0.4)
        col2_width = total_width - col1_width

        overall_table = Table(overall_data, colWidths=[col1_width, col2_width])
        overall_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2e75b6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),  # Add horizontal padding
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),  # Add horizontal padding
            ('BACKGROUND', (0, 1), (-1, -1), HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#dee2e6')),  # Reduced grid line thickness
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('WORDWRAP', (0, 0), (-1, -1), True)
        ]))

        story.append(overall_table)
        story.append(Spacer(1, 20))

        # Domain Analysis
        story.append(Paragraph("Domain Analysis Scores", heading_style))

        domain_analysis = report.domain_analysis
        domain_data = [['Domain', 'Score', 'Summary']]

        domain_mapping = {
            'power_infrastructure': 'Power Infrastructure',
            'network_connectivity': 'Network Connectivity',
            'climate_environmental': 'Climate Suitability',
            'site_civil': 'Site & Civil',
            'mechanical_thermal': 'Mechanical & Thermal',
            'regulatory_esg': 'Regulatory & ESG',
            'market_competition': 'Market & Competition'
        }

        for key, display_name in domain_mapping.items():
            domain_info = domain_analysis.get(key)
            if domain_info:
                rounded_domain_score = round_numeric_value(domain_info.score)
                # Use Paragraph object for proper text wrapping
                clean_summary = clean_markdown_text(domain_info.summary)
                summary_paragraph = Paragraph(clean_summary, styles['Normal'])
                domain_data.append([display_name, f"{rounded_domain_score}/5.0", summary_paragraph])
            else:
                domain_data.append([display_name, "N/A", "N/A"])

        # Standard column sizing for domain table
        total_width = 5.5 * inch  # Standard page width
        col1_width = 1.5 * inch   # Domain names
        col2_width = 0.7 * inch   # Scores (e.g., "4.5/5.0")
        col3_width = 3.3 * inch   # Summary text (controlled by truncation)

        domain_table = Table(domain_data, colWidths=[col1_width, col2_width, col3_width])
        domain_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2e75b6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),  # Standardized header font size
            ('FONTSIZE', (0, 1), (-1, -1), 9),  # Standardized body font size
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 8),  # Increased top padding
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),  # Increased bottom padding
            ('LEFTPADDING', (0, 0), (-1, -1), 8),  # Controlled horizontal padding
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),  # Controlled horizontal padding
            ('BACKGROUND', (0, 1), (-1, -1), HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#dee2e6')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('WORDWRAP', (0, 0), (-1, -1), True),
            ('ROWHEIGHT', (0, 0), (-1, -1), None),  # Allow auto row height
            ('SPLITLONGWORDS', (0, 0), (-1, -1), True),  # Enable word splitting for long words
            ('LEADING', (0, 1), (-1, -1), 10)  # Control line spacing for readability
        ]))

        story.append(domain_table)
        story.append(Spacer(1, 20))

        # Key Strengths
        strengths = report.executive_summary.key_strengths
        if strengths:
            story.append(Paragraph("Key Strengths", heading_style))
            for strength in strengths:
                clean_strength = clean_markdown_text(strength)
                story.append(Paragraph(f"• {clean_strength}", styles['Normal']))
            story.append(Spacer(1, 15))

        # Key Challenges
        challenges = report.executive_summary.key_challenges
        if challenges:
            story.append(Paragraph("Key Challenges", heading_style))
            for challenge in challenges:
                clean_challenge = clean_markdown_text(challenge)
                story.append(Paragraph(f"• {clean_challenge}", styles['Normal']))
            story.append(Spacer(1, 15))

        # Detailed Domain Analysis - Enhanced with Rich Domain-Specific Data
        story.append(Paragraph("Detailed Domain Analysis", heading_style))
        for key, display_name in domain_mapping.items():
            domain_info = domain_analysis.get(key)
            structured_agent_output = report.structured_analysis.get(key)

            if domain_info and structured_agent_output:
                # Add domain subsection with proper formatting
                clean_display_name = clean_markdown_text(display_name)
                story.append(Paragraph(clean_display_name, domain_subsection_style))

                # Check if structured_agent_output has domain-specific RichSection properties
                # Note: isinstance() fails on JSON-deserialized objects, so check for RichSection attributes
                has_rich_sections = False
                rich_section_attributes = []

                # Define expected RichSection attributes for each domain (matching JSON structure)
                domain_rich_sections = {
                    'power_infrastructure': ['grid_reliability', 'power_capacity', 'generation_mix', 'connection_process', 'electricity_costs', 'cost_model', 'industrial_heritage'],
                    'network_connectivity': ['fiber_infrastructure', 'last_mile_diversity', 'subsea_cables', 'ixp_peering', 'carrier_diversity', 'latency_performance', 'bandwidth_costs', 'future_proofing'],
                    'climate_environmental': ['temperature_humidity', 'cooling_strategy', 'free_cooling', 'seismic_geological', 'hydrological_flood', 'wind_storm', 'climate_extremes'],
                    'site_civil': ['land_availability', 'topography', 'geotechnical', 'water_resources', 'transportation_access', 'utilities_hookup'],
                    'mechanical_thermal': ['cooling_systems', 'hvac_design', 'backup_power', 'fire_suppression', 'cabling_distribution', 'equipment_specifications', 'energy_efficiency'],
                    'regulatory_esg': ['data_sovereignty', 'government_incentives', 'operational_compliance', 'permitting_zoning', 'esg_trajectory'],
                    'market_competition': ['competitive_landscape', 'cloud_ecosystem', 'peering_opportunities', 'proximity_to_demand', 'labor_market', 'infrastructure_scalability', 'strategic_relevance']
                }

                expected_sections = domain_rich_sections.get(key, [])
                for section_name in expected_sections:
                    if hasattr(structured_agent_output, section_name):
                        section_obj = getattr(structured_agent_output, section_name)
                        # Check if it has RichSection properties (name, content, sub_score, metrics)
                        if (hasattr(section_obj, 'name') and hasattr(section_obj, 'content') and
                            hasattr(section_obj, 'sub_score') and hasattr(section_obj, 'metrics')):
                            has_rich_sections = True
                            rich_section_attributes.append((section_name, section_obj))

                if has_rich_sections:
                    # Use enhanced rendering for domain-specific models with metrics tables
                    print(f"🎯 Using enhanced domain-specific rendering for {display_name} - found {len(rich_section_attributes)} RichSections")
                    render_domain_specific_rich_sections(structured_agent_output, story, styles, display_name, rich_section_attributes)
                else:
                    # Fallback to legacy rendering for backward compatibility
                    print(f"⚠️ Using legacy rendering for {display_name} - no domain-specific model available")

                    # Add executive summary
                    if structured_agent_output.executive_summary and structured_agent_output.executive_summary.strip():
                        story.append(Paragraph(structured_agent_output.executive_summary, styles['Normal']))
                        story.append(Spacer(1, 10))

                    # Add structured sections (legacy approach)
                    if hasattr(structured_agent_output, 'sections') and structured_agent_output.sections:
                        for section_key, section in structured_agent_output.sections.items():
                            section_title = section.name if section.name else section_key.replace('_', ' ').title()
                            story.append(Paragraph(f"<b>{section_title}:</b>", styles['Normal']))

                            # Add section content
                            if section.content and section.content.strip():
                                story.append(Paragraph(section.content, styles['Normal']))

                            # Add sub-score if available
                            if section.sub_score > 0:
                                rounded_sub_score = round_numeric_value(section.sub_score)
                                story.append(Paragraph(f"<i>Score: {rounded_sub_score}/5.0</i>", styles['Normal']))

                            story.append(Spacer(1, 8))

                    # Add assumptions if available
                    if hasattr(structured_agent_output, 'assumptions') and structured_agent_output.assumptions:
                        story.append(Paragraph("<b>Key Assumptions:</b>", styles['Normal']))
                        for assumption in structured_agent_output.assumptions:
                            story.append(Paragraph(f"• {assumption}", styles['Normal']))
                        story.append(Spacer(1, 10))

                    # Add insights if available
                    if hasattr(structured_agent_output, 'key_insights') and structured_agent_output.key_insights:
                        story.append(Paragraph("<b>Key Insights:</b>", styles['Normal']))
                        for insight in structured_agent_output.key_insights:
                            clean_insight = clean_markdown_text(insight)
                            story.append(Paragraph(f"• {clean_insight}", styles['Normal']))
                        story.append(Spacer(1, 10))

        # Phase 1 Deployment Details
        phase_1 = report.phase_1_deployment
        if phase_1:
            story.append(Paragraph("Phase 1 Deployment Plan", heading_style))
            phase_1_text = f"<b>Capacity:</b> {phase_1.recommended_capacity}<br/>"
            phase_1_text += f"<b>Estimated Investment:</b> {phase_1.estimated_investment}<br/>"
            phase_1_text += f"<b>Timeline:</b> {phase_1.timeline}<br/><br/>"

            priority_actions = phase_1.priority_actions
            if priority_actions:
                phase_1_text += "<b>Priority Actions:</b><br/>"
                for action in priority_actions:
                    phase_1_text += f"• {action}<br/>"
                phase_1_text += "<br/>"

            risk_mitigation = phase_1.risk_mitigation
            if risk_mitigation:
                phase_1_text += "<b>Risk Mitigation:</b><br/>"
                for item in risk_mitigation:
                    phase_1_text += f"• {item}<br/>"

            story.append(Paragraph(phase_1_text, styles['Normal']))
            story.append(Spacer(1, 15))

        # Critical Success Factors (from executive summary)
        critical_factors = report.executive_summary.critical_success_factors
        if critical_factors:
            story.append(Paragraph("Critical Success Factors", heading_style))
            for factor in critical_factors:
                story.append(Paragraph(f"• {factor}", styles['Normal']))
            story.append(Spacer(1, 15))

        # Add Strategic Opportunities section (from insights agent)
        if hasattr(report, 'strategic_opportunities') and report.strategic_opportunities:
            story.append(Paragraph("Strategic Opportunities", heading_style))
            for opportunity in report.strategic_opportunities:
                clean_opportunity = clean_markdown_text(opportunity)
                story.append(Paragraph(f"• {clean_opportunity}", styles['Normal']))
            story.append(Spacer(1, 15))

        # Add Strategic Recommendations section (from insights agent)
        if hasattr(report, 'strategic_recommendation') and report.strategic_recommendation:
            story.append(Paragraph("Strategic Recommendations", heading_style))
            clean_recommendation = clean_markdown_text(report.strategic_recommendation)
            story.append(Paragraph(clean_recommendation, styles['Normal']))
            story.append(Spacer(1, 15))

        # Add Next Steps section (from insights agent)
        if hasattr(report, 'next_steps') and report.next_steps:
            story.append(Paragraph("Next Steps", heading_style))
            for step in report.next_steps:
                clean_step = clean_markdown_text(step)
                story.append(Paragraph(f"• {clean_step}", styles['Normal']))
            story.append(Spacer(1, 15))

        # Add Conclusion section (from insights agent)
        if hasattr(report, 'conclusion') and report.conclusion:
            story.append(Paragraph("Conclusion & Go/No-Go Decision", heading_style))
            clean_conclusion = clean_markdown_text(report.conclusion)
            story.append(Paragraph(clean_conclusion, styles['Normal']))
            story.append(Spacer(1, 20))

        # Add Data Gap Analysis section
        if hasattr(report, 'data_gap_analysis') and report.data_gap_analysis:
            story.append(Paragraph("Data Gaps & Third-Party Verification", heading_style))

            data_gap_analysis = report.data_gap_analysis

            # Overall confidence level
            if hasattr(data_gap_analysis, 'overall_confidence') and data_gap_analysis.overall_confidence:
                confidence_text = f"<b>Analysis Confidence Level:</b> {data_gap_analysis.overall_confidence.title()}"
                story.append(Paragraph(confidence_text, styles['Normal']))
                story.append(Spacer(1, 10))

            # Data gaps identified
            if hasattr(data_gap_analysis, 'data_gaps_identified') and data_gap_analysis.data_gaps_identified:
                story.append(Paragraph("<b>Data Gaps Identified:</b>", styles['Normal']))
                for gap in data_gap_analysis.data_gaps_identified:
                    clean_gap = clean_markdown_text(gap)
                    story.append(Paragraph(f"• {clean_gap}", styles['Normal']))
                story.append(Spacer(1, 10))

            # Third-party verification requirements
            if hasattr(data_gap_analysis, 'third_party_requirements') and data_gap_analysis.third_party_requirements:
                story.append(Paragraph("<b>Third-Party Verification Required:</b>", styles['Normal']))
                for requirement in data_gap_analysis.third_party_requirements:
                    clean_requirement = clean_markdown_text(requirement)
                    story.append(Paragraph(f"• {clean_requirement}", styles['Normal']))
                story.append(Spacer(1, 10))

            # Next steps priority
            if hasattr(data_gap_analysis, 'next_steps_priority') and data_gap_analysis.next_steps_priority:
                story.append(Paragraph("<b>Priority Next Steps:</b>", styles['Normal']))
                for step in data_gap_analysis.next_steps_priority:
                    clean_step = clean_markdown_text(step)
                    story.append(Paragraph(f"• {clean_step}", styles['Normal']))
                story.append(Spacer(1, 15))

            # Important note about analysis limitations
            story.append(Paragraph("<b>Important:</b> This analysis is based on publicly available information. Critical business decisions should include verification of the identified data gaps through third-party specialists.", styles['Normal']))
            story.append(Spacer(1, 20))

        # Sources & References Section
        story.append(Paragraph("Sources & References", heading_style))

        # Collect all sources from domain analyses
        all_sources = []
        domain_mapping = {
            'power_infrastructure': 'Power Infrastructure',
            'network_connectivity': 'Network Connectivity',
            'climate_environmental': 'Climate Suitability',
            'site_civil': 'Site & Civil',
            'mechanical_thermal': 'Mechanical & Thermal',
            'regulatory_esg': 'Regulatory & ESG',
            'market_competition': 'Market & Competition'
        }

        for domain_key, domain_name in domain_mapping.items():
            if hasattr(report, domain_key):
                domain_data = getattr(report, domain_key)
                if domain_data and hasattr(domain_data, 'sources') and domain_data.sources:
                    for source in domain_data.sources:
                        source_with_domain = source.copy()
                        source_with_domain['domain'] = domain_name
                        all_sources.append(source_with_domain)

        if all_sources:
            story.append(Paragraph("This analysis incorporates real-time data from the following web sources:", styles['Normal']))
            story.append(Spacer(1, 10))

            # Group sources by domain
            from collections import defaultdict
            sources_by_domain = defaultdict(list)
            for source in all_sources:
                sources_by_domain[source.get('domain', 'General')].append(source)

            # Display sources grouped by domain
            for domain_name in domain_mapping.values():
                if domain_name in sources_by_domain:
                    story.append(Paragraph(f"<b>{domain_name}:</b>", styles['Normal']))
                    for source in sources_by_domain[domain_name]:
                        url = source.get('url', 'N/A')
                        title = source.get('title', 'Untitled')
                        date = source.get('date', 'N/A')
                        snippet = source.get('snippet', '')

                        # Clean text for PDF
                        clean_title = clean_markdown_text(title)
                        clean_snippet = clean_markdown_text(snippet)[:150] + '...' if snippet else ''

                        source_text = f"• <b>{clean_title}</b>"
                        if date != 'N/A':
                            source_text += f" ({date})"
                        source_text += f"<br/>&nbsp;&nbsp;{url}"
                        if clean_snippet:
                            source_text += f"<br/>&nbsp;&nbsp;<i>{clean_snippet}</i>"

                        story.append(Paragraph(source_text, styles['Normal']))
                        story.append(Spacer(1, 5))
                    story.append(Spacer(1, 10))
        else:
            story.append(Paragraph("This analysis is based on the agent's comprehensive knowledge base and publicly available information. No specific web sources were cited for this location.", styles['Normal']))

        story.append(Spacer(1, 20))

        # Build PDF
        print(f"🔧 DEBUG: Building PDF with {len(story)} story elements...")
        doc.build(story)
        print(f"🔧 DEBUG: PDF build completed")

        # Verify file was created
        if not file_path.exists():
            print(f"❌ DEBUG: PDF file verification FAILED - file does not exist at {file_path}")
            raise Exception(f"PDF file was not created at {file_path}")

        file_size = file_path.stat().st_size
        print(f"🔧 DEBUG: PDF file verification successful - size: {file_size} bytes")

        result = {
            "status": "success",
            "file_path": str(file_path),
            "filename": filename,
            "message": f"PDF report generated successfully at {file_path}"
        }
        print(f"✅ DEBUG: PDF generation completed successfully: {filename}")



        return result
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"Failed to generate PDF report: {str(e)}"
        }
        print(f"⚠️  Error generating PDF report: {str(e)}")
        return error_result


# Create FunctionTool instances
json_report_tool = FunctionTool(func=save_json_report)
pdf_report_tool = FunctionTool(func=generate_pdf_report)
save_report_tool = FunctionTool(func=save_report_schema)  # New Pydantic-based tool