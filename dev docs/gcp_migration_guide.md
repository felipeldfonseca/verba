# ☁️ GCP Migration Guide — Projeto **Verba**

> **Objetivo**: Mover o MVP de Azure para Google Cloud, mantendo a mesma arquitetura (parser → tradutor → LLM → DOC/PDF). Este guia cobre provisionamento, ajustes de código e variáveis de ambiente.

---

## 1. Visão Geral das Trocas de Serviço

| Camada                | Azure (atual)       | Google Cloud (novo)                  | SDK / Endpoint            |
| --------------------- | ------------------- | ------------------------------------ | ------------------------- |
| Tradução              | Translator          | Cloud Translation                    | `google-cloud-translate`  |
| LLM                   | Azure OpenAI GPT‑4o | Vertex AI Gemini 1.5 Pro             | `google-cloud-aiplatform` |
| Hospedagem serverless | Azure Functions     | Cloud Run (pref.) ou Cloud Functions | `gcloud run deploy`       |
| Armazenamento         | Blob Storage        | Cloud Storage (bucket Standard)      | `gs://verba‑output`       |
| Autenticação SMTP     | Graph Mail / Gmail  | Gmail API ou SMTP idem               | sem mudança               |

---

## 2. Provisionamento Passo a Passo

> Use **gcloud CLI** ≥ 480.0 ou Google Cloud Console.

### 2.1 Criar projeto & billing

```bash
gcloud projects create verba‑mvp --set‑as‑default
# Vincule seu crédito trial
```

### 2.2 Cloud Translation API

```bash
gcloud services enable translate.googleapis.com
```

Crie **chave de conta de serviço**:

```bash
gcloud iam service‑accounts create verba‑sa

gcloud iam service‑accounts keys create key.json \
  --iam‑account verba‑sa@verba‑mvp.iam.gserviceaccount.com
```

Guarde `GOOGLE_APPLICATION_CREDENTIALS=path/key.json`.

### 2.3 Vertex AI / Gemini

```bash
gcloud services enable aiplatform.googleapis.com
```

Nenhuma criação de recurso extra: Gemini 1.5 Pro é chamado on‑demand.

### 2.4 Cloud Storage Bucket

```bash
gsutil mb -l us-central1 gs://verba-output
```

### 2.5 Cloud Run (opcional para prod)

```bash
gcloud run deploy verba‑pipeline \
  --source . \
  --region us-central1 \
  --allow‑unauthenticated
```

---

## 3. Ajustes de Código

### 3.1 Dependências novas

```bash
pip install google-cloud-translate google-cloud-aiplatform
```

(Remova azure‑translator + openai se desejar.)

### 3.2 Wrapper Translation (src/translate/gcp.py)

```python
from google.cloud import translate_v2 as translate
client = translate.Client()

def translate_text(text, target="pt"):
    resp = client.translate(text, target_language=target)
    return resp["translatedText"]
```

### 3.3 Wrapper LLM (src/summarize/gcp.py)

```python
from vertexai.preview.language_models import TextGenerationModel
model = TextGenerationModel.from_pretrained("gemini-1.5-pro")

def summarize(text, prompt):
    resp = model.predict(prompt + text, temperature=0.3, max_output_tokens=1024)
    return resp.text
```

> **Dica**: Gemini 1.5 Pro aceita **\~1 M tokens** de contexto; você talvez nem precise de chunking.

### 3.4 Exportar para PDF e E‑mail

Sem mudanças.

---

## 4. `.env.example` (GCP)

```env
# Google Cloud creds
GOOGLE_APPLICATION_CREDENTIALS=./key.json
GCP_PROJECT=verba-mvp

# Translation
GCP_TRANSLATE_LOCATION=global

# LLM
GCP_GEMINI_LOCATION=us-central1
GCP_GEMINI_MODEL=gemini-1.5-pro

# Output bucket
GCS_BUCKET=verba-output
```

---

## 5. Build & Test Locais

```bash
export GOOGLE_APPLICATION_CREDENTIALS=./key.json
python scripts/run_local.py data/video.vtt
```

Deve gerar `ata.pdf` e fazer upload para `gs://verba-output/<slug>/`.

---

## 6. Atualizar CI‑CD

- Substitua passo **Azure login** por:

```yaml
- id: "setup-gcloud"
  uses: google-github-actions/setup-gcloud@v2
  with:
    project_id: ${{ secrets.GCP_PROJECT }}
    service_account_key: ${{ secrets.GCP_SA_KEY }}
```

- Opcional: deploy Cloud Run em `main`.

---

## 7. Custo & Quotas

| API            | Free Tier                     | Pós‑trial (preço maio 2025)                    |
| -------------- | ----------------------------- | ---------------------------------------------- |
| Translation    | 500 000 chars/mês             | US \$20 / M caracteres                         |
| Gemini 1.5 Pro | 60 prompts/min no trial       | US \$1.25 / M tokens input + US \$5 / M output |
| Cloud Run      | 2 M requests + 360 k GB‑s/mês | US \$0.000024 / GB‑s                           |

---

## 8. Checklist de Migração

1.

---

> **Pronto:** com esses passos, o projeto **Verba** roda 100 % em Google Cloud usando seus créditos de trial, sem perder compatibilidade futura com as APIs do Microsoft Graph para Teams.

