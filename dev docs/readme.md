# 🎯 MVP — Gerador Automático de Atas

> **Status:** PoC / MVP em desenvolvimento  
> **Objetivo:** Processar transcrições de reuniões (.vtt), traduzir para pt‑BR, resumir e gerar PDF/DOCX com valor em ≤ 5 min.

---

## 🚀 Stack

| Camada | Tecnologia | Motivo |
|--------|------------|--------|
| Orquestração | **Azure Functions** (Python 3.11) | Escala sob demanda & fácil cron/webhook |
| Transcrição de teste | **yt‑dlp** + legendas automáticas do YouTube | Substitui Teams durante validação _off‑radar_ |
| Parsing | [`webvtt-py`](https://pypi.org/project/webvtt-py/) | Converte `.vtt` em objetos Python |
| Tradução | **Azure Translator** (Cognitive Services) | Latência < 300 ms / 1 k tokens |
| LLM | **Azure OpenAI GPT‑4o** (trocar por Llama 3 local depois) | Resumo & extração de ações |
| Exportação | [`python-docx`](https://python-docx.readthedocs.io/) + **WeasyPrint** | Gera `.docx` + converte para PDF |
| Storage | **Azure Blob Storage** | Guarda VTT, JSON e PDFs gerados |

---

## 🛠️ Configuração Rápida

1. **Clone o repo:**
   ```bash
   git clone https://github.com/SEU_USUARIO/auto-ata.git && cd auto-ata
   ```
2. **Virtualenv + deps:**
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Variáveis de ambiente:**  
   Copie `.env.example` → `.env` e preencha chaves:
   ```env
   AZURE_OPENAI_KEY=...
   AZURE_OPENAI_ENDPOINT=...
   AZURE_TRANSLATOR_KEY=...
   AZURE_TRANSLATOR_REGION=...
   STORAGE_CONN_STRING=...
   FROM_EMAIL=bot@exemplo.com
   TO_EMAIL=usuario@exemplo.com
   COMPANY_LOGO_URL=https://...
   ```
4. **Rodar pipeline local (vídeo YouTube):**
   ```bash
   make local-test URL="https://youtu.be/abc123"
   # gera ./output/<slug>/ata.pdf
   ```

---

## 📂 Estrutura de Pastas

```text
auto-ata/
├── src/
│   ├── ingest/            # Captura & parsing (.vtt → JSON)
│   ├── translate/         # Wrapper Azure Translator
│   ├── summarize/         # Prompt + chamada GPT‑4o
│   ├── export/            # DOCX → PDF
│   └── utils/             # Helpers comuns
├── scripts/
│   ├── download_subs.py   # yt‑dlp wrapper
│   └── run_local.py       # Pipeline CLI p/ testes
├── output/                # PDFs gerados em dev
├── tests/                 # PyTest unit/integration
├── requirements.txt
├── .env.example
└── README.md (este arquivo)
```

---

## 🏃‍♂️ Scripts Principais

| Script | Descrição | Uso |
|--------|-----------|-----|
| `scripts/download_subs.py` | Baixa legendas automáticas (`.vtt`) de um vídeo do YouTube | `python scripts/download_subs.py <url> --lang en` |
| `scripts/run_local.py` | Roda pipeline completo usando `.vtt` local | `python scripts/run_local.py data/video.vtt` |
| `src/azure_function/` | Entry‑point HTTP Trigger para Azure | Deploy automático via `func azure functionapp publish` |

---

## ✅ Roadmap MVP (curto)
- [x] Parsing de `.vtt` → JSON
- [x] Tradução pt‑BR
- [x] Prompt GPT e resumo
- [x] Geração DOCX
- [ ] Conversão PDF + branding
- [ ] Envio por e‑mail SMTP/O365
- [ ] Time ≤ 5 min – benchmark

> **Teste rápido:** Rode `make local-test` com qualquer vídeo (> 15 min) e confira `./output/**/ata.pdf`.

---

## 🧪 Testes
```bash
pytest -q
```
Inclui mocks das APIs Azure para evitar custo em CI.

---

## 🤝 Contribuição
1. Abra uma issue com sugestão/bug.  
2. Envie PR com branch descritivo.

---

## 📝 Licença
MIT — use, modifique, compartilhe. Créditos são bem‑vindos.

