"""
Email service for sending notifications
"""

from fastapi_mail import FastMail, MessageSchema
from typing import List, Optional
import os
from app.core.config import settings
from app.services.smtp_config import conf

class EmailService:
    def __init__(self):
        self.fastmail = FastMail(conf)
    
    async def send_welcome_email(
        self, 
        to_email: str, 
        officer_name: str, 
        employee_id: str, 
        badge_number: str,
        assigned_area: str,
        login_credentials: dict
    ):
        """
        Send welcome email to newly registered traffic police officer
        """
        try:
            subject = f"Welcome to Traffic Management System - {employee_id}"
            
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Welcome to Traffic Management System</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                        background-color: #f4f4f4;
                    }}
                    .container {{
                        background-color: #ffffff;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                        overflow: hidden;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                        color: white;
                        padding: 30px 20px;
                        text-align: center;
                    }}
                    .header h1 {{
                        margin: 0;
                        font-size: 28px;
                        font-weight: 300;
                    }}
                    .header p {{
                        margin: 10px 0 0 0;
                        opacity: 0.9;
                        font-size: 16px;
                    }}
                    .content {{
                        padding: 30px 20px;
                    }}
                    .welcome-section {{
                        background-color: #f8f9fa;
                        border-left: 4px solid #2a5298;
                        padding: 20px;
                        margin: 20px 0;
                        border-radius: 0 5px 5px 0;
                    }}
                    .credentials-box {{
                        background-color: #fff3cd;
                        border: 1px solid #ffeaa7;
                        border-radius: 8px;
                        padding: 20px;
                        margin: 20px 0;
                    }}
                    .credentials-box h3 {{
                        color: #856404;
                        margin-top: 0;
                        font-size: 18px;
                    }}
                    .credentials-list {{
                        list-style: none;
                        padding: 0;
                    }}
                    .credentials-list li {{
                        background-color: #ffffff;
                        margin: 10px 0;
                        padding: 12px 15px;
                        border-radius: 5px;
                        border-left: 3px solid #ffc107;
                    }}
                    .credentials-list strong {{
                        color: #495057;
                        display: inline-block;
                        width: 120px;
                    }}
                    .details-section {{
                        background-color: #e7f3ff;
                        border: 1px solid #b3d9ff;
                        border-radius: 8px;
                        padding: 20px;
                        margin: 20px 0;
                    }}
                    .details-section h3 {{
                        color: #0066cc;
                        margin-top: 0;
                        font-size: 18px;
                    }}
                    .details-list {{
                        list-style: none;
                        padding: 0;
                    }}
                    .details-list li {{
                        background-color: #ffffff;
                        margin: 10px 0;
                        padding: 12px 15px;
                        border-radius: 5px;
                        border-left: 3px solid #0066cc;
                    }}
                    .details-list strong {{
                        color: #495057;
                        display: inline-block;
                        width: 120px;
                    }}
                    .security-notice {{
                        background-color: #f8d7da;
                        border: 1px solid #f5c6cb;
                        border-radius: 8px;
                        padding: 15px;
                        margin: 20px 0;
                        color: #721c24;
                    }}
                    .security-notice strong {{
                        color: #721c24;
                    }}
                    .footer {{
                        background-color: #f8f9fa;
                        padding: 20px;
                        text-align: center;
                        border-top: 1px solid #dee2e6;
                        color: #6c757d;
                        font-size: 14px;
                    }}
                    .footer p {{
                        margin: 5px 0;
                    }}
                    .logo {{
                        font-size: 24px;
                        font-weight: bold;
                        margin-bottom: 10px;
                    }}
                    .badge {{
                        display: inline-block;
                        background-color: #28a745;
                        color: white;
                        padding: 4px 8px;
                        border-radius: 12px;
                        font-size: 12px;
                        font-weight: bold;
                        margin-left: 10px;
                    }}
                    .steps-section {{
                        background-color: #d1ecf1;
                        border: 1px solid #bee5eb;
                        border-radius: 8px;
                        padding: 20px;
                        margin: 20px 0;
                    }}
                    .steps-section h3 {{
                        color: #0c5460;
                        margin-top: 0;
                    }}
                    .steps-section ol {{
                        color: #0c5460;
                        padding-left: 20px;
                    }}
                    .quote {{
                        text-align: center;
                        margin: 30px 0;
                        color: #6c757d;
                        font-style: italic;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="logo">🚦 Traffic Management System</div>
                        <h1>Welcome, Officer!</h1>
                        <p>Your account has been successfully created</p>
                    </div>
                    
                    <div class="content">
                        <div class="welcome-section">
                            <h2>Dear {officer_name},</h2>
                            <p>Welcome to the Traffic Management System! We're excited to have you join our team of dedicated traffic enforcement officers.</p>
                        </div>
                        
                        <div class="credentials-box">
                            <h3>🔐 Your Login Credentials</h3>
                            <ul class="credentials-list">
                                <li><strong>Email:</strong> {login_credentials['email']}</li>
                                <li><strong>Password:</strong> {login_credentials['password']}</li>
                            </ul>
                        </div>
                        
                        <div class="security-notice">
                            <strong>⚠️ Security Notice:</strong> Please log in immediately and change your password to ensure account security.
                        </div>
                        
                        <div class="details-section">
                            <h3>👮‍♂️ Your Officer Details</h3>
                            <ul class="details-list">
                                <li><strong>Employee ID:</strong> {employee_id}</li>
                                <li><strong>Badge Number:</strong> {badge_number if badge_number else 'N/A'}</li>
                                <li><strong>Assigned Area:</strong> {assigned_area}</li>
                                <li><strong>Status:</strong> Active <span class="badge">ACTIVE</span></li>
                            </ul>
                        </div>
                        
                        <div class="steps-section">
                            <h3>📱 Next Steps</h3>
                            <ol>
                                <li>Download the Traffic Police mobile application</li>
                                <li>Log in using your credentials above</li>
                                <li>Change your password immediately</li>
                                <li>Complete your profile setup</li>
                                <li>Review your assigned area and responsibilities</li>
                            </ol>
                        </div>
                        
                        <div class="quote">
                            <p>"Ensuring road safety through technology and dedicated enforcement"</p>
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p><strong>Traffic Management System</strong></p>
                        <p>Government of India | Ministry of Road Transport & Highways</p>
                        <p>For support, contact: support@traffic.gov.in | +91-XXX-XXXX-XXXX</p>
                        <p style="font-size: 12px; margin-top: 15px;">
                            This is an automated message. Please do not reply to this email.
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            message = MessageSchema(
                subject=subject,
                recipients=[to_email],
                body=html_content,
                subtype="html"
            )
            
            await self.fastmail.send_message(message)
            return True
            
        except Exception as e:
            print(f"Error sending welcome email: {str(e)}")
            return False
    
    async def send_password_reset_email(self, to_email: str, reset_token: str, officer_name: str):
        """
        Send password reset email
        """
        try:
            subject = "Password Reset - Traffic Management System"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Password Reset</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #f44336; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .button {{ display: inline-block; background: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔒 Password Reset</h1>
                    </div>
                    
                    <div class="content">
                        <h2>Hello {officer_name},</h2>
                        
                        <p>You have requested to reset your password for the Traffic Management System.</p>
                        
                        <p>Click the button below to reset your password:</p>
                        
                        <a href="#" class="button">Reset Password</a>
                        
                        <p>If the button doesn't work, copy and paste this link into your browser:</p>
                        <p style="word-break: break-all; background: #f0f0f0; padding: 10px; border-radius: 5px;">
                            {reset_token}
                        </p>
                        
                        <p><strong>Note:</strong> This link will expire in 24 hours for security reasons.</p>
                        
                        <p>If you didn't request this password reset, please ignore this email.</p>
                        
                        <div class="footer">
                            <p>This is an automated message from the Traffic Management System.</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            message = MessageSchema(
                subject=subject,
                recipients=[to_email],
                body=html_content,
                subtype="html"
            )
            
            await self.fastmail.send_message(message)
            return True
            
        except Exception as e:
            print(f"Error sending password reset email: {str(e)}")
            return False
    
    async def send_violation_alert_email(self, to_email: str, violation_details: dict):
        """
        Send violation alert email to traffic police
        """
        try:
            subject = f"Traffic Violation Alert - {violation_details.get('violation_type', 'Unknown')}"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Traffic Violation Alert</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #ff9800; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .alert {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🚨 Traffic Violation Alert</h1>
                    </div>
                    
                    <div class="content">
                        <div class="alert">
                            <h3>⚠️ New Traffic Violation Detected</h3>
                            <p>A traffic violation has been detected in your assigned area.</p>
                        </div>
                        
                        <h3>Violation Details</h3>
                        <p><strong>Type:</strong> {violation_details.get('violation_type', 'Unknown')}</p>
                        <p><strong>Vehicle:</strong> {violation_details.get('vehicle_number', 'Unknown')}</p>
                        <p><strong>Location:</strong> {violation_details.get('location', 'Unknown')}</p>
                        <p><strong>Time:</strong> {violation_details.get('timestamp', 'Unknown')}</p>
                        <p><strong>Confidence:</strong> {violation_details.get('confidence', 'Unknown')}</p>
                        
                        <p>Please review the violation details in the mobile application and take appropriate action.</p>
                        
                        <div class="footer">
                            <p>This is an automated alert from the Traffic Management System.</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            message = MessageSchema(
                subject=subject,
                recipients=[to_email],
                body=html_content,
                subtype="html"
            )
            
            await self.fastmail.send_message(message)
            return True
            
        except Exception as e:
            print(f"Error sending violation alert email: {str(e)}")
            return False

    async def send_email_with_attachment(self, to_email: str, subject: str, body: str, attachment_path: str):
        """
        Send email with PDF attachment using FastMail
        """
        try:
            import os
            from fastapi_mail import MessageSchema, MessageType
            
            # Check if attachment exists
            if not os.path.exists(attachment_path):
                print(f"Attachment not found: {attachment_path}")
                # Send without attachment
                return await self.send_email(to_email, subject, body)
            
            # Create message with attachment
            message = MessageSchema(
                subject=subject,
                recipients=[to_email],
                body=body,
                subtype=MessageType.html,
                attachments=[attachment_path]
            )
            
            await self.fastmail.send_message(message)
            print(f"✅ Email with attachment sent successfully to {to_email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email with attachment: {e}")
            # Fallback: send without attachment
            try:
                return await self.send_email(to_email, subject, body)
            except:
                return False

async def send_challan_email(to_email: str, challan_data: dict, pdf_path: str):
    """
    Send E-Challan email with PDF attachment
    """
    subject = f"🚔 E-Challan Notice - {challan_data['challan_id']}"
    
    vehicle_info = challan_data.get('vehicle_info', {})
    owner_name = vehicle_info.get('Owner Name', 'Vehicle Owner')
    
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd;">
            <header style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #d32f2f; margin: 0;">DELHI POLICE</h1>
                <h2 style="color: #1976d2; margin: 5px 0;">TRAFFIC CHALLAN NOTICE</h2>
                <p style="margin: 0; font-size: 14px; color: #666;">Government of National Capital Territory of Delhi</p>
            </header>
            
            <div style="background: #f5f5f5; padding: 15px; border-left: 4px solid #d32f2f; margin: 20px 0;">
                <h3 style="margin: 0 0 10px 0; color: #d32f2f;">VIOLATION NOTICE</h3>
                <p style="margin: 0;"><strong>Dear {owner_name},</strong></p>
                <p>Your vehicle <strong>{challan_data['license_plate']}</strong> has been found violating traffic rules.</p>
            </div>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background: #f9f9f9;">
                    <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Challan ID:</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{challan_data['challan_id']}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Violation Type:</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{challan_data['violation_type'].replace('_', ' ').title()}</td>
                </tr>
                <tr style="background: #f9f9f9;">
                    <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Date & Time:</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{challan_data['timestamp']}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Location:</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{challan_data['location']}</td>
                </tr>
                <tr style="background: #fff3e0;">
                    <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; color: #e65100;">Penalty Amount:</td>
                    <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; color: #e65100; font-size: 18px;">₹ {challan_data['challan_amount']}</td>
                </tr>
                <tr style="background: #ffebee;">
                    <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; color: #c62828;">Due Date:</td>
                    <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; color: #c62828;">{challan_data['due_date']}</td>
                </tr>
            </table>
            
            <div style="background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h4 style="margin: 0 0 10px 0; color: #1976d2;">📋 Payment Instructions:</h4>
                <ul style="margin: 0; padding-left: 20px;">
                    <li>Pay online at <strong>parivahan.gov.in</strong></li>
                    <li>Visit nearest Traffic Police Station</li>
                    <li>Use UPI payment with Challan ID</li>
                    <li>Pay before due date to avoid additional penalty</li>
                </ul>
            </div>
            
            <div style="background: #fff3e0; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h4 style="margin: 0 0 10px 0; color: #f57c00;">⚠️ Important Notes:</h4>
                <ul style="margin: 0; padding-left: 20px; font-size: 14px;">
                    <li>This is an electronically generated challan</li>
                    <li>Late payment attracts additional penalty</li>
                    <li>For queries, call Delhi Traffic Police: <strong>1095</strong></li>
                    <li>Contest in court if you believe this is incorrect</li>
                </ul>
            </div>
            
            <div style="background: #f3e5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h4 style="margin: 0 0 10px 0; color: #7b1fa2;">📎 Attachment:</h4>
                <p style="margin: 0;">Detailed E-Challan PDF is attached to this email.</p>
            </div>
            
            <footer style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px;">
                <p><strong>Delhi Traffic Police</strong><br>
                Road Safety Division, New Delhi<br>
                Email: traffic.delhi@gov.in | Helpline: 1095</p>
                <p style="margin-top: 10px;">This is an automated email. Please do not reply to this email.</p>
            </footer>
        </div>
    </body>
    </html>
    """
    
    try:
        # Use the email service with attachment
        await email_service.send_email_with_attachment(to_email, subject, body, pdf_path)
        print(f"✅ E-Challan email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send challan email to {to_email}: {e}")

# Global email service instance
email_service = EmailService()
