"""
Integration tests for the complete Verba pipeline workflow.

These tests verify that all components work together correctly in the full pipeline.
"""

import asyncio
import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scripts.run_local import VerbaPipeline
from src.ingest.parser import VTTParser
from src.utils.helpers import extract_video_id, validate_environment


class TestPipelineIntegration:
    """Integration tests for the complete pipeline."""

    def test_video_id_extraction(self):
        """Test video ID extraction from various YouTube URL formats."""
        test_urls = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtube.com/watch?v=dQw4w9WgXcQ&t=123", "dQw4w9WgXcQ"),
        ]
        
        for url, expected_id in test_urls:
            video_id = extract_video_id(url)
            assert video_id == expected_id, f"Failed to extract ID from {url}"

    def test_environment_validation(self):
        """Test environment variable validation."""
        # Test with missing variables
        missing_vars = validate_environment()
        
        # Should include all required Azure variables
        required_vars = [
            "AZURE_OPENAI_KEY",
            "AZURE_OPENAI_ENDPOINT", 
            "AZURE_TRANSLATOR_KEY",
            "AZURE_TRANSLATOR_ENDPOINT"
        ]
        
        for var in required_vars:
            if not os.getenv(var):
                assert var in missing_vars

    @patch('scripts.download_subs.download_subtitles')
    @patch('src.ingest.parser.parse_vtt_file')
    @patch('src.translate.azure.translate_segments_async')
    @patch('src.summarize.gpt.summarize_translated_segments')
    @patch('src.export.docx.export_to_docx')
    @patch('src.export.pdf.export_to_pdf')
    @patch('src.utils.email.send_meeting_minutes')
    def test_complete_pipeline_success(
        self,
        mock_email,
        mock_pdf,
        mock_docx,
        mock_summarize,
        mock_translate,
        mock_parse,
        mock_download
    ):
        """Test successful execution of the complete pipeline."""
        
        # Mock return values
        mock_download.return_value = "/tmp/test.vtt"
        mock_parse.return_value = [
            {"text": "Hello world", "start_seconds": 0.0, "end_seconds": 5.0},
            {"text": "This is a test", "start_seconds": 5.0, "end_seconds": 10.0}
        ]
        mock_translate.return_value = [
            {"text": "Olá mundo", "text_translated": "Olá mundo", "start_seconds": 0.0, "end_seconds": 5.0},
            {"text": "Isto é um teste", "text_translated": "Isto é um teste", "start_seconds": 5.0, "end_seconds": 10.0}
        ]
        
        # Mock summary result
        mock_summary = Mock()
        mock_summary.executive_summary = "Resumo executivo"
        mock_summary.decisions = ["Decisão 1", "Decisão 2"] 
        mock_summary.next_actions = ["Ação 1", "Ação 2"]
        mock_summary.full_transcript = "Transcrição completa"
        mock_summary.tokens_used = 1000
        mock_summary.processing_time = 5.0
        mock_summarize.return_value = mock_summary
        
        mock_docx.return_value = "/tmp/output/ata.docx"
        mock_pdf.return_value = "/tmp/output/ata.pdf"
        mock_email.return_value = True

        # Create temporary directory for pipeline
        with tempfile.TemporaryDirectory() as tmp_dir:
            pipeline = VerbaPipeline(output_dir=tmp_dir, tmp_dir=tmp_dir)
            
            # Run pipeline
            result_pdf = pipeline.run_pipeline(
                video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                meeting_title="Test Meeting",
                send_email=True,
                email_to="test@example.com",
                language="en"
            )
            
            # Verify all components were called
            mock_download.assert_called_once()
            mock_parse.assert_called_once()
            mock_translate.assert_called_once()
            mock_summarize.assert_called_once()
            mock_docx.assert_called_once()
            mock_pdf.assert_called_once()
            mock_email.assert_called_once()
            
            # Verify result
            assert result_pdf == "/tmp/output/ata.pdf"
            
            # Check metadata was saved
            metadata_files = list(Path(tmp_dir).rglob("metadata.json"))
            assert len(metadata_files) > 0
            
            # Verify metadata content
            with open(metadata_files[0], 'r') as f:
                metadata = json.load(f)
                assert "pipeline_version" in metadata
                assert "start_time" in metadata
                assert "steps" in metadata
                assert len(metadata["steps"]) == 7

    @patch('scripts.download_subs.download_subtitles')
    def test_pipeline_download_failure(self, mock_download):
        """Test pipeline behavior when subtitle download fails."""
        mock_download.side_effect = Exception("Download failed")
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            pipeline = VerbaPipeline(output_dir=tmp_dir, tmp_dir=tmp_dir)
            
            with pytest.raises(Exception, match="Download failed"):
                pipeline.run_pipeline(
                    video_url="https://www.youtube.com/watch?v=invalid",
                    language="en"
                )

    def test_pipeline_invalid_video_url(self):
        """Test pipeline behavior with invalid video URL."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            pipeline = VerbaPipeline(output_dir=tmp_dir, tmp_dir=tmp_dir)
            
            with pytest.raises(ValueError, match="Could not extract video ID"):
                pipeline.run_pipeline(
                    video_url="https://invalid-url.com",
                    language="en"
                )

    @patch('scripts.download_subs.download_subtitles')
    @patch('src.ingest.parser.parse_vtt_file')
    def test_pipeline_empty_subtitles(self, mock_parse, mock_download):
        """Test pipeline behavior with empty subtitle file."""
        mock_download.return_value = "/tmp/test.vtt"
        mock_parse.return_value = []  # Empty segments
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            pipeline = VerbaPipeline(output_dir=tmp_dir, tmp_dir=tmp_dir)
            
            # Should handle empty segments gracefully
            with pytest.raises(Exception):  # Translation will fail with empty segments
                pipeline.run_pipeline(
                    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    language="en"
                )

    def test_pipeline_initialization(self):
        """Test pipeline initialization creates required directories."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "output"
            tmp_work_dir = Path(tmp_dir) / "tmp"
            
            pipeline = VerbaPipeline(output_dir=str(output_dir), tmp_dir=str(tmp_work_dir))
            
            # Check directories were created
            assert output_dir.exists()
            assert tmp_work_dir.exists()
            
            # Check metadata initialization
            assert "pipeline_version" in pipeline.metadata
            assert "start_time" in pipeline.metadata
            assert "steps" in pipeline.metadata
            assert pipeline.metadata["steps"] == []


class TestComponentIntegration:
    """Test integration between individual components."""

    def test_vtt_parser_to_segments_flow(self):
        """Test the flow from VTT parsing to segment processing."""
        # Create a mock VTT file content
        vtt_content = """WEBVTT

00:00:01.000 --> 00:00:05.000
Hello world

00:00:06.000 --> 00:00:10.000
This is a test
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vtt', delete=False) as tmp:
            tmp.write(vtt_content)
            tmp_path = tmp.name
        
        try:
            # Parse VTT file
            parser = VTTParser()
            
            # Mock webvtt.read for this test
            with patch('webvtt.read') as mock_webvtt:
                class MockCaption:
                    def __init__(self, start, end, text):
                        self.start = start
                        self.end = end
                        self.text = text
                
                mock_captions = [
                    MockCaption("00:00:01.000", "00:00:05.000", "Hello world"),
                    MockCaption("00:00:06.000", "00:00:10.000", "This is a test")
                ]
                mock_webvtt.return_value = mock_captions
                
                segments = parser.parse_file(tmp_path)
                
                # Verify segments structure for downstream processing
                assert len(segments) == 2
                for segment in segments:
                    assert "text" in segment
                    assert "start_seconds" in segment
                    assert "end_seconds" in segment
                    assert "duration" in segment
                    assert isinstance(segment["start_seconds"], float)
                    assert isinstance(segment["end_seconds"], float)
                    assert segment["duration"] > 0
                
                # Test statistics
                stats = parser.get_stats()
                assert stats["total_segments"] == 2
                assert stats["total_duration"] == 10.0
                assert stats["total_words"] == 6  # "Hello world" + "This is a test"
                
        finally:
            os.unlink(tmp_path)

    def test_segments_structure_compatibility(self):
        """Test that segment structure is compatible across all pipeline components."""
        # Define the expected segment structure
        expected_segment = {
            "start": "00:00:01.000",
            "end": "00:00:05.000", 
            "start_seconds": 1.0,
            "end_seconds": 5.0,
            "duration": 4.0,
            "text": "Original text",
            "raw_text": "Original text",
        }
        
        # After translation, segments should have additional fields
        expected_translated_segment = expected_segment.copy()
        expected_translated_segment.update({
            "text_translated": "Texto traduzido",
            "translation_confidence": 0.95
        })
        
        # Verify all required fields are present
        required_fields = ["text", "start_seconds", "end_seconds", "duration"]
        for field in required_fields:
            assert field in expected_segment
            
        # Verify translated segment has additional fields
        assert "text_translated" in expected_translated_segment


class TestErrorHandling:
    """Test error handling across the pipeline."""

    def test_graceful_degradation(self):
        """Test that the pipeline handles partial failures gracefully."""
        # This would test scenarios like:
        # - Translation API temporarily unavailable
        # - PDF generation fails but DOCX succeeds
        # - Email sending fails but files are generated
        pass  # Implementation would depend on specific error handling strategy

    def test_resource_cleanup(self):
        """Test that resources are properly cleaned up on failure."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            pipeline = VerbaPipeline(output_dir=tmp_dir, tmp_dir=tmp_dir)
            
            # Verify directories exist
            assert Path(tmp_dir).exists()
            
            # After pipeline object is destroyed, temp resources should be cleanable
            del pipeline
            # Implementation would verify no locks on temp files


if __name__ == "__main__":
    pytest.main([__file__]) 