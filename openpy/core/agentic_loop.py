"""
OpenPy Agentic Loop — Loop de execução multi-turn com ferramentas.

Equivalente ao agentic loop do Claude Code:
1. Recebe input do usuário
2. Chama LLM com ferramentas disponíveis
3. LLM retorna tool_calls
4. Executa ferramentas
5. Injeta resultados de volta no contexto
6. Repete até LLM responder sem tool_calls (resposta final)

Isso permite ao agente raciocinar iterativamente, coletar informações,
executar ações e verificar resultados — tudo em um único fluxo.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from openpy.tools.registry import ToolRegistry, create_default_registry
from openpy.tools.base import ToolResult
from openpy.utils.config import load_config

console = Console(force_terminal=True)

MAX_ITERATIONS = 15  # Limite de iterações para evitar loop infinito
MAX_CONTEXT_TOKENS = 32000  # Limite de contexto


@dataclass
class LoopMessage:
    """Uma mensagem no contexto do loop."""
    role: str  # "user", "assistant", "tool"
    content: str
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None


@dataclass
class AgenticResult:
    """Resultado do loop agêntico."""
    final_response: str = ""
    messages: list[LoopMessage] = field(default_factory=list)
    tool_calls_made: int = 0
    iterations: int = 0
    total_duration_ms: int = 0
    success: bool = False
    skills_context: str = ""


async def run_agentic_loop(
    raw_input: str,
    system_prompt: str,
    model_override: Optional[str] = None,
    registry: Optional[ToolRegistry] = None,
    max_iterations: int = MAX_ITERATIONS,
) -> AgenticResult:
    """
    Executa o loop agêntico completo.

    O LLM pode chamar ferramentas iterativamente até chegar numa resposta final.
    """
    if registry is None:
        registry = create_default_registry()

    config = load_config()
    model = model_override or config.providers.default.model
    provider = config.providers.default

    result = AgenticResult()
    start_time = time.monotonic()

    # Contexto de mensagens (como no Claude Code)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": raw_input},
    ]

    for iteration in range(max_iterations):
        result.iterations = iteration + 1
        console.print(f"  [dim]Iteracao {iteration + 1}/{max_iterations}[/dim]")

        # Chamar LLM
        try:
            import litellm
            litellm.suppress_debug_info = True

            from openpy.core.llm_engine import _resolve_model_name
            resolved_model = _resolve_model_name(model, provider.type, provider.base_url)

            kwargs = {
                "model": resolved_model,
                "messages": messages,
                "temperature": provider.temperature,
                "max_tokens": provider.max_tokens,
            }
            if provider.base_url:
                kwargs["api_base"] = provider.base_url
            if provider.api_key:
                kwargs["api_key"] = provider.api_key

            response = litellm.completion(**kwargs)
            assistant_content = response.choices[0].message.content or ""

        except Exception as e:
            result.final_response = f"Erro LLM: {str(e)}"
            break

        # Tentar parsear JSON da resposta
        parsed = _try_parse_json(assistant_content)

        # Verificar se tem tool_calls
        tool_calls = []
        if isinstance(parsed, dict):
            tool_calls = parsed.get("tool_calls", [])

        if not tool_calls:
            # Resposta final — sem mais tool_calls
            result.final_response = assistant_content
            result.success = True
            console.print(f"  [green]Resposta final na iteracao {iteration + 1}[/green]")
            break

        # Executar tool_calls
        messages.append({"role": "assistant", "content": assistant_content})

        for tc in tool_calls:
            tool_name = tc.get("tool", "")
            params = tc.get("params", {})
            result.tool_calls_made += 1

            console.print(f"  [cyan]Tool:[/cyan] {tool_name}({_format_params(params)})")

            # Validar risco antes de executar
            tool = registry.get(tool_name)
            if not tool:
                tool_output = f"Erro: ferramenta '{tool_name}' nao encontrada. Disponiveis: {[s.name for s in registry.list_all()]}"
            else:
                from openpy.tools.base import ToolRisk
                spec = tool.spec()

                # Executar
                tool_result = await registry.execute(tool_name, **params)

                if tool_result.success:
                    tool_output = tool_result.output[:3000]  # Limitar output
                    console.print(f"    [green]OK[/green] ({tool_result.duration_ms}ms)")
                else:
                    tool_output = f"Erro: {tool_result.error}"
                    console.print(f"    [red]Erro:[/red] {tool_result.error[:100]}")

            # Adicionar resultado da ferramenta ao contexto
            messages.append({
                "role": "user",
                "content": f"[Resultado da ferramenta {tool_name}]:\n{tool_output}",
            })

            result.messages.append(LoopMessage(
                role="tool",
                content=tool_output,
                tool_name=tool_name,
            ))

    else:
        # Atingiu limite de iterações
        result.final_response = "Limite de iteracoes atingido."
        console.print(f"  [yellow]Limite de {max_iterations} iteracoes atingido[/yellow]")

    result.total_duration_ms = int((time.monotonic() - start_time) * 1000)
    return result


def _try_parse_json(text: str) -> Any:
    """Tenta extrair JSON de uma resposta que pode ter markdown."""
    text = text.strip()

    # Tentar direto
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # Tentar extrair de code block
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        try:
            return json.loads(text[start:end].strip())
        except (json.JSONDecodeError, ValueError):
            pass

    if "```" in text:
        parts = text.split("```")
        for part in parts[1::2]:  # Blocos de código (índices ímpares)
            cleaned = part.strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
            try:
                return json.loads(cleaned)
            except (json.JSONDecodeError, ValueError):
                continue

    return text


def _format_params(params: dict) -> str:
    """Formata parâmetros para log."""
    parts = []
    for k, v in params.items():
        if isinstance(v, str) and len(v) > 50:
            v = v[:50] + "..."
        parts.append(f'{k}="{v}"' if isinstance(v, str) else f"{k}={v}")
    return ", ".join(parts)
