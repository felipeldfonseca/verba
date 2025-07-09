# 📜 Prompt & Evaluation Spec

> **Objetivo**: Documentar o *prompt canonical* para o LLM, garantir consistência de saída e definir critérios automáticos de validação (eval). Usado tanto em desenvolvimento local quanto em produção do MVP.

---

## 1. Prompt Canonical

### 1.1. Variáveis de contexto

| Placeholder       | Descrição                              | Exemplo                             |
| ----------------- | -------------------------------------- | ----------------------------------- |
| `<TRANSCRIPT_PT>` | Texto completo em pt‑BR (já traduzido) | "[00:02:11] João: Bom dia a todos…" |
| `<DURATION>`      | Duração total (min)                    | 47                                  |
| `<MEETING_DATE>`  | Data ISO                               | 2025‑07‑10                          |
| `<LANG_NOTE>`     | Nota de idioma (opcional)              | "80 % inglês, 20 % espanhol"        |

### 1.2. Template (modo *system*)

```text
Você é um redator corporativo sênior. Gere um documento em Markdown com as seções na ordem exata:

### Resumo executivo
Breve resumo (≈150 palavras) em português‑BR.

### Decisões
- Lista enumerada de decisões objetivas.

### Próximas ações
| Responsável | Ação | Prazo |
|-------------|------|-------|
| ... | ... | ... |

### Transcrição completa
<Reescreva o `<TRANSCRIPT_PT>` exatamente aqui>
```

*Use a data **`<MEETING_DATE>`** no primeiro parágrafo do resumo. Se não houver decisões ou ações, crie a linha “*(nenhuma)*”.*

---

## 2. Esperado da Saída

- **Formato Markdown válido**
- Deve conter **as quatro headings** (`###`) exatamente como especificado.
- Tabela “Próximas ações” precisa ter **3 colunas**.
- Linguagem: ≥ 95 % tokens em pt‑BR; estrangeirismos permitidos apenas para termos técnicos.
- Limite de **≈4 000 tokens** para evitar PDF gigante.

---

## 3. Avaliação Automática (pytest)

### 3.1. Esquema Regex

| Elemento         | Regex                      |
| ---------------- | -------------------------- |
| Heading Resumo   | `^###\s+Resumo executivo$` |
| Heading Decisões | `^###\s+Decisões$`         |
| Tabela Ações     | `^\|\s*Responsável\s*\|`   |

### 3.2. Script `eval_output.py`

```python
import re, pathlib, sys, json, statistics
from lingua import Language, LanguageDetectorBuilder

def main(md_path):
    text = pathlib.Path(md_path).read_text(encoding="utf-8")
    # 1️⃣ Structure
    headings = ["Resumo executivo", "Decisões", "Próximas ações", "Transcrição completa"]
    assert all(f"### {h}" in text for h in headings), "Missing heading"
    # 2️⃣ Language predominance pt‑BR
    detector = LanguageDetectorBuilder.from_all_languages().build()
    lang_counts = sum(1 for _ in text.split())
    pt_tokens = sum(1 for w in text.split() if detector.detect_language_of(w) == Language.PORTUGUESE)
    assert pt_tokens / lang_counts >= 0.95, "Portuguese fraction too low"
    print("✅ All checks passed")

if __name__ == "__main__":
    main(sys.argv[1])
```

### 3.3. Métricas

| Métrica                  | Alvo                                 |
| ------------------------ | ------------------------------------ |
| **Pass rate** (`pytest`) | ≥ 95 % nos 10 vídeos‑teste           |
| **Tempo geração**        | ≤ 15 s para 30 min de áudio (resumo) |

---

## 4. Edge Cases & Regras Manuais

- **Sem ações detectadas** → inserir tabela com linha “*(nenhuma)*”.
- Se duração `<DURATION>` < 5 min, permitir resumo de até 80 palavras.
- Caso o transcript possua > 8 000 tokens, dividir em blocos e resumir incrementalmente (estratégia *map‑reduce*).

---

## 5. Versionamento do Prompt

- Guardar este arquivo no repo em `docs/prompt/2025‑07‑v1.md`.
- Alterações requerem *pull‑request* + update da `PROMPT_VERSION` no `.env`.

