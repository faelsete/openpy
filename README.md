# OpenPy 🧬

> ⚠️ **PROJETO EM RECONSTRUÇÃO** — Este projeto passou por uma reformulação completa e está sendo reescrito do zero. Não use em produção. Se encontrou este repositório, saiba que estamos trabalhando pesado para deixar tudo funcionando. NÃO abra issues reportando bugs por enquanto — já sabemos.

## O que é

OpenPy é um ecossistema operacional agêntico que amplifica a capacidade de modelos de IA através de um harness disciplinado. Inspirado no OpenClaw, Hermes Agent e Claude Code.

**Conceito:** Não importa o tamanho do modelo — o que importa é o harness. Um modelo de 4B com harness bom supera um de 120B sem.

## Instalação Rápida (Linux)

```bash
# Clonar
git clone https://github.com/faelfer/openpy.git
cd openpy

# Instalar
bash install.sh

# Ou manual:
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Configurar
openpy onboard

# Rodar
openpy doctor
openpy gateway start
openpy repl
```

## Requisitos

- Python >= 3.10
- Linux (target principal) ou Windows (dev)
- Um provider de LLM (Ollama local, OpenRouter gratuito, NVIDIA NIM, Gemini, OpenAI, etc.)

## Providers Suportados

**API (13):** OpenAI, Anthropic, Google Gemini, Groq, DeepSeek, NVIDIA NIM, OpenRouter, Together AI, Mistral, Ollama, OpenAI-compatible

**CLI (6):** Ollama, OpenCode, Gemini CLI, Codex CLI, Kimi CLI, Qwen CLI

## Comandos

```bash
openpy run "tarefa"          # Executa tarefa
openpy repl                  # Modo interativo
openpy gateway start|stop    # Daemon API
openpy doctor [--fix]        # Diagnóstico
openpy onboard               # Setup inicial
openpy config get|set        # Configuração
openpy skills list|show      # Skills
openpy memory status|history # Memória
```

## Status

🔴 Em desenvolvimento ativo. Não usar em produção.
