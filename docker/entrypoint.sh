#!/bin/bash
set -e

echo "🧬 OpenPy Container Iniciando..."

# Garantir diretórios
mkdir -p $OPENPY_HOME/{data,logs,skills,workspace}

# Copiar skills bundled se não existirem
if [ ! -f "$OPENPY_HOME/skills/core/CORE_ALWAYS.md" ]; then
    echo "📄 Copiando skills bundled..."
    cp -rn /opt/openpy/openpy/skills/* $OPENPY_HOME/skills/ 2>/dev/null || true
fi

# Configurar ngrok se token existir
if [ -n "$NGROK_TOKEN" ]; then
    echo "🔗 Configurando ngrok..."
    ngrok config add-authtoken $NGROK_TOKEN
fi

# Executar comando passado
echo "🚀 Executando: $@"
exec "$@"
