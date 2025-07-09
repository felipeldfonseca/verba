"""
Utility helpers module for common functionality.

This module provides common utility functions used throughout the Verba pipeline.
"""

import logging
import time
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
import hashlib
import json
import os


logger = logging.getLogger(__name__)

T = TypeVar('T')


def timing_decorator(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to measure function execution time.
    
    Args:
        func: Function to time
        
    Returns:
        Wrapped function that logs execution time
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} executed in {execution_time:.2f} seconds")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.2f} seconds: {e}")
            raise
    return wrapper


def chunk_text(text: str, max_tokens: int = 7500, overlap: int = 0) -> List[str]:
    """
    Split text into chunks with optional overlap.
    
    Args:
        text: Text to chunk
        max_tokens: Maximum tokens per chunk (≈4 characters per token)
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text:
        return []
    
    max_chars = max_tokens * 4
    
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_chars
        
        # If this is not the last chunk, try to break at a sentence boundary
        if end < len(text):
            # Look for sentence endings within the last 500 characters
            sentence_end = text.rfind('. ', start, end)
            if sentence_end > start and (end - sentence_end) < 500:
                end = sentence_end + 2
            else:
                # Look for word boundaries
                word_end = text.rfind(' ', start, end)
                if word_end > start and (end - word_end) < 100:
                    end = word_end
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position with overlap
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks


def chunk_segments(segments: List[Dict], max_tokens: int = 7500) -> List[List[Dict]]:
    """
    Split segments into chunks based on token count.
    
    Args:
        segments: List of segments from VTT parser
        max_tokens: Maximum tokens per chunk
        
    Returns:
        List of segment chunks
    """
    if not segments:
        return []
    
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for segment in segments:
        # Estimate tokens (≈4 characters per token)
        text = segment.get('text', '') or segment.get('text_translated', '')
        segment_tokens = len(text) // 4
        
        # Check if adding this segment would exceed the limit
        if current_tokens + segment_tokens > max_tokens and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_tokens = 0
        
        current_chunk.append(segment)
        current_tokens += segment_tokens
    
    # Add the last chunk if it has segments
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def estimate_tokens(text: str) -> int:
    """
    Estimate the number of tokens in a text.
    
    Args:
        text: Text to estimate tokens for
        
    Returns:
        Estimated number of tokens
    """
    if not text:
        return 0
    
    # Simple estimation: ≈4 characters per token
    return len(text) // 4


def calculate_cost(tokens: int, model: str = "gpt-4o") -> float:
    """
    Calculate estimated cost for token usage.
    
    Args:
        tokens: Number of tokens used
        model: Model name
        
    Returns:
        Estimated cost in USD
    """
    # Pricing as of 2024 (approximate)
    pricing = {
        "gpt-4o": 0.03,  # $0.03 per 1K tokens
        "gpt-4": 0.06,   # $0.06 per 1K tokens
        "gpt-3.5-turbo": 0.002,  # $0.002 per 1K tokens
        "azure-translator": 0.01,  # $0.01 per 1K characters
    }
    
    rate = pricing.get(model, pricing["gpt-4o"])
    return (tokens / 1000) * rate


def generate_slug(text: str, max_length: int = 50) -> str:
    """
    Generate a URL-friendly slug from text.
    
    Args:
        text: Text to convert to slug
        max_length: Maximum length of the slug
        
    Returns:
        URL-friendly slug
    """
    import re
    
    # Convert to lowercase and replace spaces with hyphens
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    
    # Truncate to max length
    if len(slug) > max_length:
        slug = slug[:max_length]
        # Try to break at a hyphen
        last_hyphen = slug.rfind('-')
        if last_hyphen > max_length // 2:
            slug = slug[:last_hyphen]
    
    return slug.strip('-')


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract video ID from YouTube URL.
    
    Args:
        url: YouTube URL
        
    Returns:
        Video ID if found, None otherwise
    """
    import re
    
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:watch\?v=)([0-9A-Za-z_-]{11})',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def create_output_directory(base_dir: Union[str, Path], video_id: str) -> Path:
    """
    Create output directory for a video processing session.
    
    Args:
        base_dir: Base output directory
        video_id: Video ID for the subdirectory
        
    Returns:
        Path to the created directory
    """
    base_path = Path(base_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = base_path / f"{video_id}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def load_config(config_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load configuration from JSON file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    config_path = Path(config_path)
    
    if not config_path.exists():
        logger.warning(f"Configuration file not found: {config_path}")
        return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return {}


def save_metadata(output_dir: Path, metadata: Dict[str, Any]) -> None:
    """
    Save processing metadata to JSON file.
    
    Args:
        output_dir: Output directory
        metadata: Metadata dictionary
    """
    metadata_file = output_dir / "metadata.json"
    
    try:
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Metadata saved to {metadata_file}")
    except Exception as e:
        logger.error(f"Error saving metadata: {e}")


def compute_file_hash(file_path: Union[str, Path]) -> str:
    """
    Compute SHA-256 hash of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        SHA-256 hash string
    """
    hash_sha256 = hashlib.sha256()
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    
    return hash_sha256.hexdigest()


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Union[str, Path]] = None,
    log_format: Optional[str] = None
) -> None:
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        log_format: Optional log format string
    """
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            *([] if log_file is None else [logging.FileHandler(log_file)])
        ]
    )
    
    # Set specific logger levels
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def validate_environment() -> List[str]:
    """
    Validate that required environment variables are set.
    
    Returns:
        List of missing environment variables
    """
    required_vars = [
        "AZURE_OPENAI_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_TRANSLATOR_KEY",
        "AZURE_TRANSLATOR_ENDPOINT"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    return missing_vars


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}h {minutes}m {secs}s"


def clean_filename(filename: str) -> str:
    """
    Clean filename by removing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename
    """
    import re
    
    # Remove leading/trailing dots and spaces first
    filename = filename.strip('. ')
    
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Replace spaces with underscores
    filename = re.sub(r'\s+', '_', filename)
    
    return filename


class ProgressTracker:
    """Simple progress tracker for long-running operations."""
    
    def __init__(self, total_steps: int, description: str = "Processing"):
        """
        Initialize progress tracker.
        
        Args:
            total_steps: Total number of steps
            description: Description of the operation
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.start_time = time.time()
    
    def update(self, step: int = 1, message: str = "") -> None:
        """
        Update progress.
        
        Args:
            step: Number of steps to advance
            message: Optional status message
        """
        self.current_step += step
        progress = (self.current_step / self.total_steps) * 100
        elapsed = time.time() - self.start_time
        
        status = f"{self.description}: {self.current_step}/{self.total_steps} ({progress:.1f}%)"
        if message:
            status += f" - {message}"
        
        if elapsed > 1:  # Only show ETA after 1 second
            eta = (elapsed / self.current_step) * (self.total_steps - self.current_step)
            status += f" - ETA: {format_duration(eta)}"
        
        logger.info(status)
    
    def finish(self) -> None:
        """Mark progress as finished."""
        total_time = time.time() - self.start_time
        logger.info(f"{self.description} completed in {format_duration(total_time)}")


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure directory exists, creating it if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        Path object for the directory
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path 