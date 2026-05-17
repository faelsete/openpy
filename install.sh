#!/usr/bin/env bash
# ============================================================================
# OpenPy — Script de instalacao automatica (Linux)
#
# Uso:
#   curl -fsSL https://raw.githubusercontent.com/.../install.sh | bash
#   ou
#   bash install.sh
#
# O que faz:
#   1. Verifica Python >= 3.10
#   2. Cria virtualenv
#   3. Instala dependencias
#   4. Roda onboard interativo
#   5. (Opcional) Instala systemd service
# ============================================================================

set -euo pipefail

OPENPY_HOME="${OPENPY_HOME:-$HOME/.openpy}"
OPENPY_VENV="$OPENPY_HOME/.venv"
OPENPY_REPO="${OPENPY_REPO:-}"
OPENPY_BRANCH="${OPENPY_BRANCH:-main}"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info() { echo -e "${CYAN}[INFO]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC}   $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERRO]${NC} $1"; }

# ============================================================================
# 1. Verificar Python
# ============================================================================
info "Verificando Python..."

PYTHON=""
for cmd in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || true)
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    err "Python >= 3.10 nao encontrado!"
    err "Instale: sudo apt install python3.11 python3.11-venv"
    exit 1
fi

ok "Python encontrado: $PYTHON ($($PYTHON --version))"

# ============================================================================
# 2. Verificar dependencias do sistema
# ============================================================================
info "Verificando dependencias do sistema..."

MISSING=""
for dep in git curl; do
    if ! command -v "$dep" &>/dev/null; then
        MISSING="$MISSING $dep"
    fi
done

if [ -n "$MISSING" ]; then
    warn "Dependencias faltando:$MISSING"
    if command -v apt &>/dev/null; then
        info "Instalando via apt..."
        sudo apt update -qq && sudo apt install -y -qq $MISSING
    elif command -v dnf &>/dev/null; then
        info "Instalando via dnf..."
        sudo dnf install -y $MISSING
    else
        err "Instale manualmente:$MISSING"
        exit 1
    fi
fi

ok "Dependencias do sistema OK"

# ============================================================================
# 3. Criar diretorio e virtualenv
# ============================================================================
info "Criando diretorio OpenPy em $OPENPY_HOME..."
mkdir -p "$OPENPY_HOME"

if [ ! -d "$OPENPY_VENV" ]; then
    info "Criando virtualenv..."
    $PYTHON -m venv "$OPENPY_VENV"
fi

# Ativar venv
source "$OPENPY_VENV/bin/activate"
ok "Virtualenv ativado: $OPENPY_VENV"

# ============================================================================
# 4. Instalar OpenPy
# ============================================================================
if [ -n "$OPENPY_REPO" ]; then
    info "Clonando repositorio..."
    CLONE_DIR="$OPENPY_HOME/src"
    if [ -d "$CLONE_DIR" ]; then
        cd "$CLONE_DIR" && git pull
    else
        git clone --branch "$OPENPY_BRANCH" "$OPENPY_REPO" "$CLONE_DIR"
    fi
    cd "$CLONE_DIR"
    pip install -e ".[all]" --quiet
elif [ -f "pyproject.toml" ]; then
    info "Instalando do diretorio local..."
    pip install -e ".[all]" --quiet
else
    info "Instalando dependencias minimas..."
    pip install --quiet \
        typer rich fastapi uvicorn litellm \
        psutil pydantic httpx structlog chromadb
fi

ok "OpenPy instalado"

# ============================================================================
# 5. Criar alias
# ============================================================================
SHELL_RC=""
if [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
elif [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
fi

ALIAS_LINE="alias openpy='$OPENPY_VENV/bin/python -m openpy.cli.main'"

if [ -n "$SHELL_RC" ]; then
    if ! grep -q "alias openpy=" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# OpenPy" >> "$SHELL_RC"
        echo "$ALIAS_LINE" >> "$SHELL_RC"
        ok "Alias 'openpy' adicionado a $SHELL_RC"
    fi
fi

# ============================================================================
# 6. Rodar onboard
# ============================================================================
echo ""
echo "============================================"
echo "   OpenPy — Instalacao concluida!"
echo "============================================"
echo ""
echo "Para configurar, execute:"
echo "  source $SHELL_RC"
echo "  openpy onboard"
echo ""
echo "Ou diretamente:"
echo "  $OPENPY_VENV/bin/python -m openpy.cli.main onboard"
echo ""

# Perguntar se quer rodar onboard agora
read -p "Deseja rodar o onboard agora? [S/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]] || [[ -z $REPLY ]]; then
    $OPENPY_VENV/bin/python -m openpy.cli.main onboard
fi
