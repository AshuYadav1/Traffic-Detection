"""
E-Challan PDF Generation Service
Creates professional government-style E-Challan PDFs
"""

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import os
from typing import Dict, Any
from datetime import datetime
import qrcode
from io import BytesIO

from app.core.config import settings

class ChallanPDFService:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom styles for the PDF"""
        self.styles.add(ParagraphStyle(
            name='CenterTitle',
            parent=self.styles['Title'],
            alignment=TA_CENTER,
            fontSize=18,
            fontName='Helvetica-Bold',
            textColor=colors.darkblue,
            spaceAfter=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='CenterSubtitle',
            parent=self.styles['Normal'],
            alignment=TA_CENTER,
            fontSize=12,
            fontName='Helvetica-Bold',
            textColor=colors.darkred,
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='FieldLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=colors.black
        ))
        
        self.styles.add(ParagraphStyle(
            name='FieldValue',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Helvetica',
            textColor=colors.black
        ))

    async def generate_challan_pdf(self, challan_data: Dict[str, Any]) -> str:
        """
        Generate professional E-Challan PDF
        """
        try:
            # Create output directory if it doesn't exist
            output_dir = os.path.join(settings.BASE_DIR, "challans")
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename
            filename = f"echallan_{challan_data['challan_id']}.pdf"
            pdf_path = os.path.join(output_dir, filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(
                pdf_path,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # Build PDF content
            story = []
            
            # Header with logo
            story.extend(self._create_header(challan_data))
            
            # Challan details
            story.extend(self._create_challan_details(challan_data))
            
            # Violation details
            story.extend(self._create_violation_details(challan_data))
            
            # Vehicle details
            story.extend(self._create_vehicle_details(challan_data))
            
            # Payment details
            story.extend(self._create_payment_details(challan_data))
            
            # Footer
            story.extend(self._create_footer(challan_data))
            
            # Build PDF
            doc.build(story)
            
            print(f"✅ E-Challan PDF generated: {pdf_path}")
            return pdf_path
            
        except Exception as e:
            print(f"❌ Error generating PDF: {e}")
            raise e

    def _create_header(self, challan_data: Dict[str, Any]) -> list:
        """Create PDF header with logo and title"""
        elements = []
        
        # Add Delhi Police logo
        try:
            logo_path = os.path.join(settings.BASE_DIR, "static", "delhi_police_logo.png")
            if not os.path.exists(logo_path):
                # Create a placeholder logo directory
                os.makedirs(os.path.dirname(logo_path), exist_ok=True)
                # Use text placeholder if logo not available
                pass
            else:
                logo = Image(logo_path, width=1*inch, height=1*inch)
                elements.append(logo)
        except:
            pass
        
        # Header table with logo and title
        header_data = [
            [
                self._create_logo_placeholder(),
                Paragraph("DELHI POLICE<br/>TRAFFIC CHALLAN", self.styles['CenterTitle']),
                self._create_qr_code(challan_data['challan_id'])
            ]
        ]
        
        header_table = Table(header_data, colWidths=[2*inch, 4*inch, 2*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 12))
        
        # Government header
        elements.append(Paragraph("GOVERNMENT OF NATIONAL CAPITAL TERRITORY OF DELHI", self.styles['CenterSubtitle']))
        elements.append(Paragraph("DELHI TRAFFIC POLICE", self.styles['CenterSubtitle']))
        elements.append(Spacer(1, 12))
        
        # Red line separator
        line_table = Table([['']], colWidths=[7*inch])
        line_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 3, colors.darkred),
        ]))
        elements.append(line_table)
        elements.append(Spacer(1, 12))
        
        return elements

    def _create_logo_placeholder(self):
        """Create a text placeholder for Delhi Police logo"""
        logo_text = """<font size=8><b>DELHI<br/>POLICE</b><br/>
        <font size=6>सेवा और सुरक्षा</font></font>"""
        return Paragraph(logo_text, self.styles['Normal'])

    def _create_qr_code(self, challan_id: str):
        """Create QR code for challan verification"""
        try:
            qr = qrcode.QRCode(version=1, box_size=3, border=1)
            qr.add_data(f"Challan ID: {challan_id}")
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to bytes
            img_buffer = BytesIO()
            qr_img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            # Save temporarily
            qr_path = f"/tmp/qr_{challan_id}.png"
            with open(qr_path, 'wb') as f:
                f.write(img_buffer.getvalue())
            
            return Image(qr_path, width=0.8*inch, height=0.8*inch)
        except:
            return Paragraph("<font size=8>QR Code</font>", self.styles['Normal'])

    def _create_challan_details(self, challan_data: Dict[str, Any]) -> list:
        """Create challan identification details"""
        elements = []
        
        elements.append(Paragraph("E-CHALLAN DETAILS", self.styles['Heading2']))
        elements.append(Spacer(1, 6))
        
        challan_table_data = [
            ["Challan No:", challan_data['challan_id'], "Date & Time:", challan_data['timestamp']],
            ["Officer Name:", challan_data['officer_name'], "Officer ID:", challan_data['officer_id']],
            ["Location:", challan_data['location'], "Due Date:", challan_data['due_date']]
        ]
        
        challan_table = Table(challan_table_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
        challan_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(challan_table)
        elements.append(Spacer(1, 12))
        
        return elements

    def _create_violation_details(self, challan_data: Dict[str, Any]) -> list:
        """Create violation details section"""
        elements = []
        
        elements.append(Paragraph("VIOLATION DETAILS", self.styles['Heading2']))
        elements.append(Spacer(1, 6))
        
        # Violation description mapping
        violation_descriptions = {
            "red_light": "Jumping Red Light / Signal Violation",
            "helmet": "Riding Without Helmet",
            "wrong_way": "Wrong Way Driving",
            "overspeeding": "Over Speeding",
            "no_parking": "Parking Violation"
        }
        
        violation_desc = violation_descriptions.get(
            challan_data['violation_type'], 
            challan_data['violation_type'].replace('_', ' ').title()
        )
        
        violation_table_data = [
            ["Violation Type:", violation_desc],
            ["Vehicle Registration:", challan_data['license_plate']],
            ["Vehicle Type:", challan_data['vehicle_type'].title()],
            ["Detection Confidence:", f"{float(challan_data.get('confidence', 0.0)) * 100:.1f}%"],
            ["Section/Rule:", self._get_traffic_rule(challan_data['violation_type'])],
        ]
        
        violation_table = Table(violation_table_data, colWidths=[2*inch, 4*inch])
        violation_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(violation_table)
        elements.append(Spacer(1, 12))
        
        # Add evidence image if available
        evidence_image = self._add_evidence_image(challan_data)
        if evidence_image:
            elements.append(Paragraph("VIOLATION EVIDENCE", self.styles['Heading3']))
            elements.append(Spacer(1, 6))
            elements.append(evidence_image)
            elements.append(Spacer(1, 12))
        
        return elements

    def _create_vehicle_details(self, challan_data: Dict[str, Any]) -> list:
        """Create vehicle and owner details section"""
        elements = []
        
        elements.append(Paragraph("VEHICLE & OWNER DETAILS", self.styles['Heading2']))
        elements.append(Spacer(1, 6))
        
        vehicle_info = challan_data.get('vehicle_info', {})
        
        vehicle_table_data = [
            ["Registration No:", vehicle_info.get('Registration No', challan_data['license_plate'])],
            ["Owner Name:", vehicle_info.get('Owner Name', 'Vehicle Owner')],
            ["Vehicle Class:", vehicle_info.get('Vehicle Class', challan_data['vehicle_type'])],
            ["Fuel Type:", vehicle_info.get('Fuel Type', 'Petrol')],
            ["Registration Date:", vehicle_info.get('Registration Date', 'N/A')],
            ["Engine No:", vehicle_info.get('Engine No', 'N/A')],
            ["Chassis No:", vehicle_info.get('Chassis No', 'N/A')],
        ]
        
        vehicle_table = Table(vehicle_table_data, colWidths=[2*inch, 4*inch])
        vehicle_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(vehicle_table)
        elements.append(Spacer(1, 12))
        
        return elements

    def _create_payment_details(self, challan_data: Dict[str, Any]) -> list:
        """Create payment details section"""
        elements = []
        
        elements.append(Paragraph("PENALTY & PAYMENT DETAILS", self.styles['Heading2']))
        elements.append(Spacer(1, 6))
        
        amount = challan_data['challan_amount']
        
        payment_table_data = [
            ["Penalty Amount:", f"₹ {amount}"],
            ["Late Fee (if any):", "₹ 0"],
            ["Total Amount:", f"₹ {amount}"],
            ["Payment Due Date:", challan_data['due_date']],
            ["Payment Mode:", "Online / Cash at Traffic Police Station"],
        ]
        
        payment_table = Table(payment_table_data, colWidths=[2*inch, 4*inch])
        payment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('BACKGROUND', (0, 2), (-1, 2), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(payment_table)
        elements.append(Spacer(1, 12))
        
        return elements

    def _create_footer(self, challan_data: Dict[str, Any]) -> list:
        """Create footer with important notes"""
        elements = []
        
        elements.append(Paragraph("IMPORTANT NOTES", self.styles['Heading3']))
        
        notes = [
            "• This is an electronically generated challan and does not require signature.",
            "• Payment can be made online at parivahan.gov.in or at any traffic police station.",
            "• Late payment may attract additional penalty as per Delhi Motor Vehicle Rules.",
            "• For any queries, contact Delhi Traffic Police Helpline: 1095",
            "• Court address for contest: " + challan_data.get('court_address', 'Metropolitan Magistrate Court, Delhi'),
        ]
        
        for note in notes:
            elements.append(Paragraph(note, self.styles['Normal']))
        
        elements.append(Spacer(1, 12))
        
        # Footer line
        footer_text = f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} | Challan ID: {challan_data['challan_id']}"
        elements.append(Paragraph(footer_text, self.styles['Normal']))
        
        return elements

    def _add_evidence_image(self, challan_data: Dict[str, Any]):
        """Add evidence image to the PDF"""
        try:
            evidence_path = challan_data.get('evidence_path')
            
            if not evidence_path:
                # Try to find a suitable evidence image based on violation type
                evidence_path = self._get_mock_evidence_image(challan_data)
            
            if evidence_path and os.path.exists(evidence_path):
                # Create evidence image with appropriate size
                evidence_img = Image(evidence_path, width=4*inch, height=3*inch)
                
                # Create a table to center the image with a caption
                evidence_table_data = [
                    [evidence_img],
                    [Paragraph(
                        f"Evidence Image - {challan_data['violation_type'].replace('_', ' ').title()} Violation",
                        self.styles['Normal']
                    )]
                ]
                
                evidence_table = Table(evidence_table_data, colWidths=[6*inch])
                evidence_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 1), (0, 1), 10),
                    ('TEXTCOLOR', (0, 1), (0, 1), colors.darkblue),
                    ('TOPPADDING', (0, 1), (0, 1), 8),
                ]))
                
                return evidence_table
            
        except Exception as e:
            print(f"Warning: Could not add evidence image: {e}")
            # Return a placeholder if image loading fails
            return Paragraph(
                "Evidence image not available",
                self.styles['Normal']
            )
        
        return None

    def _get_mock_evidence_image(self, challan_data: Dict[str, Any]) -> str:
        """Get mock evidence image based on violation type"""
        violation_type = challan_data['violation_type']
        vehicle_type = challan_data.get('vehicle_type', 'car')
        
        # Try to find an appropriate evidence image
        base_dir = settings.BASE_DIR
        
        # Look for specific violation type images in the backend directory
        possible_images = [
            f"{violation_type}_violator_{vehicle_type}_*.jpg",
            f"{violation_type}_violator_*.jpg"
        ]
        
        # Search for existing evidence images
        import glob
        for pattern in possible_images:
            image_path = os.path.join(base_dir, pattern)
            matches = glob.glob(image_path)
            if matches:
                return matches[0]
        
        # Fallback to any available evidence image
        evidence_dir = os.path.join(base_dir, "evidence")
        if os.path.exists(evidence_dir):
            for subdir in os.listdir(evidence_dir):
                subdir_path = os.path.join(evidence_dir, subdir)
                if os.path.isdir(subdir_path):
                    for file in os.listdir(subdir_path):
                        if file.endswith('.jpg') and violation_type in file:
                            return os.path.join(subdir_path, file)
        
        # Final fallback - any violation image in the base directory
        for file in os.listdir(base_dir):
            if file.endswith('.jpg') and 'violator' in file:
                return os.path.join(base_dir, file)
        
        return None

    def _get_traffic_rule(self, violation_type: str) -> str:
        """Get traffic rule section for violation type"""
        rules = {
            "red_light": "Section 119/177 Motor Vehicle Act",
            "helmet": "Section 129/177 Motor Vehicle Act", 
            "wrong_way": "Section 184 Motor Vehicle Act",
            "overspeeding": "Section 183/177 Motor Vehicle Act",
            "no_parking": "Section 122/177 Motor Vehicle Act"
        }
        return rules.get(violation_type, "Section 177 Motor Vehicle Act")

# Create global instance
challan_pdf_service = ChallanPDFService()
