"""
Unit tests for the summarize module (gpt.py).

These tests verify GPT summarization functionality.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.summarize.gpt import (
    GPTSummarizer, 
    SummaryResult, 
    summarize_meeting, 
    summarize_translated_segments
)


class TestSummaryResult:
    """Test cases for SummaryResult dataclass."""
    
    def test_summary_result_creation(self):
        """Test SummaryResult creation with all fields."""
        result = SummaryResult(
            resumo_executivo="Resumo teste",
            decisoes=["Decisão 1", "Decisão 2"],
            proximas_acoes=[{"responsavel": "João", "acao": "Tarefa", "prazo": "2024-01-15"}],
            transcricao_completa="Transcrição completa",
            tokens_used=1500,
            processing_time=12.5
        )
        
        assert result.resumo_executivo == "Resumo teste"
        assert len(result.decisoes) == 2
        assert len(result.proximas_acoes) == 1
        assert result.tokens_used == 1500
        assert result.processing_time == 12.5
    
    def test_summary_result_empty_lists(self):
        """Test SummaryResult with empty lists."""
        result = SummaryResult(
            resumo_executivo="Resumo teste",
            decisoes=[],
            proximas_acoes=[],
            transcricao_completa="Transcrição completa",
            tokens_used=500,
            processing_time=5.0
        )
        
        assert len(result.decisoes) == 0
        assert len(result.proximas_acoes) == 0


class TestGPTSummarizer:
    """Test cases for GPTSummarizer class."""
    
    def test_init_with_env_vars(self):
        """Test GPTSummarizer initialization with environment variables."""
        with patch.dict(os.environ, {
            'AZURE_OPENAI_KEY': 'test_key',
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
            'AZURE_OPENAI_DEPLOYMENT': 'gpt-4o-test',
            'AZURE_OPENAI_API_VERSION': '2024-02-01'
        }):
            with patch('src.summarize.gpt.AzureOpenAI') as mock_client:
                summarizer = GPTSummarizer()
                
                assert summarizer.api_key == 'test_key'
                assert summarizer.endpoint == 'https://test.openai.azure.com/'
                assert summarizer.deployment_name == 'gpt-4o-test'
                assert summarizer.api_version == '2024-02-01'
                mock_client.assert_called_once()
    
    def test_init_with_parameters(self):
        """Test GPTSummarizer initialization with explicit parameters."""
        with patch('src.summarize.gpt.AzureOpenAI') as mock_client:
            summarizer = GPTSummarizer(
                api_key='param_key',
                endpoint='https://param.openai.azure.com/',
                deployment_name='param-deployment',
                api_version='2024-03-01'
            )
            
            assert summarizer.api_key == 'param_key'
            assert summarizer.endpoint == 'https://param.openai.azure.com/'
            assert summarizer.deployment_name == 'param-deployment'
            assert summarizer.api_version == '2024-03-01'
            mock_client.assert_called_once()
    
    def test_init_missing_api_key(self):
        """Test GPTSummarizer initialization with missing API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Azure OpenAI API key is required"):
                GPTSummarizer()
    
    def test_init_missing_endpoint(self):
        """Test GPTSummarizer initialization with missing endpoint."""
        with patch.dict(os.environ, {'AZURE_OPENAI_KEY': 'test_key'}, clear=True):
            with pytest.raises(ValueError, match="Azure OpenAI endpoint is required"):
                GPTSummarizer()
    
    def test_build_canonical_prompt(self):
        """Test canonical prompt building."""
        with patch('src.summarize.gpt.AzureOpenAI'):
            summarizer = GPTSummarizer(
                api_key='test_key',
                endpoint='https://test.openai.azure.com/'
            )
            
            transcript = "Esta é uma transcrição de teste."
            duration = 30
            meeting_date = "2024-01-15"
            language_note = "Reunião em português"
            
            prompt = summarizer._build_canonical_prompt(
                transcript, duration, meeting_date, language_note
            )
            
            # Verify key components are present
            assert "Resumo executivo" in prompt
            assert "Decisões" in prompt
            assert "Próximas ações" in prompt
            assert "Transcrição completa" in prompt
            assert meeting_date in prompt
            assert str(duration) in prompt
            assert language_note in prompt
            assert transcript in prompt
    
    def test_build_canonical_prompt_no_language_note(self):
        """Test canonical prompt building without language note."""
        with patch('src.summarize.gpt.AzureOpenAI'):
            summarizer = GPTSummarizer(
                api_key='test_key',
                endpoint='https://test.openai.azure.com/'
            )
            
            prompt = summarizer._build_canonical_prompt(
                "Transcrição", 30, "2024-01-15", ""
            )
            
            # Should not contain language note section
            assert "Nota de idioma:" not in prompt
    
    def test_chunk_text_short_text(self):
        """Test text chunking with short text."""
        with patch('src.summarize.gpt.AzureOpenAI'):
            summarizer = GPTSummarizer(
                api_key='test_key',
                endpoint='https://test.openai.azure.com/'
            )
            
            short_text = "Esta é uma frase curta."
            chunks = summarizer._chunk_text(short_text, max_tokens=1000)
            
            assert len(chunks) == 1
            assert chunks[0] == short_text
    
    def test_chunk_text_long_text(self):
        """Test text chunking with long text."""
        with patch('src.summarize.gpt.AzureOpenAI'):
            summarizer = GPTSummarizer(
                api_key='test_key',
                endpoint='https://test.openai.azure.com/'
            )
            
            # Create a long text with multiple sentences
            long_text = ". ".join([f"Esta é a frase número {i}" for i in range(1000)])
            chunks = summarizer._chunk_text(long_text, max_tokens=100)  # Very small chunks
            
            assert len(chunks) > 1
            # Each chunk should be within the token limit
            for chunk in chunks:
                assert len(chunk) <= 100 * 4  # 4 chars per token approximation
    
    def test_parse_gpt_response_complete(self):
        """Test parsing complete GPT response."""
        with patch('src.summarize.gpt.AzureOpenAI'):
            summarizer = GPTSummarizer(
                api_key='test_key',
                endpoint='https://test.openai.azure.com/'
            )
            
            response_text = """
### Resumo executivo
Esta é uma reunião importante sobre desenvolvimento de software realizada em 2024-01-15.

### Decisões
- Implementar nova funcionalidade de autenticação
- Revisar processo de deploy

### Próximas ações
| Responsável | Ação | Prazo |
|-------------|------|-------|
| João Silva | Criar documentação | 2024-01-20 |
| Maria Santos | Revisar código | 2024-01-25 |

### Transcrição completa
Esta é a transcrição completa da reunião.
"""
            
            resumo, decisoes, proximas_acoes = summarizer._parse_gpt_response(response_text)
            
            assert "reunião importante" in resumo
            assert len(decisoes) == 2
            assert "autenticação" in decisoes[0]
            assert "deploy" in decisoes[1]
            assert len(proximas_acoes) == 2
            assert proximas_acoes[0]["responsavel"] == "João Silva"
            assert proximas_acoes[0]["acao"] == "Criar documentação"
            assert proximas_acoes[0]["prazo"] == "2024-01-20"
    
    def test_parse_gpt_response_empty_sections(self):
        """Test parsing GPT response with empty sections."""
        with patch('src.summarize.gpt.AzureOpenAI'):
            summarizer = GPTSummarizer(
                api_key='test_key',
                endpoint='https://test.openai.azure.com/'
            )
            
            response_text = """
### Resumo executivo
Esta é uma reunião sem decisões específicas.

### Decisões
*(nenhuma)*

### Próximas ações
*(nenhuma)*

### Transcrição completa
Esta é a transcrição completa da reunião.
"""
            
            resumo, decisoes, proximas_acoes = summarizer._parse_gpt_response(response_text)
            
            assert "reunião sem decisões" in resumo
            assert len(decisoes) == 0
            assert len(proximas_acoes) == 0
    
    def test_parse_gpt_response_numbered_decisions(self):
        """Test parsing GPT response with numbered decisions."""
        with patch('src.summarize.gpt.AzureOpenAI'):
            summarizer = GPTSummarizer(
                api_key='test_key',
                endpoint='https://test.openai.azure.com/'
            )
            
            response_text = """
### Decisões
1. Primeira decisão importante
2. Segunda decisão também importante
3. Terceira e última decisão
"""
            
            resumo, decisoes, proximas_acoes = summarizer._parse_gpt_response(response_text)
            
            assert len(decisoes) == 3
            assert "Primeira decisão" in decisoes[0]
            assert "Segunda decisão" in decisoes[1]
            assert "Terceira e última" in decisoes[2]
    
    @patch('src.summarize.gpt.AzureOpenAI')
    def test_process_single_chunk(self, mock_azure_client):
        """Test processing single chunk of text."""
        # Mock the Azure OpenAI client
        mock_client = MagicMock()
        mock_azure_client.return_value = mock_client
        
        # Mock the completion response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """
### Resumo executivo
Resumo da reunião teste.

### Decisões
- Decisão teste

### Próximas ações
| Responsável | Ação | Prazo |
|-------------|------|-------|
| João | Tarefa teste | 2024-01-20 |

### Transcrição completa
Transcrição completa.
"""
        mock_response.usage.total_tokens = 1000
        mock_client.chat.completions.create.return_value = mock_response
        
        summarizer = GPTSummarizer(
            api_key='test_key',
            endpoint='https://test.openai.azure.com/'
        )
        
        resumo, decisoes, proximas_acoes, tokens = summarizer._process_single_chunk(
            "Transcrição teste",
            30,
            "2024-01-15",
            ""
        )
        
        assert "Resumo da reunião teste" in resumo
        assert len(decisoes) == 1
        assert "Decisão teste" in decisoes[0]
        assert len(proximas_acoes) == 1
        assert proximas_acoes[0]["responsavel"] == "João"
        assert tokens == 1000
    
    @patch('src.summarize.gpt.AzureOpenAI')
    def test_summarize_transcript_short(self, mock_azure_client):
        """Test summarizing short transcript."""
        # Mock the Azure OpenAI client
        mock_client = MagicMock()
        mock_azure_client.return_value = mock_client
        
        # Mock the completion response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """
### Resumo executivo
Resumo da reunião teste realizada em 2024-01-15.

### Decisões
- Decisão importante da reunião

### Próximas ações
| Responsável | Ação | Prazo |
|-------------|------|-------|
| João | Implementar funcionalidade | 2024-01-20 |

### Transcrição completa
Transcrição completa da reunião.
"""
        mock_response.usage.total_tokens = 1500
        mock_client.chat.completions.create.return_value = mock_response
        
        summarizer = GPTSummarizer(
            api_key='test_key',
            endpoint='https://test.openai.azure.com/'
        )
        
        result = summarizer.summarize_transcript(
            transcript_pt="Esta é uma transcrição de teste.",
            duration_minutes=30,
            meeting_date="2024-01-15"
        )
        
        assert isinstance(result, SummaryResult)
        assert "Resumo da reunião teste" in result.resumo_executivo
        assert len(result.decisoes) == 1
        assert len(result.proximas_acoes) == 1
        assert result.tokens_used == 1500
        assert result.processing_time > 0
        assert result.transcricao_completa == "Esta é uma transcrição de teste."
    
    @patch('src.summarize.gpt.time.time')
    @patch('src.summarize.gpt.AzureOpenAI')
    def test_summarize_transcript_timing(self, mock_azure_client, mock_time):
        """Test that processing time is calculated correctly."""
        # Mock time to return predictable values
        mock_time.side_effect = [100.0, 112.5]  # 12.5 seconds difference
        
        # Mock the Azure OpenAI client
        mock_client = MagicMock()
        mock_azure_client.return_value = mock_client
        
        # Mock the completion response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """
### Resumo executivo
Resumo teste.

### Decisões
*(nenhuma)*

### Próximas ações
*(nenhuma)*

### Transcrição completa
Transcrição.
"""
        mock_response.usage.total_tokens = 800
        mock_client.chat.completions.create.return_value = mock_response
        
        summarizer = GPTSummarizer(
            api_key='test_key',
            endpoint='https://test.openai.azure.com/'
        )
        
        result = summarizer.summarize_transcript(
            transcript_pt="Transcrição teste",
            duration_minutes=15
        )
        
        assert result.processing_time == 12.5
    
    @patch('src.summarize.gpt.AzureOpenAI')
    def test_summarize_transcript_api_error(self, mock_azure_client):
        """Test handling of API errors."""
        # Mock the Azure OpenAI client
        mock_client = MagicMock()
        mock_azure_client.return_value = mock_client
        
        # Mock API error
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        summarizer = GPTSummarizer(
            api_key='test_key',
            endpoint='https://test.openai.azure.com/'
        )
        
        with pytest.raises(Exception, match="API Error"):
            summarizer.summarize_transcript(
                transcript_pt="Transcrição teste",
                duration_minutes=30
            )


class TestStandaloneFunctions:
    """Test cases for standalone functions."""
    
    @patch('src.summarize.gpt.GPTSummarizer')
    def test_summarize_meeting(self, mock_summarizer_class):
        """Test summarize_meeting convenience function."""
        # Mock the summarizer
        mock_summarizer = MagicMock()
        mock_summarizer_class.return_value = mock_summarizer
        
        # Mock the result
        mock_result = SummaryResult(
            resumo_executivo="Resumo teste",
            decisoes=["Decisão 1"],
            proximas_acoes=[{"responsavel": "João", "acao": "Tarefa", "prazo": "2024-01-20"}],
            transcricao_completa="Transcrição teste",
            tokens_used=1200,
            processing_time=10.0
        )
        mock_summarizer.summarize_transcript.return_value = mock_result
        
        # Call the function
        result = summarize_meeting(
            transcript_pt="Transcrição teste",
            duration_minutes=25,
            meeting_date="2024-01-15",
            language_note="Português brasileiro"
        )
        
        # Verify summarizer was created and called correctly
        mock_summarizer_class.assert_called_once()
        mock_summarizer.summarize_transcript.assert_called_once_with(
            transcript_pt="Transcrição teste",
            duration_minutes=25,
            meeting_date="2024-01-15",
            language_note="Português brasileiro"
        )
        
        assert result == mock_result
    
    @patch('src.summarize.gpt.GPTSummarizer')
    def test_summarize_translated_segments(self, mock_summarizer_class):
        """Test summarize_translated_segments convenience function."""
        # Mock the summarizer
        mock_summarizer = MagicMock()
        mock_summarizer_class.return_value = mock_summarizer
        
        # Mock the result
        mock_result = SummaryResult(
            resumo_executivo="Resumo teste",
            decisoes=[],
            proximas_acoes=[],
            transcricao_completa="Transcrição completa",
            tokens_used=800,
            processing_time=8.0
        )
        mock_summarizer.summarize_transcript.return_value = mock_result
        
        # Test segments
        segments = [
            {
                "text_translated": "Primeira frase traduzida.",
                "start_seconds": 0.0,
                "end_seconds": 5.0,
                "duration": 5.0
            },
            {
                "text_translated": "Segunda frase traduzida.",
                "start_seconds": 5.0,
                "end_seconds": 10.0,
                "duration": 5.0
            }
        ]
        
        # Call the function
        result = summarize_translated_segments(
            segments=segments,
            meeting_date="2024-01-15",
            language_note="Reunião em português"
        )
        
        # Verify summarizer was created and called correctly
        mock_summarizer_class.assert_called_once()
        mock_summarizer.summarize_transcript.assert_called_once()
        
        # Verify the transcript was constructed correctly
        call_args = mock_summarizer.summarize_transcript.call_args
        assert "Primeira frase traduzida." in call_args[1]["transcript_pt"]
        assert "Segunda frase traduzida." in call_args[1]["transcript_pt"]
        assert call_args[1]["duration_minutes"] == 1  # 10 seconds = 1 minute (rounded up)
        assert call_args[1]["meeting_date"] == "2024-01-15"
        assert call_args[1]["language_note"] == "Reunião em português"
        
        assert result == mock_result
    
    @patch('src.summarize.gpt.GPTSummarizer')
    def test_summarize_translated_segments_empty(self, mock_summarizer_class):
        """Test summarize_translated_segments with empty segments."""
        # Mock the summarizer
        mock_summarizer = MagicMock()
        mock_summarizer_class.return_value = mock_summarizer
        
        # Mock the result
        mock_result = SummaryResult(
            resumo_executivo="Reunião vazia",
            decisoes=[],
            proximas_acoes=[],
            transcricao_completa="",
            tokens_used=100,
            processing_time=1.0
        )
        mock_summarizer.summarize_transcript.return_value = mock_result
        
        # Call with empty segments
        result = summarize_translated_segments(
            segments=[],
            meeting_date="2024-01-15"
        )
        
        # Verify summarizer was called with empty transcript
        call_args = mock_summarizer.summarize_transcript.call_args
        assert call_args[1]["transcript_pt"] == ""
        assert call_args[1]["duration_minutes"] == 0
        
        assert result == mock_result


if __name__ == "__main__":
    pytest.main([__file__]) 