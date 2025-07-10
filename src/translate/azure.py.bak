"""
Azure Translator module for translating text segments.

This module provides functionality to translate text segments using Azure Cognitive Services
Translator API with batch processing and async support.
"""

import asyncio
import aiohttp
import json
import logging
import os
import time
from typing import Dict, List, Optional, Tuple, Union
from uuid import uuid4
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class TranslationResult:
    """Result of a translation operation."""
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    confidence: float
    processing_time: float


class AzureTranslator:
    """Azure Cognitive Services Translator client."""
    
    def __init__(
        self,
        subscription_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        region: Optional[str] = None,
        target_language: str = "pt"
    ):
        """
        Initialize the Azure Translator client.
        
        Args:
            subscription_key: Azure Translator subscription key
            endpoint: Azure Translator endpoint URL
            region: Azure Translator region
            target_language: Target language code (default: 'pt' for Portuguese)
        """
        self.subscription_key = subscription_key or os.getenv("AZURE_TRANSLATOR_KEY")
        self.endpoint = endpoint or os.getenv("AZURE_TRANSLATOR_ENDPOINT", 
                                             "https://api.cognitive.microsofttranslator.com")
        self.region = region or os.getenv("AZURE_TRANSLATOR_REGION", "eastus")
        self.target_language = target_language
        
        if not self.subscription_key:
            raise ValueError("Azure Translator subscription key is required")
        
        # API configuration
        self.api_version = "3.0"
        self.translate_url = f"{self.endpoint}/translate"
        self.detect_url = f"{self.endpoint}/detect"
        
        # Headers for API requests
        self.headers = {
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            'Ocp-Apim-Subscription-Region': self.region,
            'Content-Type': 'application/json'
        }
    
    async def translate_text(
        self,
        text: str,
        source_language: Optional[str] = None,
        target_language: Optional[str] = None
    ) -> TranslationResult:
        """
        Translate a single text string.
        
        Args:
            text: Text to translate
            source_language: Source language code (auto-detect if None)
            target_language: Target language code (uses instance default if None)
            
        Returns:
            TranslationResult object
        """
        target_lang = target_language or self.target_language
        
        # Prepare request parameters
        params = {
            'api-version': self.api_version,
            'to': target_lang
        }
        
        if source_language:
            params['from'] = source_language
        
        # Prepare request body
        body = [{'text': text}]
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.translate_url,
                    params=params,
                    headers=self.headers,
                    json=body
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Translation API error {response.status}: {error_text}")
                    
                    result = await response.json()
                    
                    # Extract translation result
                    translation_data = result[0]
                    detected_language = translation_data.get('detectedLanguage', {}).get('language', source_language or 'unknown')
                    translated_text = translation_data['translations'][0]['text']
                    confidence = translation_data.get('detectedLanguage', {}).get('score', 1.0)
                    
                    processing_time = time.time() - start_time
                    
                    return TranslationResult(
                        original_text=text,
                        translated_text=translated_text,
                        source_language=detected_language,
                        target_language=target_lang,
                        confidence=confidence,
                        processing_time=processing_time
                    )
        
        except Exception as e:
            logger.error(f"Translation error: {e}")
            raise
    
    async def translate_batch(
        self,
        texts: List[str],
        source_language: Optional[str] = None,
        target_language: Optional[str] = None,
        batch_size: int = 100
    ) -> List[TranslationResult]:
        """
        Translate multiple texts in batches.
        
        Args:
            texts: List of texts to translate
            source_language: Source language code (auto-detect if None)
            target_language: Target language code (uses instance default if None)
            batch_size: Maximum number of texts per batch
            
        Returns:
            List of TranslationResult objects
        """
        results = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_results = await self._translate_batch_internal(
                batch, source_language, target_language
            )
            results.extend(batch_results)
        
        return results
    
    async def _translate_batch_internal(
        self,
        texts: List[str],
        source_language: Optional[str] = None,
        target_language: Optional[str] = None
    ) -> List[TranslationResult]:
        """
        Internal method to translate a single batch.
        
        Args:
            texts: List of texts to translate
            source_language: Source language code
            target_language: Target language code
            
        Returns:
            List of TranslationResult objects
        """
        target_lang = target_language or self.target_language
        
        # Prepare request parameters
        params = {
            'api-version': self.api_version,
            'to': target_lang
        }
        
        if source_language:
            params['from'] = source_language
        
        # Prepare request body
        body = [{'text': text} for text in texts]
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.translate_url,
                    params=params,
                    headers=self.headers,
                    json=body
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Translation API error {response.status}: {error_text}")
                    
                    results_data = await response.json()
                    processing_time = time.time() - start_time
                    
                    # Process results
                    results = []
                    for i, result_data in enumerate(results_data):
                        detected_language = result_data.get('detectedLanguage', {}).get('language', source_language or 'unknown')
                        translated_text = result_data['translations'][0]['text']
                        confidence = result_data.get('detectedLanguage', {}).get('score', 1.0)
                        
                        results.append(TranslationResult(
                            original_text=texts[i],
                            translated_text=translated_text,
                            source_language=detected_language,
                            target_language=target_lang,
                            confidence=confidence,
                            processing_time=processing_time / len(texts)  # Distribute time across texts
                        ))
                    
                    return results
        
        except Exception as e:
            logger.error(f"Batch translation error: {e}")
            raise
    
    async def detect_language(self, text: str) -> Dict[str, Union[str, float]]:
        """
        Detect the language of a text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with language code and confidence score
        """
        params = {
            'api-version': self.api_version
        }
        
        body = [{'text': text}]
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.detect_url,
                    params=params,
                    headers=self.headers,
                    json=body
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Language detection API error {response.status}: {error_text}")
                    
                    result = await response.json()
                    detection_data = result[0]
                    
                    return {
                        'language': detection_data['language'],
                        'confidence': detection_data['score']
                    }
        
        except Exception as e:
            logger.error(f"Language detection error: {e}")
            raise
    
    async def translate_segments(
        self,
        segments: List[Dict],
        source_language: Optional[str] = None,
        target_language: Optional[str] = None
    ) -> List[Dict]:
        """
        Translate a list of segments with text content.
        
        Args:
            segments: List of segment dictionaries with 'text' key
            source_language: Source language code (auto-detect if None)
            target_language: Target language code (uses instance default if None)
            
        Returns:
            List of segments with added 'text_translated' and 'translation_confidence' fields
        """
        if not segments:
            return []
        
        # Extract texts from segments
        texts = []
        for segment in segments:
            text = segment.get('text', '') or segment.get('raw_text', '')
            if not text:
                logger.warning(f"Segment missing text: {segment}")
                text = ""
            texts.append(text)
        
        # Translate texts
        translation_results = await self.translate_batch(
            texts, source_language, target_language
        )
        
        # Add translation results to segments
        translated_segments = []
        for i, segment in enumerate(segments):
            translated_segment = segment.copy()
            
            if i < len(translation_results):
                result = translation_results[i]
                translated_segment['text_translated'] = result.translated_text
                translated_segment['translation_confidence'] = result.confidence
                translated_segment['source_language'] = result.source_language
                translated_segment['target_language'] = result.target_language
            else:
                # Fallback for missing translations
                translated_segment['text_translated'] = translated_segment.get('text', '')
                translated_segment['translation_confidence'] = 0.0
                translated_segment['source_language'] = source_language or 'unknown'
                translated_segment['target_language'] = target_language or self.target_language
            
            translated_segments.append(translated_segment)
        
        return translated_segments


# Standalone functions for convenience
async def translate_text(
    text: str,
    source_language: Optional[str] = None,
    target_language: str = "pt",
    subscription_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    region: Optional[str] = None
) -> TranslationResult:
    """
    Translate a single text string using Azure Translator.
    
    Args:
        text: Text to translate
        source_language: Source language code (auto-detect if None)
        target_language: Target language code
        subscription_key: Azure Translator subscription key
        endpoint: Azure Translator endpoint URL
        region: Azure Translator region
        
    Returns:
        TranslationResult object
    """
    translator = AzureTranslator(
        subscription_key=subscription_key,
        endpoint=endpoint,
        region=region,
        target_language=target_language
    )
    
    return await translator.translate_text(text, source_language, target_language)


async def translate_segments_async(
    segments: List[Dict],
    source_language: Optional[str] = None,
    target_language: str = "pt",
    subscription_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    region: Optional[str] = None
) -> List[Dict]:
    """
    Translate a list of segments asynchronously using Azure Translator.
    
    Args:
        segments: List of segment dictionaries with 'text' key
        source_language: Source language code (auto-detect if None)
        target_language: Target language code
        subscription_key: Azure Translator subscription key
        endpoint: Azure Translator endpoint URL
        region: Azure Translator region
        
    Returns:
        List of segments with added translation fields
    """
    translator = AzureTranslator(
        subscription_key=subscription_key,
        endpoint=endpoint,
        region=region,
        target_language=target_language
    )
    
    return await translator.translate_segments(segments, source_language, target_language)


def translate_segments(
    segments: List[Dict],
    source_language: Optional[str] = None,
    target_language: str = "pt",
    subscription_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    region: Optional[str] = None
) -> List[Dict]:
    """
    Synchronous wrapper for translate_segments_async.
    
    Args:
        segments: List of segment dictionaries with 'text' key
        source_language: Source language code (auto-detect if None)
        target_language: Target language code
        subscription_key: Azure Translator subscription key
        endpoint: Azure Translator endpoint URL
        region: Azure Translator region
        
    Returns:
        List of segments with added translation fields
    """
    return asyncio.run(translate_segments_async(
        segments, source_language, target_language,
        subscription_key, endpoint, region
    ))
