import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings


def send_otp_email(email: str, otp_code: str) -> bool:
    """
    Send OTP verification email to user via Gmail SMTP
    """
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your AlsaTalk Verification Code: {otp_code}"
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = email

        # Plain text version
        text = f"""
Hello,

Your AlsaTalk verification code is: {otp_code}

This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.

If you didn't request this code, please ignore this email.

Best regards,
The AlsaTalk Team
        """

        # HTML version
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .otp-code {{ background: white; border: 2px dashed #667eea; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #667eea; margin: 20px 0; border-radius: 5px; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Email Verification</h1>
        </div>
        <div class="content">
            <p>Hello,</p>
            <p>Thank you for signing up with AlsaTalk! Please use the verification code below to complete your registration:</p>
            <div class="otp-code">{otp_code}</div>
            <p>This code will expire in <strong>{settings.OTP_EXPIRE_MINUTES} minutes</strong>.</p>
            <p>If you didn't request this code, please ignore this email.</p>
            <div class="footer">
                <p>Best regards,<br>The AlsaTalk Team</p>
                <p>&copy; 2025 AlsaTalk. All rights reserved.</p>
            </div>
        </div>
    </div>
</body>
</html>
        """

        # Attach both versions
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        msg.attach(part1)
        msg.attach(part2)

        # Connect to Gmail SMTP server
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()  # Enable TLS encryption
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        return True

    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False


def send_welcome_email(email: str, first_name: str) -> bool:
    """
    Send welcome email after successful signup
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Welcome to AlsaTalk!"
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = email

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to AlsaTalk! 🎉</h1>
        </div>
        <div class="content">
            <p>Hi {first_name},</p>
            <p>Welcome aboard! Your account has been successfully created.</p>
            <p>You can now start using AlsaTalk's AI-powered call center platform to empower your team with intelligent call management.</p>
            <p>Best regards,<br>The AlsaTalk Team</p>
        </div>
    </div>
</body>
</html>
        """

        part = MIMEText(html, "html")
        msg.attach(part)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        return True

    except Exception as e:
        print(f"Error sending welcome email: {str(e)}")
        return False


def send_reset_password_email(email: str, otp_code: str) -> bool:
    """
    Send password reset email with OTP code
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your AlsaTalk Password Reset Code: {otp_code}"
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = email

        # Plain text version
        text = f"""
Hello,

We received a request to reset your password for your AlsaTalk account.

Your password reset code is: {otp_code}

This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.

If you didn't request a password reset, please ignore this email and your password will remain unchanged.

Best regards,
The AlsaTalk Team
        """

        # HTML version
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .otp-code {{ background: white; border: 2px dashed #667eea; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #667eea; margin: 20px 0; border-radius: 5px; }}
        .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset Request</h1>
        </div>
        <div class="content">
            <p>Hello,</p>
            <p>We received a request to reset your password for your AlsaTalk account.</p>
            <p>Your password reset code is:</p>
            <div class="otp-code">{otp_code}</div>
            <p>This code will expire in <strong>{settings.OTP_EXPIRE_MINUTES} minutes</strong>.</p>
            <div class="warning">
                <strong>⚠️ Security Notice:</strong> If you didn't request a password reset, please ignore this email and your password will remain unchanged.
            </div>
            <div class="footer">
                <p>Best regards,<br>The AlsaTalk Team</p>
                <p>&copy; 2025 AlsaTalk. All rights reserved.</p>
            </div>
        </div>
    </div>
</body>
</html>
        """

        # Attach both versions
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        msg.attach(part1)
        msg.attach(part2)

        # Connect to SMTP server
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        return True

    except Exception as e:
        print(f"Error sending password reset email: {str(e)}")
        return False


def send_admin_organization_notification(
    organization_data: dict, user_data: dict, approval_token: str, decline_token: str
) -> bool:
    """
    Send notification email to admin when a new organization completes onboarding
    Includes View Details, Approve, and Decline buttons
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = (
            f"New Organization Onboarding: {organization_data.get('name', 'N/A')}"
        )
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = settings.ADMIN_EMAIL

        # Generate action URLs
        view_url = (
            f"{settings.FRONTEND_URL}/admin/organizations/{organization_data.get('id')}"
        )
        # If API_PUBLIC_URL is provided, link directly to backend endpoints; otherwise rely on frontend proxy
        if settings.API_PUBLIC_URL:
            approve_url = f"{settings.API_PUBLIC_URL}/organization/approve?token={approval_token}&silent=true"
            decline_url = f"{settings.API_PUBLIC_URL}/organization/decline?token={decline_token}&silent=true"
        else:
            approve_url = f"{settings.FRONTEND_URL}/api/auth/organization/approve?token={approval_token}&silent=true"
            decline_url = f"{settings.FRONTEND_URL}/api/auth/organization/decline?token={decline_token}&silent=true"

        # HTML version
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .info-section {{ background: white; border-left: 4px solid #667eea; padding: 20px; margin: 20px 0; border-radius: 5px; }}
        .info-row {{ display: flex; padding: 8px 0; border-bottom: 1px solid #eee; }}
        .info-label {{ font-weight: bold; min-width: 180px; color: #555; }}
        .info-value {{ color: #333; flex: 1; }}
        .button-container {{ text-align: center; margin: 30px 0; }}
        .button {{ display: inline-block; padding: 14px 32px; margin: 8px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 14px; }}
        .button-view {{ background: #667eea; color: white; }}
        .button-approve {{ background: #10b981; color: white; }}
        .button-decline {{ background: #ef4444; color: white; }}
        .alert {{ background: #e0f2fe; border-left: 4px solid #0ea5e9; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏢 New Organization Onboarding</h1>
            <p style="margin: 0; opacity: 0.9;">Action Required: Review and Approve</p>
        </div>
        <div class="content">
            <div class="alert">
                <strong>📋 Summary:</strong> A new organization has completed their onboarding profile and is ready for review.
            </div>

            <div class="info-section">
                <h3 style="margin-top: 0; color: #667eea;">👤 User Information</h3>
                <div class="info-row">
                    <span class="info-label">Name:</span>
                    <span class="info-value">{user_data.get('first_name', '')} {user_data.get('last_name', '')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Email:</span>
                    <span class="info-value">{user_data.get('email', 'N/A')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Role:</span>
                    <span class="info-value">{user_data.get('role', 'N/A')}</span>
                </div>
            </div>

            <div class="info-section">
                <h3 style="margin-top: 0; color: #667eea;">🏢 Organization Information</h3>
                <div class="info-row">
                    <span class="info-label">Organization Name:</span>
                    <span class="info-value"><strong>{organization_data.get('name', 'N/A')}</strong></span>
                </div>
                <div class="info-row">
                    <span class="info-label">Legal Business Name:</span>
                    <span class="info-value">{organization_data.get('legal_business_name', 'N/A')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Industry:</span>
                    <span class="info-value">{organization_data.get('industry', 'N/A')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Email:</span>
                    <span class="info-value">{organization_data.get('email', 'N/A')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Phone:</span>
                    <span class="info-value">{organization_data.get('phone', 'N/A')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Website:</span>
                    <span class="info-value">{organization_data.get('website', 'N/A')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Timezone:</span>
                    <span class="info-value">{organization_data.get('timezone', 'N/A')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Currency:</span>
                    <span class="info-value">{organization_data.get('default_currency', 'N/A')}</span>
                </div>
            </div>

            <div class="button-container">
                <a href="{view_url}" class="button button-view">📄 View Full Details</a>
                <a href="{approve_url}" class="button button-approve">✓ Approve</a>
                <a href="{decline_url}" class="button button-decline">✗ Decline</a>
            </div>

            <div class="footer">
                <p><strong>Action Required:</strong> Please review the organization details and approve or decline their access.</p>
                <p>Best regards,<br>AlsaTalk Automated Notification System</p>
                <p>&copy; 2025 AlsaTalk. All rights reserved.</p>
            </div>
        </div>
    </div>
</body>
</html>
        """

        part = MIMEText(html, "html")
        msg.attach(part)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        return True

    except Exception as e:
        print(f"Error sending admin notification email: {str(e)}")
        return False


def send_organization_approved_email(
    email: str, first_name: str, organization_name: str
) -> bool:
    """
    Send email to user when their organization is approved
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"✓ Your AlsaTalk Organization Has Been Approved!"
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = email

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .success-box {{ background: #d1fae5; border: 2px solid #10b981; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0; }}
        .button {{ display: inline-block; background: #667eea; color: white; padding: 14px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: bold; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Congratulations!</h1>
        </div>
        <div class="content">
            <p>Hi {first_name},</p>
            <div class="success-box">
                <h2 style="color: #10b981; margin: 0;">✓ Organization Approved</h2>
                <p style="margin: 10px 0 0 0; font-size: 18px;"><strong>{organization_name}</strong></p>
            </div>
            <p>Great news! Your organization has been reviewed and approved by our team.</p>
            <p><strong>You can now login with your credentials and start using AlsaTalk!</strong></p>
            <div style="text-align: center;">
                <a href="{settings.FRONTEND_URL}/login" class="button">Login to AlsaTalk</a>
            </div>
            <p>If you have any questions or need assistance getting started, please don't hesitate to reach out to our support team.</p>
            <div class="footer">
                <p>Best regards,<br>The AlsaTalk Team</p>
                <p>&copy; 2025 AlsaTalk. All rights reserved.</p>
            </div>
        </div>
    </div>
</body>
</html>
        """

        part = MIMEText(html, "html")
        msg.attach(part)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        return True

    except Exception as e:
        print(f"Error sending approval email: {str(e)}")
        return False


def send_organization_declined_email(
    email: str, first_name: str, organization_name: str, reason: str = None
) -> bool:
    """
    Send email to user when their organization is declined
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Update on Your AlsaTalk Organization Application"
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = email

        reason_html = (
            f"""
            <div class="reason-box">
                <strong>Reason:</strong> {reason}
            </div>
        """
            if reason
            else ""
        )

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .decline-box {{ background: #fee2e2; border: 2px solid #ef4444; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0; }}
        .reason-box {{ background: white; border-left: 4px solid #ef4444; padding: 15px; margin: 20px 0; }}
        .contact-box {{ background: #dbeafe; border-left: 4px solid #3b82f6; padding: 15px; margin: 20px 0; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Organization Application Update</h1>
        </div>
        <div class="content">
            <p>Hi {first_name},</p>
            <div class="decline-box">
                <h2 style="color: #ef4444; margin: 0;">Application Not Approved</h2>
                <p style="margin: 10px 0 0 0; font-size: 18px;"><strong>{organization_name}</strong></p>
            </div>
            <p>Thank you for your interest in AlsaTalk. After reviewing your organization application, we are unable to approve it at this time.</p>
            {reason_html}
            <div class="contact-box">
                <strong>Need Help?</strong><br>
                If you have questions or would like to discuss this decision, please contact our support team at <a href="mailto:{settings.SMTP_FROM_EMAIL}">{settings.SMTP_FROM_EMAIL}</a>
            </div>
            <div class="footer">
                <p>Best regards,<br>The AlsaTalk Team</p>
                <p>&copy; 2025 AlsaTalk. All rights reserved.</p>
            </div>
        </div>
    </div>
</body>
</html>
        """

        part = MIMEText(html, "html")
        msg.attach(part)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        return True

    except Exception as e:
        print(f"Error sending decline email: {str(e)}")
        return False


def send_user_credentials_email(
    email: str, first_name: str, last_name: str, temp_password: str
) -> bool:
    """
    Send email to new user with their login credentials
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Your AlsaTalk Account Has Been Created"
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = email

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .credentials-box {{ background: white; border: 2px solid #667eea; padding: 20px; margin: 20px 0; border-radius: 5px; }}
        .credential-row {{ padding: 10px; border-bottom: 1px solid #eee; }}
        .credential-label {{ font-weight: bold; color: #555; }}
        .credential-value {{ color: #667eea; font-family: monospace; font-size: 16px; }}
        .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
        .button {{ display: inline-block; background: #667eea; color: white; padding: 14px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: bold; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to AlsaTalk! 🎉</h1>
        </div>
        <div class="content">
            <p>Hi {first_name} {last_name},</p>
            <p>Your AlsaTalk account has been created by your organization administrator. Below are your login credentials:</p>

            <div class="credentials-box">
                <div class="credential-row">
                    <div class="credential-label">Email:</div>
                    <div class="credential-value">{email}</div>
                </div>
                <div class="credential-row" style="border-bottom: none;">
                    <div class="credential-label">Temporary Password:</div>
                    <div class="credential-value">{temp_password}</div>
                </div>
            </div>

            <div class="warning">
                <strong>🔒 Important Security Notice:</strong> Please reset your password immediately after your first login using the "Forgot Password" feature.
            </div>

            <div style="text-align: center;">
                <a href="{settings.FRONTEND_URL}/login" class="button">Login to AlsaTalk</a>
            </div>

            <p><strong>Next Steps:</strong></p>
            <ol>
                <li>Click the login button above or visit our login page</li>
                <li>Enter your email and temporary password</li>
                <li>Use "Forgot Password" to set your own secure password</li>
            </ol>

            <div class="footer">
                <p>Best regards,<br>The AlsaTalk Team</p>
                <p>&copy; 2025 AlsaTalk. All rights reserved.</p>
            </div>
        </div>
    </div>
</body>
</html>
        """

        part = MIMEText(html, "html")
        msg.attach(part)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        return True

    except Exception as e:
        print(f"Error sending credentials email: {str(e)}")
        return False
