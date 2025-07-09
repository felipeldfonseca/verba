"""
Unit tests for the translate module (azure.py).

These tests verify Azure translation functionality.
"""

import asyncio
import json
import os
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.translate.azure import (
    AzureTranslator, 
    TranslationResult, 
    translate_text, 
    translate_segments_async,
    translate_segments
)


class TestTranslationResult:
    """Test cases for TranslationResult dataclass."""
    
    def test_translation_result_creation(self):
        """Test TranslationResult creation with all fields."""
        result = TranslationResult(
            original_text="Hello world",
            translated_text="Olá mundo",
            source_language="en",
            target_language="pt",
            confidence=0.95,
            processing_time=1.5
        )
        
        assert result.original_text == "Hello world"
        assert result.translated_text == "Olá mundo"
        assert result.source_language == "en"
        assert result.target_language == "pt"
        assert result.confidence == 0.95
        assert result.processing_time == 1.5


class TestAzureTranslator:
    """Test cases for AzureTranslator class."""
    
    def test_init_with_env_vars(self):
        """Test AzureTranslator initialization with environment variables."""
        with patch.dict(os.environ, {
            'AZURE_TRANSLATOR_KEY': 'test_key',
            'AZURE_TRANSLATOR_ENDPOINT': 'https://test.translator.com',
            'AZURE_TRANSLATOR_REGION': 'westus'
        }):
            translator = AzureTranslator()
            
            assert translator.subscription_key == 'test_key'
            assert translator.endpoint == 'https://test.translator.com'
            assert translator.region == 'westus'
            assert translator.target_language == 'pt'
    
    def test_init_with_parameters(self):
        """Test AzureTranslator initialization with explicit parameters."""
        translator = AzureTranslator(
            subscription_key='param_key',
            endpoint='https://param.translator.com',
            region='eastus',
            target_language='es'
        )
        
        assert translator.subscription_key == 'param_key'
        assert translator.endpoint == 'https://param.translator.com'
        assert translator.region == 'eastus'
        assert translator.target_language == 'es'
    
    def test_init_missing_subscription_key(self):
        """Test AzureTranslator initialization with missing subscription key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Azure Translator subscription key is required"):
                AzureTranslator()
    
    def test_init_defaults(self):
        """Test AzureTranslator initialization with default values."""
        translator = AzureTranslator(subscription_key='test_key')
        
        assert translator.endpoint == 'https://api.cognitive.microsofttranslator.com'
        assert translator.region == 'eastus'
        assert translator.target_language == 'pt'
        assert translator.api_version == '3.0'
    
    def test_headers_configuration(self):
        """Test that headers are configured correctly."""
        translator = AzureTranslator(
            subscription_key='test_key',
            region='westus'
        )
        
        expected_headers = {
            'Ocp-Apim-Subscription-Key': 'test_key',
            'Ocp-Apim-Subscription-Region': 'westus',
            'Content-Type': 'application/json'
        }
        
        assert translator.headers == expected_headers
    
    @pytest.mark.asyncio
    @patch('src.translate.azure.aiohttp.ClientSession')
    async def test_translate_text_success(self, mock_session):
        """Test successful text translation."""
        # Mock response data
        mock_response_data = [{
            'detectedLanguage': {
                'language': 'en',
                'score': 0.95
            },
            'translations': [{
                'text': 'Olá mundo',
                'to': 'pt'
            }]
        }]
        
        # Mock aiohttp session and response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_response_data
        
        mock_session_instance = AsyncMock()
        mock_session_instance.post.return_value.__aenter__.return_value = mock_response
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        translator = AzureTranslator(subscription_key='test_key')
        
        result = await translator.translate_text('Hello world')
        
        assert isinstance(result, TranslationResult)
        assert result.original_text == 'Hello world'
        assert result.translated_text == 'Olá mundo'
        assert result.source_language == 'en'
        assert result.target_language == 'pt'
        assert result.confidence == 0.95
        assert result.processing_time > 0
    
    @pytest.mark.asyncio
    @patch('src.translate.azure.aiohttp.ClientSession')
    async def test_translate_text_with_source_language(self, mock_session):
        """Test text translation with specified source language."""
        mock_response_data = [{
            'translations': [{
                'text': 'Hola mundo',
                'to': 'es'
            }]
        }]
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_response_data
        
        mock_session_instance = AsyncMock()
        mock_session_instance.post.return_value.__aenter__.return_value = mock_response
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        translator = AzureTranslator(subscription_key='test_key')
        
        result = await translator.translate_text(
            'Hello world',
            source_language='en',
            target_language='es'
        )
        
        assert result.translated_text == 'Hola mundo'
        assert result.source_language == 'en'
        assert result.target_language == 'es'
        assert result.confidence == 1.0  # Default when no detection info
    
    @pytest.mark.asyncio
    @patch('src.translate.azure.aiohttp.ClientSession')
    async def test_translate_text_api_error(self, mock_session):
        """Test translation with API error."""
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.text.return_value = "Bad Request"
        
        mock_session_instance = AsyncMock()
        mock_session_instance.post.return_value.__aenter__.return_value = mock_response
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        translator = AzureTranslator(subscription_key='test_key')
        
        with pytest.raises(Exception, match="Translation API error 400"):
            await translator.translate_text('Hello world')
    
    @pytest.mark.asyncio
    @patch('src.translate.azure.aiohttp.ClientSession')
    async def test_translate_batch_success(self, mock_session):
        """Test successful batch translation."""
        mock_response_data = [
            {
                'detectedLanguage': {'language': 'en', 'score': 0.95},
                'translations': [{'text': 'Olá mundo', 'to': 'pt'}]
            },
            {
                'detectedLanguage': {'language': 'en', 'score': 0.92},
                'translations': [{'text': 'Este é um teste', 'to': 'pt'}]
            }
        ]
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_response_data
        
        mock_session_instance = AsyncMock()
        mock_session_instance.post.return_value.__aenter__.return_value = mock_response
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        translator = AzureTranslator(subscription_key='test_key')
        
        texts = ['Hello world', 'This is a test']
        results = await translator.translate_batch(texts)
        
        assert len(results) == 2
        assert results[0].translated_text == 'Olá mundo'
        assert results[1].translated_text == 'Este é um teste'
        assert all(r.source_language == 'en' for r in results)
        assert all(r.target_language == 'pt' for r in results)
    
    @pytest.mark.asyncio
    @patch('src.translate.azure.aiohttp.ClientSession')
    async def test_translate_batch_large_batch(self, mock_session):
        """Test batch translation with large batch that needs splitting."""
        # Mock response for multiple batches
        mock_response_data = [
            {
                'detectedLanguage': {'language': 'en', 'score': 0.95},
                'translations': [{'text': f'Texto {i}', 'to': 'pt'}]
            }
            for i in range(50)  # 50 items per batch
        ]
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_response_data
        
        mock_session_instance = AsyncMock()
        mock_session_instance.post.return_value.__aenter__.return_value = mock_response
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        translator = AzureTranslator(subscription_key='test_key')
        
        # Create 150 texts (should be split into 3 batches of 50)
        texts = [f'Text {i}' for i in range(150)]
        results = await translator.translate_batch(texts, batch_size=50)
        
        assert len(results) == 150
        # Should have made 3 API calls (150/50 = 3)
        assert mock_session_instance.post.call_count == 3
    
    @pytest.mark.asyncio
    @patch('src.translate.azure.aiohttp.ClientSession')
    async def test_detect_language_success(self, mock_session):
        """Test successful language detection."""
        mock_response_data = [{
            'language': 'en',
            'score': 0.95
        }]
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_response_data
        
        mock_session_instance = AsyncMock()
        mock_session_instance.post.return_value.__aenter__.return_value = mock_response
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        translator = AzureTranslator(subscription_key='test_key')
        
        result = await translator.detect_language('Hello world')
        
        assert result['language'] == 'en'
        assert result['confidence'] == 0.95
    
    @pytest.mark.asyncio
    @patch('src.translate.azure.aiohttp.ClientSession')
    async def test_detect_language_api_error(self, mock_session):
        """Test language detection with API error."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text.return_value = "Internal Server Error"
        
        mock_session_instance = AsyncMock()
        mock_session_instance.post.return_value.__aenter__.return_value = mock_response
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        translator = AzureTranslator(subscription_key='test_key')
        
        with pytest.raises(Exception, match="Language detection API error 500"):
            await translator.detect_language('Hello world')
    
    @pytest.mark.asyncio
    @patch('src.translate.azure.aiohttp.ClientSession')
    async def test_translate_segments_success(self, mock_session):
        """Test successful segment translation."""
        mock_response_data = [
            {
                'detectedLanguage': {'language': 'en', 'score': 0.95},
                'translations': [{'text': 'Olá mundo', 'to': 'pt'}]
            },
            {
                'detectedLanguage': {'language': 'en', 'score': 0.92},
                'translations': [{'text': 'Este é um teste', 'to': 'pt'}]
            }
        ]
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_response_data
        
        mock_session_instance = AsyncMock()
        mock_session_instance.post.return_value.__aenter__.return_value = mock_response
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        translator = AzureTranslator(subscription_key='test_key')
        
        segments = [
            {'text': 'Hello world', 'start_seconds': 0.0, 'end_seconds': 5.0},
            {'text': 'This is a test', 'start_seconds': 5.0, 'end_seconds': 10.0}
        ]
        
        result = await translator.translate_segments(segments)
        
        assert len(result) == 2
        assert result[0]['text_translated'] == 'Olá mundo'
        assert result[1]['text_translated'] == 'Este é um teste'
        assert result[0]['translation_confidence'] == 0.95
        assert result[1]['translation_confidence'] == 0.92
        assert result[0]['source_language'] == 'en'
        assert result[1]['source_language'] == 'en'
        assert result[0]['target_language'] == 'pt'
        assert result[1]['target_language'] == 'pt'
        
        # Original segment data should be preserved
        assert result[0]['start_seconds'] == 0.0
        assert result[0]['end_seconds'] == 5.0
    
    @pytest.mark.asyncio
    async def test_translate_segments_empty_list(self):
        """Test segment translation with empty list."""
        translator = AzureTranslator(subscription_key='test_key')
        
        result = await translator.translate_segments([])
        
        assert result == []
    
    @pytest.mark.asyncio
    @patch('src.translate.azure.aiohttp.ClientSession')
    async def test_translate_segments_missing_text(self, mock_session):
        """Test segment translation with missing text fields."""
        mock_response_data = [
            {
                'detectedLanguage': {'language': 'en', 'score': 0.95},
                'translations': [{'text': 'Olá mundo', 'to': 'pt'}]
            },
            {
                'detectedLanguage': {'language': 'unknown', 'score': 0.0},
                'translations': [{'text': '', 'to': 'pt'}]
            }
        ]
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_response_data
        
        mock_session_instance = AsyncMock()
        mock_session_instance.post.return_value.__aenter__.return_value = mock_response
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        translator = AzureTranslator(subscription_key='test_key')
        
        segments = [
            {'text': 'Hello world', 'start_seconds': 0.0},
            {'raw_text': '', 'start_seconds': 5.0},  # Missing 'text' field
        ]
        
        result = await translator.translate_segments(segments)
        
        assert len(result) == 2
        assert result[0]['text_translated'] == 'Olá mundo'
        assert result[1]['text_translated'] == ''  # Empty text translated to empty
    
    @pytest.mark.asyncio
    @patch('src.translate.azure.aiohttp.ClientSession')
    async def test_translate_segments_with_raw_text(self, mock_session):
        """Test segment translation using raw_text field."""
        mock_response_data = [{
            'detectedLanguage': {'language': 'en', 'score': 0.95},
            'translations': [{'text': 'Olá mundo', 'to': 'pt'}]
        }]
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_response_data
        
        mock_session_instance = AsyncMock()
        mock_session_instance.post.return_value.__aenter__.return_value = mock_response
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        translator = AzureTranslator(subscription_key='test_key')
        
        segments = [
            {'raw_text': 'Hello world', 'start_seconds': 0.0}  # No 'text' field
        ]
        
        result = await translator.translate_segments(segments)
        
        assert len(result) == 1
        assert result[0]['text_translated'] == 'Olá mundo'


class TestStandaloneFunctions:
    """Test cases for standalone functions."""
    
    @pytest.mark.asyncio
    @patch('src.translate.azure.AzureTranslator')
    async def test_translate_text_convenience_function(self, mock_translator_class):
        """Test translate_text convenience function."""
        # Mock translator
        mock_translator = AsyncMock()
        mock_translator_class.return_value = mock_translator
        
        # Mock translation result
        mock_result = TranslationResult(
            original_text='Hello world',
            translated_text='Olá mundo',
            source_language='en',
            target_language='pt',
            confidence=0.95,
            processing_time=1.0
        )
        mock_translator.translate_text.return_value = mock_result
        
        # Call the function
        result = await translate_text(
            'Hello world',
            source_language='en',
            target_language='pt',
            subscription_key='test_key',
            endpoint='https://test.com',
            region='westus'
        )
        
        # Verify translator was created with correct parameters
        mock_translator_class.assert_called_once_with(
            subscription_key='test_key',
            endpoint='https://test.com',
            region='westus',
            target_language='pt'
        )
        
        # Verify translation method was called
        mock_translator.translate_text.assert_called_once_with(
            'Hello world', 'en', 'pt'
        )
        
        assert result == mock_result
    
    @pytest.mark.asyncio
    @patch('src.translate.azure.AzureTranslator')
    async def test_translate_segments_async_convenience_function(self, mock_translator_class):
        """Test translate_segments_async convenience function."""
        # Mock translator
        mock_translator = AsyncMock()
        mock_translator_class.return_value = mock_translator
        
        # Mock translation result
        mock_result = [
            {
                'text': 'Hello world',
                'text_translated': 'Olá mundo',
                'translation_confidence': 0.95,
                'source_language': 'en',
                'target_language': 'pt'
            }
        ]
        mock_translator.translate_segments.return_value = mock_result
        
        # Test segments
        segments = [
            {'text': 'Hello world', 'start_seconds': 0.0, 'end_seconds': 5.0}
        ]
        
        # Call the function
        result = await translate_segments_async(
            segments,
            source_language='en',
            target_language='pt',
            subscription_key='test_key'
        )
        
        # Verify translator was created and called correctly
        mock_translator_class.assert_called_once_with(
            subscription_key='test_key',
            endpoint=None,
            region=None,
            target_language='pt'
        )
        
        mock_translator.translate_segments.assert_called_once_with(
            segments, 'en', 'pt'
        )
        
        assert result == mock_result
    
    @patch('src.translate.azure.asyncio.run')
    @patch('src.translate.azure.translate_segments_async')
    def test_translate_segments_sync_wrapper(self, mock_translate_async, mock_asyncio_run):
        """Test translate_segments synchronous wrapper."""
        # Mock async function result
        mock_result = [
            {
                'text': 'Hello world',
                'text_translated': 'Olá mundo',
                'translation_confidence': 0.95
            }
        ]
        mock_asyncio_run.return_value = mock_result
        
        # Test segments
        segments = [
            {'text': 'Hello world', 'start_seconds': 0.0}
        ]
        
        # Call the function
        result = translate_segments(
            segments,
            source_language='en',
            target_language='pt',
            subscription_key='test_key'
        )
        
        # Verify asyncio.run was called with the async function
        mock_asyncio_run.assert_called_once()
        
        assert result == mock_result
    
    @pytest.mark.asyncio
    @patch('src.translate.azure.AzureTranslator')
    async def test_translate_text_with_defaults(self, mock_translator_class):
        """Test translate_text with default parameters."""
        # Mock translator
        mock_translator = AsyncMock()
        mock_translator_class.return_value = mock_translator
        
        mock_result = TranslationResult(
            original_text='Hello',
            translated_text='Olá',
            source_language='en',
            target_language='pt',
            confidence=0.95,
            processing_time=1.0
        )
        mock_translator.translate_text.return_value = mock_result
        
        # Call with minimal parameters
        result = await translate_text('Hello')
        
        # Verify translator was created with defaults
        mock_translator_class.assert_called_once_with(
            subscription_key=None,
            endpoint=None,
            region=None,
            target_language='pt'
        )
        
        mock_translator.translate_text.assert_called_once_with(
            'Hello', None, 'pt'
        )
        
        assert result == mock_result


if __name__ == "__main__":
    pytest.main([__file__]) 