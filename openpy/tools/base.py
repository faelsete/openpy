"""
OpenPy Tools — Sistema de ferramentas estilo Claude Code.

Cada ferramenta é uma classe que herda de BaseTool.
O agente pode usar qualquer ferramenta disponível no inventário.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ToolRisk(Enum):
    """Nível de risco de uma ferramenta."""
    SAFE_READ = "safe_read"      # Leitura, sem efeito colateral
    NORMAL = "normal"            # Escrita local, baixo risco
    RISKY = "risky"              # Pode afetar sistema
    DESTRUCTIVE = "destructive"  # Pode causar dano irreversível


@dataclass
class ToolResult:
    """Resultado da execução de uma ferramenta."""
    success: bool
    output: str = ""
    error: str = ""
    data: Any = None
    duration_ms: int = 0


@dataclass
class ToolSpec:
    """Especificação de uma ferramenta para o LLM."""
    name: str
    description: str
    parameters: dict = field(default_factory=dict)
    risk: ToolRisk = ToolRisk.SAFE_READ
    examples: list[str] = field(default_factory=list)


class BaseTool(ABC):
    """Interface base para todas as ferramentas do OpenPy."""

    @abstractmethod
    def spec(self) -> ToolSpec:
        """Retorna a especificação da ferramenta."""
        ...

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Executa a ferramenta com os parâmetros fornecidos."""
        ...

    def to_prompt_description(self) -> str:
        """Gera descrição da ferramenta para injeção no prompt do LLM."""
        s = self.spec()
        params_desc = ""
        if s.parameters:
            params_list = []
            for name, info in s.parameters.items():
                required = info.get("required", False)
                desc = info.get("description", "")
                typ = info.get("type", "string")
                req_mark = " (obrigatório)" if required else ""
                params_list.append(f"    - {name} ({typ}){req_mark}: {desc}")
            params_desc = "\n".join(params_list)

        examples_desc = ""
        if s.examples:
            examples_desc = "\n  Exemplos:\n" + "\n".join(f"    {e}" for e in s.examples)

        return (
            f"- **{s.name}** [{s.risk.value}]: {s.description}\n"
            f"  Parâmetros:\n{params_desc}"
            f"{examples_desc}"
        )
