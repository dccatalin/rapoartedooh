import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import datetime
from src.data.company_settings import CompanySettings

class EmailService:
    """
    Handles sending emails using SMTP settings from CompanySettings.
    """
    def __init__(self):
        self.cs = CompanySettings()
        
    def _get_smtp_settings(self):
        settings = self.cs.get_settings()
        return {
            'host': settings.get('smtp_host', ''),
            'port': int(settings.get('smtp_port', 587)),
            'user': settings.get('smtp_user', ''),
            'password': settings.get('smtp_password', ''),
            'sender': settings.get('smtp_sender', ''),
            'use_tls': settings.get('smtp_use_tls', True)
        }

    def send_email(self, recipient, subject, body, is_html=True):
        """Send an email to a single recipient"""
        smtp = self._get_smtp_settings()
        
        if not smtp['host'] or not smtp['user'] or not smtp['password']:
            print("EmailService: SMTP settings missing.")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = smtp['sender'] if smtp['sender'] else smtp['user']
            msg['To'] = recipient
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'html' if is_html else 'plain'))

            server = smtplib.SMTP(smtp['host'], smtp['port'])
            if smtp['use_tls']:
                server.starttls()
            
            server.login(smtp['user'], smtp['password'])
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            print(f"EmailService Error: {e}")
            return False

    def send_notification(self, recipient, notification_type, details):
        """Convenience method for sending standard notifications"""
        subject = f"Alerta DOOH: {notification_type}"
        
        # Simple HTML template
        html = f"""
        <html>
        <body style="font-family: sans-serif; color: #333;">
            <h2 style="color: #d9534f;">Alerta Sistem Raportare DOOH</h2>
            <p>A fost generată o notificare de tip: <strong>{notification_type}</strong></p>
            <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; border-left: 5px solid #d9534f;">
                {details}
            </div>
            <p style="font-size: 0.8em; color: #777; margin-top: 20px;">
                Aceasta este un mesaj automat generat la data de {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}.
            </p>
        </body>
        </html>
        """
        return self.send_email(recipient, subject, html)
