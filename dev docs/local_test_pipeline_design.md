# 🛠️ Local Test Pipeline — YouTube ➜ PDF (MVP)

> **Objetivo**: Validar toda a lógica de parsing → tradução → resumo → geração de documento **sem** depender das APIs do Microsoft Teams. Usaremos um vídeo público do YouTube como fonte de áudio.

---

## 1. Requisitos de ambiente

| Item                 | Versão mínima | Observações                   |
| -------------------- | ------------- | ----------------------------- |
| Python               | 3.11          | Virtualenv recomendado        |
| yt‑dlp               | 2025.01.10    | `pip install yt-dlp`          |
| webvtt‑py            | 0.4.x         | Parsing `.vtt`                |
| Azure Translator SDK | 3.x           | Necessita chave e endpoint    |
| Azure OpenAI SDK     | 1.x           | GPT‑4o (ou modelo local opc.) |
| python‑docx          | 1.1+          | Geração `.docx`               |
| WeasyPrint           | 62+           | `.docx` → PDF                 |
| dotenv               | —             | Variáveis de ambiente         |

Crie o arquivo `.env` com:

```
AZURE_TRANSLATOR_KEY=...
AZURE_TRANSLATOR_ENDPOINT=...
AZURE_OPENAI_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

---

## 2. Pipeline — visão geral

```mermaid
flowchart TD
    A[Selecionar URL do
    vídeo YouTube] --> B[yt-dlp
    --write-auto-subs]
    B --> C[Arquivo .vtt]
    C --> D[Parser
    webvtt ➜ JSON]
    D --> E[Azure Translator
    en/es ➜ pt-BR]
    E --> F[Chunker
    (≤ 8k tokens)]
    F --> G[Azure OpenAI
    GPT-4o ➜ summary & tasks]
    G --> H[python-docx
    template]
    H --> I[WeasyPrint ➜ PDF]
    I --> J[Enviar e-mail
    p/ usuário]
```

---

## 3. Pseudo‑código

```python
"""
main.py — Pipeline de teste local
"""
from pathlib import Path
from subprocess import run
import os, json, webvtt, requests
from docx import Document
from weasyprint import HTML
from utils import chunk_text, build_prompt, send_email

VIDEO_URL = "https://www.youtube.com/watch?v=..."
TMP_DIR   = Path("tmp")
TMP_DIR.mkdir(exist_ok=True)

# 1. Baixar legendas automáticas (.vtt)
run([
    "yt-dlp",
    "--write-auto-subs",
    "--sub-lang", "en",
    "--skip-download",
    "-o", str(TMP_DIR / "video"),
    VIDEO_URL,
])
caption_file = next(TMP_DIR.glob("*.en.vtt"))

# 2. Parsear VTT ➜ lista de segmentos
segments = []
for caption in webvtt.read(caption_file):
    segments.append({
        "start": caption.start,
        "end": caption.end,
        "text": caption.text.replace("\n", " ").strip(),
    })

# 3. Traduzir para pt-BR
translator_key  = os.getenv("AZURE_TRANSLATOR_KEY")
translator_ep   = os.getenv("AZURE_TRANSLATOR_ENDPOINT")
translated = []
for seg in segments:
    resp = requests.post(
        f"{translator_ep}/translate?api-version=3.0&to=pt-br",
        headers={"Ocp-Apim-Subscription-Key": translator_key},
        json=[{"text": seg["text"]}],
    ).json()
    seg["pt"] = resp[0]["translations"][0]["text"]
    translated.append(seg)

# 4. Chunking p/ LLM
chunks = chunk_text([s["pt"] for s in translated], max_tokens=7500)
summary_parts = []
for ch in chunks:
    prompt = build_prompt(ch)
    # chamada Azure OpenAI
    summary_parts.append(call_openai(prompt))
summary = "\n".join(summary_parts)

# 5. Gerar DOCX

doc = Document("template.docx")
doc.add_heading("Resumo Executivo", level=1)
doc.add_paragraph(summary)
# ... gerar tabela de ações, etc.
output_docx = TMP_DIR / "ata.docx"
doc.save(output_docx)

# 6. Converter ➜ PDF
output_pdf = TMP_DIR / "ata.pdf"
HTML(string=docx2html(output_docx)).write_pdf(output_pdf)

# 7. Enviar e-mail (util.user@gmail)
send_email(
    to="tio@example.com",
    subject="Ata gerada automático — vídeo de teste",
    body="Segue em anexo o PDF.",
    attachments=[output_pdf],
)
```

### utils.py (esboço)

```python
from openai import AzureOpenAI
import smtplib, email

def chunk_text(lines, max_tokens):
    # Implementar contagem simples ≈4 caracteres/token
    ...

def build_prompt(text):
    return f"""
Você é um assistente que gera atas em português.
Texto original:
{text}
\n\n### Gere:
1. Resumo executivo (≤150 palavras)
2. Decisões
3. Próximas ações (quem/o quê/quando)
"""

def call_openai(prompt):
    client = AzureOpenAI(...)
    return client.chat.completions.create(...).choices[0].message.content

def send_email(to, subject, body, attachments):
    msg = email.message.EmailMessage()
    msg["Subject"] = subject
    msg["To"] = to
    msg.set_content(body)
    for file in attachments:
        msg.add_attachment(Path(file).read_bytes(), filename=file.name)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login("user", "pass")
        s.send_message(msg)
```

> **Observação**: no MVP real usaremos Graph Mail ou serviço SMTP corporativo; aqui basta Gmail/app‑password.

---

## 4. Teste & Métricas de aceitação

| Teste                | Critério                  | Passou? |
| -------------------- | ------------------------- | ------- |
| 1. Pipeline completo | PDF gerado sem erros      | ☐       |
| 2. Tempo total       | ≤ 3 min para vídeo 20 min | ☐       |
| 3. Qualidade resumo  | Avaliação 4/5+ manual     | ☐       |

Preencher a checklist para validar antes de migrar para Teams Graph.

---

## 5. Próximos passos após validação

1. Substituir **passo 1** pelo webhook `/onlineMeetings/{id}/transcripts`.
2. Criar template `.docx` oficial com branding PAC.
3. Embalar tudo em Azure Function + Blob Storage.

