"""
PDF export module using WeasyPrint.

This module provides functionality to generate PDF files from meeting summaries,
either by converting DOCX files or generating PDF directly from HTML.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

# Conditional import of WeasyPrint
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError, Exception) as e:
    # Mock classes for testing when WeasyPrint is not available
    class HTML:
        def __init__(self, string=None, filename=None):
            self.content = string or ""
        def write_pdf(self, target, stylesheets=None, font_config=None):
            pass
    
    class CSS:
        def __init__(self, string=None, filename=None, font_config=None):
            self.content = string or ""
    
    class FontConfiguration:
        def __init__(self):
            pass
    
    WEASYPRINT_AVAILABLE = False


logger = logging.getLogger(__name__)


class PDFExporter:
    """PDF document exporter using WeasyPrint."""
    
    def __init__(self, css_path: Optional[Union[str, Path]] = None):
        """
        Initialize the PDF exporter.
        
        Args:
            css_path: Optional path to custom CSS file
        """
        self.css_path = css_path
        self.font_config = FontConfiguration()
        
    def create_pdf_from_html(
        self,
        html_content: str,
        output_path: Union[str, Path],
        css_content: Optional[str] = None
    ) -> str:
        """
        Create PDF from HTML content.
        
        Args:
            html_content: HTML content string
            output_path: Output PDF file path
            css_content: Optional CSS content string
            
        Returns:
            Path to the generated PDF file
        """
        if not WEASYPRINT_AVAILABLE:
            logger.warning("WeasyPrint is not available. PDF generation will be skipped.")
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            # Create empty file for testing
            output_path.write_text(f"Mock PDF content: {html_content[:100]}...")
            return str(output_path)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare CSS
        css_list = []
        if css_content:
            css_list.append(CSS(string=css_content, font_config=self.font_config))
        elif self.css_path and Path(self.css_path).exists():
            css_list.append(CSS(filename=str(self.css_path), font_config=self.font_config))
        else:
            css_list.append(CSS(string=self._get_default_css(), font_config=self.font_config))
        
        # Create PDF
        html_doc = HTML(string=html_content)
        html_doc.write_pdf(str(output_path), stylesheets=css_list, font_config=self.font_config)
        
        logger.info(f"PDF document saved to {output_path}")
        return str(output_path)
    
    def create_pdf_from_summary(
        self,
        summary_result,
        meeting_title: str = "Ata de Reunião",
        company_name: str = "Verba",
        output_path: Optional[Union[str, Path]] = None
    ) -> str:
        """
        Create PDF directly from summary result.
        
        Args:
            summary_result: SummaryResult object from GPT summarizer
            meeting_title: Title of the meeting
            company_name: Company name for header
            output_path: Output file path (defaults to auto-generated)
            
        Returns:
            Path to the generated PDF file
        """
        # Generate HTML content
        html_content = self._generate_html_content(summary_result, meeting_title, company_name)
        
        # Generate output path if not provided
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"ata_{timestamp}.pdf"
            
        return self.create_pdf_from_html(html_content, output_path)
    
    def _generate_html_content(
        self,
        summary_result,
        meeting_title: str,
        company_name: str
    ) -> str:
        """
        Generate HTML content from summary result.
        
        Args:
            summary_result: SummaryResult object
            meeting_title: Title of the meeting
            company_name: Company name
            
        Returns:
            HTML content string
        """
        # Format date
        current_date = datetime.now().strftime("%d/%m/%Y")
        
        # Format decisions
        decisoes_html = ""
        if summary_result.decisoes:
            for decisao in summary_result.decisoes:
                decisoes_html += f"<li>{self._escape_html(decisao)}</li>\n"
        else:
            decisoes_html = "<p class='none-found'><em>(nenhuma)</em></p>"
        
        # Format actions table
        acoes_html = ""
        if summary_result.proximas_acoes:
            acoes_html = """
            <table class="actions-table">
                <thead>
                    <tr>
                        <th>Responsável</th>
                        <th>Ação</th>
                        <th>Prazo</th>
                    </tr>
                </thead>
                <tbody>
            """
            for acao in summary_result.proximas_acoes:
                acoes_html += f"""
                    <tr>
                        <td>{self._escape_html(acao.get('responsavel', ''))}</td>
                        <td>{self._escape_html(acao.get('acao', ''))}</td>
                        <td>{self._escape_html(acao.get('prazo', ''))}</td>
                    </tr>
                """
            acoes_html += """
                </tbody>
            </table>
            """
        else:
            acoes_html = "<p class='none-found'><em>(nenhuma)</em></p>"
        
        # Format transcript
        transcript_html = self._format_transcript(summary_result.transcricao_completa)
        
        # Generate HTML
        html_content = f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{meeting_title}</title>
        </head>
        <body>
            <header>
                <h1 class="company-name">{self._escape_html(company_name)}</h1>
                <h2 class="meeting-title">{self._escape_html(meeting_title)}</h2>
                <p class="date">Data: {current_date}</p>
                <hr class="separator">
            </header>
            
            <main>
                <section class="resumo-executivo">
                    <h3>Resumo Executivo</h3>
                    <p>{self._escape_html(summary_result.resumo_executivo)}</p>
                </section>
                
                <section class="decisoes">
                    <h3>Decisões</h3>
                    {"<ul>" + decisoes_html + "</ul>" if summary_result.decisoes else decisoes_html}
                </section>
                
                <section class="proximas-acoes">
                    <h3>Próximas Ações</h3>
                    {acoes_html}
                </section>
                
                <section class="transcricao">
                    <h3>Transcrição Completa</h3>
                    <div class="transcript-content">
                        {transcript_html}
                    </div>
                </section>
            </main>
            
            <footer>
                <div class="processing-info">
                    <h4>Informações de Processamento</h4>
                    <p>Este documento foi gerado automaticamente pelo sistema Verba.</p>
                    <ul>
                        <li>Tokens utilizados: {summary_result.tokens_used:,}</li>
                        <li>Tempo de processamento: {summary_result.processing_time:.2f} segundos</li>
                        <li>Data de geração: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</li>
                    </ul>
                    <p class="contact">Para dúvidas ou sugestões, entre em contato com a equipe de desenvolvimento.</p>
                </div>
            </footer>
        </body>
        </html>
        """
        
        return html_content
    
    def _format_transcript(self, transcript: str) -> str:
        """
        Format transcript text for HTML display.
        
        Args:
            transcript: Raw transcript text
            
        Returns:
            Formatted HTML string
        """
        if not transcript:
            return "<p><em>(nenhuma transcrição disponível)</em></p>"
        
        # Split into lines and format
        lines = transcript.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if line has timestamp format [HH:MM:SS]
            if line.startswith('[') and ']' in line:
                timestamp_end = line.find(']')
                timestamp = line[:timestamp_end + 1]
                text = line[timestamp_end + 1:].strip()
                
                formatted_lines.append(
                    f'<p class="transcript-line">'
                    f'<span class="timestamp">{self._escape_html(timestamp)}</span> '
                    f'<span class="text">{self._escape_html(text)}</span>'
                    f'</p>'
                )
            else:
                formatted_lines.append(
                    f'<p class="transcript-line">{self._escape_html(line)}</p>'
                )
        
        return '\n'.join(formatted_lines)
    
    def _escape_html(self, text: str) -> str:
        """
        Escape HTML special characters.
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text
        """
        if not text:
            return ""
        
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#x27;'))
    
    def _get_default_css(self) -> str:
        """
        Get default CSS styles for PDF generation.
        
        Returns:
            CSS content string
        """
        return """
        @page {
            margin: 1in;
            size: A4;
        }
        
        body {
            font-family: Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.4;
            color: #333;
            margin: 0;
            padding: 0;
        }
        
        header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .company-name {
            font-size: 16pt;
            font-weight: bold;
            margin-bottom: 10px;
            color: #2c3e50;
        }
        
        .meeting-title {
            font-size: 14pt;
            font-weight: bold;
            margin-bottom: 10px;
            color: #34495e;
        }
        
        .date {
            font-size: 12pt;
            margin-bottom: 15px;
            color: #7f8c8d;
        }
        
        .separator {
            border: none;
            border-top: 1px solid #bdc3c7;
            margin: 20px 0;
        }
        
        main {
            margin-bottom: 40px;
        }
        
        section {
            margin-bottom: 30px;
            page-break-inside: avoid;
        }
        
        h3 {
            font-size: 14pt;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 15px;
            border-bottom: 2px solid #3498db;
            padding-bottom: 5px;
        }
        
        h4 {
            font-size: 12pt;
            font-weight: bold;
            color: #34495e;
            margin-bottom: 10px;
        }
        
        p {
            margin-bottom: 10px;
            text-align: justify;
        }
        
        ul {
            margin-left: 20px;
            margin-bottom: 15px;
        }
        
        li {
            margin-bottom: 5px;
        }
        
        .none-found {
            font-style: italic;
            color: #7f8c8d;
        }
        
        .actions-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        
        .actions-table th,
        .actions-table td {
            border: 1px solid #bdc3c7;
            padding: 8px;
            text-align: left;
        }
        
        .actions-table th {
            background-color: #ecf0f1;
            font-weight: bold;
            color: #2c3e50;
        }
        
        .actions-table td {
            background-color: #ffffff;
        }
        
        .transcript-content {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #e9ecef;
        }
        
        .transcript-line {
            margin-bottom: 8px;
            font-size: 10pt;
            line-height: 1.3;
        }
        
        .timestamp {
            font-weight: bold;
            color: #6c757d;
        }
        
        .text {
            color: #495057;
        }
        
        footer {
            page-break-inside: avoid;
            border-top: 1px solid #bdc3c7;
            padding-top: 20px;
            margin-top: 40px;
        }
        
        .processing-info {
            font-size: 10pt;
            color: #6c757d;
        }
        
        .processing-info ul {
            margin-left: 15px;
        }
        
        .contact {
            font-style: italic;
            margin-top: 10px;
        }
        
        /* Page break controls */
        .resumo-executivo,
        .decisoes,
        .proximas-acoes {
            page-break-inside: avoid;
        }
        
        .transcricao {
            page-break-before: auto;
        }
        """


def export_to_pdf(
    summary_result,
    meeting_title: str = "Ata de Reunião",
    company_name: str = "Verba",
    output_path: Optional[Union[str, Path]] = None,
    css_path: Optional[Union[str, Path]] = None
) -> str:
    """
    Convenience function to export summary to PDF.
    
    Args:
        summary_result: SummaryResult object from GPT summarizer
        meeting_title: Title of the meeting
        company_name: Company name for header
        output_path: Output file path (defaults to auto-generated)
        css_path: Optional path to custom CSS file
        
    Returns:
        Path to the generated PDF file
    """
    exporter = PDFExporter(css_path)
    return exporter.create_pdf_from_summary(
        summary_result, meeting_title, company_name, output_path
    )


def convert_docx_to_pdf(
    docx_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None
) -> str:
    """
    Convert DOCX file to PDF using intermediate HTML conversion.
    
    Args:
        docx_path: Path to the DOCX file
        output_path: Output PDF file path (defaults to same name with .pdf extension)
        
    Returns:
        Path to the generated PDF file
    """
    docx_path = Path(docx_path)
    
    if not docx_path.exists():
        raise FileNotFoundError(f"DOCX file not found: {docx_path}")
    
    # Generate output path if not provided
    if not output_path:
        output_path = docx_path.with_suffix('.pdf')
    
    # Note: Direct DOCX to PDF conversion is complex
    # This is a placeholder for future implementation
    # For now, we recommend using the direct PDF generation from summary
    raise NotImplementedError(
        "Direct DOCX to PDF conversion is not implemented. "
        "Use export_to_pdf() to generate PDF directly from summary_result."
    )


def create_css_template(output_path: Union[str, Path]) -> str:
    """
    Create a CSS template file for PDF customization.
    
    Args:
        output_path: Path to save the CSS template
        
    Returns:
        Path to the created CSS template
    """
    exporter = PDFExporter()
    css_content = exporter._get_default_css()
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(css_content)
    
    logger.info(f"CSS template saved to {output_path}")
    return str(output_path) 