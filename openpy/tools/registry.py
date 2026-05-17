"""
OpenPy Tool Registry — Registro central de todas as ferramentas.

Equivalente ao tools.ts do Claude Code.
Auto-descobre ferramentas e gera inventário para o prompt.
"""

from typing import Optional

from openpy.tools.base import BaseTool, ToolResult, ToolRisk, ToolSpec


class ToolRegistry:
    """Registro central de ferramentas disponíveis."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Registra uma ferramenta."""
        self._tools[tool.spec().name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Busca ferramenta por nome."""
        return self._tools.get(name)

    def list_all(self) -> list[ToolSpec]:
        """Lista todas as ferramentas registradas."""
        return [t.spec() for t in self._tools.values()]

    def list_by_risk(self, max_risk: ToolRisk) -> list[ToolSpec]:
        """Lista ferramentas até o nível de risco especificado."""
        risk_order = [ToolRisk.SAFE_READ, ToolRisk.NORMAL, ToolRisk.RISKY, ToolRisk.DESTRUCTIVE]
        max_idx = risk_order.index(max_risk)
        return [
            t.spec() for t in self._tools.values()
            if risk_order.index(t.spec().risk) <= max_idx
        ]

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """Executa uma ferramenta pelo nome."""
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(success=False, error=f"Ferramenta nao encontrada: {tool_name}")
        return await tool.execute(**kwargs)

    def generate_tools_prompt(self, max_risk: ToolRisk = ToolRisk.RISKY) -> str:
        """Gera descrição de ferramentas para injetar no prompt do LLM."""
        tools = self.list_by_risk(max_risk)
        if not tools:
            return ""

        lines = ["## Ferramentas Disponíveis\n"]
        lines.append("Você pode usar as seguintes ferramentas. Para usar, inclua no JSON de resposta:")
        lines.append('```json')
        lines.append('{')
        lines.append('  "tool_calls": [')
        lines.append('    {"tool": "nome_ferramenta", "params": {"param1": "valor1"}}')
        lines.append('  ]')
        lines.append('}')
        lines.append('```\n')

        for spec in tools:
            tool = self._tools[spec.name]
            lines.append(tool.to_prompt_description())

        return "\n".join(lines)

    def count(self) -> int:
        return len(self._tools)


def create_default_registry() -> ToolRegistry:
    """Cria registry com todas as ferramentas padrão."""
    from openpy.tools.shell import ShellTool
    from openpy.tools.file_tools import FileReadTool, FileWriteTool, FileSearchTool, ListDirTool
    from openpy.tools.web_tools import WebFetchTool, SystemInfoTool

    registry = ToolRegistry()
    registry.register(ShellTool())
    registry.register(FileReadTool())
    registry.register(FileWriteTool())
    registry.register(FileSearchTool())
    registry.register(ListDirTool())
    registry.register(WebFetchTool())
    registry.register(SystemInfoTool())

    return registry
