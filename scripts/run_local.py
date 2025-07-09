#!/usr/bin/env python3
"""
Main CLI orchestrator for the Verba pipeline.

This script orchestrates the complete pipeline from YouTube video URL to PDF generation.
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

from scripts.download_subs import download_subtitles
from src.ingest.parser import parse_vtt_file
from src.translate.azure import translate_segments_async
from src.summarize.gpt import summarize_translated_segments
from src.export.docx import export_to_docx
from src.export.pdf import export_to_pdf
from src.utils.helpers import (
    setup_logging,
    validate_environment,
    extract_video_id,
    create_output_directory,
    save_metadata,
    timing_decorator,
    format_duration,
    calculate_cost,
    ProgressTracker
)
from src.utils.email import send_meeting_minutes


logger = logging.getLogger(__name__)


class VerbaPipeline:
    """Main pipeline orchestrator for Verba."""
    
    def __init__(self, output_dir: str = "output", tmp_dir: str = "tmp"):
        """
        Initialize the pipeline.
        
        Args:
            output_dir: Base output directory
            tmp_dir: Temporary files directory
        """
        self.output_dir = Path(output_dir)
        self.tmp_dir = Path(tmp_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.tmp_dir.mkdir(exist_ok=True)
        
        self.metadata = {
            "pipeline_version": "1.0.0",
            "start_time": datetime.now().isoformat(),
            "steps": []
        }
    
    @timing_decorator
    def run_pipeline(
        self,
        video_url: str,
        meeting_title: Optional[str] = None,
        send_email: bool = False,
        email_to: Optional[str] = None,
        language: str = "en"
    ) -> str:
        """
        Run the complete pipeline.
        
        Args:
            video_url: YouTube video URL
            meeting_title: Optional meeting title
            send_email: Whether to send email after completion
            email_to: Email address to send to
            language: Subtitle language code
            
        Returns:
            Path to generated PDF file
        """
        start_time = time.time()
        
        # Extract video ID
        video_id = extract_video_id(video_url)
        if not video_id:
            raise ValueError(f"Could not extract video ID from URL: {video_url}")
        
        # Create output directory for this run
        run_output_dir = create_output_directory(self.output_dir, video_id)
        
        # Set up progress tracking
        progress = ProgressTracker(7, "Verba Pipeline")
        
        try:
            # Step 1: Download subtitles
            progress.update(message="Downloading subtitles")
            subtitle_file = self._download_subtitles(video_url, video_id, language)
            self._add_step_metadata("download_subtitles", subtitle_file)
            
            # Step 2: Parse VTT file
            progress.update(message="Parsing subtitles")
            segments = self._parse_vtt_file(subtitle_file)
            self._add_step_metadata("parse_vtt", len(segments))
            
            # Step 3: Translate segments
            progress.update(message="Translating to Portuguese")
            translated_segments = asyncio.run(self._translate_segments(segments))
            self._add_step_metadata("translate_segments", len(translated_segments))
            
            # Step 4: Summarize with GPT
            progress.update(message="Generating summary with GPT-4o")
            summary_result = self._summarize_segments(translated_segments)
            self._add_step_metadata("summarize_segments", {
                "tokens_used": summary_result.tokens_used,
                "processing_time": summary_result.processing_time
            })
            
            # Step 5: Generate DOCX
            progress.update(message="Creating DOCX document")
            docx_path = self._generate_docx(summary_result, meeting_title, run_output_dir)
            self._add_step_metadata("generate_docx", docx_path)
            
            # Step 6: Generate PDF
            progress.update(message="Creating PDF document")
            pdf_path = self._generate_pdf(summary_result, meeting_title, run_output_dir)
            self._add_step_metadata("generate_pdf", pdf_path)
            
            # Step 7: Send email (if requested)
            if send_email and email_to:
                progress.update(message="Sending email")
                email_sent = self._send_email(pdf_path, email_to, meeting_title)
                self._add_step_metadata("send_email", email_sent)
            else:
                progress.update(message="Skipping email")
                self._add_step_metadata("send_email", "skipped")
            
            # Save metadata
            self._finalize_metadata(start_time, pdf_path, summary_result)
            save_metadata(run_output_dir, self.metadata)
            
            progress.finish()
            
            # Print summary
            self._print_summary(pdf_path, summary_result, start_time)
            
            return pdf_path
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            self.metadata["error"] = str(e)
            self.metadata["end_time"] = datetime.now().isoformat()
            save_metadata(run_output_dir, self.metadata)
            raise
    
    def _download_subtitles(self, video_url: str, video_id: str, language: str) -> str:
        """Download subtitles from YouTube."""
        return download_subtitles(video_url, str(self.tmp_dir), language, video_id)
    
    def _parse_vtt_file(self, subtitle_file: str) -> list:
        """Parse VTT file to segments."""
        return parse_vtt_file(subtitle_file)
    
    async def _translate_segments(self, segments: list) -> list:
        """Translate segments to Portuguese."""
        return await translate_segments_async(segments)
    
    def _summarize_segments(self, segments: list):
        """Summarize segments with GPT."""
        return summarize_translated_segments(segments)
    
    def _generate_docx(self, summary_result, meeting_title: Optional[str], output_dir: Path) -> str:
        """Generate DOCX document."""
        title = meeting_title or "Ata de Reunião"
        docx_path = output_dir / "ata.docx"
        return export_to_docx(summary_result, title, "Verba", docx_path)
    
    def _generate_pdf(self, summary_result, meeting_title: Optional[str], output_dir: Path) -> str:
        """Generate PDF document."""
        title = meeting_title or "Ata de Reunião"
        pdf_path = output_dir / "ata.pdf"
        return export_to_pdf(summary_result, title, "Verba", pdf_path)
    
    def _send_email(self, pdf_path: str, email_to: str, meeting_title: Optional[str]) -> bool:
        """Send email with PDF attachment."""
        title = meeting_title or "Ata de Reunião"
        return send_meeting_minutes(pdf_path, email_to, title)
    
    def _add_step_metadata(self, step_name: str, result):
        """Add step metadata."""
        self.metadata["steps"].append({
            "step": step_name,
            "timestamp": datetime.now().isoformat(),
            "result": result
        })
    
    def _finalize_metadata(self, start_time: float, pdf_path: str, summary_result):
        """Finalize metadata with summary information."""
        end_time = time.time()
        total_time = end_time - start_time
        
        self.metadata.update({
            "end_time": datetime.now().isoformat(),
            "total_processing_time": total_time,
            "output_file": pdf_path,
            "summary": {
                "tokens_used": summary_result.tokens_used,
                "processing_time": summary_result.processing_time,
                "estimated_cost": calculate_cost(summary_result.tokens_used),
                "resumo_length": len(summary_result.resumo_executivo),
                "decisoes_count": len(summary_result.decisoes),
                "acoes_count": len(summary_result.proximas_acoes)
            }
        })
    
    def _print_summary(self, pdf_path: str, summary_result, start_time: float):
        """Print pipeline summary."""
        total_time = time.time() - start_time
        
        print("\n" + "="*60)
        print("🎯 VERBA PIPELINE COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"📄 PDF Generated: {pdf_path}")
        print(f"⏱️  Total Time: {format_duration(total_time)}")
        print(f"🔤 Tokens Used: {summary_result.tokens_used:,}")
        print(f"💰 Estimated Cost: ${calculate_cost(summary_result.tokens_used):.4f}")
        print(f"📊 Summary Length: {len(summary_result.resumo_executivo)} chars")
        print(f"✅ Decisions Found: {len(summary_result.decisoes)}")
        print(f"📋 Actions Found: {len(summary_result.proximas_acoes)}")
        
        # Check performance targets
        if total_time <= 180:  # 3 minutes
            print("🚀 Performance: EXCELLENT (≤ 3 minutes)")
        elif total_time <= 300:  # 5 minutes
            print("⚡ Performance: GOOD (≤ 5 minutes)")
        else:
            print("⚠️  Performance: SLOW (> 5 minutes)")
        
        estimated_cost = calculate_cost(summary_result.tokens_used)
        if estimated_cost <= 0.50:
            print("💸 Cost: EXCELLENT (≤ $0.50)")
        elif estimated_cost <= 1.00:
            print("💰 Cost: GOOD (≤ $1.00)")
        else:
            print("💵 Cost: HIGH (> $1.00)")
        
        print("="*60)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Verba - Automatic Meeting Minutes Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_local.py https://youtu.be/abc123 --title "Weekly Standup"
  python run_local.py https://youtu.be/abc123 --email user@company.com --send-email
  python run_local.py https://youtu.be/abc123 --language es --output-dir ./my-output
        """
    )
    
    parser.add_argument(
        "video_url",
        help="YouTube video URL"
    )
    
    parser.add_argument(
        "--title",
        help="Meeting title (default: 'Ata de Reunião')"
    )
    
    parser.add_argument(
        "--language",
        default="en",
        help="Subtitle language code (default: en)"
    )
    
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Output directory (default: output)"
    )
    
    parser.add_argument(
        "--tmp-dir",
        default="tmp",
        help="Temporary files directory (default: tmp)"
    )
    
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Send email after completion"
    )
    
    parser.add_argument(
        "--email-to",
        help="Email address to send to"
    )
    
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--log-file",
        help="Log file path (logs to console if not specified)"
    )
    
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Environment file path (default: .env)"
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    if Path(args.env_file).exists():
        load_dotenv(args.env_file)
        print(f"✅ Loaded environment from {args.env_file}")
    else:
        print(f"⚠️  Environment file not found: {args.env_file}")
    
    # Set up logging
    setup_logging(args.log_level, args.log_file)
    
    # Validate environment
    missing_vars = validate_environment()
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables in your .env file or environment")
        sys.exit(1)
    
    # Validate email arguments
    if args.send_email and not args.email_to:
        print("❌ --email-to is required when --send-email is specified")
        sys.exit(1)
    
    # Print startup banner
    print("🎯 Starting Verba Pipeline")
    print(f"📺 Video: {args.video_url}")
    print(f"🌍 Language: {args.language}")
    print(f"📁 Output: {args.output_dir}")
    if args.title:
        print(f"📝 Title: {args.title}")
    if args.send_email:
        print(f"📧 Email: {args.email_to}")
    print("-" * 50)
    
    try:
        # Initialize and run pipeline
        pipeline = VerbaPipeline(args.output_dir, args.tmp_dir)
        
        pdf_path = pipeline.run_pipeline(
            video_url=args.video_url,
            meeting_title=args.title,
            send_email=args.send_email,
            email_to=args.email_to,
            language=args.language
        )
        
        print(f"\n✅ Success! PDF generated: {pdf_path}")
        
    except KeyboardInterrupt:
        print("\n❌ Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        logger.exception("Pipeline failed with exception")
        sys.exit(1)


if __name__ == "__main__":
    main() 