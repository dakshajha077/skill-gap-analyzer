import smtplib
import os
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import json
from io import BytesIO
from datetime import datetime


class EmailConfigError(RuntimeError):
    pass


class EmailSender:
    """Send emails with interview reports to users"""
    
    def __init__(
        self,
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        sender_email=None,
        sender_password=None,
        use_tls=True,
        timeout_seconds=20,
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.use_tls = use_tls
        self.timeout_seconds = timeout_seconds

        self.sender_email = (
            sender_email
            or os.environ.get("MAIL_USERNAME")
            or os.environ.get("GMAIL_EMAIL")
            or ""
        ).strip()
        self.sender_password = (
            sender_password
            or os.environ.get("MAIL_PASSWORD")
            or os.environ.get("GMAIL_PASSWORD")
            or ""
        ).strip()

        self.last_error = None

        if self._looks_like_placeholder(self.sender_email) or self._looks_like_placeholder(self.sender_password):
            raise EmailConfigError(
                "Email is not configured. Set GMAIL_EMAIL and GMAIL_PASSWORD (Gmail App Password), "
                "or MAIL_USERNAME and MAIL_PASSWORD."
            )

    @staticmethod
    def _looks_like_placeholder(value: str) -> bool:
        if not value:
            return True
        lowered = value.strip().lower()
        return lowered in {"your-email@gmail.com", "your-app-password"} or lowered.startswith("your-")
    
    def send_interview_report(self, recipient_email, user_name, interview_data, report_pdf=None):
        """
        Send interview results report via email
        
        Args:
            recipient_email (str): User's email address
            user_name (str): User's name
            interview_data (dict): Interview results data
            report_pdf (bytes): PDF file bytes (optional)
        
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            subject = f"Your Interview Performance Report - {interview_data.get('category', 'Interview')} | SkillGap AI"
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            
            # Generate HTML email body
            html_body = self._generate_html_body(user_name, interview_data)
            text_body = self._generate_text_body(user_name, interview_data)
            
            # Attach HTML and text versions
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            # Attach PDF if provided
            if report_pdf:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(report_pdf)
                encoders.encode_base64(part)
                report_filename = interview_data.get(
                    'report_filename',
                    f"Interview_Report_{interview_data.get('category', 'Report')}.pdf"
                )
                part.add_header('Content-Disposition', 'attachment', 
                               filename=report_filename)
                msg.attach(part)
            
            # Send email
            self.last_error = None
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=self.timeout_seconds) as server:
                server.ehlo()
                if self.use_tls:
                    server.starttls(context=context)
                    server.ehlo()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            print(f"Email sent successfully to {recipient_email}")
            return True
            
        except Exception as e:
            self.last_error = str(e)
            print(f"Error sending email: {self.last_error}")
            return False
    
    def _generate_html_body(self, user_name, data):
        """Generate HTML email body with interview results"""
        
        avg_score = data.get('avg_score', 0)
        category = data.get('category', 'Interview')
        performance_label = data.get('performance_label', 'Average 📈')
        job_label = data.get('job_label', 'Entry Level Roles')
        strong_points = data.get('strong_points', [])
        weak_points = data.get('weak_points', [])
        job_recommendations = data.get('job_recommendations', [])
        profile_details = data.get('profile_details', {})
        
        # Performance color based on score
        if avg_score >= 80:
            score_color = '#10b981'
        elif avg_score >= 65:
            score_color = '#f59e0b'
        elif avg_score >= 50:
            score_color = '#3b82f6'
        else:
            score_color = '#ef4444'
        
        strong_html = ''.join([f'<li style="margin-bottom: 8px;"><span style="color: #10b981;">✓</span> {p}</li>' 
                              for p in strong_points])
        weak_html = ''.join([f'<li style="margin-bottom: 8px;"><span style="color: #f59e0b;">→</span> {p}</li>' 
                            for p in weak_points])
        jobs_html = ''.join([f'<li style="margin-bottom: 8px;"><span style="color: #3b82f6;">📋</span> {job}</li>' 
                            for job in job_recommendations[:5]])
        profile_html = ''.join([
            f'<p style="margin: 0 0 8px;"><strong>{label}:</strong> {value}</p>'
            for label, value in [
                ('Student Name', profile_details.get('name', user_name)),
                ('Email', profile_details.get('email', 'Not available')),
                ('Phone', profile_details.get('phone') or 'Not added'),
                ('Location', profile_details.get('location') or 'Not added'),
                ('Member Since', profile_details.get('member_since', 'Not available')),
            ]
        ])
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif; line-height: 1.6; color: #202124; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: #f8fafc; padding: 20px; border-radius: 12px; }}
                .header {{ background: linear-gradient(135deg, #1a73e8 0%, #34a853 100%); color: white; padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 30px; }}
                .header h1 {{ margin: 0; font-size: 28px; font-weight: bold; }}
                .header p {{ margin: 10px 0 0; opacity: 0.9; }}
                .content {{ background: white; padding: 30px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(60,64,67,0.1); }}
                .score-section {{ text-align: center; padding: 30px; background: linear-gradient(135deg, rgba({self._hex_to_rgb(score_color)},0.1), rgba({self._hex_to_rgb(score_color)},0.05)); border-radius: 12px; margin-bottom: 20px; }}
                .score-ring {{ font-size: 48px; font-weight: bold; color: {score_color}; }}
                .score-label {{ font-size: 18px; font-weight: 600; color: #202124; margin-top: 10px; }}
                .category-label {{ display: inline-block; background-color: #e2e8f0; color: #202124; padding: 6px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; margin-top: 10px; }}
                .section {{ margin-bottom: 25px; }}
                .section-title {{ font-size: 16px; font-weight: 700; color: #202124; margin-bottom: 15px; display: flex; align-items: center; }}
                .section-title i {{ margin-right: 8px; }}
                .section-content {{ margin-left: 20px; }}
                .section-content ul {{ list-style: none; padding: 0; margin: 0; }}
                .section-content li {{ margin-bottom: 10px; color: #5f6368; }}
                .footer {{ background-color: #f1f5f9; padding: 20px; border-radius: 12px; text-align: center; font-size: 13px; color: #80868b; }}
                .button {{ background-color: #1a73e8; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block; margin-top: 15px; font-weight: 600; }}
                .divider {{ border-top: 1px solid #e8eaed; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>SkillGap AI</h1>
                    <p>Your Interview Performance Report</p>
                </div>
                
                <div class="content">
                    <p>Hi <strong>{user_name}</strong>,</p>
                    <p>Thank you for completing your interview session on <strong>{datetime.now().strftime('%B %d, %Y')}</strong>. We've analyzed your performance and generated this comprehensive report.</p>

                    <div class="section">
                        <div class="section-title">👤 Student Profile Details</div>
                        <div class="section-content">
                            {profile_html}
                        </div>
                    </div>
                    
                    <div class="divider"></div>
                    
                    <div class="score-section">
                        <div class="score-ring">{int(avg_score)}<span style="font-size: 32px;">/100</span></div>
                        <div class="score-label">{performance_label}</div>
                        <div class="category-label">{category} Category</div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">💪 Your Strong Points</div>
                        <div class="section-content">
                            <ul>
                                {strong_html}
                            </ul>
                        </div>
                    </div>
                    
                    <div class="divider"></div>
                    
                    <div class="section">
                        <div class="section-title">📈 Areas to Improve</div>
                        <div class="section-content">
                            <ul>
                                {weak_html}
                            </ul>
                        </div>
                    </div>
                    
                    <div class="divider"></div>
                    
                    <div class="section">
                        <div class="section-title">💼 Recommended Job Roles</div>
                        <div class="section-content">
                            <p style="color: #5f6368; margin-bottom: 10px;"><strong>{job_label}</strong></p>
                            <ul>
                                {jobs_html}
                            </ul>
                        </div>
                    </div>
                    
                    <p style="margin-top: 30px; text-align: center;">
                        <a href="https://skillgap-ai.com" class="button">PDF Report Attached</a>
                    </p>
                </div>
                
                <div class="footer">
                    <p>This is an automated email from SkillGap AI. Please do not reply to this email.</p>
                    <p style="margin-top: 10px; color: #999;">© 2026 SkillGap AI. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    def _generate_text_body(self, user_name, data):
        """Generate plain text email body"""
        
        avg_score = data.get('avg_score', 0)
        category = data.get('category', 'Interview')
        performance_label = data.get('performance_label', 'Average')
        job_label = data.get('job_label', 'Entry Level Roles')
        strong_points = data.get('strong_points', [])
        weak_points = data.get('weak_points', [])
        job_recommendations = data.get('job_recommendations', [])
        profile_details = data.get('profile_details', {})
        
        text = f"""
SkillGap AI - Interview Performance Report
==========================================

Hello {user_name},

Thank you for completing your interview session. Here's your performance summary:

STUDENT PROFILE DETAILS:
- Student Name: {profile_details.get('name', user_name)}
- Email: {profile_details.get('email', 'Not available')}
- Phone: {profile_details.get('phone') or 'Not added'}
- Location: {profile_details.get('location') or 'Not added'}
- Member Since: {profile_details.get('member_since', 'Not available')}

OVERALL SCORE: {int(avg_score)}/100
Performance Level: {performance_label}
Category: {category}

STRONG POINTS:
{chr(10).join(['- ' + p for p in strong_points])}

AREAS TO IMPROVE:
{chr(10).join(['- ' + p for p in weak_points])}

RECOMMENDED JOB ROLES ({job_label}):
{chr(10).join(['- ' + job for job in job_recommendations[:5]])}

For a detailed analysis and visual report, please visit your dashboard at:
https://skillgap-ai.com

The PDF report for this session is attached with this email.

Best regards,
SkillGap AI Team

---
This is an automated email. Please do not reply to this message.
"""
        return text
    
    @staticmethod
    def _hex_to_rgb(hex_color):
        """Convert hex color to RGB"""
        hex_color = hex_color.lstrip('#')
        return f"{int(hex_color[0:2], 16)}, {int(hex_color[2:4], 16)}, {int(hex_color[4:6], 16)}"
