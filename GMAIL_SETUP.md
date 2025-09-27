# Gmail SMTP Setup Guide

## Quick Setup for Gmail SMTP

### 1. Enable 2-Factor Authentication
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Factor Authentication if not already enabled

### 2. Generate App Password
1. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
2. Select "Mail" as the app
3. Select "Other" as the device and enter "Traffic Management System"
4. Click "Generate"
5. Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)

### 3. Configure Environment Variables
Create a `.env` file in the backend directory:

```bash
# Gmail SMTP Configuration
GMAIL_USERNAME=your_email@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password
GMAIL_FROM=your_email@gmail.com
```

### 4. Test Email Configuration
```bash
# Test the email setup
curl -X POST "http://localhost:8000/api/v1/traffic-police/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Officer",
    "email": "test@example.com",
    "password": "password123",
    "badge_number": "TEST001",
    "assigned_area": {"name": "Test Area", "coordinates": [19.0760, 72.8777]},
    "rto_office_id": 1
  }'
```

### 5. Troubleshooting
- **Error 535**: Check your app password and username
- **Error 534**: Enable "Less secure app access" (not recommended)
- **Connection timeout**: Check firewall settings

### 6. Alternative Email Providers
If Gmail doesn't work, you can use:
- **Outlook**: `smtp-mail.outlook.com:587`
- **Yahoo**: `smtp.mail.yahoo.com:587`
- **SendGrid**: Professional email service
- **Mailtrap**: For development/testing

## Security Notes
- Never commit app passwords to version control
- Use environment variables for sensitive data
- Consider using a dedicated email service for production