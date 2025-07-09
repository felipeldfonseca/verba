"""
Unit tests for the export modules (docx.py and pdf.py).

These tests verify DOCX and PDF generation functionality.
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.export.docx import DocxExporter, export_to_docx, create_template_docx, format_actions_for_docx
from src.export.pdf import PDFExporter, export_to_pdf, convert_docx_to_pdf, create_css_template


class MockSummaryResult:
    """Mock summary result for testing."""
    
    def __init__(self):
        self.resumo_executivo = "Este é um resumo executivo de teste."
        self.decisoes = [
            "Decisão 1: Implementar nova funcionalidade",
            "Decisão 2: Revisar processo existente"
        ]
        self.proximas_acoes = [
            {
                "responsavel": "João",
                "acao": "Criar documentação",
                "prazo": "2024-01-15"
            },
            {
                "responsavel": "Maria",
                "acao": "Revisar código",
                "prazo": "2024-01-20"
            }
        ]
        self.transcricao_completa = "Esta é a transcrição completa da reunião de teste."
        self.tokens_used = 1500
        self.processing_time = 12.5
        self.cost_estimate = 0.045


class TestDocxExporter:
    """Test cases for DocxExporter class."""

    def test_init_default(self):
        """Test DocxExporter initialization with default parameters."""
        exporter = DocxExporter()
        assert exporter.template_path is None

    def test_init_with_template(self):
        """Test DocxExporter initialization with template path."""
        template_path = "/path/to/template.docx"
        exporter = DocxExporter(template_path=template_path)
        assert exporter.template_path == template_path

    @patch('src.export.docx.Document')
    def test_create_document_basic(self, mock_document_class):
        """Test basic document creation."""
        # Mock Document and its methods
        mock_doc = MagicMock()
        mock_document_class.return_value = mock_doc
        
        # Mock properties
        mock_doc.core_properties = MagicMock()
        
        exporter = DocxExporter()
        summary_result = MockSummaryResult()
        
        # Create document
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "test.docx"
            result_path = exporter.create_document(
                summary_result=summary_result,
                meeting_title="Test Meeting",
                company_name="Test Company",
                output_path=output_path
            )
            
            # Verify document was created
            assert result_path == str(output_path)
            mock_document_class.assert_called_once()
            mock_doc.save.assert_called_once_with(str(output_path))

    @patch('src.export.docx.Document')
    def test_create_document_with_template(self, mock_document_class):
        """Test document creation with template."""
        # Create a temporary template file
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_template:
            template_path = tmp_template.name
        
        try:
            mock_doc = MagicMock()
            mock_document_class.return_value = mock_doc
            mock_doc.core_properties = MagicMock()
            
            exporter = DocxExporter(template_path=template_path)
            summary_result = MockSummaryResult()
            
            with tempfile.TemporaryDirectory() as tmp_dir:
                output_path = Path(tmp_dir) / "test.docx"
                result_path = exporter.create_document(
                    summary_result=summary_result,
                    output_path=output_path
                )
                
                # Verify template was used
                mock_document_class.assert_called_once_with(template_path)
                assert result_path == str(output_path)
                
        finally:
            os.unlink(template_path)

    @patch('src.export.docx.Document')
    def test_create_document_auto_path(self, mock_document_class):
        """Test document creation with auto-generated path."""
        mock_doc = MagicMock()
        mock_document_class.return_value = mock_doc
        mock_doc.core_properties = MagicMock()
        
        exporter = DocxExporter()
        summary_result = MockSummaryResult()
        
        result_path = exporter.create_document(summary_result=summary_result)
        
        # Verify auto-generated path
        assert result_path.startswith("ata_")
        assert result_path.endswith(".docx")
        mock_doc.save.assert_called_once()

    @patch('src.export.docx.Document')
    def test_add_header(self, mock_document_class):
        """Test header addition."""
        mock_doc = MagicMock()
        mock_document_class.return_value = mock_doc
        
        # Mock paragraph methods
        mock_para = MagicMock()
        mock_run = MagicMock()
        mock_para.add_run.return_value = mock_run
        mock_doc.add_paragraph.return_value = mock_para
        
        exporter = DocxExporter()
        exporter._add_header(mock_doc, "Test Meeting", "Test Company")
        
        # Verify paragraphs were added (company, title, date, separator, empty)
        assert mock_doc.add_paragraph.call_count >= 4

    @patch('src.export.docx.Document')
    def test_add_summary_sections(self, mock_document_class):
        """Test summary sections addition."""
        mock_doc = MagicMock()
        mock_document_class.return_value = mock_doc
        
        exporter = DocxExporter()
        summary_result = MockSummaryResult()
        
        # Mock the helper methods
        exporter._add_section_heading = MagicMock()
        exporter._add_paragraph = MagicMock()
        exporter._add_bullet_point = MagicMock()
        exporter._add_actions_table = MagicMock()
        exporter._add_processing_info = MagicMock()
        
        exporter._add_summary_sections(mock_doc, summary_result)
        
        # Verify all sections were added
        assert exporter._add_section_heading.call_count == 4  # 4 sections
        assert exporter._add_paragraph.call_count >= 2  # Resumo + Transcrição
        assert exporter._add_bullet_point.call_count == 2  # 2 decisions
        exporter._add_actions_table.assert_called_once()
        exporter._add_processing_info.assert_called_once()

    @patch('src.export.docx.Document')
    def test_add_summary_sections_empty_lists(self, mock_document_class):
        """Test summary sections with empty decisions and actions."""
        mock_doc = MagicMock()
        mock_document_class.return_value = mock_doc
        
        exporter = DocxExporter()
        summary_result = MockSummaryResult()
        summary_result.decisoes = []
        summary_result.proximas_acoes = []
        
        # Mock the helper methods
        exporter._add_section_heading = MagicMock()
        exporter._add_paragraph = MagicMock()
        exporter._add_bullet_point = MagicMock()
        exporter._add_actions_table = MagicMock()
        exporter._add_processing_info = MagicMock()
        
        exporter._add_summary_sections(mock_doc, summary_result)
        
        # Verify bullet points and actions table were not called for empty lists
        exporter._add_bullet_point.assert_not_called()
        exporter._add_actions_table.assert_not_called()
        # But "(nenhuma)" paragraphs should be added
        assert exporter._add_paragraph.call_count >= 4  # Resumo + Transcrição + 2x "(nenhuma)"


class TestDocxFunctions:
    """Test cases for standalone docx functions."""

    @patch('src.export.docx.DocxExporter')
    def test_export_to_docx(self, mock_exporter_class):
        """Test export_to_docx convenience function."""
        mock_exporter = MagicMock()
        mock_exporter_class.return_value = mock_exporter
        mock_exporter.create_document.return_value = "/path/to/output.docx"
        
        summary_result = MockSummaryResult()
        result = export_to_docx(
            summary_result=summary_result,
            meeting_title="Test Meeting",
            company_name="Test Company",
            output_path="/path/to/output.docx",
            template_path="/path/to/template.docx"
        )
        
        # Verify exporter was created and used correctly
        mock_exporter_class.assert_called_once_with(template_path="/path/to/template.docx")
        mock_exporter.create_document.assert_called_once_with(
            summary_result=summary_result,
            meeting_title="Test Meeting",
            company_name="Test Company",
            output_path="/path/to/output.docx"
        )
        assert result == "/path/to/output.docx"

    @patch('src.export.docx.Document')
    def test_create_template_docx(self, mock_document_class):
        """Test template DOCX creation."""
        mock_doc = MagicMock()
        mock_document_class.return_value = mock_doc
        mock_doc.core_properties = MagicMock()
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "template.docx"
            result = create_template_docx(output_path)
            
            assert result == str(output_path)
            mock_doc.save.assert_called_once_with(str(output_path))

    def test_format_actions_for_docx(self):
        """Test action formatting for DOCX."""
        actions = [
            {"responsavel": "João", "acao": "Tarefa 1", "prazo": "2024-01-15"},
            {"responsavel": "Maria", "acao": "Tarefa 2", "prazo": "2024-01-20"}
        ]
        
        result = format_actions_for_docx(actions)
        
        assert "João" in result
        assert "Tarefa 1" in result
        assert "Maria" in result
        assert "Tarefa 2" in result


class TestPDFExporter:
    """Test cases for PDFExporter class."""

    def test_init_default(self):
        """Test PDFExporter initialization with default parameters."""
        exporter = PDFExporter()
        assert exporter.css_path is None
        assert exporter.font_config is not None

    def test_init_with_css(self):
        """Test PDFExporter initialization with CSS path."""
        css_path = "/path/to/styles.css"
        exporter = PDFExporter(css_path=css_path)
        assert exporter.css_path == css_path

    @patch('src.export.pdf.HTML')
    @patch('src.export.pdf.CSS')
    def test_create_pdf_from_html(self, mock_css_class, mock_html_class):
        """Test PDF creation from HTML."""
        # Mock HTML and CSS objects
        mock_html = MagicMock()
        mock_css = MagicMock()
        mock_html_class.return_value = mock_html
        mock_css_class.return_value = mock_css
        
        exporter = PDFExporter()
        html_content = "<html><body><h1>Test</h1></body></html>"
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "test.pdf"
            result = exporter.create_pdf_from_html(html_content, output_path)
            
            assert result == str(output_path)
            mock_html_class.assert_called_once_with(string=html_content)
            mock_html.write_pdf.assert_called_once()

    @patch('src.export.pdf.HTML')
    @patch('src.export.pdf.CSS')
    def test_create_pdf_from_html_with_css(self, mock_css_class, mock_html_class):
        """Test PDF creation from HTML with custom CSS."""
        mock_html = MagicMock()
        mock_css = MagicMock()
        mock_html_class.return_value = mock_html
        mock_css_class.return_value = mock_css
        
        exporter = PDFExporter()
        html_content = "<html><body><h1>Test</h1></body></html>"
        css_content = "body { font-family: Arial; }"
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "test.pdf"
            result = exporter.create_pdf_from_html(html_content, output_path, css_content)
            
            assert result == str(output_path)
            mock_css_class.assert_called_once_with(string=css_content, font_config=exporter.font_config)

    @patch('src.export.pdf.PDFExporter.create_pdf_from_html')
    def test_create_pdf_from_summary(self, mock_create_pdf):
        """Test PDF creation from summary result."""
        mock_create_pdf.return_value = "/path/to/output.pdf"
        
        exporter = PDFExporter()
        summary_result = MockSummaryResult()
        
        result = exporter.create_pdf_from_summary(
            summary_result=summary_result,
            meeting_title="Test Meeting",
            company_name="Test Company",
            output_path="/path/to/output.pdf"
        )
        
        assert result == "/path/to/output.pdf"
        mock_create_pdf.assert_called_once()

    def test_generate_html_content(self):
        """Test HTML content generation."""
        exporter = PDFExporter()
        summary_result = MockSummaryResult()
        
        html_content = exporter._generate_html_content(
            summary_result=summary_result,
            meeting_title="Test Meeting",
            company_name="Test Company"
        )
        
        # Verify key content is present
        assert "Test Company" in html_content
        assert "Test Meeting" in html_content
        assert "Resumo Executivo" in html_content
        assert "Decisões" in html_content
        assert "Próximas Ações" in html_content
        assert "Transcrição Completa" in html_content
        assert summary_result.resumo_executivo in html_content
        assert summary_result.transcricao_completa in html_content

    def test_generate_html_content_empty_lists(self):
        """Test HTML content generation with empty decisions and actions."""
        exporter = PDFExporter()
        summary_result = MockSummaryResult()
        summary_result.decisoes = []
        summary_result.proximas_acoes = []
        
        html_content = exporter._generate_html_content(
            summary_result=summary_result,
            meeting_title="Test Meeting",
            company_name="Test Company"
        )
        
        # Verify empty state messages are present
        assert "(nenhuma)" in html_content

    def test_format_transcript(self):
        """Test transcript formatting."""
        exporter = PDFExporter()
        transcript = "Este é um texto longo que precisa ser formatado adequadamente."
        
        result = exporter._format_transcript(transcript)
        
        # Should return HTML-safe content
        assert isinstance(result, str)
        assert len(result) > 0

    def test_escape_html(self):
        """Test HTML escaping."""
        exporter = PDFExporter()
        
        # Test special characters
        test_cases = [
            ("<script>", "&lt;script&gt;"),
            ("Text & more", "Text &amp; more"),
            ("Quote \"here\"", "Quote &quot;here&quot;"),
            ("Normal text", "Normal text")
        ]
        
        for input_text, expected in test_cases:
            result = exporter._escape_html(input_text)
            assert result == expected

    def test_get_default_css(self):
        """Test default CSS generation."""
        exporter = PDFExporter()
        css = exporter._get_default_css()
        
        # Verify CSS contains essential styles
        assert "body" in css
        assert "font-family" in css
        assert "header" in css
        assert "h1" in css
        assert ".actions-table" in css


class TestPDFFunctions:
    """Test cases for standalone PDF functions."""

    @patch('src.export.pdf.PDFExporter')
    def test_export_to_pdf(self, mock_exporter_class):
        """Test export_to_pdf convenience function."""
        mock_exporter = MagicMock()
        mock_exporter_class.return_value = mock_exporter
        mock_exporter.create_pdf_from_summary.return_value = "/path/to/output.pdf"
        
        summary_result = MockSummaryResult()
        result = export_to_pdf(
            summary_result=summary_result,
            meeting_title="Test Meeting",
            company_name="Test Company",
            output_path="/path/to/output.pdf",
            css_path="/path/to/styles.css"
        )
        
        # Verify exporter was created and used correctly
        mock_exporter_class.assert_called_once_with(css_path="/path/to/styles.css")
        mock_exporter.create_pdf_from_summary.assert_called_once_with(
            summary_result=summary_result,
            meeting_title="Test Meeting",
            company_name="Test Company",
            output_path="/path/to/output.pdf"
        )
        assert result == "/path/to/output.pdf"

    @patch('subprocess.run')
    def test_convert_docx_to_pdf(self, mock_subprocess):
        """Test DOCX to PDF conversion."""
        mock_subprocess.return_value.returncode = 0
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_docx:
            docx_path = tmp_docx.name
        
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                result = convert_docx_to_pdf(docx_path)
                
                # Verify auto-generated PDF path
                assert result.endswith('.pdf')
                
        finally:
            os.unlink(docx_path)

    def test_create_css_template(self):
        """Test CSS template creation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "template.css"
            result = create_css_template(output_path)
            
            assert result == str(output_path)
            assert output_path.exists()
            
            # Verify CSS content
            with open(output_path, 'r', encoding='utf-8') as f:
                css_content = f.read()
                assert "body" in css_content
                assert "font-family" in css_content


if __name__ == "__main__":
    pytest.main([__file__]) 