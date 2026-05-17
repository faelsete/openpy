"""
OpenPy Gateway — Daemon persistente (control plane).

Equivalente ao `openclaw gateway` do OpenClaw.
"""

import os
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from openpy.utils.config import get_openpy_home, load_config

console = Console()
gateway_app = typer.Typer()


PIDFILE = get_openpy_home() / "gateway.pid"


def _get_pid() -> int | None:
    """Retorna PID do gateway se estiver rodando."""
    if not PIDFILE.exists():
        return None
    try:
        pid = int(PIDFILE.read_text().strip())
        # Verificar se o processo existe (cross-platform)
        import psutil
        if psutil.pid_exists(pid):
            return pid
        else:
            PIDFILE.unlink(missing_ok=True)
            return None
    except (ValueError, Exception):
        PIDFILE.unlink(missing_ok=True)
        return None


@gateway_app.command("start")
def start(
    daemon: bool = typer.Option(False, "-d", "--daemon", help="Rodar em background"),
    port: int = typer.Option(None, "--port", "-p", help="Porta (override do config)"),
):
    """Inicia o Gateway daemon."""
    pid = _get_pid()
    if pid:
        console.print(f"[yellow]⚠ Gateway já está rodando (PID {pid})[/yellow]")
        raise typer.Exit(1)

    config = load_config()
    actual_port = port or config.gateway.port

    if daemon:
        console.print(f"[green]Iniciando Gateway em background na porta {actual_port}...[/green]")
        # Iniciar como subprocesso desacoplado
        log_path = get_openpy_home() / "logs" / "gateway.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = open(log_path, "a")
        creation_flags = 0
        kwargs = {}
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NO_WINDOW
            kwargs["creationflags"] = creation_flags
        else:
            kwargs["start_new_session"] = True
        proc = subprocess.Popen(
            [sys.executable, "-m", "openpy.gateway.server", "--port", str(actual_port)],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            **kwargs,
        )
        PIDFILE.parent.mkdir(parents=True, exist_ok=True)
        PIDFILE.write_text(str(proc.pid))
        console.print(f"[green]Gateway iniciado (PID {proc.pid})[/green]")
    else:
        console.print(f"[green]🚀 Iniciando Gateway em foreground na porta {actual_port}...[/green]")
        console.print("[dim]Pressione Ctrl+C para parar.[/dim]\n")
        try:
            from openpy.gateway.server import run_server
            run_server(port=actual_port)
        except KeyboardInterrupt:
            console.print("\n[yellow]Gateway parado.[/yellow]")


@gateway_app.command("stop")
def stop():
    """Para o Gateway daemon."""
    pid = _get_pid()
    if not pid:
        console.print("[yellow]⚠ Gateway não está rodando.[/yellow]")
        return

    try:
        import psutil
        proc = psutil.Process(pid)
        proc.terminate()
        proc.wait(timeout=5)
        console.print(f"[green]✅ Gateway parado (PID {pid})[/green]")
    except Exception:
        console.print("[yellow]Processo já finalizado.[/yellow]")

    PIDFILE.unlink(missing_ok=True)


@gateway_app.command("restart")
def restart():
    """Reinicia o Gateway daemon."""
    stop()
    import time
    time.sleep(1)
    start(daemon=True)


@gateway_app.command("status")
def status(
    deep: bool = typer.Option(False, "--deep", help="Scan profundo (systemd, portas)"),
):
    """Verifica status do Gateway."""
    pid = _get_pid()
    config = load_config()

    if pid:
        console.print(Panel(
            f"[green]✅ Gateway RODANDO[/green]\n\n"
            f"PID: {pid}\n"
            f"Porta: {config.gateway.port}\n"
            f"Provider: {config.providers.default.model or 'não configurado'}",
            title="Gateway Status",
            border_style="green",
        ))
    else:
        console.print(Panel(
            "[red]❌ Gateway PARADO[/red]\n\n"
            "Inicie com: openpy gateway start",
            title="Gateway Status",
            border_style="red",
        ))

    if deep:
        _deep_scan()


@gateway_app.command("install")
def install(
    system: bool = typer.Option(False, "--system", help="Instalar como serviço do sistema (requer sudo)"),
):
    """Registra o Gateway como serviço systemd."""
    _install_systemd(system_wide=system)


@gateway_app.command("logs")
def logs(
    follow: bool = typer.Option(False, "--follow", "-f", help="Seguir logs em tempo real"),
    lines: int = typer.Option(50, "--lines", "-n", help="Número de linhas"),
):
    """Mostra logs do Gateway."""
    log_file = get_openpy_home() / "logs" / "gateway.log"
    if not log_file.exists():
        console.print("[yellow]Nenhum log encontrado.[/yellow]")
        return

    if follow:
        subprocess.run(["tail", "-f", "-n", str(lines), str(log_file)])
    else:
        content = log_file.read_text(encoding="utf-8", errors="replace")
        log_lines = content.strip().split("\n")
        for line in log_lines[-lines:]:
            console.print(line)


def _install_systemd(system_wide: bool = False):
    """Gera e instala unit file systemd."""
    python_path = sys.executable
    unit_content = f"""[Unit]
Description=OpenPy Gateway - Agentic AI Daemon
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
ExecStart={python_path} -m openpy.gateway.server
Restart=on-failure
RestartSec=5
Environment=OPENPY_HOME={get_openpy_home()}
WorkingDirectory={get_openpy_home() / "workspace"}

[Install]
WantedBy=default.target
"""
    if system_wide:
        unit_path = Path("/etc/systemd/system/openpy-gateway.service")
        console.print(f"[yellow]Requer sudo para instalar em {unit_path}[/yellow]")
    else:
        unit_path = Path.home() / ".config" / "systemd" / "user" / "openpy-gateway.service"

    unit_path.parent.mkdir(parents=True, exist_ok=True)
    unit_path.write_text(unit_content)

    if system_wide:
        subprocess.run(["sudo", "systemctl", "daemon-reload"])
        subprocess.run(["sudo", "systemctl", "enable", "openpy-gateway"])
    else:
        subprocess.run(["systemctl", "--user", "daemon-reload"])
        subprocess.run(["systemctl", "--user", "enable", "openpy-gateway"])

    console.print(f"[green]✅ Serviço instalado: {unit_path}[/green]")
    console.print("[dim]Inicie com: openpy gateway start -d[/dim]")


def _deep_scan():
    """Scan profundo do sistema."""
    console.print("\n[bold]Scan profundo:[/bold]")

    # Verificar systemd
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", "openpy-gateway"],
            capture_output=True, text=True
        )
        systemd_status = result.stdout.strip()
        console.print(f"  systemd user service: {systemd_status}")
    except FileNotFoundError:
        console.print("  systemd: [dim]não disponível (Windows?)[/dim]")

    # Verificar porta
    import socket
    config = load_config()
    port = config.gateway.port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(2)
        result = sock.connect_ex(("localhost", port))
        if result == 0:
            console.print(f"  Porta {port}: [green]aberta[/green]")
        else:
            console.print(f"  Porta {port}: [red]fechada[/red]")
    finally:
        sock.close()
