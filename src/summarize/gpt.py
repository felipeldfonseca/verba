"""
GPT summarizer module using Azure OpenAI GPT-4o.

This module provides functionality to summarize meeting transcripts using
Azure OpenAI GPT-4o with the canonical prompt specification.
"""

import asyncio
import logging
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from openai import AzureOpenAI
from src.utils.helpers import (
    timing_decorator,
    estimate_tokens,
    load_config,
    generate_slug
)


logger = logging.getLogger(__name__)


@dataclass
class SummaryResult:
    """Result of a summarization operation."""
    resumo_executivo: str
    decisoes: List[str]
    proximas_acoes: List[Dict[str, str]]  # [{"responsavel": "", "acao": "", "prazo": ""}]
    transcricao_completa: str
    tokens_used: int
    processing_time: float
    title: str
    slug: str


class GPTSummarizer:
    """Azure OpenAI GPT-4o summarizer client."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        deployment_name: Optional[str] = None,
        api_version: Optional[str] = None
    ):
        """
        Initialize the GPT summarizer client.
        
        Args:
            api_key: Azure OpenAI API key
            endpoint: Azure OpenAI endpoint URL
            deployment_name: GPT deployment name
            api_version: API version
        """
        self.api_key = api_key or os.getenv("AZURE_OPENAI_KEY")
        self.endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment_name = deployment_name or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        self.api_version = "2023-05-15"
        
        if not self.api_key:
            raise ValueError("Azure OpenAI API key is required")
        
        if not self.endpoint:
            raise ValueError("Azure OpenAI endpoint is required")
        
        self.client = AzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.endpoint
        )
        self.max_tokens = 8192

    def _build_canonical_prompt(
        self,
        transcript_pt: str,
        duration_minutes: int,
        meeting_date: str,
        language_note: str = ""
    ) -> str:
        """
        Build the canonical prompt according to the specification.
        
        Args:
            transcript_pt: Complete transcript in Portuguese
            duration_minutes: Meeting duration in minutes
            meeting_date: Meeting date in ISO format
            language_note: Optional language note
            
        Returns:
            Formatted prompt string
        """
        system_prompt = f"""Você é um redator corporativo sênior. Gere um documento em Markdown com as seções na ordem exata:

### Resumo executivo
Breve resumo (≈150 palavras) em português-BR.

### Decisões
- Lista enumerada de decisões objetivas.

### Próximas ações
| Responsável | Ação | Prazo |
|-------------|------|-------|
| ... | ... | ... |

### Transcrição completa
{transcript_pt}

Use a data **{meeting_date}** no primeiro parágrafo do resumo. Se não houver decisões ou ações, crie a linha "*(nenhuma)*".

Duração da reunião: {duration_minutes} minutos.
{f"Nota de idioma: {language_note}" if language_note else ""}"""
        
        return system_prompt
    
    def _chunk_text(self, text: str, max_tokens: int = 7500) -> List[str]:
        """
        Split text into chunks for processing.
        
        Args:
            text: Text to chunk
            max_tokens: Maximum tokens per chunk (≈4 characters per token)
            
        Returns:
            List of text chunks
        """
        max_chars = max_tokens * 4
        
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # Split by sentences to maintain context
        sentences = text.split('. ')
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 2 <= max_chars:
                current_chunk += sentence + '. '
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + '. '
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _parse_gpt_response(self, response_text: str) -> Tuple[str, List[str], List[Dict[str, str]]]:
        """
        Parse GPT response to extract structured data.
        
        Args:
            response_text: Raw GPT response
            
        Returns:
            Tuple of (resumo, decisoes, proximas_acoes)
        """
        
        # Extract resumo executivo
        resumo_match = re.search(r'### Resumo executivo\s*\n(.*?)(?=### |$)', response_text, re.DOTALL)
        resumo = resumo_match.group(1).strip() if resumo_match else ""
        
        # Extract decisões
        decisoes_match = re.search(r'### Decisões\s*\n(.*?)(?=### |$)', response_text, re.DOTALL)
        decisoes_text = decisoes_match.group(1).strip() if decisoes_match else ""
        
        # Parse decisões list
        decisoes = []
        if decisoes_text and decisoes_text != "*(nenhuma)*":
            for line in decisoes_text.split('\n'):
                line = line.strip()
                if line.startswith('- ') or line.startswith('• '):
                    decisoes.append(line[2:])
                elif line.startswith(('1.', '2.', '3.', '4.', '5.')):
                    decisoes.append(line[3:])
        
        # Extract próximas ações
        acoes_match = re.search(r'### Próximas ações\s*\n(.*?)(?=### |$)', response_text, re.DOTALL)
        acoes_text = acoes_match.group(1).strip() if acoes_match else ""
        
        # Parse próximas ações table
        proximas_acoes = []
        if acoes_text and "*(nenhuma)*" not in acoes_text:
            lines = acoes_text.split('\n')
            for line in lines:
                if '|' in line and not line.strip().startswith('|---'):
                    # Skip header line
                    if 'Responsável' in line:
                        continue
                    
                    parts = [part.strip() for part in line.split('|') if part.strip()]
                    if len(parts) >= 3:
                        proximas_acoes.append({
                            "responsavel": parts[0],
                            "acao": parts[1],
                            "prazo": parts[2]
                        })
        
        return resumo, decisoes, proximas_acoes
    
    def summarize_transcript(
        self,
        transcript_pt: str,
        duration_minutes: int,
        meeting_date: Optional[str] = None,
        language_note: str = ""
    ) -> SummaryResult:
        """
        Summarize a meeting transcript using GPT-4o.
        
        Args:
            transcript_pt: Complete transcript in Portuguese
            duration_minutes: Meeting duration in minutes
            meeting_date: Meeting date in ISO format (defaults to today)
            language_note: Optional language note
            
        Returns:
            SummaryResult object
        """
        
        start_time = time.time()
        
        if not meeting_date:
            meeting_date = datetime.now().strftime("%Y-%m-%d")
        
        # Split transcript into chunks if needed
        chunks = self._chunk_text(transcript_pt)
        
        if len(chunks) == 1:
            # Single chunk processing
            result = self._process_single_chunk(
                chunks[0], duration_minutes, meeting_date, language_note
            )
        else:
            # Multi-chunk processing with map-reduce
            result = self._process_multi_chunks(
                chunks, duration_minutes, meeting_date, language_note
            )
        
        processing_time = time.time() - start_time
        
        return SummaryResult(
            resumo_executivo=result[0],
            decisoes=result[1],
            proximas_acoes=result[2],
            transcricao_completa=transcript_pt,
            tokens_used=result[3],
            processing_time=processing_time,
            title="", # Placeholder, will be populated later
            slug="" # Placeholder, will be populated later
        )
    
    def _process_single_chunk(
        self,
        transcript_chunk: str,
        duration_minutes: int,
        meeting_date: str,
        language_note: str
    ) -> Tuple[str, List[str], List[Dict[str, str]], int]:
        """
        Process a single transcript chunk.
        
        Args:
            transcript_chunk: Transcript chunk to process
            duration_minutes: Meeting duration in minutes
            meeting_date: Meeting date in ISO format
            language_note: Optional language note
            
        Returns:
            Tuple of (resumo, decisoes, proximas_acoes, tokens_used)
        """
        prompt = self._build_canonical_prompt(
            transcript_chunk, duration_minutes, meeting_date, language_note
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.3
            )
            
            response_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            resumo, decisoes, proximas_acoes = self._parse_gpt_response(response_text)
            
            return resumo, decisoes, proximas_acoes, tokens_used
            
        except Exception as e:
            logger.error(f"Error processing transcript chunk: {e}")
            raise
    
    def _process_multi_chunks(
        self,
        chunks: List[str],
        duration_minutes: int,
        meeting_date: str,
        language_note: str
    ) -> Tuple[str, List[str], List[Dict[str, str]], int]:
        """
        Process multiple transcript chunks using map-reduce strategy.
        
        Args:
            chunks: List of transcript chunks
            duration_minutes: Meeting duration in minutes
            meeting_date: Meeting date in ISO format
            language_note: Optional language note
            
        Returns:
            Tuple of (resumo, decisoes, proximas_acoes, tokens_used)
        """
        # First pass: Summarize each chunk
        chunk_summaries = []
        total_tokens = 0
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            
            # Simplified prompt for chunk processing
            chunk_prompt = f"""Você é um redator corporativo. Extraia as informações principais deste trecho de transcrição:

{chunk}

Formate a resposta em:
- Resumo do trecho (≈50 palavras)
- Decisões identificadas (se houver)
- Ações identificadas (se houver)"""
            
            try:
                response = self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=[
                        {"role": "system", "content": chunk_prompt}
                    ],
                    max_tokens=1000,
                    temperature=0.3
                )
                
                chunk_summaries.append(response.choices[0].message.content)
                total_tokens += response.usage.total_tokens
                
            except Exception as e:
                logger.error(f"Error processing chunk {i+1}: {e}")
                chunk_summaries.append(f"[Erro ao processar trecho {i+1}]")
        
        # Second pass: Combine summaries into final format
        combined_summary = "\n\n".join(chunk_summaries)
        
        final_prompt = self._build_canonical_prompt(
            combined_summary, duration_minutes, meeting_date, language_note
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": final_prompt}
                ],
                max_tokens=4000,
                temperature=0.3
            )
            
            response_text = response.choices[0].message.content
            total_tokens += response.usage.total_tokens
            
            resumo, decisoes, proximas_acoes = self._parse_gpt_response(response_text)
            
            return resumo, decisoes, proximas_acoes, total_tokens
            
        except Exception as e:
            logger.error(f"Error in final summarization: {e}")
            raise

    @timing_decorator
    async def summarize(
        self,
        segments: List[Dict[str, Any]],
        video_duration: int,
        meeting_date: str,
        language_note: str
    ) -> SummaryResult:
        """
        Summarize a list of translated segments using GPT.

        Args:
            segments: A list of translated segments.
            video_duration: The duration of the video in seconds.
            meeting_date: The date of the meeting.
            language_note: A note about the translation language.

        Returns:
            A SummaryResult object containing the summary.
        """
        full_transcript = " ".join([seg['text'] for seg in segments])
        
        prompt = self._build_prompt(full_transcript, video_duration, meeting_date, language_note)

        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=0.3
            )
            
            summary_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens

            title_match = re.search(r"^\s*Título:\s*(.*)", summary_text, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else "Ata de Reunião"
            slug = generate_slug(title)

            return SummaryResult(
                resumo_executivo=summary_text, # Changed to response_text as per new_code
                decisoes=[], # Placeholder, needs actual parsing
                proximas_acoes=[], # Placeholder, needs actual parsing
                transcricao_completa=full_transcript,
                tokens_used=tokens_used,
                processing_time=0, # This will be updated by timing_decorator
                title=title,
                slug=slug
            )
            
        except Exception as e:
            logger.error(f"Error summarizing segments: {e}")
            raise

    def _build_prompt(self, transcript: str, duration: int, date: str, lang_note: str) -> str:
        """Build the prompt for the GPT model."""
        
        duration_str = f"{duration // 60} minutos"
        
        prompt = f"""
        **Objective:** Generate a concise, professional meeting minutes document in Brazilian Portuguese from the provided transcript.

        **Context:**
        - **Video Duration:** {duration_str}
        - **Meeting Date:** {date}
        - **Language Note:** {lang_note}

        **Input Transcript:**
        ---
        {transcript}
        ---

        **Instructions:**
        Analyze the transcript and produce a structured meeting minutes document with the following sections:
        
        1.  **Título (Title):** Create a short, descriptive title for the meeting.
        2.  **Visão Geral (Overview):** A brief, one-paragraph summary of the meeting's main purpose and key outcomes.
        3.  **Principais Tópicos Discutidos (Main Topics Discussed):** A bulleted list of the most important subjects covered.
        4.  **Decisões Chave (Key Decisions):** A bulleted list of any significant decisions made.
        5.  **Itens de Ação (Action Items):** A numbered list of tasks assigned, including who is responsible (if mentioned).
        6.  **Principais Citações (Key Quotes):** A few impactful or representative quotes from the discussion.

        **Format:**
        - Use clear headings for each section.
        - Ensure the output is well-organized and easy to read.
        - The entire output must be in Brazilian Portuguese.
        """
        return prompt


def summarize_meeting(
    transcript_pt: str,
    duration_minutes: int,
    meeting_date: Optional[str] = None,
    language_note: str = ""
) -> SummaryResult:
    """
    Convenience function to summarize a meeting transcript.
    
    Args:
        transcript_pt: Complete transcript in Portuguese
        duration_minutes: Meeting duration in minutes
        meeting_date: Meeting date in ISO format (defaults to today)
        language_note: Optional language note
        
    Returns:
        SummaryResult object
    """
    summarizer = GPTSummarizer()
    return summarizer.summarize_transcript(
        transcript_pt, duration_minutes, meeting_date, language_note
    )


def summarize_translated_segments(
    segments: List[Dict[str, Any]],
    video_duration: int,
    meeting_date: str,
    language_note: str
) -> SummaryResult:
    """
    High-level function to summarize translated segments.

    Args:
        segments: A list of dictionaries, where each dictionary represents a translated segment.
        video_duration: The duration of the video in seconds.
        meeting_date: The date of the meeting.
        language_note: A note about the translation language.
        
    Returns:
        A SummaryResult object.
    """
    summarizer = GPTSummarizer()
    return asyncio.run(summarizer.summarize(segments, video_duration, meeting_date, language_note)) 