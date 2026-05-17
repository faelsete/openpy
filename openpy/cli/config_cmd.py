"""
OpenPy Config CLI — Gerenciar configuração.
"""

import json

import typer
from rich.console import Console
from rich.syntax import Syntax

from openpy.utils.config import get_config_path, load_config, save_config

console = Console()
config_app = typer.Typer()


@config_app.command("get")
def config_get(key: str = typer.Argument(None, help="Chave (ex: providers.default.model). Vazio = mostra tudo")):
    """Mostra configuração atual."""
    config = load_config()
    data = config.model_dump()

    if key:
        parts = key.split(".")
        value = data
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                console.print(f"[red]Chave não encontrada: {key}[/red]")
                raise typer.Exit(1)
        console.print(json.dumps(value, indent=2, ensure_ascii=False))
    else:
        syntax = Syntax(json.dumps(data, indent=2, ensure_ascii=False), "json", theme="monokai")
        console.print(syntax)


@config_app.command("set")
def config_set(key: str = typer.Argument(..., help="Chave (ex: agent.harness_mode)"), value: str = typer.Argument(..., help="Valor")):
    """Altera um valor de configuração."""
    config = load_config()
    data = config.model_dump()

    parts = key.split(".")
    target = data
    for part in parts[:-1]:
        if isinstance(target, dict) and part in target:
            target = target[part]
        else:
            console.print(f"[red]Caminho não encontrado: {key}[/red]")
            raise typer.Exit(1)

    last_key = parts[-1]
    if last_key not in target:
        console.print(f"[red]Chave não encontrada: {key}[/red]")
        raise typer.Exit(1)

    # Tentar converter tipo
    old_value = target[last_key]
    if isinstance(old_value, bool):
        target[last_key] = value.lower() in ("true", "1", "yes")
    elif isinstance(old_value, int):
        target[last_key] = int(value)
    elif isinstance(old_value, float):
        target[last_key] = float(value)
    else:
        target[last_key] = value

    from openpy.utils.config import OpenPyConfig
    new_config = OpenPyConfig(**data)
    save_config(new_config)
    console.print(f"[green]✅ {key} = {value}[/green]")


@config_app.command("schema")
def config_schema():
    """Mostra o schema completo de configuração."""
    from openpy.utils.config import OpenPyConfig
    schema = OpenPyConfig.model_json_schema()
    syntax = Syntax(json.dumps(schema, indent=2, ensure_ascii=False), "json", theme="monokai")
    console.print(syntax)


@config_app.command("validate")
def config_validate():
    """Valida o arquivo de configuração atual."""
    try:
        config = load_config(force_reload=True)
        console.print("[green]✅ Configuração válida[/green]")
        console.print(f"  Provider: {config.providers.default.type}/{config.providers.default.model}")
        console.print(f"  Harness: {config.agent.harness_mode}")
        console.print(f"  Autonomia: {config.agent.autonomy_level}")
    except Exception as e:
        console.print(f"[red]❌ Erro de validação: {e}[/red]")
