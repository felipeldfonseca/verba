"""
VTT parser module for converting subtitle files to structured JSON format.

This module parses .vtt (WebVTT) subtitle files and converts them into
structured JSON segments for further processing by the Verba pipeline.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union
import webvtt


logger = logging.getLogger(__name__)


class VTTParser:
    """Parser for WebVTT subtitle files."""
    
    def __init__(self):
        """Initialize the VTT parser."""
        self.segments = []
        
    def parse_file(self, vtt_file_path: Union[str, Path]) -> List[Dict]:
        """
        Parse a VTT file and return structured segments.
        
        Args:
            vtt_file_path: Path to the .vtt file
            
        Returns:
            List of segments with start, end, and text information
            
        Raises:
            FileNotFoundError: If the VTT file doesn't exist
            ValueError: If the file is not a valid VTT file
        """
        vtt_path = Path(vtt_file_path)
        
        if not vtt_path.exists():
            raise FileNotFoundError(f"VTT file not found: {vtt_file_path}")
        
        if not vtt_path.suffix.lower() == '.vtt':
            raise ValueError(f"File must have .vtt extension: {vtt_file_path}")
        
        try:
            captions = webvtt.read(str(vtt_path))
            segments = []
            
            for caption in captions:
                segment = {
                    "start": caption.start,
                    "end": caption.end,
                    "start_seconds": self._time_to_seconds(caption.start),
                    "end_seconds": self._time_to_seconds(caption.end),
                    "duration": self._time_to_seconds(caption.end) - self._time_to_seconds(caption.start),
                    "text": self._clean_text(caption.text),
                    "raw_text": caption.text
                }
                segments.append(segment)
                
            self.segments = segments
            logger.info(f"Successfully parsed {len(segments)} segments from {vtt_file_path}")
            return segments
            
        except Exception as e:
            logger.error(f"Error parsing VTT file {vtt_file_path}: {e}")
            raise ValueError(f"Invalid VTT file format: {e}")
    
    def _time_to_seconds(self, time_str: str) -> float:
        """
        Convert WebVTT time format to seconds.
        
        Args:
            time_str: Time string in format "HH:MM:SS.mmm" or "MM:SS.mmm"
            
        Returns:
            Time in seconds as float
        """
        try:
            # Split by colon and dot
            parts = time_str.replace(',', '.').split(':')
            
            if len(parts) == 3:
                # HH:MM:SS.mmm format
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
            elif len(parts) == 2:
                # MM:SS.mmm format
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            else:
                logger.warning(f"Unexpected time format: {time_str}")
                return 0.0
                
        except (ValueError, IndexError) as e:
            logger.warning(f"Error parsing time '{time_str}': {e}")
            return 0.0
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize subtitle text.
        
        Args:
            text: Raw subtitle text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove HTML tags (common in VTT files)
        import re
        text = re.sub(r'<[^>]+>', '', text)
        
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def get_full_transcript(self, join_char: str = " ") -> str:
        """
        Get the full transcript text by joining all segments.
        
        Args:
            join_char: Character to join segments with
            
        Returns:
            Full transcript text
        """
        if not self.segments:
            return ""
            
        return join_char.join(segment["text"] for segment in self.segments if segment["text"])
    
    def get_segments_by_time_range(self, start_seconds: float, end_seconds: float) -> List[Dict]:
        """
        Get segments within a specific time range.
        
        Args:
            start_seconds: Start time in seconds
            end_seconds: End time in seconds
            
        Returns:
            List of segments within the time range
        """
        if not self.segments:
            return []
            
        return [
            segment for segment in self.segments
            if segment["start_seconds"] >= start_seconds and segment["end_seconds"] <= end_seconds
        ]
    
    def export_to_json(self, output_path: Union[str, Path], pretty: bool = True) -> None:
        """
        Export parsed segments to JSON file.
        
        Args:
            output_path: Path to save the JSON file
            pretty: Whether to format JSON with indentation
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(self.segments, f, indent=2, ensure_ascii=False)
            else:
                json.dump(self.segments, f, ensure_ascii=False)
                
        logger.info(f"Exported {len(self.segments)} segments to {output_path}")
    
    def get_stats(self) -> Dict:
        """
        Get statistics about the parsed segments.
        
        Returns:
            Dictionary with statistics
        """
        if not self.segments:
            return {
                "total_segments": 0,
                "total_duration": 0.0,
                "total_words": 0,
                "average_segment_duration": 0.0
            }
        
        total_duration = max(segment["end_seconds"] for segment in self.segments)
        total_words = sum(len(segment["text"].split()) for segment in self.segments)
        avg_duration = sum(segment["duration"] for segment in self.segments) / len(self.segments)
        
        return {
            "total_segments": len(self.segments),
            "total_duration": total_duration,
            "total_words": total_words,
            "average_segment_duration": avg_duration
        }


def parse_vtt_file(vtt_file_path: Union[str, Path]) -> List[Dict]:
    """
    Convenience function to parse a VTT file and return segments.
    
    Args:
        vtt_file_path: Path to the .vtt file
        
    Returns:
        List of parsed segments
    """
    parser = VTTParser()
    return parser.parse_file(vtt_file_path)


def vtt_to_json(vtt_file_path: Union[str, Path], json_output_path: Union[str, Path]) -> None:
    """
    Convert a VTT file to JSON format.
    
    Args:
        vtt_file_path: Path to the input .vtt file
        json_output_path: Path to save the output JSON file
    """
    parser = VTTParser()
    parser.parse_file(vtt_file_path)
    parser.export_to_json(json_output_path) 