"""
OpenPy Onboard — Wizard de configuracao inicial.

Verifica pre-requisitos, detecta providers, configura tudo interativamente.
Equivalente ao `openclaw onboard` do OpenClaw.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from openpy.utils.config import (
    OpenPyConfig,
    ProviderConfig,
    ensure_directories,
    get_config_path,
    get_openpy_home,
    load_config,
    save_config,
)

console = Console(force_terminal=True)
onboard_app = typer.Typer(invoke_without_command=True)


# ============================================================================
# Verificacao de pre-requisitos
# ============================================================================

PREREQUISITES = [
    {"name": "Python", "cmd": "python3 --version", "fallback_cmd": "python --version", "min_version": "3.10", "install_hint": "https://python.org/downloads/"},
    {"name": "pip", "cmd": "pip3 --version", "fallback_cmd": "pip --version", "install_hint": "python -m ensurepip --upgrade"},
    {"name": "git", "cmd": "git --version", "install_hint": "sudo apt install git"},
    {"name": "Docker", "cmd": "docker --version", "install_hint": "https://docs.docker.com/engine/install/", "optional": True},
    {"name": "ngrok", "cmd": "ngrok version", "install_hint": "https://ngrok.com/download", "optional": True},
    {"name": "ffmpeg", "cmd": "ffmpeg -version", "install_hint": "sudo apt install ffmpeg", "optional": True},
    {"name": "curl", "cmd": "curl --version", "install_hint": "sudo apt install curl"},
]


def check_command(cmd: str) -> tuple[bool, str]:
    """Verifica se um comando existe e retorna (exists, version_output)."""
    try:
        result = subprocess.run(
            cmd.split(), capture_output=True, text=True, timeout=10
        )
        output = result.stdout.strip() or result.stderr.strip()
        return result.returncode == 0, output.split("\n")[0]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, ""


def check_prerequisites() -> list[dict]:
    """Verifica todos os pre-requisitos e retorna resultados."""
    results = []
    for prereq in PREREQUISITES:
        found, version = check_command(prereq["cmd"])
        if not found and "fallback_cmd" in prereq:
            found, version = check_command(prereq["fallback_cmd"])
        results.append({
            **prereq,
            "found": found,
            "version": version,
        })
    return results


def display_prerequisites(results: list[dict]) -> bool:
    """Mostra tabela de pre-requisitos. Retorna True se todos obrigatorios OK."""
    table = Table(title="Pre-requisitos do Sistema", show_lines=True)
    table.add_column("Componente", style="bold")
    table.add_column("Status")
    table.add_column("Versao / Info")
    table.add_column("Como instalar")

    all_required_ok = True
    for r in results:
        is_optional = r.get("optional", False)
        if r["found"]:
            status = "[green]OK[/green]"
            hint = ""
        elif is_optional:
            status = "[yellow]Opcional[/yellow]"
            hint = r.get("install_hint", "")
        else:
            status = "[red]Faltando[/red]"
            hint = r.get("install_hint", "")
            all_required_ok = False

        name = f"{r['name']}" + (" (opcional)" if is_optional else "")
        table.add_row(name, status, r["version"] or "-", hint)

    console.print(table)
    return all_required_ok


# ============================================================================
# Provider Detection & Wizard
# ============================================================================

PROVIDER_CHOICES = [
    ("openai-compatible", "Ollama, vLLM, LM Studio, GPT4All (local)"),
    ("ollama", "Ollama (local, gratuito)"),
    ("openai", "OpenAI (GPT-4o, GPT-4o-mini)"),
    ("anthropic", "Anthropic (Claude Sonnet, Opus)"),
    ("google", "Google (Gemini Pro, Flash)"),
    ("groq", "Groq (Llama, Mixtral - rapido)"),
    ("deepseek", "DeepSeek (V3, Coder)"),
    ("nvidia-nim", "NVIDIA NIM (modelos enterprise)"),
    ("openrouter", "OpenRouter (multi-provider, gratuitos disponiveis)"),
    ("together", "Together AI (open-source models)"),
    ("mistral", "Mistral AI (Mistral Large, Small)"),
]

PROVIDER_DEFAULTS = {
    "openai-compatible": {"base_url": "http://localhost:11434/v1", "api_key": "ollama", "model": "nemotron-mini:4b"},
    "ollama": {"base_url": "http://localhost:11434/v1", "api_key": "ollama", "model": "llama3.2"},
    "openai": {"base_url": "", "api_key": "", "model": "gpt-4o-mini"},
    "anthropic": {"base_url": "", "api_key": "", "model": "claude-sonnet-4-20250514"},
    "google": {"base_url": "", "api_key": "", "model": "gemini-2.0-flash"},
    "groq": {"base_url": "", "api_key": "", "model": "llama-3.3-70b-versatile"},
    "deepseek": {"base_url": "", "api_key": "", "model": "deepseek-chat"},
    "nvidia-nim": {"base_url": "https://integrate.api.nvidia.com/v1", "api_key": "", "model": "meta/llama-3.1-8b-instruct"},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "api_key": "", "model": "meta-llama/llama-3.3-70b-instruct:free"},
    "together": {"base_url": "", "api_key": "", "model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"},
    "mistral": {"base_url": "", "api_key": "", "model": "mistral-small-latest"},
}


def wizard_provider() -> ProviderConfig:
    """Configura provider de LLM interativamente com deteccao automatica."""
    console.print("\n[bold cyan]Configuracao do Provider de LLM[/bold cyan]\n")

    # Detectar CLI providers
    from openpy.core.cli_providers import detect_available_providers
    available_cli = detect_available_providers()
    if available_cli:
        console.print("[green]CLI Providers detectados:[/green]")
        for p in available_cli:
            console.print(f"  [green]>[/green] {p.name()}")
        console.print()

    # Mostrar opcoes
    console.print("[bold]Providers disponiveis:[/bold]\n")
    for i, (key, desc) in enumerate(PROVIDER_CHOICES, 1):
        console.print(f"  [cyan]{i:2d}.[/cyan] {key:20s} — {desc}")

    console.print()
    choice = Prompt.ask(
        "Escolha o numero do provider",
        default="1",
    )

    try:
        idx = int(choice) - 1
        provider_type = PROVIDER_CHOICES[idx][0]
    except (ValueError, IndexError):
        provider_type = "openai-compatible"

    defaults = PROVIDER_DEFAULTS.get(provider_type, PROVIDER_DEFAULTS["openai-compatible"])

    console.print(f"\n[bold]Configurando: {provider_type}[/bold]\n")

    base_url = defaults["base_url"]
    if base_url:
        base_url = Prompt.ask("URL base da API", default=base_url)
    elif provider_type in ("openai", "anthropic", "google", "groq", "deepseek", "mistral"):
        # Esses providers nao precisam de base_url (litellm resolve)
        base_url = ""
    else:
        base_url = Prompt.ask("URL base da API", default="")

    api_key = Prompt.ask(
        "API Key" + (" (enter para pular se local)" if provider_type in ("openai-compatible", "ollama") else ""),
        default=defaults["api_key"],
    )

    model = Prompt.ask("Nome do modelo", default=defaults["model"])
    temperature = float(Prompt.ask("Temperature", default="0.3"))

    return ProviderConfig(
        type=provider_type,
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=temperature,
    )


def wizard_telegram() -> dict:
    """Configura Telegram interativamente."""
    console.print("\n[bold cyan]Configuracao do Telegram[/bold cyan]\n")

    if not Confirm.ask("Deseja configurar o Telegram como channel?", default=False):
        return {"enabled": False}

    console.print("[dim]Crie um bot em @BotFather no Telegram e copie o token.[/dim]")
    token = Prompt.ask("Bot Token")

    console.print("[dim]Envie /start pro seu bot e acesse https://api.telegram.org/bot<TOKEN>/getUpdates para ver seu ID.[/dim]")
    user_id = Prompt.ask("Seu Telegram User ID (numero)")

    return {
        "enabled": True,
        "token": token,
        "allowed_users": [int(user_id)],
        "shortcuts": True,
    }


def wizard_autonomy() -> str:
    """Configura nivel de autonomia."""
    console.print("\n[bold cyan]Nivel de Autonomia[/bold cyan]\n")
    console.print("[dim]safe_read  — So leitura, nunca executa[/dim]")
    console.print("[dim]normal     — Executa comandos seguros, pede confirmacao para riscos[/dim]")
    console.print("[dim]risky      — Executa quase tudo, pede so para acoes destrutivas[/dim]")
    console.print("[dim]full       — Autonomia total (perigoso)[/dim]")

    return Prompt.ask(
        "Nivel de autonomia",
        choices=["safe_read", "normal", "risky", "full"],
        default="normal",
    )


def wizard_harness() -> str:
    """Configura modo do harness."""
    console.print("\n[bold cyan]Modo do Harness[/bold cyan]\n")
    console.print("[dim]plain   — Sem harness (modelo cru)[/dim]")
    console.print("[dim]strong  — Harness completo com analise e contrato JSON (recomendado)[/dim]")
    console.print("[dim]xhigh   — Strong + analise de risco extendida[/dim]")
    console.print("[dim]brutal  — XHigh + revisao adversarial[/dim]")

    return Prompt.ask(
        "Modo do harness",
        choices=["plain", "strong", "xhigh", "brutal"],
        default="strong",
    )


# ============================================================================
# Systemd Service
# ============================================================================

SYSTEMD_TEMPLATE = """[Unit]
Description=OpenPy Gateway — Agente Autonomo
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User={user}
WorkingDirectory={home}
ExecStart={python} -m openpy.gateway.server
Restart=always
RestartSec=5
Environment=PYTHONIOENCODING=utf-8
Environment=HOME={user_home}
StandardOutput=journal
StandardError=journal
SyslogIdentifier=openpy

[Install]
WantedBy=multi-user.target
"""


def install_systemd():
    """Instala servico systemd para o gateway."""
    import getpass
    import os

    if sys.platform == "win32":
        console.print("[yellow]systemd nao disponivel no Windows. Use 'openpy gateway start -d' para daemon.[/yellow]")
        return

    user = getpass.getuser()
    python = sys.executable
    home = str(get_openpy_home())
    user_home = os.path.expanduser("~")

    service_content = SYSTEMD_TEMPLATE.format(
        user=user,
        home=home,
        python=python,
        user_home=user_home,
    )

    # User-level systemd
    service_dir = Path.home() / ".config" / "systemd" / "user"
    service_dir.mkdir(parents=True, exist_ok=True)
    service_path = service_dir / "openpy-gateway.service"
    service_path.write_text(service_content)

    console.print(f"[green]Servico criado:[/green] {service_path}")

    # Habilitar e iniciar
    try:
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "--user", "enable", "openpy-gateway"], check=True)
        subprocess.run(["systemctl", "--user", "start", "openpy-gateway"], check=True)
        console.print("[green]Servico habilitado e iniciado![/green]")
        console.print("[dim]Comandos uteis:[/dim]")
        console.print("  systemctl --user status openpy-gateway")
        console.print("  journalctl --user -u openpy-gateway -f")
    except Exception as e:
        console.print(f"[yellow]Servico criado mas nao iniciado: {e}[/yellow]")
        console.print(f"[dim]Inicie manualmente: systemctl --user start openpy-gateway[/dim]")


# ============================================================================
# Comando principal
# ============================================================================

@onboard_app.callback(invoke_without_command=True)
def onboard(
    install_daemon: bool = typer.Option(False, "--install-daemon", help="Instalar como servico systemd apos configurar"),
):
    """Wizard de configuracao inicial do OpenPy."""
    console.print(Panel(
        "[bold green]OpenPy[/bold green]\n\n"
        "Este wizard vai configurar seu ecossistema agentico.\n"
        "Vamos verificar pre-requisitos e configurar tudo passo a passo.",
        title="OpenPy Onboard",
        border_style="green",
    ))

    # 1. Verificar pre-requisitos
    console.print("\n[bold]Etapa 1/6 — Verificando pre-requisitos...[/bold]\n")
    results = check_prerequisites()
    all_ok = display_prerequisites(results)

    if not all_ok:
        console.print("\n[red]Alguns pre-requisitos obrigatorios estao faltando.[/red]")
        console.print("[yellow]Instale-os e rode 'openpy onboard' novamente.[/yellow]")
        if not Confirm.ask("Deseja continuar mesmo assim?", default=False):
            raise typer.Exit(1)

    # 2. Criar diretorios
    console.print("\n[bold]Etapa 2/6 — Criando estrutura de diretorios...[/bold]\n")
    ensure_directories()
    console.print(f"[green]Diretorios criados em {get_openpy_home()}[/green]")

    # 3. Configurar provider
    console.print("\n[bold]Etapa 3/6 — Configurar Provider de LLM[/bold]")
    provider = wizard_provider()

    # 4. Configurar Harness
    console.print("\n[bold]Etapa 4/6 — Configurar Harness[/bold]")
    harness_mode = wizard_harness()

    # 5. Configurar Telegram
    console.print("\n[bold]Etapa 5/6 — Configurar Channels[/bold]")
    telegram_cfg = wizard_telegram()

    # 6. Configurar autonomia
    console.print("\n[bold]Etapa 6/6 — Configurar Autonomia[/bold]")
    autonomy = wizard_autonomy()

    # Montar e salvar config
    config = OpenPyConfig()
    config.providers.default = provider
    config.agent.autonomy_level = autonomy
    config.agent.harness_mode = harness_mode

    if telegram_cfg.get("enabled"):
        config.channels.telegram.enabled = True
        config.channels.telegram.token = telegram_cfg["token"]
        config.channels.telegram.allowed_users = telegram_cfg["allowed_users"]
        config.channels.telegram.shortcuts = telegram_cfg["shortcuts"]

    save_config(config)

    # Copiar skills bundled para ~/.openpy/skills se nao existirem
    _copy_bundled_skills()

    # Resumo
    console.print("\n")
    console.print(Panel(
        f"[green]Configuracao salva em:[/green] {get_config_path()}\n\n"
        f"[bold]Provider:[/bold] {provider.type} -> {provider.model}\n"
        f"[bold]Harness:[/bold] {harness_mode}\n"
        f"[bold]Telegram:[/bold] {'Configurado' if telegram_cfg.get('enabled') else 'Nao configurado'}\n"
        f"[bold]Autonomia:[/bold] {autonomy}\n\n"
        "[dim]Proximos passos:[/dim]\n"
        "  openpy gateway start     -> Iniciar o daemon\n"
        "  openpy doctor            -> Verificar saude do sistema\n"
        "  openpy repl              -> Modo interativo\n"
        '  openpy run "tarefa"      -> Executar uma tarefa',
        title="Onboarding Completo",
        border_style="green",
    ))

    # Instalar daemon se solicitado
    if install_daemon:
        console.print("\n[bold]Instalando como servico systemd...[/bold]")
        install_systemd()


def _copy_bundled_skills():
    """Copia skills bundled para o diretorio do usuario."""
    bundled_dir = Path(__file__).parent.parent / "skills"
    user_skills = get_openpy_home() / "skills"

    if not bundled_dir.exists():
        return

    for skill_file in bundled_dir.rglob("*.md"):
        relative = skill_file.relative_to(bundled_dir)
        target = user_skills / relative
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(skill_file, target)
            console.print(f"  [dim]Skill copiada: {relative}[/dim]")
