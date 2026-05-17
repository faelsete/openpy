"""
OpenPy File Tools — Leitura, escrita, busca em arquivos.

Equivalente ao ReadFile/WriteFile/Search do Claude Code.
"""

import os
from pathlib import Path
from typing import Optional

from openpy.tools.base import BaseTool, ToolResult, ToolRisk, ToolSpec


class FileReadTool(BaseTool):
    """Lê conteúdo de um arquivo."""

    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="file_read",
            description="Lê o conteúdo de um arquivo do sistema de arquivos",
            risk=ToolRisk.SAFE_READ,
            parameters={
                "path": {"type": "string", "description": "Caminho do arquivo", "required": True},
                "start_line": {"type": "integer", "description": "Linha inicial (1-indexed)", "required": False},
                "end_line": {"type": "integer", "description": "Linha final (1-indexed)", "required": False},
            },
            examples=['file_read(path="/etc/nginx/nginx.conf")', 'file_read(path="docker-compose.yml", start_line=1, end_line=20)'],
        )

    async def execute(self, path: str, start_line: int = None, end_line: int = None, **kwargs) -> ToolResult:
        try:
            p = Path(path).expanduser()
            if not p.exists():
                return ToolResult(success=False, error=f"Arquivo nao encontrado: {path}")
            if not p.is_file():
                return ToolResult(success=False, error=f"Nao e um arquivo: {path}")

            content = p.read_text(encoding="utf-8", errors="replace")
            lines = content.split("\n")

            if start_line or end_line:
                s = (start_line or 1) - 1
                e = end_line or len(lines)
                selected = lines[s:e]
                output = "\n".join(f"{s+i+1}: {line}" for i, line in enumerate(selected))
            else:
                output = content

            return ToolResult(
                success=True,
                output=output,
                data={"path": str(p), "total_lines": len(lines), "size_bytes": p.stat().st_size},
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class FileWriteTool(BaseTool):
    """Escreve ou cria um arquivo."""

    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="file_write",
            description="Cria ou sobrescreve um arquivo com o conteúdo fornecido",
            risk=ToolRisk.NORMAL,
            parameters={
                "path": {"type": "string", "description": "Caminho do arquivo", "required": True},
                "content": {"type": "string", "description": "Conteúdo para escrever", "required": True},
                "append": {"type": "boolean", "description": "Se true, adiciona ao final", "required": False},
            },
            examples=['file_write(path="/tmp/test.txt", content="hello world")'],
        )

    async def execute(self, path: str, content: str, append: bool = False, **kwargs) -> ToolResult:
        try:
            p = Path(path).expanduser()
            p.parent.mkdir(parents=True, exist_ok=True)

            mode = "a" if append else "w"
            p.write_text(content, encoding="utf-8") if not append else open(p, "a", encoding="utf-8").write(content)

            return ToolResult(
                success=True,
                output=f"Arquivo {'atualizado' if append else 'criado'}: {p} ({len(content)} bytes)",
                data={"path": str(p), "bytes_written": len(content)},
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class FileSearchTool(BaseTool):
    """Busca padrões em arquivos (grep-like)."""

    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="file_search",
            description="Busca texto em arquivos de um diretório (equivalente a grep -rn)",
            risk=ToolRisk.SAFE_READ,
            parameters={
                "pattern": {"type": "string", "description": "Texto ou regex para buscar", "required": True},
                "path": {"type": "string", "description": "Diretório ou arquivo para buscar", "required": True},
                "include": {"type": "string", "description": "Filtro de extensão (ex: *.py)", "required": False},
            },
            examples=['file_search(pattern="ERROR", path="/var/log", include="*.log")'],
        )

    async def execute(self, pattern: str, path: str, include: str = None, **kwargs) -> ToolResult:
        import asyncio

        cmd = f'grep -rn --color=never "{pattern}" "{path}"'
        if include:
            cmd += f' --include="{include}"'
        cmd += " 2>/dev/null | head -50"

        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        output = stdout.decode("utf-8", errors="replace").strip()

        if not output:
            return ToolResult(success=True, output="Nenhum resultado encontrado.", data={"matches": 0})

        matches = len(output.split("\n"))
        return ToolResult(success=True, output=output, data={"matches": matches})


class ListDirTool(BaseTool):
    """Lista conteúdo de um diretório."""

    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="list_dir",
            description="Lista arquivos e diretórios em um caminho",
            risk=ToolRisk.SAFE_READ,
            parameters={
                "path": {"type": "string", "description": "Caminho do diretório", "required": True},
                "recursive": {"type": "boolean", "description": "Listar recursivamente", "required": False},
            },
            examples=['list_dir(path="/opt/app")', 'list_dir(path=".", recursive=true)'],
        )

    async def execute(self, path: str, recursive: bool = False, **kwargs) -> ToolResult:
        try:
            p = Path(path).expanduser()
            if not p.exists():
                return ToolResult(success=False, error=f"Diretório nao encontrado: {path}")

            entries = []
            if recursive:
                for item in sorted(p.rglob("*")):
                    rel = item.relative_to(p)
                    if item.is_dir():
                        entries.append(f"  {rel}/")
                    else:
                        size = item.stat().st_size
                        entries.append(f"  {rel} ({size} bytes)")
            else:
                for item in sorted(p.iterdir()):
                    if item.is_dir():
                        entries.append(f"  {item.name}/")
                    else:
                        size = item.stat().st_size
                        entries.append(f"  {item.name} ({size} bytes)")

            output = f"{p}/\n" + "\n".join(entries[:200])
            if len(entries) > 200:
                output += f"\n  ... e mais {len(entries) - 200} itens"

            return ToolResult(success=True, output=output, data={"total_entries": len(entries)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
