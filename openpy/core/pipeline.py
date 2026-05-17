"""
OpenPy Pipeline — Orquestrador principal das 9 camadas.

intake → classifier → skill_loader → harness_builder → llm → validator → executor → verifier → memory/learner

Pipeline completo com execução real, verificação e auto-learning.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from openpy.core.classifier import classify_intent
from openpy.core.harness_builder import build_harness
from openpy.core.skill_loader import load_skill
from openpy.core.contracts import TaskContract, TaskResult
from openpy.utils.config import load_config

console = Console(force_terminal=True)


def _run_async(coro):
    """Executa coroutine de forma segura (funciona dentro ou fora de event loop)."""
    try:
        loop = asyncio.get_running_loop()
        # Ja estamos dentro de um event loop (ex: Telegram bot)
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=300)
    except RuntimeError:
        # Nao tem event loop rodando — usar asyncio.run normal
        return asyncio.run(coro)


def run_task(
    raw_input: str,
    model_override: Optional[str] = None,
    harness_override: Optional[str] = None,
    auto_execute: bool = False,
) -> TaskResult:
    """Executa o pipeline completo para uma tarefa."""

    task_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().isoformat()
    config = load_config()

    console.print(f"\n[dim]Task {task_id} — {timestamp}[/dim]")

    # ── C1: INTAKE ──
    console.print("[bold]C1 INTAKE[/bold] — Registrando pedido...")
    intake = {
        "task_id": task_id,
        "raw_input": raw_input,
        "timestamp": timestamp,
        "language": "pt-BR",
    }

    # ── C2: CLASSIFIER ──
    console.print("[bold]C2 CLASSIFIER[/bold] — Classificando intencao...")
    classification = classify_intent(raw_input)
    console.print(f"  Categoria: [cyan]{classification['category']}[/cyan]")
    console.print(f"  Confianca: [cyan]{classification['confidence']}[/cyan]")
    console.print(f"  Metodo: [dim]{classification['method']}[/dim]")

    # ── C3: SKILL LOADER ──
    console.print("[bold]C3 SKILL LOADER[/bold] — Carregando skills...")
    core_skill, specific_skill = load_skill(classification["category"])
    console.print(f"  Core: [green]CORE_ALWAYS.md[/green]")
    console.print(f"  Skill: [green]{classification['category']}[/green]")

    # ── C4: HARNESS BUILDER ──
    harness_mode = harness_override or config.agent.harness_mode
    console.print(f"[bold]C4 HARNESS[/bold] — Modo: [cyan]{harness_mode}[/cyan]")

    # Injetar ferramentas disponíveis no prompt
    from openpy.tools.registry import create_default_registry
    tool_registry = create_default_registry()
    tools_prompt = tool_registry.generate_tools_prompt()
    console.print(f"  Tools: [green]{tool_registry.count()} ferramentas[/green]")

    full_prompt = build_harness(
        raw_input=raw_input,
        core_skill=core_skill,
        specific_skill=specific_skill,
        classification=classification,
        mode=harness_mode,
        tools_prompt=tools_prompt,
    )

    # ── C5: LLM ENGINE ──
    model = model_override or config.providers.default.model
    console.print(f"[bold]C5 LLM ENGINE[/bold] — Chamando [cyan]{model}[/cyan]...")

    try:
        from openpy.core.llm_engine import call_llm
        llm_response = call_llm(full_prompt, model_override=model_override)
    except Exception as e:
        console.print(f"[red]Erro na chamada LLM: {e}[/red]")
        llm_response = {"error": str(e)}

    # ── C6: VALIDATOR ──
    console.print("[bold]C6 VALIDATOR[/bold] — Validando resposta...")
    from openpy.core.validator import validate_response
    validation = validate_response(llm_response, config.agent.autonomy_level)
    risk_color = "red" if validation["risk"] == "destructive" else "yellow" if validation["risk"] == "risky" else "green"
    console.print(f"  Risco: [{risk_color}]{validation['risk']}[/{risk_color}]")
    console.print(f"  Aprovado: {'[green]OK[/green]' if validation['approved'] else '[red]Requer confirmacao[/red]'}")

    # ── Resultado parcial ──
    result = TaskResult(
        task_id=task_id,
        raw_input=raw_input,
        classification=classification,
        harness_mode=harness_mode,
        model_used=model,
        llm_response=llm_response,
        validation=validation,
    )

    # Mostrar resposta formatada
    console.print("\n")
    has_executable_plan = isinstance(llm_response, dict) and "error" not in llm_response and "steps" in llm_response

    from openpy.core.formatter import format_response
    format_response(llm_response)

    # ── C7: EXECUTOR ──
    if has_executable_plan and validation["approved"]:
        console.print("[bold]C7 EXECUTOR[/bold] — Executando plano...")
        from openpy.core.executor import execute_plan

        execution_result = _run_async(
            execute_plan(
                task_id=task_id,
                llm_response=llm_response,
                validation=validation,
                autonomy_level=config.agent.autonomy_level,
                registry=tool_registry,
            )
        )

        # ── C8: VERIFIER ──
        if execution_result.overall_success:
            console.print("[bold]C8 VERIFIER[/bold] — Verificacao concluida no executor")

            # ── C9: LEARNER (Memory) ──
            console.print("[bold]C9 LEARNER[/bold] — Aprendendo com sucesso...")
            from openpy.core.learner import learn_from_success
            skill_path = learn_from_success(result, execution_result)
            if skill_path:
                console.print(f"  [green]Nova skill aprendida![/green] {skill_path}")
            else:
                console.print("  [dim]Nada novo para aprender[/dim]")
        else:
            console.print("[bold]C8 VERIFIER[/bold] — [yellow]Execucao parcial[/yellow]")
            console.print("[bold]C9 LEARNER[/bold] — [dim]Skipped (execucao nao completa)[/dim]")

    elif has_executable_plan and not validation["approved"]:
        console.print("[bold]C7 EXECUTOR[/bold] — [yellow]Bloqueado pelo validator[/yellow]")

    # ── PERSISTIR NA MEMÓRIA ──
    try:
        from openpy.core.memory import save_task
        exec_success = None
        exec_duration = None
        steps_t = 0
        steps_c = 0
        skill_path_saved = None

        if has_executable_plan and validation["approved"]:
            exec_success = execution_result.overall_success
            exec_duration = execution_result.total_duration_ms
            steps_t = execution_result.total_steps
            steps_c = execution_result.steps_completed
            if execution_result.overall_success and 'skill_path' in dir():
                skill_path_saved = skill_path

        save_task(
            task_id=task_id,
            session_id=None,
            raw_input=raw_input,
            classification=classification,
            harness_mode=harness_mode,
            model_used=model,
            validation=validation,
            execution_success=exec_success,
            execution_duration_ms=exec_duration,
            steps_total=steps_t,
            steps_completed=steps_c,
            skill_learned=skill_path_saved,
            llm_response=llm_response,
        )
    except Exception:
        pass  # Memória não deve bloquear o pipeline

    return result
