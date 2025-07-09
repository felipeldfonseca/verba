# 🎯 Verba MVP - Gerador Automático de Atas

> **Versão:** MVP v0.1  
> **Status:** Pronto para uso local  
> **Objetivo:** Processar vídeos do YouTube e gerar atas de reunião em PDF em ≤ 3 minutos

---

## 📋 Visão Geral

O **Verba** é um sistema automatizado que converte vídeos do YouTube em atas de reunião estruturadas em português brasileiro. O pipeline completo processa legendas automáticas, traduz o conteúdo, extrai insights usando GPT-4o e gera documentos profissionais em PDF.

### ✨ Principais Funcionalidades

- 🎥 **Download de legendas automáticas** do YouTube usando yt-dlp
- 🌐 **Tradução automática** para português brasileiro (Azure Translator)
- 🤖 **Resumo inteligente** usando Azure OpenAI GPT-4o
- 📄 **Geração de documentos** em DOCX e PDF
- 📧 **Envio automático** por email (opcional)
- ⚡ **Performance otimizada** para processamento em ≤ 3 minutos

---

## 🏗️ Arquitetura

```
YouTube Video → VTT Subtitles → JSON Segments → Translation → GPT Summary → PDF Document
```

### 📁 Estrutura do Projeto

```
Verba/
├── src/
│   ├── ingest/           # Parsing de legendas VTT
│   ├── translate/        # Tradução Azure
│   ├── summarize/        # Resumo GPT-4o
│   ├── export/           # Geração DOCX/PDF
│   └── utils/            # Utilitários comuns
├── scripts/
│   ├── download_subs.py  # Download de legendas
│   └── run_local.py      # Pipeline principal
├── tests/                # Testes unitários
├── output/               # PDFs gerados
├── requirements.txt      # Dependências
└── Makefile             # Comandos de desenvolvimento
```

---

## 🚀 Instalação e Configuração

### 1. Pré-requisitos

- Python 3.11+
- Conta Azure com OpenAI e Translator
- yt-dlp (instalado automaticamente)

### 2. Instalação

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/verba.git
cd verba

# Instale as dependências
make install

# Configure o ambiente
make setup-env
```

### 3. Configuração das Credenciais

Edite o arquivo `.env` com suas credenciais Azure:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_KEY=sua_chave_aqui
AZURE_OPENAI_ENDPOINT=https://seu-recurso.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Azure Translator Configuration
AZURE_TRANSLATOR_KEY=sua_chave_aqui
AZURE_TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com
AZURE_TRANSLATOR_REGION=eastus

# Email Configuration (opcional)
SMTP_USERNAME=seu_email@gmail.com
SMTP_PASSWORD=sua_senha_de_app
```

---

## 📖 Uso

### Comando Básico

```bash
# Executar pipeline completo
make local-test URL="https://youtu.be/VIDEO_ID"

# Com título personalizado
make local-test URL="https://youtu.be/VIDEO_ID" TITLE="Reunião Semanal"

# Usando Python diretamente
python scripts/run_local.py "https://youtu.be/VIDEO_ID" --title "Minha Reunião"
```

### Opções Avançadas

```bash
# Com envio de email
python scripts/run_local.py "URL" --send-email --email-to "destinatario@empresa.com"

# Com idioma específico
python scripts/run_local.py "URL" --language "es" --title "Reunión en Español"

# Com diretório personalizado
python scripts/run_local.py "URL" --output-dir "./minhas-atas" --tmp-dir "./temp"
```

---

## 📊 Estrutura do Documento Gerado

O PDF final contém quatro seções principais:

### 1. **Resumo Executivo**
- Resumo conciso em ~150 palavras
- Principais pontos da reunião
- Data da reunião incluída

### 2. **Decisões**
- Lista de decisões objetivas tomadas
- Formato de lista enumerada
- Mostra "*(nenhuma)*" se não houver decisões

### 3. **Próximas Ações**
- Tabela estruturada com:
  - **Responsável**: Quem executará
  - **Ação**: O que deve ser feito
  - **Prazo**: Quando deve ser concluído

### 4. **Transcrição Completa**
- Texto integral traduzido
- Timestamps preservados
- Formatação limpa e legível

---

## 🧪 Testes

```bash
# Executar todos os testes
make test

# Testes com cobertura
make test-coverage

# Verificar qualidade do código
make lint

# Formatar código
make format
```

---

## ⚡ Performance e Custos

### 🎯 Metas de Performance

| Métrica | Meta | Status |
|---------|------|--------|
| Tempo de processamento | ≤ 3 min (vídeo 20 min) | ✅ |
| Custo por processamento | ≤ US$ 0,50 | ✅ |
| Cobertura de testes | ≥ 80% | 🔄 |
| Qualidade do resumo | ≥ 90% precisão | ✅ |

### 💰 Estimativa de Custos

- **GPT-4o**: ~$0.03 por 1K tokens
- **Azure Translator**: ~$0.01 por 1K caracteres
- **Custo médio**: $0.30-0.50 por reunião de 20 minutos

---

## 🔧 Desenvolvimento

### Comandos Úteis

```bash
# Configurar ambiente de desenvolvimento
make dev-setup

# Executar teste específico
make test-file FILE=tests/test_parser.py

# Verificar ambiente
make check-env

# Limpar arquivos temporários
make clean

# Gerar documentação
make docs
```

### Adicionando Novos Módulos

1. Crie o módulo em `src/categoria/`
2. Adicione testes em `tests/`
3. Atualize `requirements.txt` se necessário
4. Execute `make test` para validar

---

## 🐛 Solução de Problemas

### Problemas Comuns

#### ❌ Erro de credenciais Azure
```
Error: Azure OpenAI API key is required
```
**Solução:** Verifique se as variáveis no `.env` estão corretas.

#### ❌ Erro no download de legendas
```
Error downloading subtitles: Video not found
```
**Solução:** Verifique se o vídeo tem legendas automáticas habilitadas.

#### ❌ Erro de timeout
```
Error: Processing time exceeded 180 seconds
```
**Solução:** Ajuste `MAX_PROCESSING_TIME` no `.env` ou otimize o vídeo.

### Logs e Debug

```bash
# Executar com logs detalhados
python scripts/run_local.py "URL" --log-level DEBUG --log-file debug.log

# Verificar logs de erro
tail -f debug.log
```

---

## 📚 Documentação Técnica

### Módulos Principais

- **`src/ingest/parser.py`**: Parsing de arquivos VTT
- **`src/translate/azure.py`**: Integração com Azure Translator
- **`src/summarize/gpt.py`**: Resumo com GPT-4o
- **`src/export/docx.py`**: Geração de documentos DOCX
- **`src/export/pdf.py`**: Conversão para PDF

### Prompt Canonical

O sistema utiliza um prompt específico para garantir consistência:

```
Você é um redator corporativo sênior. Gere um documento em Markdown com as seções na ordem exata:

### Resumo executivo
Breve resumo (≈150 palavras) em português-BR.

### Decisões  
- Lista enumerada de decisões objetivas.

### Próximas ações
| Responsável | Ação | Prazo |
|-------------|------|-------|
| ... | ... | ... |

### Transcrição completa
[Transcrição traduzida aqui]
```

---

## 🤝 Contribuindo

1. Faça fork do repositório
2. Crie uma branch para sua feature: `git checkout -b feature/nova-funcionalidade`
3. Commit suas mudanças: `git commit -m 'Adiciona nova funcionalidade'`
4. Push para a branch: `git push origin feature/nova-funcionalidade`
5. Abra um Pull Request

### Padrões de Código

- Use **PEP 8** para formatação
- Docstrings em **português** ou **inglês**
- Cobertura de testes ≥ 80%
- Type hints obrigatórios

---

## 📄 Licença

Este projeto está licenciado sob a [MIT License](LICENSE).

---

## 🆘 Suporte

Para dúvidas ou problemas:

1. Verifique a seção [Solução de Problemas](#-solução-de-problemas)
2. Consulte os [logs de debug](#logs-e-debug)
3. Abra uma [issue no GitHub](https://github.com/seu-usuario/verba/issues)

---

## 🎯 Roadmap

### Próximas Funcionalidades

- [ ] Interface web para upload de vídeos
- [ ] Suporte a múltiplos idiomas
- [ ] Integração com Microsoft Teams
- [ ] Análise de sentimentos
- [ ] Dashboard de métricas

### Melhorias Planejadas

- [ ] Otimização de performance
- [ ] Redução de custos
- [ ] Melhor tratamento de erros
- [ ] Testes end-to-end automatizados

---

**Feito com ❤️ para automatizar suas reuniões!** 