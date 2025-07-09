#!/usr/bin/env python3
"""
Download subtitles from YouTube videos using yt-dlp.

This script downloads automatic subtitles from YouTube videos in .vtt format
for processing by the Verba pipeline.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional


def download_subtitles(
    video_url: str, 
    output_dir: str = "tmp", 
    language: str = "en",
    video_id: Optional[str] = None
) -> str:
    """
    Download subtitles from a YouTube video.
    
    Args:
        video_url: YouTube video URL
        output_dir: Directory to save the subtitle file
        language: Language code for subtitles (default: 'en')
        video_id: Optional video ID for filename (extracted from URL if not provided)
    
    Returns:
        Path to the downloaded subtitle file
        
    Raises:
        subprocess.CalledProcessError: If yt-dlp command fails
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Extract video ID from URL if not provided
    if not video_id:
        if "youtu.be/" in video_url:
            video_id = video_url.split("youtu.be/")[1].split("?")[0]
        elif "watch?v=" in video_url:
            video_id = video_url.split("watch?v=")[1].split("&")[0]
        else:
            video_id = "video"
    
    output_template = str(output_path / f"{video_id}.%(ext)s")
    
    # yt-dlp command to download only subtitles
    cmd = [
        "yt-dlp",
        "--write-auto-subs",
        "--sub-lang", language,
        "--skip-download",
        "--output", output_template,
        video_url
    ]
    
    print(f"Downloading subtitles for {video_url}...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"yt-dlp output: {result.stdout}")
        
        # Find the generated subtitle file
        subtitle_file = output_path / f"{video_id}.{language}.vtt"
        if subtitle_file.exists():
            print(f"Subtitles downloaded successfully: {subtitle_file}")
            return str(subtitle_file)
        else:
            # Try to find any .vtt file in the output directory
            vtt_files = list(output_path.glob("*.vtt"))
            if vtt_files:
                print(f"Found subtitle file: {vtt_files[0]}")
                return str(vtt_files[0])
            else:
                raise FileNotFoundError(f"No subtitle file found in {output_path}")
                
    except subprocess.CalledProcessError as e:
        print(f"Error downloading subtitles: {e}")
        print(f"stderr: {e.stderr}")
        raise


def main():
    """Main command-line interface."""
    parser = argparse.ArgumentParser(
        description="Download subtitles from YouTube videos using yt-dlp"
    )
    parser.add_argument(
        "url", 
        help="YouTube video URL"
    )
    parser.add_argument(
        "--output-dir", 
        default="tmp", 
        help="Directory to save subtitle files (default: tmp)"
    )
    parser.add_argument(
        "--language", 
        default="en", 
        help="Language code for subtitles (default: en)"
    )
    parser.add_argument(
        "--video-id", 
        help="Custom video ID for filename (extracted from URL if not provided)"
    )
    
    args = parser.parse_args()
    
    try:
        subtitle_file = download_subtitles(
            args.url, 
            args.output_dir, 
            args.language, 
            args.video_id
        )
        print(f"\nSuccess! Subtitle file saved as: {subtitle_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 