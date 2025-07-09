# 🚢 CI‑CD Outline — MVP Atas

> Automatizar lint, testes e build artefacts PDF em cada push.

---

## 1. GitHub Actions Workflow (`.github/workflows/ci.yml`)

```yaml
name: CI
on:
  push:
    branches: ["main", "dev/*"]
  pull_request:
    branches: ["main"]

jobs:
  build:
    runs-on: ubuntu-latest
...

