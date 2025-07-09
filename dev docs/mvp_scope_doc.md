# MVP Scope Document

## 1. Visão do Produto
Criar um **gerador automático de atas** que receba uma transcrição de reunião (arquivo `.vtt`), traduza tudo para português‑BR, extraia um _resumo executivo_, _decisões_ e _próximas ações_, e entregue um PDF/Word ao usuário em até **5 min** após o fim da reunião — sem depender de credenciais corporativas do Microsoft Teams.

## 2. Objetivos & KPIs do MVP
| Métrica                                | Meta                | Método de Medição |
|----------------------------------------|---------------------|-------------------|
| Tempo de entrega do documento          | **≤ 5 min**         | Cronômetro por reunião |
| NPS do usuário‑alvo (tio)              | **≥ 8/10**          | Pesquisa 1‑click pós‑leitura |
| Acurácia de extração de ações          | **≥ 90 %**          | Validação manual em 3 reuniões |
| Custo por reunião                      | **≤ US$ 0,50**      | Logs de billing Azure |

## 3. Público‑Alvo & Caso de Uso
* **Usuário primário:** tio (engenheiro de planejamento) que não fala inglês.
* **Cenário:** recebe o PDF no e‑mail logo após a reunião e consegue, em <5 min, explicar a alguém as decisões e tarefas.

## 4. Funcionalidades em Escopo
1. **Input local**: arquivo `.vtt` (legendas automáticas YouTube ou Whisper).
2. **Pipeline**: Parser → Azure Translator → GPT‑4o (resumo) → Geração DOCX/PDF.
3. **Entrega**: envio automático por e‑mail (SMTP pessoal) ou gravação em pasta local.
4. **Template**: logo PAC, seções fixas (Resumo, Decisões, Ações).

## 5. Fora de Escopo (MVP)
* Integração direta com Teams Graph.
* Painel web ou banco de dados histórico.
* Tradução bidirecional ou multilíngue avançada.
* Interface gráfica para configuração.

## 6. Stack Técnica
| Camada            | Tecnologia                 |
|-------------------|----------------------------|
| Linguagem         | Python 3.12               |
| Parsing           | `webvtt-py`               |
| Tradução          | Azure Translator          |
| LLM               | Azure OpenAI GPT‑4o       |
| Documento         | `python-docx`, WeasyPrint |
| Orquestração      | Script CLI + Makefile     |
| Versionamento     | Git (GitHub privado)      |

## 7. Cronograma (4 semanas)
| Semana | Entregáveis                                          |
|--------|------------------------------------------------------|
| 1      | Repositório, parser `.vtt`, pipeline de tradução     |
| 2      | Prompt GPT, geração de Resumo/Decisões/Ações         |
| 3      | Template DOCX, exportação PDF, envio por e‑mail      |
| 4      | Testes end‑to‑end, coleta de feedback, ajustes finais|

## 8. Dependências
* Conta Azure com chaves do Translator e OpenAI.
* Vídeo de teste (>20 min) com legendas automáticas.
* SMTP ou token de e‑mail.

## 9. Riscos & Mitigações
| Risco                                   | Mitigação                               |
|-----------------------------------------|-----------------------------------------|
| Latência >5 min                         | Paralelizar tradução; usar batches      |
| Custos acima do previsto                | Testar modelo local (Whisper + Llama)   |
| Formato do documento não satisfatório   | Iterar templates com feedback do tio    |

## 10. Critérios de Aceite
1. Documento entregue ≤ 5 min após rodar o script.
2. PDF contém as quatro seções no template PAC.
3. Tio responde NPS ≥ 8 na primeira semana de uso.
4. Custo calculado ≤ US$ 0,50 por reunião de 60 min.

