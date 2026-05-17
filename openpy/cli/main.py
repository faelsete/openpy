"""
OpenPy CLI — Entry point principal.

Padrao: openpy <noun> [subcommand]
Seguindo arquitetura OpenClaw/Hermes.
"""

import sys
import os

# Fix encoding para Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import typer
from rich.console import Console

from openpy import __version__

console = Console(force_terminal=True)

# App principal
app = typer.Typer(
    name="openpy",
    help="OpenPy - Ecossistema operacional agentico",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


# ============================================================================
# Sub-apps (cada modulo registra seus comandos)
# ============================================================================

from openpy.cli.gateway_cmd import gateway_app
from openpy.cli.doctor_cmd import doctor_app
from openpy.cli.onboard_cmd import onboard_app
from openpy.cli.config_cmd import config_app
from openpy.cli.memory_cmd import memory_app
from openpy.cli.skills_cmd import skills_app

app.add_typer(gateway_app, name="gateway", help="Gerenciar o Gateway daemon")
app.add_typer(doctor_app, name="doctor", help="Diagnostico e reparo do sistema")
app.add_typer(onboard_app, name="onboard", help="Wizard de configuracao inicial")
app.add_typer(config_app, name="config", help="Gerenciar configuracao")
app.add_typer(memory_app, name="memory", help="Gerenciar memoria do agente")
app.add_typer(skills_app, name="skills", help="Gerenciar skills")


# ============================================================================
# Comandos diretos
# ============================================================================

@app.command("run")
def run_task_cmd(
    task: str = typer.Argument(..., help="Tarefa para executar"),
    model: str = typer.Option(None, "--model", "-m", help="Modelo LLM a usar"),
    harness: str = typer.Option(None, "--harness", "-H", help="Modo de harness"),
):
    """Executar uma tarefa diretamente (ex: openpy run 'arruma o servidor')."""
    from openpy.core.pipeline import run_task
    run_task(task, model_override=model, harness_override=harness)


@app.command("repl")
def repl_cmd():
    """Iniciar modo interativo (REPL)."""
    from openpy.cli.repl import start_repl
    start_repl()


@app.command("telegram")
def telegram_cmd():
    """Iniciar bot Telegram (polling)."""
    from openpy.channels.telegram_bot import start_telegram_bot
    start_telegram_bot()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", "-v", help="Mostrar versao"),
):
    """OpenPy - Compilador operacional de intencao humana."""
    if version:
        console.print(f"[bold green]openpy[/bold green] v{__version__}")
        raise typer.Exit()


if __name__ == "__main__":
    app()
