"""
OpenPy Response Formatter — Converte resposta JSON do LLM em output legivel.

O harness forca JSON para execucao, mas o usuario precisa ver texto bonito.
"""

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.text import Text
from rich.markdown import Markdown

console = Console(force_terminal=True)


def format_response(llm_response: Any, show_json: bool = False) -> None:
    """Formata e exibe a resposta do LLM de forma legivel."""

    if isinstance(llm_response, str):
        # Resposta em texto puro
        console.print(Panel(
            Markdown(llm_response),
            title="Resposta",
            border_style="green",
        ))
        return

    if isinstance(llm_response, dict) and "error" in llm_response:
        console.print(Panel(
            f"[red]{llm_response['error']}[/red]",
            title="Erro",
            border_style="red",
        ))
        return

    if not isinstance(llm_response, dict):
        console.print(Panel(str(llm_response), title="Resposta", border_style="yellow"))
        return

    # Resposta JSON estruturada do harness
    _format_structured(llm_response, show_json)


def _format_structured(data: dict, show_json: bool = False) -> None:
    """Formata resposta JSON estruturada do harness."""

    # Diagnostico
    diagnostic = data.get("diagnostic", "")
    if diagnostic:
        console.print(f"\n[bold cyan]Diagnostico:[/bold cyan] {diagnostic}")

    # Risco
    risk = data.get("risk", "")
    if risk:
        risk_colors = {"low": "green", "medium": "yellow", "high": "red", "critical": "red bold"}
        color = risk_colors.get(risk, "white")
        console.print(f"[bold]Risco:[/bold] [{color}]{risk}[/{color}]")

    # Confirmacao
    needs_confirm = data.get("needs_confirmation", False)
    if needs_confirm:
        console.print("[yellow]Requer confirmacao antes de executar[/yellow]")

    # Steps
    steps = data.get("steps", [])
    if steps:
        console.print(f"\n[bold]Plano de Execucao ({len(steps)} passos):[/bold]\n")
        for i, step in enumerate(steps, 1):
            desc = step.get("description", "Sem descricao")
            console.print(f"  [cyan]{i}.[/cyan] {desc}")

            # Comandos
            commands = step.get("commands", [])
            for cmd in commands:
                console.print(f"     [dim]$ {cmd}[/dim]")

            # Verificacao
            verification = step.get("verification", [])
            for v in verification:
                console.print(f"     [green]check:[/green] [dim]{v}[/dim]")

            # Rollback
            rollback = step.get("rollback", "")
            if rollback:
                console.print(f"     [yellow]rollback:[/yellow] [dim]{rollback}[/dim]")

    # Tool calls
    tool_calls = data.get("tool_calls", [])
    if tool_calls:
        console.print(f"\n[bold]Ferramentas a usar:[/bold]")
        for tc in tool_calls:
            tool = tc.get("tool", "?")
            params = tc.get("params", {})
            params_str = ", ".join(f"{k}={v}" for k, v in params.items())
            console.print(f"  [cyan]{tool}[/cyan]({params_str})")

    # Sucesso esperado
    expected = data.get("expected_success", "")
    if expected:
        console.print(f"\n[bold green]Resultado esperado:[/bold green] {expected}")

    # Proximo bloqueador
    next_blocker = data.get("next_blocker", "")
    if next_blocker:
        console.print(f"[dim]Proximo possivel problema: {next_blocker}[/dim]")

    # Resposta livre (caso o LLM mande texto junto)
    answer = data.get("answer", "") or data.get("response", "") or data.get("message", "")
    if answer:
        console.print(f"\n{answer}")

    # Mostrar JSON bruto se solicitado
    if show_json:
        console.print("\n")
        syntax = Syntax(json.dumps(data, indent=2, ensure_ascii=False), "json", theme="monokai")
        console.print(Panel(syntax, title="JSON bruto", border_style="dim"))
