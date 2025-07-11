#!/usr/bin/env python3
"""
Download subtitles from YouTube videos using yt-dlp.

This script downloads automatic subtitles from YouTube videos in .vtt format
for processing by the Verba pipeline.
"""

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple


def download_subtitles(
    video_url: str,
    output_dir: str = "tmp",
    language: str = "en",
    video_id: Optional[str] = None
) -> Tuple[str, int]:
    """
    Download subtitles from a YouTube video using yt-dlp.

    Args:
        video_url: The URL of the YouTube video.
        output_dir: The directory to save the subtitle file.
        language: The language of the subtitles to download.
        video_id: The ID of the video.

    Returns:
        A tuple containing the path to the downloaded VTT file and the video duration in seconds.
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
    
    output_template = f"{output_path}/{video_id}.%(ext)s"
    vtt_path = f"{output_path}/{video_id}.{language}.vtt"

    # yt-dlp command to download only subtitles
    command = [
        "yt-dlp",
        "--write-auto-subs",
        "--sub-lang", language,
        "--skip-download",
        "--output", output_template,
        video_url
    ]
    
    print(f"Downloading subtitles for {video_url}...")
    print(f"Command: {' '.join(command)}")
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print(f"yt-dlp output: {result.stdout}")
        
        # Find the generated subtitle file
        if Path(vtt_path).is_file():
            print(f"Subtitles downloaded successfully: {vtt_path}")
            # Command to get video metadata, including duration
            info_command = [
                "yt-dlp",
                "--dump-single-json",
                "--skip-download",
                video_url
            ]
            try:
                info_result = subprocess.run(info_command, capture_output=True, text=True, check=True)
                video_info = json.loads(info_result.stdout)
                duration = int(video_info.get("duration", 0))
                print(f"Video duration: {duration} seconds")
                return vtt_path, duration
            except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
                print(f"Failed to get video duration: {e}")
                duration = 0
            return vtt_path, duration
        else:
            # Try to find any .vtt file in the output directory
            vtt_files = list(output_path.glob("*.vtt"))
            if vtt_files:
                print(f"Found subtitle file: {vtt_files[0]}")
                return str(vtt_files[0]), 0 # Return 0 for duration if not found
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
        subtitle_file, duration = download_subtitles(
            args.url, 
            args.output_dir, 
            args.language, 
            args.video_id
        )
        print(f"\nSuccess! Subtitle file saved as: {subtitle_file}")
        print(f"Video duration: {duration} seconds")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 