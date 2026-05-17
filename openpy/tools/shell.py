"""
OpenPy Shell Tool — Execução de comandos via /bin/bash.

Equivalente ao BashTool do Claude Code.
Target: Linux (VM/Docker). Sempre usa /bin/bash explicitamente.
Controle de timeout, captura de output, sandbox de segurança.
"""

import asyncio
import shutil
import sys
import time
from typing import Optional

from openpy.tools.base import BaseTool, ToolResult, ToolRisk, ToolSpec

# Shell explícito: bash no Linux (target), fallback para o que existir
BASH_PATH = shutil.which("bash") or shutil.which("sh") or ("/bin/bash" if sys.platform != "win32" else None)


class ShellTool(BaseTool):
    """Executa comandos via /bin/bash no sistema Linux."""

    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="bash",
            description="Executa um comando bash no sistema Linux (equivalente ao BashTool do Claude Code)",
            risk=ToolRisk.RISKY,
            parameters={
                "command": {
                    "type": "string",
                    "description": "Comando bash a executar",
                    "required": True,
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout em segundos (padrao: 120)",
                    "required": False,
                },
                "cwd": {
                    "type": "string",
                    "description": "Diretorio de trabalho",
                    "required": False,
                },
            },
            examples=[
                'bash(command="ls -la /var/log")',
                'bash(command="docker compose ps", cwd="/opt/app")',
                'bash(command="systemctl status nginx")',
                'bash(command="ufw status verbose")',
                'bash(command="cat /etc/os-release")',
            ],
        )

    async def execute(
        self,
        command: str,
        timeout: int = 120,
        cwd: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        """Executa comando via bash com timeout e captura de output."""
        start = time.monotonic()

        try:
            # Forçar uso de bash explicitamente (nunca cmd.exe)
            if BASH_PATH:
                proc = await asyncio.create_subprocess_exec(
                    BASH_PATH, "-c", command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                )
            else:
                # Fallback: subprocess_shell (só em ambiente sem bash)
                proc = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                elapsed = int((time.monotonic() - start) * 1000)
                return ToolResult(
                    success=False,
                    error=f"Timeout apos {timeout}s",
                    duration_ms=elapsed,
                )

            elapsed = int((time.monotonic() - start) * 1000)
            stdout_str = stdout.decode("utf-8", errors="replace").strip()
            stderr_str = stderr.decode("utf-8", errors="replace").strip()

            if proc.returncode == 0:
                return ToolResult(
                    success=True,
                    output=stdout_str,
                    error=stderr_str if stderr_str else "",
                    data={"returncode": 0, "command": command},
                    duration_ms=elapsed,
                )
            else:
                return ToolResult(
                    success=False,
                    output=stdout_str,
                    error=stderr_str or f"Exit code: {proc.returncode}",
                    data={"returncode": proc.returncode, "command": command},
                    duration_ms=elapsed,
                )

        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            return ToolResult(
                success=False,
                error=str(e),
                duration_ms=elapsed,
            )
