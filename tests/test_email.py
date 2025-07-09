"""
Unit tests for the email module (email.py).

These tests verify email sending functionality.
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import sys

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.utils.email import EmailSender, send_meeting_minutes


class TestEmailSender:
    """Test cases for EmailSender class."""
    
    def test_init_with_env_vars(self):
        """Test EmailSender initialization with environment variables."""
        with patch.dict(os.environ, {
            'SMTP_SERVER': 'smtp.test.com',
            'SMTP_PORT': '465',
            'SMTP_USERNAME': 'test@test.com',
            'SMTP_PASSWORD': 'testpass'
        }):
            sender = EmailSender()
            
            assert sender.smtp_server == 'smtp.test.com'
            assert sender.smtp_port == 465
            assert sender.username == 'test@test.com'
            assert sender.password == 'testpass'
            assert sender.use_tls == True
    
    def test_init_with_parameters(self):
        """Test EmailSender initialization with explicit parameters."""
        sender = EmailSender(
            smtp_server='smtp.param.com',
            smtp_port=587,
            username='param@test.com',
            password='parampass',
            use_tls=False
        )
        
        assert sender.smtp_server == 'smtp.param.com'
        assert sender.smtp_port == 587
        assert sender.username == 'param@test.com'
        assert sender.password == 'parampass'
        assert sender.use_tls == False
    
    def test_init_missing_credentials(self):
        """Test EmailSender initialization with missing credentials."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Email username and password are required"):
                EmailSender()
    
    def test_init_missing_password(self):
        """Test EmailSender initialization with missing password."""
        with patch.dict(os.environ, {'SMTP_USERNAME': 'test@test.com'}, clear=True):
            with pytest.raises(ValueError, match="Email username and password are required"):
                EmailSender()
    
    def test_init_defaults(self):
        """Test EmailSender initialization with default values."""
        sender = EmailSender(username='test@test.com', password='testpass')
        
        assert sender.smtp_server == 'smtp.gmail.com'
        assert sender.smtp_port == 587
        assert sender.use_tls == True
    
    @patch('src.utils.email.smtplib.SMTP')
    def test_send_meeting_minutes_success(self, mock_smtp):
        """Test successful email sending."""
        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            tmp_pdf.write(b'PDF content')
            pdf_path = tmp_pdf.name
        
        try:
            # Mock SMTP server
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            sender = EmailSender(
                username='test@test.com',
                password='testpass'
            )
            
            # Mock file operations
            with patch('builtins.open', mock_open(read_data=b'PDF content')):
                result = sender.send_meeting_minutes(
                    pdf_path=pdf_path,
                    to_email='recipient@test.com',
                    meeting_title='Test Meeting'
                )
            
            assert result == True
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with('test@test.com', 'testpass')
            mock_server.send_message.assert_called_once()
            mock_server.quit.assert_called_once()
            
        finally:
            os.unlink(pdf_path)
    
    def test_send_meeting_minutes_file_not_found(self):
        """Test email sending with non-existent PDF file."""
        sender = EmailSender(username='test@test.com', password='testpass')
        
        result = sender.send_meeting_minutes(
            pdf_path='nonexistent.pdf',
            to_email='recipient@test.com'
        )
        
        assert result == False
    
    @patch('src.utils.email.smtplib.SMTP')
    def test_send_meeting_minutes_with_cc_bcc(self, mock_smtp):
        """Test email sending with CC and BCC recipients."""
        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            tmp_pdf.write(b'PDF content')
            pdf_path = tmp_pdf.name
        
        try:
            # Mock SMTP server
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            sender = EmailSender(username='test@test.com', password='testpass')
            
            with patch('builtins.open', mock_open(read_data=b'PDF content')):
                result = sender.send_meeting_minutes(
                    pdf_path=pdf_path,
                    to_email='recipient@test.com',
                    cc_emails=['cc1@test.com', 'cc2@test.com'],
                    bcc_emails=['bcc@test.com'],
                    from_email='sender@test.com'
                )
            
            assert result == True
            mock_server.send_message.assert_called_once()
            
        finally:
            os.unlink(pdf_path)
    
    @patch('src.utils.email.smtplib.SMTP')
    def test_send_meeting_minutes_with_additional_attachments(self, mock_smtp):
        """Test email sending with additional attachments."""
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            tmp_pdf.write(b'PDF content')
            pdf_path = tmp_pdf.name
        
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_txt:
            tmp_txt.write(b'Text content')
            txt_path = tmp_txt.name
        
        try:
            # Mock SMTP server
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            sender = EmailSender(username='test@test.com', password='testpass')
            
            with patch('builtins.open', mock_open(read_data=b'File content')):
                result = sender.send_meeting_minutes(
                    pdf_path=pdf_path,
                    to_email='recipient@test.com',
                    additional_attachments=[txt_path]
                )
            
            assert result == True
            
        finally:
            os.unlink(pdf_path)
            os.unlink(txt_path)
    
    def test_create_email_body(self):
        """Test email body creation."""
        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            tmp_pdf.write(b'PDF content')
            pdf_path = Path(tmp_pdf.name)
        
        try:
            sender = EmailSender(username='test@test.com', password='testpass')
            
            body = sender._create_email_body('Test Meeting', pdf_path)
            
            # Verify key content is present
            assert 'Test Meeting' in body
            assert 'Ata de Reunião Gerada Automaticamente' in body
            assert 'Resumo Executivo' in body
            assert 'Decisões' in body
            assert 'Próximas Ações' in body
            assert 'Transcrição Completa' in body
            assert pdf_path.name in body
            assert 'Sistema Verba' in body
            
        finally:
            os.unlink(pdf_path)
    
    def test_attach_file_success(self):
        """Test successful file attachment."""
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_file:
            tmp_file.write(b'Test content')
            file_path = tmp_file.name
        
        try:
            sender = EmailSender(username='test@test.com', password='testpass')
            
            # Mock MIMEMultipart
            mock_msg = MagicMock()
            
            with patch('builtins.open', mock_open(read_data=b'Test content')):
                result = sender._attach_file(mock_msg, file_path)
            
            assert result == True
            mock_msg.attach.assert_called_once()
            
        finally:
            os.unlink(file_path)
    
    def test_attach_file_not_found(self):
        """Test file attachment with non-existent file."""
        sender = EmailSender(username='test@test.com', password='testpass')
        mock_msg = MagicMock()
        
        result = sender._attach_file(mock_msg, 'nonexistent.txt')
        
        assert result == False
        mock_msg.attach.assert_not_called()
    
    def test_attach_file_read_error(self):
        """Test file attachment with read error."""
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_file:
            tmp_file.write(b'Test content')
            file_path = tmp_file.name
        
        try:
            sender = EmailSender(username='test@test.com', password='testpass')
            mock_msg = MagicMock()
            
            # Mock file open to raise exception
            with patch('builtins.open', side_effect=IOError("Read error")):
                result = sender._attach_file(mock_msg, file_path)
            
            assert result == False
            mock_msg.attach.assert_not_called()
            
        finally:
            os.unlink(file_path)
    
    @patch('src.utils.email.smtplib.SMTP')
    def test_send_email_success(self, mock_smtp):
        """Test successful email sending."""
        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        sender = EmailSender(username='test@test.com', password='testpass')
        
        # Mock message
        mock_msg = MagicMock()
        
        result = sender._send_email(
            msg=mock_msg,
            to_email='recipient@test.com',
            cc_emails=['cc@test.com'],
            bcc_emails=['bcc@test.com']
        )
        
        assert result == True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with('test@test.com', 'testpass')
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()
    
    @patch('src.utils.email.smtplib.SMTP')
    def test_send_email_smtp_error(self, mock_smtp):
        """Test email sending with SMTP error."""
        # Mock SMTP server to raise exception
        mock_smtp.side_effect = Exception("SMTP Error")
        
        sender = EmailSender(username='test@test.com', password='testpass')
        mock_msg = MagicMock()
        
        result = sender._send_email(
            msg=mock_msg,
            to_email='recipient@test.com'
        )
        
        assert result == False
    
    @patch('src.utils.email.smtplib.SMTP')
    def test_send_email_login_error(self, mock_smtp):
        """Test email sending with login error."""
        # Mock SMTP server
        mock_server = MagicMock()
        mock_server.login.side_effect = Exception("Login failed")
        mock_smtp.return_value = mock_server
        
        sender = EmailSender(username='test@test.com', password='testpass')
        mock_msg = MagicMock()
        
        result = sender._send_email(
            msg=mock_msg,
            to_email='recipient@test.com'
        )
        
        assert result == False
        mock_server.quit.assert_called_once()
    
    def test_format_file_size(self):
        """Test file size formatting."""
        sender = EmailSender(username='test@test.com', password='testpass')
        
        # Test different file sizes
        test_cases = [
            (0, "0 B"),
            (512, "512 B"),
            (1024, "1.0 KB"),
            (1536, "1.5 KB"),
            (1048576, "1.0 MB"),
            (1073741824, "1.0 GB")
        ]
        
        for size_bytes, expected in test_cases:
            result = sender._format_file_size(size_bytes)
            assert result == expected
    
    @patch('src.utils.email.smtplib.SMTP')
    def test_test_connection_success(self, mock_smtp):
        """Test successful connection test."""
        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        sender = EmailSender(username='test@test.com', password='testpass')
        
        result = sender.test_connection()
        
        assert result == True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with('test@test.com', 'testpass')
        mock_server.quit.assert_called_once()
    
    @patch('src.utils.email.smtplib.SMTP')
    def test_test_connection_failure(self, mock_smtp):
        """Test connection test failure."""
        # Mock SMTP server to raise exception
        mock_smtp.side_effect = Exception("Connection failed")
        
        sender = EmailSender(username='test@test.com', password='testpass')
        
        result = sender.test_connection()
        
        assert result == False
    
    @patch('src.utils.email.smtplib.SMTP')
    def test_test_connection_no_tls(self, mock_smtp):
        """Test connection test without TLS."""
        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        sender = EmailSender(
            username='test@test.com',
            password='testpass',
            use_tls=False
        )
        
        result = sender.test_connection()
        
        assert result == True
        mock_server.starttls.assert_not_called()
        mock_server.login.assert_called_once_with('test@test.com', 'testpass')
        mock_server.quit.assert_called_once()


class TestStandaloneFunctions:
    """Test cases for standalone functions."""
    
    @patch('src.utils.email.EmailSender')
    def test_send_meeting_minutes_convenience_function(self, mock_email_sender_class):
        """Test send_meeting_minutes convenience function."""
        # Mock EmailSender
        mock_sender = MagicMock()
        mock_email_sender_class.return_value = mock_sender
        mock_sender.send_meeting_minutes.return_value = True
        
        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            tmp_pdf.write(b'PDF content')
            pdf_path = tmp_pdf.name
        
        try:
            result = send_meeting_minutes(
                pdf_path=pdf_path,
                to_email='recipient@test.com',
                meeting_title='Test Meeting',
                from_email='sender@test.com',
                cc_emails=['cc@test.com']
            )
            
            assert result == True
            mock_email_sender_class.assert_called_once()
            mock_sender.send_meeting_minutes.assert_called_once_with(
                pdf_path=pdf_path,
                to_email='recipient@test.com',
                meeting_title='Test Meeting',
                from_email='sender@test.com',
                cc_emails=['cc@test.com']
            )
            
        finally:
            os.unlink(pdf_path)
    
    @patch('src.utils.email.EmailSender')
    def test_send_meeting_minutes_convenience_function_failure(self, mock_email_sender_class):
        """Test send_meeting_minutes convenience function failure."""
        # Mock EmailSender to raise exception
        mock_email_sender_class.side_effect = Exception("Email error")
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            tmp_pdf.write(b'PDF content')
            pdf_path = tmp_pdf.name
        
        try:
            result = send_meeting_minutes(
                pdf_path=pdf_path,
                to_email='recipient@test.com'
            )
            
            assert result == False
            
        finally:
            os.unlink(pdf_path)
    
    @patch('src.utils.email.EmailSender')
    def test_send_meeting_minutes_convenience_function_defaults(self, mock_email_sender_class):
        """Test send_meeting_minutes convenience function with defaults."""
        # Mock EmailSender
        mock_sender = MagicMock()
        mock_email_sender_class.return_value = mock_sender
        mock_sender.send_meeting_minutes.return_value = True
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            tmp_pdf.write(b'PDF content')
            pdf_path = tmp_pdf.name
        
        try:
            result = send_meeting_minutes(
                pdf_path=pdf_path,
                to_email='recipient@test.com'
            )
            
            assert result == True
            mock_sender.send_meeting_minutes.assert_called_once_with(
                pdf_path=pdf_path,
                to_email='recipient@test.com',
                meeting_title='Ata de Reunião',
                from_email=None,
                cc_emails=None
            )
            
        finally:
            os.unlink(pdf_path)


if __name__ == "__main__":
    pytest.main([__file__]) 