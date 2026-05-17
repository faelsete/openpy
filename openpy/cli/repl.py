"""
OpenPy REPL — Modo interativo no terminal com loop agentico.

O REPL e o modo principal de uso do OpenPy.
Suporta comandos internos (/help, /status, etc.) e tarefas em linguagem natural.
Tarefas sao executadas via agentic loop multi-turn quando o LLM esta disponivel.
"""

import asyncio

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from openpy import __version__
from openpy.core.memory import create_session, end_session

console = Console(force_terminal=True)


def start_repl():
    """Inicia o REPL interativo do OpenPy."""

    # Criar sessao
    session_id = create_session()

    console.print(Panel(
        f"[bold green]OpenPy v{__version__}[/bold green]\n\n"
        "Digite uma tarefa em linguagem natural.\n"
        "Comandos: /help, /status, /skills, /config, /history, /doctor, /exit\n\n"
        f"[dim]Sessao: {session_id}[/dim]",
        border_style="green",
    ))

    task_count = 0

    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]openpy[/bold cyan]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Ate logo![/dim]")
            break

        if not user_input.strip():
            continue

        # Comandos internos
        cmd = user_input.strip().lower()
        if cmd in ("/exit", "/quit", "/q"):
            console.print("[dim]Ate logo![/dim]")
            break
        elif cmd == "/help":
            _show_help()
        elif cmd == "/status":
            _show_status()
        elif cmd == "/skills":
            from openpy.cli.skills_cmd import skills_list
            skills_list()
        elif cmd == "/config":
            from openpy.cli.config_cmd import config_get
            config_get(key=None)
        elif cmd == "/doctor":
            from openpy.cli.doctor_cmd import doctor
            doctor(fix=False, deep=False)
        elif cmd == "/history":
            from openpy.cli.memory_cmd import memory_history
            memory_history(limit=10)
        elif cmd == "/memory":
            from openpy.cli.memory_cmd import memory_status
            memory_status()
        elif cmd == "/providers":
            _show_providers()
        elif cmd == "/tools":
            _show_tools()
        elif cmd.startswith("/"):
            console.print(f"[yellow]Comando desconhecido: {cmd}. Use /help[/yellow]")
        else:
            # Processar tarefa via pipeline
            task_count += 1
            console.print(f"[dim]Processando tarefa #{task_count}...[/dim]")
            from openpy.core.pipeline import run_task
            run_task(user_input)

    # Finalizar sessao
    end_session(session_id)
    console.print(f"[dim]Sessao {session_id} finalizada. {task_count} tarefa(s) executada(s).[/dim]")


def _show_help():
    """Mostra ajuda."""
    console.print(Panel(
        "[bold]Comandos do REPL:[/bold]\n\n"
        "  /help       — Esta ajuda\n"
        "  /status     — Status do sistema (CPU, RAM, disco)\n"
        "  /skills     — Listar skills disponiveis\n"
        "  /config     — Mostrar configuracao\n"
        "  /doctor     — Diagnostico do sistema\n"
        "  /history    — Historico de tarefas\n"
        "  /memory     — Status da memoria\n"
        "  /providers  — Providers de LLM disponiveis\n"
        "  /tools      — Ferramentas do agente\n"
        "  /exit       — Sair\n\n"
        "[dim]Qualquer outro texto sera tratado como tarefa.[/dim]",
        title="Ajuda",
        border_style="cyan",
    ))


def _show_status():
    """Mostra status rapido."""
    import shutil
    import psutil
    from pathlib import Path

    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk_root = str(Path.home().anchor)
    disk = shutil.disk_usage(disk_root)

    console.print(Panel(
        f"CPU: {cpu}%\n"
        f"RAM: {mem.percent}% ({mem.used // (1024**3)}/{mem.total // (1024**3)} GB)\n"
        f"Disco: {round(disk.used / disk.total * 100, 1)}% ({disk.used // (1024**3)}/{disk.total // (1024**3)} GB)",
        title="Status do Sistema",
        border_style="cyan",
    ))


def _show_providers():
    """Mostra providers disponiveis."""
    from openpy.core.cli_providers import ALL_CLI_PROVIDERS
    from openpy.core.llm_engine import PROVIDER_PREFIX_MAP
    from openpy.utils.config import load_config

    config = load_config()
    console.print("\n[bold]Provider ativo:[/bold]")
    console.print(f"  {config.providers.default.type}/{config.providers.default.model}")

    console.print("\n[bold]API Providers (litellm):[/bold]")
    for name, prefix in PROVIDER_PREFIX_MAP.items():
        console.print(f"  {name:25s} -> {prefix}/")

    console.print("\n[bold]CLI Providers:[/bold]")
    for p in ALL_CLI_PROVIDERS:
        status = "[green]OK[/green]" if p.is_available() else "[dim]---[/dim]"
        console.print(f"  {status} {p.name()}")


def _show_tools():
    """Mostra ferramentas do agente."""
    from openpy.tools.registry import create_default_registry
    reg = create_default_registry()
    console.print(f"\n[bold]{reg.count()} ferramentas disponiveis:[/bold]\n")
    for spec in reg.list_all():
        console.print(f"  [cyan]{spec.name:15s}[/cyan] [{spec.risk.value:10s}] {spec.description}")
