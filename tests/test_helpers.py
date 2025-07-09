"""
Unit tests for utility helpers module.
"""

import pytest
from unittest.mock import patch, mock_open, MagicMock
import tempfile
import os
import json
import logging
from pathlib import Path
import time

from src.utils.helpers import (
    timing_decorator,
    chunk_text,
    chunk_segments,
    estimate_tokens,
    calculate_cost,
    generate_slug,
    extract_video_id,
    create_output_directory,
    load_config,
    save_metadata,
    compute_file_hash,
    setup_logging,
    validate_environment,
    format_duration,
    clean_filename,
    ProgressTracker,
    ensure_directory
)


class TestTimingDecorator:
    """Test cases for timing decorator."""
    
    def test_timing_decorator_success(self):
        """Test timing decorator with successful function execution."""
        @timing_decorator
        def test_func(x, y):
            time.sleep(0.1)  # Simulate work
            return x + y
        
        with patch('src.utils.helpers.logger') as mock_logger:
            result = test_func(1, 2)
            assert result == 3
            mock_logger.info.assert_called_once()
            assert "test_func executed in" in mock_logger.info.call_args[0][0]
    
    def test_timing_decorator_exception(self):
        """Test timing decorator with function that raises exception."""
        @timing_decorator
        def failing_func():
            time.sleep(0.1)
            raise ValueError("Test error")
        
        with patch('src.utils.helpers.logger') as mock_logger:
            with pytest.raises(ValueError, match="Test error"):
                failing_func()
            
            mock_logger.error.assert_called_once()
            assert "failing_func failed after" in mock_logger.error.call_args[0][0]
    
    def test_timing_decorator_preserves_function_metadata(self):
        """Test that timing decorator preserves function metadata."""
        @timing_decorator
        def documented_func():
            """This function has documentation."""
            return "result"
        
        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "This function has documentation."


class TestTextProcessing:
    """Test cases for text processing functions."""
    
    def test_chunk_text_small(self):
        """Test chunking text that's smaller than max tokens."""
        text = "This is a small text."
        chunks = chunk_text(text, max_tokens=1000)
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_chunk_text_large(self):
        """Test chunking large text."""
        # Create text that's roughly 8000 characters (2000 tokens)
        text = "This is a sentence. " * 400
        chunks = chunk_text(text, max_tokens=500)  # 2000 chars max
        
        assert len(chunks) > 1
        assert all(len(chunk) <= 2000 for chunk in chunks)
    
    def test_chunk_text_empty(self):
        """Test chunking empty text."""
        chunks = chunk_text("", max_tokens=1000)
        assert chunks == []
    
    def test_chunk_text_with_overlap(self):
        """Test chunking with overlap."""
        text = "Sentence one. Sentence two. Sentence three. Sentence four."
        chunks = chunk_text(text, max_tokens=10, overlap=20)  # 40 chars max, 20 overlap
        
        assert len(chunks) > 1
        # Check that there's some overlap between consecutive chunks
        for i in range(len(chunks) - 1):
            # There should be some common text between chunks
            assert any(word in chunks[i+1] for word in chunks[i].split()[-3:])
    
    def test_chunk_text_sentence_boundary(self):
        """Test chunking with sentence boundary detection."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = chunk_text(text, max_tokens=15, overlap=0)  # 60 chars max
        
        # Should break at sentence boundaries when possible
        assert len(chunks) > 1
        assert all(chunk.endswith('.') or chunk == chunks[-1] for chunk in chunks)
    
    def test_chunk_text_word_boundary(self):
        """Test chunking with word boundary detection."""
        text = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10"
        chunks = chunk_text(text, max_tokens=10, overlap=0)  # 40 chars max
        
        # Should break at word boundaries
        assert len(chunks) > 1
        assert all(not chunk.endswith(' ') for chunk in chunks)
    
    def test_chunk_segments(self):
        """Test segment chunking."""
        segments = [
            {"text": "A" * 100, "start": "00:00:01.000"},
            {"text": "B" * 200, "start": "00:00:02.000"},
            {"text": "C" * 150, "start": "00:00:03.000"}
        ]
        
        chunks = chunk_segments(segments, max_tokens=100)  # 400 chars max
        
        assert len(chunks) > 1
        assert all(isinstance(chunk, list) for chunk in chunks)
        assert all(len(chunk) > 0 for chunk in chunks)
    
    def test_chunk_segments_empty(self):
        """Test segment chunking with empty list."""
        chunks = chunk_segments([], max_tokens=100)
        assert chunks == []
    
    def test_chunk_segments_with_translated_text(self):
        """Test segment chunking with translated text."""
        segments = [
            {"text_translated": "A" * 100, "start": "00:00:01.000"},
            {"text_translated": "B" * 200, "start": "00:00:02.000"}
        ]
        
        chunks = chunk_segments(segments, max_tokens=50)  # 200 chars max
        
        assert len(chunks) > 1
        assert all(isinstance(chunk, list) for chunk in chunks)
    
    def test_estimate_tokens(self):
        """Test token estimation."""
        assert estimate_tokens("") == 0
        assert estimate_tokens("test") == 1  # 4 chars / 4 = 1 token
        assert estimate_tokens("a" * 400) == 100  # 400 chars / 4 = 100 tokens


class TestCostCalculation:
    """Test cases for cost calculation functions."""
    
    def test_calculate_cost_gpt4o(self):
        """Test cost calculation for GPT-4o."""
        cost = calculate_cost(1000, "gpt-4o")
        assert cost == 0.03  # 1000 tokens * $0.03 / 1000
    
    def test_calculate_cost_gpt4(self):
        """Test cost calculation for GPT-4."""
        cost = calculate_cost(1000, "gpt-4")
        assert cost == 0.06  # 1000 tokens * $0.06 / 1000
    
    def test_calculate_cost_gpt35_turbo(self):
        """Test cost calculation for GPT-3.5-turbo."""
        cost = calculate_cost(1000, "gpt-3.5-turbo")
        assert cost == 0.002  # 1000 tokens * $0.002 / 1000
    
    def test_calculate_cost_azure_translator(self):
        """Test cost calculation for Azure Translator."""
        cost = calculate_cost(1000, "azure-translator")
        assert cost == 0.01  # 1000 tokens * $0.01 / 1000
    
    def test_calculate_cost_unknown_model(self):
        """Test cost calculation for unknown model."""
        cost = calculate_cost(1000, "unknown-model")
        assert cost == 0.03  # Falls back to gpt-4o pricing
    
    def test_calculate_cost_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        cost = calculate_cost(0, "gpt-4o")
        assert cost == 0.0


class TestStringUtilities:
    """Test cases for string utility functions."""
    
    def test_generate_slug(self):
        """Test slug generation."""
        assert generate_slug("Hello World") == "hello-world"
        assert generate_slug("Special @#$% Characters!") == "special-characters"
        assert generate_slug("Multiple   Spaces") == "multiple-spaces"
        
        # Test max length
        long_text = "a" * 100
        slug = generate_slug(long_text, max_length=10)
        assert len(slug) <= 10
    
    def test_generate_slug_hyphen_break(self):
        """Test slug generation with hyphen breaking."""
        text = "this-is-a-very-long-text-that-should-be-truncated-at-hyphen"
        slug = generate_slug(text, max_length=30)
        assert len(slug) <= 30
        assert slug.endswith("-")  # Should break at hyphen
    
    def test_generate_slug_empty_string(self):
        """Test slug generation with empty string."""
        assert generate_slug("") == ""
    
    def test_extract_video_id(self):
        """Test YouTube video ID extraction."""
        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=123s",
            "https://youtube.com/watch?v=dQw4w9WgXcQ"
        ]
        
        for url in urls:
            video_id = extract_video_id(url)
            assert video_id == "dQw4w9WgXcQ"
        
        # Test invalid URL
        assert extract_video_id("https://example.com") is None
        assert extract_video_id("") is None
        assert extract_video_id("not_a_url") is None
    
    def test_format_duration(self):
        """Test duration formatting."""
        assert format_duration(30) == "30.0s"
        assert format_duration(90) == "1m 30s"
        assert format_duration(3661) == "1h 1m 1s"
        assert format_duration(0) == "0.0s"
        assert format_duration(60) == "1m 0s"
        assert format_duration(3600) == "1h 0m 0s"
    
    def test_clean_filename(self):
        """Test filename cleaning."""
        assert clean_filename("hello<world>") == "helloworld"
        assert clean_filename("file with spaces.txt") == "file_with_spaces.txt"
        assert clean_filename("  .hidden  ") == "hidden"
        assert clean_filename("file/with\\slashes") == "filewithslashes"
        assert clean_filename("file|with?special*chars") == "filewithspecialchars"
    
    def test_clean_filename_empty(self):
        """Test filename cleaning with empty/whitespace-only strings."""
        assert clean_filename("") == ""
        assert clean_filename("   ") == ""
        assert clean_filename("...") == ""


class TestDirectoryOperations:
    """Test cases for directory operations."""
    
    def test_create_output_directory(self):
        """Test output directory creation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            video_id = "test_video_123"
            
            output_dir = create_output_directory(base_dir, video_id)
            
            assert output_dir.exists()
            assert output_dir.is_dir()
            assert video_id in output_dir.name
    
    def test_create_output_directory_existing(self):
        """Test output directory creation when directory already exists."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            video_id = "test_video_123"
            
            # Create directory first time
            output_dir1 = create_output_directory(base_dir, video_id)
            
            # Create again - should handle existing directory
            output_dir2 = create_output_directory(base_dir, video_id)
            
            assert output_dir1.exists()
            assert output_dir2.exists()
            # Should be same or similar directory
            assert output_dir1.parent == output_dir2.parent
    
    def test_ensure_directory(self):
        """Test ensure_directory function."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = Path(tmp_dir) / "new_dir" / "nested_dir"
            
            result = ensure_directory(test_path)
            
            assert result.exists()
            assert result.is_dir()
            assert result == test_path
    
    def test_ensure_directory_existing(self):
        """Test ensure_directory with existing directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            existing_dir = Path(tmp_dir)
            
            result = ensure_directory(existing_dir)
            
            assert result == existing_dir
            assert result.exists()
    
    def test_ensure_directory_string_path(self):
        """Test ensure_directory with string path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = os.path.join(tmp_dir, "string_path")
            
            result = ensure_directory(test_path)
            
            assert result.exists()
            assert result.is_dir()
            assert str(result) == test_path


class TestProgressTracker:
    """Test cases for ProgressTracker class."""
    
    def test_progress_tracker_init(self):
        """Test ProgressTracker initialization."""
        tracker = ProgressTracker(10, "Test")
        assert tracker.total_steps == 10
        assert tracker.current_step == 0
        assert tracker.description == "Test"
    
    def test_progress_tracker_update(self):
        """Test progress tracking update."""
        tracker = ProgressTracker(10, "Test")
        tracker.update(3, "Processing")
        assert tracker.current_step == 3
        
        tracker.update(2)
        assert tracker.current_step == 5
    
    def test_progress_tracker_finish(self):
        """Test progress tracking finish."""
        tracker = ProgressTracker(10, "Test")
        tracker.update(5)
        
        with patch('src.utils.helpers.logger') as mock_logger:
            tracker.finish()
            mock_logger.info.assert_called_once()
            assert "Test completed" in mock_logger.info.call_args[0][0]
    
    def test_progress_tracker_percentage(self):
        """Test progress percentage calculation."""
        tracker = ProgressTracker(10, "Test")
        assert tracker.percentage == 0.0
        
        tracker.update(5)
        assert tracker.percentage == 50.0
        
        tracker.update(5)
        assert tracker.percentage == 100.0


class TestEnvironmentValidation:
    """Test cases for environment validation."""
    
    @patch.dict(os.environ, {
        "AZURE_OPENAI_KEY": "test_key",
        "AZURE_OPENAI_ENDPOINT": "test_endpoint",
        "AZURE_TRANSLATOR_KEY": "test_key",
        "AZURE_TRANSLATOR_ENDPOINT": "test_endpoint"
    })
    def test_validate_environment_complete(self):
        """Test environment validation with all variables set."""
        missing = validate_environment()
        assert missing == []
    
    @patch.dict(os.environ, {}, clear=True)
    def test_validate_environment_missing(self):
        """Test environment validation with missing variables."""
        missing = validate_environment()
        assert len(missing) == 4
        assert "AZURE_OPENAI_KEY" in missing
        assert "AZURE_OPENAI_ENDPOINT" in missing
        assert "AZURE_TRANSLATOR_KEY" in missing
        assert "AZURE_TRANSLATOR_ENDPOINT" in missing
    
    @patch.dict(os.environ, {
        "AZURE_OPENAI_KEY": "test_key",
        "AZURE_OPENAI_ENDPOINT": "test_endpoint"
    })
    def test_validate_environment_partial(self):
        """Test environment validation with some variables set."""
        missing = validate_environment()
        assert len(missing) == 2
        assert "AZURE_TRANSLATOR_KEY" in missing
        assert "AZURE_TRANSLATOR_ENDPOINT" in missing


class TestLoggingSetup:
    """Test cases for logging setup."""
    
    @patch('src.utils.helpers.logging.basicConfig')
    def test_setup_logging_default(self, mock_basic_config):
        """Test logging setup with default parameters."""
        setup_logging()
        
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args[1]
        assert call_args['level'] == logging.INFO
        assert 'format' in call_args
    
    @patch('src.utils.helpers.logging.basicConfig')
    def test_setup_logging_custom_level(self, mock_basic_config):
        """Test logging setup with custom level."""
        setup_logging(log_level="DEBUG")
        
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args[1]
        assert call_args['level'] == logging.DEBUG
    
    @patch('src.utils.helpers.logging.basicConfig')
    def test_setup_logging_with_file(self, mock_basic_config):
        """Test logging setup with file output."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            log_file = tmp_file.name
        
        try:
            setup_logging(log_file=log_file)
            
            mock_basic_config.assert_called_once()
            call_args = mock_basic_config.call_args[1]
            assert 'handlers' in call_args
            
        finally:
            os.unlink(log_file)
    
    @patch('src.utils.helpers.logging.basicConfig')
    def test_setup_logging_custom_format(self, mock_basic_config):
        """Test logging setup with custom format."""
        custom_format = "%(levelname)s - %(message)s"
        setup_logging(log_format=custom_format)
        
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args[1]
        assert call_args['format'] == custom_format
    
    @patch('src.utils.helpers.logging.basicConfig')
    def test_setup_logging_invalid_level(self, mock_basic_config):
        """Test logging setup with invalid level."""
        setup_logging(log_level="INVALID")
        
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args[1]
        # Should default to INFO for invalid level
        assert call_args['level'] == logging.INFO


class TestFileOperations:
    """Test cases for file operation functions."""
    
    def test_load_config_existing_file(self):
        """Test loading configuration from existing file."""
        config_data = {"key": "value", "number": 42}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json.dump(config_data, tmp)
            tmp_path = tmp.name
        
        try:
            config = load_config(tmp_path)
            assert config == config_data
        finally:
            os.unlink(tmp_path)
    
    def test_load_config_non_existent_file(self):
        """Test loading configuration from non-existent file."""
        config = load_config("non_existent_file.json")
        assert config == {}
    
    def test_load_config_invalid_json(self):
        """Test loading configuration from invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp.write("invalid json content")
            tmp_path = tmp.name
        
        try:
            config = load_config(tmp_path)
            assert config == {}  # Should return empty dict for invalid JSON
        finally:
            os.unlink(tmp_path)
    
    def test_save_metadata(self):
        """Test saving metadata to JSON file."""
        metadata = {"test": "data", "timestamp": "2024-01-01"}
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            save_metadata(output_dir, metadata)
            
            metadata_file = output_dir / "metadata.json"
            assert metadata_file.exists()
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                assert saved_data == metadata
    
    def test_save_metadata_creates_directory(self):
        """Test that save_metadata creates directory if it doesn't exist."""
        metadata = {"test": "data"}
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "new_dir"
            save_metadata(output_dir, metadata)
            
            assert output_dir.exists()
            metadata_file = output_dir / "metadata.json"
            assert metadata_file.exists()
    
    def test_compute_file_hash(self):
        """Test file hash computation."""
        test_content = b"This is test content"
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(test_content)
            tmp_path = tmp.name
        
        try:
            hash1 = compute_file_hash(tmp_path)
            hash2 = compute_file_hash(tmp_path)
            
            # Same file should produce same hash
            assert hash1 == hash2
            assert len(hash1) == 64  # SHA-256 hex length
            
        finally:
            os.unlink(tmp_path)
    
    def test_compute_file_hash_different_content(self):
        """Test file hash computation with different content."""
        content1 = b"Content 1"
        content2 = b"Content 2"
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp1:
            tmp1.write(content1)
            tmp1_path = tmp1.name
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp2:
            tmp2.write(content2)
            tmp2_path = tmp2.name
        
        try:
            hash1 = compute_file_hash(tmp1_path)
            hash2 = compute_file_hash(tmp2_path)
            
            # Different content should produce different hashes
            assert hash1 != hash2
            
        finally:
            os.unlink(tmp1_path)
            os.unlink(tmp2_path)
    
    def test_compute_file_hash_nonexistent_file(self):
        """Test file hash computation with non-existent file."""
        with pytest.raises(FileNotFoundError):
            compute_file_hash("non_existent_file.txt")


if __name__ == "__main__":
    pytest.main([__file__]) 