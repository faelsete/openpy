"""
OpenPy CLI — Entry point principal.

Padrao: openpy <noun> [subcommand]
Seguindo arquitetura OpenClaw/Hermes.
"""

import sys
import os
from pathlib import Path

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


@app.command("systemd")
def systemd_cmd(
    action: str = typer.Argument("install", help="install|status|logs|remove"),
):
    """Gerenciar servicos systemd (Linux)."""
    import subprocess
    import sys

    if sys.platform == "win32":
        console.print("[yellow]systemd nao disponivel no Windows.[/yellow]")
        raise typer.Exit(1)

    venv_python = sys.executable
    workdir = str(Path(__file__).parent.parent.parent.resolve())

    gateway_unit = f"""[Unit]
Description=OpenPy Gateway + Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory={workdir}
ExecStart={venv_python} -m openpy.gateway.server
Restart=always
RestartSec=5
Environment=PYTHONIOENCODING=utf-8
StandardOutput=journal
StandardError=journal
SyslogIdentifier=openpy-gateway

[Install]
WantedBy=multi-user.target
"""

    telegram_unit = f"""[Unit]
Description=OpenPy Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory={workdir}
ExecStart={venv_python} -m openpy.cli.main telegram
Restart=always
RestartSec=5
Environment=PYTHONIOENCODING=utf-8
StandardOutput=journal
StandardError=journal
SyslogIdentifier=openpy-telegram

[Install]
WantedBy=multi-user.target
"""

    if action == "install":
        from pathlib import Path as P
        P("/etc/systemd/system/openpy-gateway.service").write_text(gateway_unit)
        P("/etc/systemd/system/openpy-telegram.service").write_text(telegram_unit)
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "enable", "openpy-gateway", "openpy-telegram"], check=True)
        console.print("[green]Servicos instalados e habilitados.[/green]")
        console.print("[dim]Iniciar: systemctl start openpy-gateway openpy-telegram[/dim]")

    elif action == "status":
        subprocess.run(["systemctl", "status", "openpy-gateway", "openpy-telegram", "--no-pager"])

    elif action == "logs":
        subprocess.run(["journalctl", "-u", "openpy-gateway", "-u", "openpy-telegram", "--no-pager", "-n", "50"])

    elif action == "remove":
        subprocess.run(["systemctl", "stop", "openpy-gateway", "openpy-telegram"], check=False)
        subprocess.run(["systemctl", "disable", "openpy-gateway", "openpy-telegram"], check=False)
        for f in ["/etc/systemd/system/openpy-gateway.service", "/etc/systemd/system/openpy-telegram.service"]:
            from pathlib import Path as P
            P(f).unlink(missing_ok=True)
        subprocess.run(["systemctl", "daemon-reload"])
        console.print("[green]Servicos removidos.[/green]")
    else:
        console.print("[red]Acao invalida. Use: install|status|logs|remove[/red]")


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
