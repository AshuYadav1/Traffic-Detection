"""
Simple Gmail SMTP Configuration
"""

import os
from fastapi_mail import ConnectionConfig

# Simple Gmail SMTP configuration
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("GMAIL_USERNAME", "aashukumaryadav1@gmail.com"),
    MAIL_PASSWORD=os.getenv("GMAIL_APP_PASSWORD", "ekcdjhqbrhgoshqk"),
    MAIL_FROM=os.getenv("GMAIL_FROM", "aashukumaryadav1@gmail.com"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_FROM_NAME="Traffic Management System",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)