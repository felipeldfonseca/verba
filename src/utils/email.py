"""
Email utility module for sending meeting minutes via email.

This module provides functionality to send generated PDF documents via email.
"""

import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional, Union
import os


logger = logging.getLogger(__name__)


class EmailSender:
    """Email sender for meeting minutes."""
    
    def __init__(
        self,
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True
    ):
        """
        Initialize email sender.
        
        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP server port
            username: Email username
            password: Email password
            use_tls: Whether to use TLS encryption
        """
        self.smtp_server = smtp_server or os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.username = username or os.getenv("SMTP_USERNAME")
        self.password = password or os.getenv("SMTP_PASSWORD")
        self.use_tls = use_tls
        
        if not self.username or not self.password:
            raise ValueError("Email username and password are required")
    
    def send_meeting_minutes(
        self,
        pdf_path: Union[str, Path],
        to_email: str,
        meeting_title: str = "Ata de Reunião",
        from_email: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
        additional_attachments: Optional[List[Union[str, Path]]] = None
    ) -> bool:
        """
        Send meeting minutes PDF via email.
        
        Args:
            pdf_path: Path to the PDF file
            to_email: Recipient email address
            meeting_title: Meeting title for subject
            from_email: Sender email address (defaults to username)
            cc_emails: List of CC email addresses
            bcc_emails: List of BCC email addresses
            additional_attachments: List of additional files to attach
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return False
        
        if not from_email:
            from_email = self.username
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = f"Ata de Reunião: {meeting_title}"
        
        if cc_emails:
            msg['Cc'] = ', '.join(cc_emails)
        
        # Email body
        body = self._create_email_body(meeting_title, pdf_path)
        msg.attach(MIMEText(body, 'html', 'utf-8'))
        
        # Attach PDF
        try:
            with open(pdf_path, 'rb') as f:
                pdf_attachment = MIMEApplication(f.read(), _subtype='pdf')
                pdf_attachment.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=pdf_path.name
                )
                msg.attach(pdf_attachment)
        except Exception as e:
            logger.error(f"Error attaching PDF: {e}")
            return False
        
        # Attach additional files
        if additional_attachments:
            for file_path in additional_attachments:
                if not self._attach_file(msg, file_path):
                    logger.warning(f"Failed to attach file: {file_path}")
        
        # Send email
        return self._send_email(msg, to_email, cc_emails, bcc_emails)
    
    def _create_email_body(self, meeting_title: str, pdf_path: Path) -> str:
        """
        Create HTML email body.
        
        Args:
            meeting_title: Meeting title
            pdf_path: Path to PDF file
            
        Returns:
            HTML email body
        """
        from datetime import datetime
        
        current_date = datetime.now().strftime("%d/%m/%Y")
        
        body = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .header {{
                    background-color: #f4f4f4;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px;
                }}
                .content {{
                    padding: 20px;
                }}
                .footer {{
                    background-color: #f9f9f9;
                    padding: 15px;
                    text-align: center;
                    font-size: 12px;
                    color: #666;
                    border-radius: 5px;
                }}
                .attachment-info {{
                    background-color: #e7f3ff;
                    padding: 15px;
                    border-left: 4px solid #007cba;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Ata de Reunião Gerada Automaticamente</h2>
                <p><strong>{meeting_title}</strong></p>
                <p>Data: {current_date}</p>
            </div>
            
            <div class="content">
                <p>Olá,</p>
                
                <p>Segue em anexo a ata da reunião gerada automaticamente pelo sistema Verba.</p>
                
                <div class="attachment-info">
                    <h4>📎 Arquivo Anexo:</h4>
                    <p><strong>{pdf_path.name}</strong></p>
                    <p>Tamanho: {self._format_file_size(pdf_path.stat().st_size)}</p>
                </div>
                
                <p>O documento contém as seguintes seções:</p>
                <ul>
                    <li><strong>Resumo Executivo:</strong> Principais pontos da reunião</li>
                    <li><strong>Decisões:</strong> Decisões tomadas durante a reunião</li>
                    <li><strong>Próximas Ações:</strong> Tarefas e responsáveis</li>
                    <li><strong>Transcrição Completa:</strong> Texto integral da reunião</li>
                </ul>
                
                <p>Se você tiver dúvidas sobre o conteúdo ou encontrar algum problema, entre em contato conosco.</p>
                
                <p>Atenciosamente,<br>
                <strong>Sistema Verba</strong></p>
            </div>
            
            <div class="footer">
                <p>Este e-mail foi enviado automaticamente pelo sistema Verba.</p>
                <p>Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """
        
        return body
    
    def _attach_file(self, msg: MIMEMultipart, file_path: Union[str, Path]) -> bool:
        """
        Attach a file to the email message.
        
        Args:
            msg: Email message object
            file_path: Path to file to attach
            
        Returns:
            True if file was attached successfully, False otherwise
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False
        
        try:
            with open(file_path, 'rb') as f:
                # Determine MIME type based on file extension
                if file_path.suffix.lower() == '.pdf':
                    attachment = MIMEApplication(f.read(), _subtype='pdf')
                elif file_path.suffix.lower() in ['.docx', '.doc']:
                    attachment = MIMEApplication(f.read(), _subtype='msword')
                elif file_path.suffix.lower() == '.json':
                    attachment = MIMEApplication(f.read(), _subtype='json')
                else:
                    attachment = MIMEApplication(f.read(), _subtype='octet-stream')
                
                attachment.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=file_path.name
                )
                msg.attach(attachment)
                
            return True
            
        except Exception as e:
            logger.error(f"Error attaching file {file_path}: {e}")
            return False
    
    def _send_email(
        self,
        msg: MIMEMultipart,
        to_email: str,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None
    ) -> bool:
        """
        Send the email message.
        
        Args:
            msg: Email message object
            to_email: Recipient email address
            cc_emails: List of CC email addresses
            bcc_emails: List of BCC email addresses
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            # Create recipient list
            recipients = [to_email]
            if cc_emails:
                recipients.extend(cc_emails)
            if bcc_emails:
                recipients.extend(bcc_emails)
            
            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                
                server.login(self.username, self.password)
                
                # Send email
                server.send_message(msg, to_addrs=recipients)
                
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def _format_file_size(self, size_bytes: int) -> str:
        """
        Format file size in human-readable format.
        
        Args:
            size_bytes: File size in bytes
            
        Returns:
            Formatted file size string
        """
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def test_connection(self) -> bool:
        """
        Test SMTP connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
            
            logger.info("SMTP connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False


def send_meeting_minutes(
    pdf_path: Union[str, Path],
    to_email: str,
    meeting_title: str = "Ata de Reunião",
    from_email: Optional[str] = None,
    cc_emails: Optional[List[str]] = None
) -> bool:
    """
    Convenience function to send meeting minutes via email.
    
    Args:
        pdf_path: Path to the PDF file
        to_email: Recipient email address
        meeting_title: Meeting title for subject
        from_email: Sender email address
        cc_emails: List of CC email addresses
        
    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        sender = EmailSender()
        return sender.send_meeting_minutes(
            pdf_path, to_email, meeting_title, from_email, cc_emails
        )
    except Exception as e:
        logger.error(f"Error sending meeting minutes: {e}")
        return False 