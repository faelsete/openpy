"""
OpenPy Doctor — Diagnóstico e reparo automático.

Equivalente ao `openclaw doctor` do OpenClaw.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from openpy.utils.config import (
    get_config_path,
    get_data_path,
    get_logs_path,
    get_openpy_home,
    get_skills_path,
    load_config,
)

console = Console()
doctor_app = typer.Typer(invoke_without_command=True)


# ============================================================================
# Checks
# ============================================================================

def check_config() -> dict:
    """Verifica configuração."""
    config_path = get_config_path()
    if not config_path.exists():
        return {"name": "Configuração", "status": "error", "msg": "openpy.json não encontrado", "fix": "openpy onboard"}
    try:
        config = load_config(force_reload=True)
        if not config.providers.default.model:
            return {"name": "Configuração", "status": "warn", "msg": "Nenhum modelo configurado", "fix": "openpy config set providers.default.model <modelo>"}
        return {"name": "Configuração", "status": "ok", "msg": f"OK — modelo: {config.providers.default.model}"}
    except Exception as e:
        return {"name": "Configuração", "status": "error", "msg": f"Erro no JSON: {e}", "fix": "openpy onboard"}


def check_directories() -> dict:
    """Verifica diretórios essenciais."""
    missing = []
    for name, path_fn in [("home", get_openpy_home), ("data", get_data_path), ("logs", get_logs_path), ("skills", get_skills_path)]:
        if not path_fn().exists():
            missing.append(name)

    if missing:
        return {"name": "Diretórios", "status": "error", "msg": f"Faltando: {', '.join(missing)}", "fix": "openpy onboard"}
    return {"name": "Diretórios", "status": "ok", "msg": "Todos os diretórios existem"}


def check_gateway() -> dict:
    """Verifica se gateway está rodando."""
    pid_file = get_openpy_home() / "gateway.pid"
    if not pid_file.exists():
        return {"name": "Gateway", "status": "warn", "msg": "Não está rodando", "fix": "openpy gateway start"}

    import psutil
    try:
        pid = int(pid_file.read_text().strip())
        if psutil.pid_exists(pid):
            return {"name": "Gateway", "status": "ok", "msg": f"Rodando (PID {pid})"}
        return {"name": "Gateway", "status": "warn", "msg": "PID file existe mas processo morto", "fix": "openpy gateway start"}
    except (ValueError, Exception):
        return {"name": "Gateway", "status": "warn", "msg": "PID file corrompido", "fix": "openpy gateway start"}


def check_provider() -> dict:
    """Verifica conectividade com provider de LLM."""
    try:
        config = load_config()
        provider = config.providers.default
        if not provider.api_key and not provider.base_url:
            return {"name": "Provider LLM", "status": "error", "msg": "Nenhum provider configurado", "fix": "openpy onboard"}
        if provider.base_url:
            import httpx
            try:
                r = httpx.get(f"{provider.base_url.rstrip('/')}/models", timeout=5, headers={"Authorization": f"Bearer {provider.api_key}"})
                if r.status_code == 200:
                    return {"name": "Provider LLM", "status": "ok", "msg": f"Conectado — {provider.model}"}
                return {"name": "Provider LLM", "status": "warn", "msg": f"Resposta {r.status_code}"}
            except Exception:
                return {"name": "Provider LLM", "status": "warn", "msg": f"Não alcançável: {provider.base_url}"}
        return {"name": "Provider LLM", "status": "ok", "msg": f"Configurado: {provider.type}/{provider.model}"}
    except Exception as e:
        return {"name": "Provider LLM", "status": "error", "msg": str(e)}


def check_cli_providers() -> dict:
    """Verifica CLI providers disponiveis (Ollama, Codex, Gemini, etc)."""
    try:
        from openpy.core.cli_providers import detect_available_providers, ALL_CLI_PROVIDERS
        available = detect_available_providers()
        names = [p.name() for p in available]
        total = len(ALL_CLI_PROVIDERS)
        if available:
            return {"name": "CLI Providers", "status": "ok", "msg": f"{len(available)}/{total}: {', '.join(names)}"}
        return {"name": "CLI Providers", "status": "warn", "msg": "Nenhum CLI provider instalado"}
    except Exception as e:
        return {"name": "CLI Providers", "status": "warn", "msg": str(e)}


def check_tools() -> dict:
    """Verifica ferramentas do agente."""
    try:
        from openpy.tools.registry import create_default_registry
        reg = create_default_registry()
        names = [s.name for s in reg.list_all()]
        return {"name": "Tools (agente)", "status": "ok", "msg": f"{reg.count()} tools: {', '.join(names)}"}
    except Exception as e:
        return {"name": "Tools (agente)", "status": "error", "msg": str(e)}


def check_skills() -> dict:
    """Verifica skills disponíveis."""
    # Bundled
    bundled = Path(__file__).parent.parent / "skills"
    user_skills = get_skills_path()

    count = 0
    for d in [bundled, user_skills]:
        if d.exists():
            count += len(list(d.rglob("*.md")))

    if count == 0:
        return {"name": "Skills", "status": "error", "msg": "Nenhuma skill encontrada", "fix": "openpy onboard (copia skills bundled)"}
    return {"name": "Skills", "status": "ok", "msg": f"{count} skills disponíveis"}


def check_memory() -> dict:
    """Verifica bancos de memória."""
    db_path = get_data_path() / "openpy.sqlite3"
    chroma_path = get_data_path() / "chroma"

    issues = []
    if not db_path.exists():
        issues.append("SQLite não inicializado")
    if not chroma_path.exists():
        issues.append("ChromaDB não inicializado")

    if issues:
        return {"name": "Memória", "status": "warn", "msg": "; ".join(issues), "fix": "Será inicializado no primeiro uso"}
    return {"name": "Memória", "status": "ok", "msg": "SQLite + ChromaDB presentes"}


def check_python_deps() -> dict:
    """Verifica dependências Python instaladas."""
    missing = []
    for pkg in ["typer", "rich", "fastapi", "litellm", "chromadb", "pydantic", "httpx", "structlog"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        return {"name": "Dependências Python", "status": "error", "msg": f"Faltando: {', '.join(missing)}", "fix": "pip install -e ."}
    return {"name": "Dependências Python", "status": "ok", "msg": "Todas instaladas"}


def check_telegram() -> dict:
    """Verifica configuração do Telegram."""
    try:
        config = load_config()
        tg = config.channels.telegram
        if not tg.enabled:
            return {"name": "Telegram", "status": "info", "msg": "Não configurado (opcional)"}
        if not tg.token:
            return {"name": "Telegram", "status": "error", "msg": "Habilitado mas sem token", "fix": "openpy onboard"}
        return {"name": "Telegram", "status": "ok", "msg": f"Configurado — {len(tg.allowed_users)} usuário(s)"}
    except Exception:
        return {"name": "Telegram", "status": "info", "msg": "Não configurado"}


# ============================================================================
# Repair
# ============================================================================

def auto_fix(results: list[dict]):
    """Tenta reparar problemas automaticamente."""
    from openpy.utils.config import ensure_directories
    ensure_directories()
    console.print("[green]✅ Diretórios recriados[/green]")

    # Limpar PID file órfão
    pid_file = get_openpy_home() / "gateway.pid"
    if pid_file.exists():
        import psutil
        try:
            pid = int(pid_file.read_text().strip())
            if not psutil.pid_exists(pid):
                pid_file.unlink()
                console.print("[green]PID file orfao removido[/green]")
        except (ValueError, Exception):
            pid_file.unlink(missing_ok=True)
            console.print("[green]PID file corrompido removido[/green]")

    console.print("\n[yellow]Para problemas de configuração, execute: openpy onboard[/yellow]")


# ============================================================================
# Comando principal
# ============================================================================

@doctor_app.callback(invoke_without_command=True)
def doctor(
    fix: bool = typer.Option(False, "--fix", help="Tentar reparar problemas automaticamente"),
    deep: bool = typer.Option(False, "--deep", help="Scan profundo (systemd, orphans)"),
):
    """🩺 Diagnóstico completo do sistema OpenPy."""
    console.print(Panel(
        "[bold]🩺 OpenPy Doctor[/bold]\n\nAnalisando saúde do sistema...",
        border_style="cyan",
    ))

    checks = [
        check_directories(),
        check_config(),
        check_python_deps(),
        check_provider(),
        check_cli_providers(),
        check_tools(),
        check_gateway(),
        check_skills(),
        check_memory(),
        check_telegram(),
    ]

    # Tabela de resultados
    table = Table(show_lines=True)
    table.add_column("Componente", style="bold")
    table.add_column("Status")
    table.add_column("Detalhes")
    table.add_column("Correção")

    status_icons = {
        "ok": "[green]✅ OK[/green]",
        "warn": "[yellow]⚠ Aviso[/yellow]",
        "error": "[red]❌ Erro[/red]",
        "info": "[blue]ℹ Info[/blue]",
    }

    errors = 0
    warnings = 0
    for check in checks:
        icon = status_icons.get(check["status"], "?")
        table.add_row(check["name"], icon, check.get("msg", ""), check.get("fix", ""))
        if check["status"] == "error":
            errors += 1
        elif check["status"] == "warn":
            warnings += 1

    console.print(table)

    # Deep scan
    if deep:
        console.print("\n[bold]Scan profundo:[/bold]")
        try:
            result = subprocess.run(["systemctl", "--user", "list-units", "--all", "openpy*"], capture_output=True, text=True)
            console.print(f"  systemd units: {result.stdout.strip() or 'nenhum'}")
        except FileNotFoundError:
            console.print("  systemd: [dim]não disponível[/dim]")

    # Sumário
    if errors == 0 and warnings == 0:
        console.print("\n[green]✅ Sistema saudável![/green]")
    else:
        console.print(f"\n[yellow]Resultado: {errors} erro(s), {warnings} aviso(s)[/yellow]")

    if fix and (errors > 0 or warnings > 0):
        console.print("\n[bold]Tentando reparar...[/bold]\n")
        auto_fix(checks)
