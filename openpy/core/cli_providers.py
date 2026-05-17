"""
OpenPy CLI Providers — Adapters para ferramentas CLI gratuitas.

Suporta chamar modelos via CLI externas como:
- OpenCode (Big Pickle e outros modelos gratuitos)
- Codex CLI (OpenAI Codex)
- Gemini CLI (Google Gemini)
- Qwen CLI (Alibaba Qwen)
- Kimi CLI (Moonshot Kimi)
- Ollama (local)

Cada adapter converte a chamada para o formato da CLI e parseia a resposta.
"""

import asyncio
import json
import shutil
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class CLIProviderResult:
    """Resultado de uma chamada via CLI provider."""
    success: bool
    content: str = ""
    error: str = ""
    model: str = ""
    duration_ms: int = 0
    raw_output: str = ""


class BaseCLIProvider(ABC):
    """Interface base para providers via CLI."""

    @abstractmethod
    def name(self) -> str:
        """Nome do provider."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se a CLI está instalada."""
        ...

    @abstractmethod
    async def call(self, prompt: str, model: Optional[str] = None) -> CLIProviderResult:
        """Executa chamada ao modelo via CLI."""
        ...


class OllamaProvider(BaseCLIProvider):
    """Provider para Ollama (modelos locais)."""

    def name(self) -> str:
        return "ollama"

    def is_available(self) -> bool:
        return shutil.which("ollama") is not None

    async def call(self, prompt: str, model: Optional[str] = None) -> CLIProviderResult:
        model = model or "llama3.2"
        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                "ollama", "run", model,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=prompt.encode("utf-8")),
                timeout=300,
            )
            elapsed = int((time.monotonic() - start) * 1000)
            output = stdout.decode("utf-8", errors="replace").strip()

            return CLIProviderResult(
                success=proc.returncode == 0,
                content=output,
                error=stderr.decode("utf-8", errors="replace") if proc.returncode != 0 else "",
                model=model,
                duration_ms=elapsed,
                raw_output=output,
            )
        except asyncio.TimeoutError:
            return CLIProviderResult(success=False, error="Timeout (300s)", model=model)
        except Exception as e:
            return CLIProviderResult(success=False, error=str(e), model=model)


class OpenCodeProvider(BaseCLIProvider):
    """
    Provider para OpenCode CLI.

    OpenCode suporta modelos gratuitos como Big Pickle.
    Usa: opencode ask "prompt"
    """

    def name(self) -> str:
        return "opencode"

    def is_available(self) -> bool:
        return shutil.which("opencode") is not None

    async def call(self, prompt: str, model: Optional[str] = None) -> CLIProviderResult:
        start = time.monotonic()
        cmd = ["opencode", "ask"]
        if model:
            cmd.extend(["--model", model])
        cmd.append(prompt)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=300,
            )
            elapsed = int((time.monotonic() - start) * 1000)
            output = stdout.decode("utf-8", errors="replace").strip()

            return CLIProviderResult(
                success=proc.returncode == 0,
                content=output,
                model=model or "default",
                duration_ms=elapsed,
                raw_output=output,
            )
        except Exception as e:
            return CLIProviderResult(success=False, error=str(e), model=model or "default")


class GeminiCLIProvider(BaseCLIProvider):
    """
    Provider para Gemini CLI (Google).

    Usa: gemini "prompt"
    """

    def name(self) -> str:
        return "gemini-cli"

    def is_available(self) -> bool:
        return shutil.which("gemini") is not None

    async def call(self, prompt: str, model: Optional[str] = None) -> CLIProviderResult:
        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                "gemini", "-p", prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=300,
            )
            elapsed = int((time.monotonic() - start) * 1000)
            output = stdout.decode("utf-8", errors="replace").strip()

            return CLIProviderResult(
                success=proc.returncode == 0,
                content=output,
                model=model or "gemini",
                duration_ms=elapsed,
                raw_output=output,
            )
        except Exception as e:
            return CLIProviderResult(success=False, error=str(e), model="gemini")


class CodexCLIProvider(BaseCLIProvider):
    """
    Provider para Codex CLI (OpenAI).

    Usa: codex "prompt"
    """

    def name(self) -> str:
        return "codex-cli"

    def is_available(self) -> bool:
        return shutil.which("codex") is not None

    async def call(self, prompt: str, model: Optional[str] = None) -> CLIProviderResult:
        start = time.monotonic()
        cmd = ["codex", "-q", prompt]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=300,
            )
            elapsed = int((time.monotonic() - start) * 1000)
            output = stdout.decode("utf-8", errors="replace").strip()

            return CLIProviderResult(
                success=proc.returncode == 0,
                content=output,
                model=model or "codex",
                duration_ms=elapsed,
                raw_output=output,
            )
        except Exception as e:
            return CLIProviderResult(success=False, error=str(e), model="codex")


class KimiCLIProvider(BaseCLIProvider):
    """
    Provider para Kimi CLI (Moonshot).

    Usa: kimi chat "prompt"
    """

    def name(self) -> str:
        return "kimi-cli"

    def is_available(self) -> bool:
        return shutil.which("kimi") is not None

    async def call(self, prompt: str, model: Optional[str] = None) -> CLIProviderResult:
        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                "kimi", "chat", prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=300,
            )
            elapsed = int((time.monotonic() - start) * 1000)
            output = stdout.decode("utf-8", errors="replace").strip()

            return CLIProviderResult(
                success=proc.returncode == 0,
                content=output,
                model=model or "kimi",
                duration_ms=elapsed,
                raw_output=output,
            )
        except Exception as e:
            return CLIProviderResult(success=False, error=str(e), model="kimi")


class QwenCLIProvider(BaseCLIProvider):
    """
    Provider para Qwen CLI (Alibaba).

    Usa: qwen-cli "prompt"
    """

    def name(self) -> str:
        return "qwen-cli"

    def is_available(self) -> bool:
        return shutil.which("qwen") is not None or shutil.which("qwen-cli") is not None

    async def call(self, prompt: str, model: Optional[str] = None) -> CLIProviderResult:
        start = time.monotonic()
        binary = shutil.which("qwen") or shutil.which("qwen-cli") or "qwen"
        try:
            proc = await asyncio.create_subprocess_exec(
                binary, prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=300,
            )
            elapsed = int((time.monotonic() - start) * 1000)
            output = stdout.decode("utf-8", errors="replace").strip()

            return CLIProviderResult(
                success=proc.returncode == 0,
                content=output,
                model=model or "qwen",
                duration_ms=elapsed,
                raw_output=output,
            )
        except Exception as e:
            return CLIProviderResult(success=False, error=str(e), model="qwen")


# ============================================================================
# Registry de CLI Providers
# ============================================================================

ALL_CLI_PROVIDERS = [
    OllamaProvider(),
    OpenCodeProvider(),
    GeminiCLIProvider(),
    CodexCLIProvider(),
    KimiCLIProvider(),
    QwenCLIProvider(),
]


def detect_available_providers() -> list[BaseCLIProvider]:
    """Detecta quais CLI providers estão instalados no sistema."""
    return [p for p in ALL_CLI_PROVIDERS if p.is_available()]


def get_provider_by_name(name: str) -> Optional[BaseCLIProvider]:
    """Busca provider pelo nome."""
    for p in ALL_CLI_PROVIDERS:
        if p.name() == name:
            return p
    return None
