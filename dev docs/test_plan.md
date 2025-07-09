# ✅ Test Plan — MVP Atas

> Cobrir funcionalidade end‑to‑end, limites de tempo e qualidade de saída.

---

## 1. Tipos de Teste
| Tipo | Objetivo | Ferramenta |
|------|----------|------------|
| **Unitário** | Validar funções de parsing, tradução, doc generation isoladamente. | `pytest`, `hypothesis` |
| **Integração** | Garantir que step‑funcs encadeiam corretamente (parser ➜ translator ➜ GPT ➜ doc). | `pytest` + `pytest‑asyncio` |
| **E2E** | Tempo total ≤ 300 s e PDF válido. | CLI `make e2e` + timer |
| **Regression** | Evitar prompt drift. | `promptfoo`, `g...

