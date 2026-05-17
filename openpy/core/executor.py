"""
OpenPy Executor — Execução segura de planos do LLM.

Pega o JSON do LLM, valida, confirma se necessário, e executa via tools.
Equivalente ao executor do OpenClaw + sandbox do Claude Code.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax

from openpy.tools.registry import ToolRegistry, create_default_registry

console = Console(force_terminal=True)


@dataclass
class StepResult:
    """Resultado de um passo de execução."""
    step_index: int
    description: str
    commands_executed: list[dict] = field(default_factory=list)
    success: bool = False
    output: str = ""
    error: str = ""
    duration_ms: int = 0


@dataclass
class ExecutionResult:
    """Resultado completo da execução de um plano."""
    task_id: str
    total_steps: int
    steps_completed: int = 0
    steps_results: list[StepResult] = field(default_factory=list)
    overall_success: bool = False
    aborted: bool = False
    abort_reason: str = ""
    total_duration_ms: int = 0


async def execute_plan(
    task_id: str,
    llm_response: dict | str,
    validation: dict,
    autonomy_level: str = "normal",
    registry: Optional[ToolRegistry] = None,
) -> ExecutionResult:
    """
    Executa o plano gerado pelo LLM.

    1. Extrai steps do JSON
    2. Para cada step, valida risco
    3. Pede confirmação se necessário
    4. Executa comandos via tools
    5. Roda verificação
    """
    if registry is None:
        registry = create_default_registry()

    start_time = time.monotonic()

    # Se não é um plano JSON estruturado, não tem o que executar
    if isinstance(llm_response, str) or "error" in (llm_response if isinstance(llm_response, dict) else {}):
        return ExecutionResult(
            task_id=task_id,
            total_steps=0,
            aborted=True,
            abort_reason="Resposta do LLM nao e um plano executavel",
        )

    steps = llm_response.get("steps", [])
    if not steps:
        return ExecutionResult(
            task_id=task_id,
            total_steps=0,
            aborted=True,
            abort_reason="Nenhum passo encontrado no plano",
        )

    result = ExecutionResult(task_id=task_id, total_steps=len(steps))

    # Pedir confirmação se necessário
    if validation.get("needs_confirmation", True):
        console.print(Panel(
            f"[bold yellow]Risco: {validation['risk']}[/bold yellow]\n"
            f"Comandos: {validation.get('commands_found', '?')}\n"
            f"Razao: {validation.get('reason', '')}",
            title="Confirmacao Necessaria",
            border_style="yellow",
        ))

        # Mostrar o plano
        for i, step in enumerate(steps):
            desc = step.get("description", f"Passo {i+1}")
            cmds = step.get("commands", [])
            console.print(f"  [cyan]{i+1}.[/cyan] {desc}")
            for cmd in cmds:
                console.print(f"     [dim]$ {cmd}[/dim]")

        if not Confirm.ask("\n[bold]Executar este plano?[/bold]", default=False):
            result.aborted = True
            result.abort_reason = "Cancelado pelo usuario"
            return result

    # Executar cada step
    console.print("\n[bold]Executando plano...[/bold]\n")

    for i, step in enumerate(steps):
        desc = step.get("description", f"Passo {i+1}")
        commands = step.get("commands", [])
        verification = step.get("verification", [])

        console.print(f"[bold cyan]Step {i+1}/{len(steps)}:[/bold cyan] {desc}")

        step_result = StepResult(step_index=i, description=desc)
        step_start = time.monotonic()

        # Executar comandos do step
        all_ok = True
        for cmd in commands:
            console.print(f"  [dim]$ {cmd}[/dim]")
            tool_result = await registry.execute("bash", command=cmd)

            cmd_info = {
                "command": cmd,
                "success": tool_result.success,
                "output": tool_result.output[:500],
                "error": tool_result.error[:500] if tool_result.error else "",
                "duration_ms": tool_result.duration_ms,
            }
            step_result.commands_executed.append(cmd_info)

            if tool_result.success:
                if tool_result.output:
                    console.print(f"  [green]OK[/green] ({tool_result.duration_ms}ms)")
                    # Mostrar output resumido
                    out_lines = tool_result.output.split("\n")
                    for line in out_lines[:5]:
                        console.print(f"    {line}")
                    if len(out_lines) > 5:
                        console.print(f"    [dim]... +{len(out_lines)-5} linhas[/dim]")
                else:
                    console.print(f"  [green]OK[/green] ({tool_result.duration_ms}ms)")
            else:
                console.print(f"  [red]ERRO:[/red] {tool_result.error}")
                all_ok = False
                break

        # Executar verificação
        if verification and all_ok:
            console.print(f"  [dim]Verificando...[/dim]")
            for vcmd in verification:
                v_result = await registry.execute("bash", command=vcmd)
                if v_result.success:
                    console.print(f"  [green]Verificacao OK[/green]: {vcmd}")
                else:
                    console.print(f"  [yellow]Verificacao falhou[/yellow]: {vcmd}")
                    all_ok = False

        step_result.success = all_ok
        step_result.duration_ms = int((time.monotonic() - step_start) * 1000)
        result.steps_results.append(step_result)

        if all_ok:
            result.steps_completed += 1
        else:
            # Verificar se tem rollback
            rollback = step.get("rollback", "")
            if rollback:
                console.print(f"  [yellow]Rollback disponivel:[/yellow] {rollback}")
            break

    result.overall_success = result.steps_completed == result.total_steps
    result.total_duration_ms = int((time.monotonic() - start_time) * 1000)

    # Sumário
    if result.overall_success:
        console.print(f"\n[bold green]Plano executado com sucesso![/bold green] ({result.total_duration_ms}ms)")
    else:
        console.print(f"\n[bold yellow]Plano parcialmente executado:[/bold yellow] {result.steps_completed}/{result.total_steps} steps")

    return result
