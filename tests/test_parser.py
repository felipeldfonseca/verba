"""
Unit tests for VTT parser module.
"""

import pytest
from pathlib import Path
from unittest.mock import mock_open, patch
import tempfile
import os

from src.ingest.parser import VTTParser, parse_vtt_file, vtt_to_json


class TestVTTParser:
    """Test cases for VTTParser class."""
    
    def test_init(self):
        """Test VTTParser initialization."""
        parser = VTTParser()
        assert parser.segments == []
    
    def test_time_to_seconds(self):
        """Test time format conversion."""
        parser = VTTParser()
        
        # Test HH:MM:SS.mmm format
        assert parser._time_to_seconds("01:23:45.123") == 5025.123
        
        # Test MM:SS.mmm format
        assert parser._time_to_seconds("23:45.123") == 1425.123
        
        # Test with comma instead of dot
        assert parser._time_to_seconds("01:23:45,123") == 5025.123
        
        # Test invalid format
        assert parser._time_to_seconds("invalid") == 0.0
    
    def test_clean_text(self):
        """Test text cleaning functionality."""
        parser = VTTParser()
        
        # Test HTML tag removal
        assert parser._clean_text("<b>Bold text</b>") == "Bold text"
        
        # Test multiple whitespace normalization
        assert parser._clean_text("Multiple    spaces\n\n\nhere") == "Multiple spaces here"
        
        # Test empty string
        assert parser._clean_text("") == ""
        
        # Test None
        assert parser._clean_text(None) == ""
    
    def test_parse_file_not_found(self):
        """Test parsing non-existent file."""
        parser = VTTParser()
        
        with pytest.raises(FileNotFoundError):
            parser.parse_file("non_existent_file.vtt")
    
    def test_parse_file_invalid_extension(self):
        """Test parsing file with invalid extension."""
        parser = VTTParser()
        
        with pytest.raises(ValueError):
            parser.parse_file("test.txt")
    
    @patch('webvtt.read')
    def test_parse_file_success(self, mock_webvtt_read):
        """Test successful VTT file parsing."""
        # Mock webvtt caption objects
        class MockCaption:
            def __init__(self, start, end, text):
                self.start = start
                self.end = end
                self.text = text
        
        mock_captions = [
            MockCaption("00:00:01.000", "00:00:05.000", "Hello world"),
            MockCaption("00:00:06.000", "00:00:10.000", "This is a test")
        ]
        
        mock_webvtt_read.return_value = mock_captions
        
        # Create temporary VTT file
        with tempfile.NamedTemporaryFile(suffix='.vtt', delete=False) as tmp:
            tmp.write(b"WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nHello world")
            tmp_path = tmp.name
        
        try:
            parser = VTTParser()
            segments = parser.parse_file(tmp_path)
            
            assert len(segments) == 2
            assert segments[0]["text"] == "Hello world"
            assert segments[0]["start"] == "00:00:01.000"
            assert segments[0]["end"] == "00:00:05.000"
            assert segments[0]["start_seconds"] == 1.0
            assert segments[0]["end_seconds"] == 5.0
            assert segments[0]["duration"] == 4.0
            
        finally:
            os.unlink(tmp_path)
    
    def test_get_full_transcript(self):
        """Test full transcript generation."""
        parser = VTTParser()
        parser.segments = [
            {"text": "Hello world", "start": "00:00:01.000"},
            {"text": "This is a test", "start": "00:00:06.000"}
        ]
        
        transcript = parser.get_full_transcript()
        assert transcript == "Hello world This is a test"
        
        # Test with custom join character
        transcript = parser.get_full_transcript(join_char="\n")
        assert transcript == "Hello world\nThis is a test"
    
    def test_get_segments_by_time_range(self):
        """Test time range filtering."""
        parser = VTTParser()
        parser.segments = [
            {"text": "Segment 1", "start_seconds": 1.0, "end_seconds": 5.0},
            {"text": "Segment 2", "start_seconds": 6.0, "end_seconds": 10.0},
            {"text": "Segment 3", "start_seconds": 11.0, "end_seconds": 15.0}
        ]
        
        # Test range that includes one segment
        filtered = parser.get_segments_by_time_range(0.0, 7.0)
        assert len(filtered) == 1
        assert filtered[0]["text"] == "Segment 1"
        
        # Test range that includes multiple segments
        filtered = parser.get_segments_by_time_range(0.0, 12.0)
        assert len(filtered) == 2
    
    def test_get_stats(self):
        """Test statistics generation."""
        parser = VTTParser()
        
        # Test empty segments
        stats = parser.get_stats()
        assert stats["total_segments"] == 0
        assert stats["total_duration"] == 0.0
        assert stats["total_words"] == 0
        assert stats["average_segment_duration"] == 0.0
        
        # Test with segments
        parser.segments = [
            {"text": "Hello world", "end_seconds": 5.0, "duration": 4.0},
            {"text": "This is a test", "end_seconds": 10.0, "duration": 4.0}
        ]
        
        stats = parser.get_stats()
        assert stats["total_segments"] == 2
        assert stats["total_duration"] == 10.0
        assert stats["total_words"] == 6  # "Hello world" (2) + "This is a test" (4) = 6
        assert stats["average_segment_duration"] == 4.0
    
    def test_export_to_json(self):
        """Test JSON export functionality."""
        parser = VTTParser()
        parser.segments = [
            {"text": "Hello world", "start": "00:00:01.000", "end": "00:00:05.000"}
        ]
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            parser.export_to_json(tmp_path)
            
            # Verify file exists and contains correct data
            with open(tmp_path, 'r', encoding='utf-8') as f:
                import json
                data = json.load(f)
                assert len(data) == 1
                assert data[0]["text"] == "Hello world"
                
        finally:
            os.unlink(tmp_path)


class TestConvenienceFunctions:
    """Test cases for convenience functions."""
    
    @patch('src.ingest.parser.VTTParser.parse_file')
    def test_parse_vtt_file(self, mock_parse_file):
        """Test parse_vtt_file convenience function."""
        mock_parse_file.return_value = [{"text": "test"}]
        
        result = parse_vtt_file("test.vtt")
        assert result == [{"text": "test"}]
        mock_parse_file.assert_called_once_with("test.vtt")
    
    @patch('src.ingest.parser.VTTParser.parse_file')
    @patch('src.ingest.parser.VTTParser.export_to_json')
    def test_vtt_to_json(self, mock_export_to_json, mock_parse_file):
        """Test vtt_to_json convenience function."""
        mock_parse_file.return_value = [{"text": "test"}]
        
        vtt_to_json("test.vtt", "output.json")
        
        mock_parse_file.assert_called_once_with("test.vtt")
        mock_export_to_json.assert_called_once_with("output.json")


if __name__ == "__main__":
    pytest.main([__file__]) 