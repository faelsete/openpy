"""
OpenPy Telegram Bot — Channel de comunicacao remota.

Permite interagir com o agente via Telegram.
Suporta comandos inline e tarefas em linguagem natural.
"""

import asyncio
import logging
from typing import Optional

from openpy.utils.config import load_config

logger = logging.getLogger("openpy.telegram")


class TelegramBot:
    """Bot Telegram para o OpenPy."""

    def __init__(self):
        self.config = load_config()
        self.telegram_cfg = self.config.channels.telegram
        self.token = self.telegram_cfg.token
        self.allowed_users = self.telegram_cfg.allowed_users
        self._offset = 0

    def is_configured(self) -> bool:
        return bool(self.token) and self.telegram_cfg.enabled

    def _is_allowed(self, user_id: int) -> bool:
        if not self.allowed_users:
            return True  # Se nao tem restricao, permite todos
        return user_id in self.allowed_users

    async def _api_call(self, method: str, **params) -> dict:
        """Chama a API do Telegram."""
        import httpx
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=params)
            return r.json()

    async def send_message(self, chat_id: int, text: str, parse_mode: str = "Markdown") -> dict:
        """Envia mensagem."""
        # Telegram limita a 4096 chars
        if len(text) > 4000:
            text = text[:4000] + "\n\n... (truncado)"
        try:
            return await self._api_call("sendMessage", chat_id=chat_id, text=text, parse_mode=parse_mode)
        except Exception:
            # Fallback sem parse_mode se markdown falhar
            return await self._api_call("sendMessage", chat_id=chat_id, text=text)

    async def get_updates(self) -> list:
        """Busca novas mensagens."""
        result = await self._api_call("getUpdates", offset=self._offset, timeout=30)
        updates = result.get("result", [])
        if updates:
            self._offset = updates[-1]["update_id"] + 1
        return updates

    async def handle_message(self, message: dict) -> str:
        """Processa uma mensagem e retorna a resposta."""
        text = message.get("text", "").strip()
        user_id = message.get("from", {}).get("id", 0)
        chat_id = message.get("chat", {}).get("id", 0)
        username = message.get("from", {}).get("first_name", "usuario")

        if not self._is_allowed(user_id):
            return "Acesso negado."

        # Comandos do bot
        if text == "/start":
            return (
                f"Ola {username}! Sou o OpenPy Agent.\n\n"
                "Envie qualquer tarefa em linguagem natural.\n\n"
                "Comandos:\n"
                "/status - Status do sistema\n"
                "/doctor - Diagnostico\n"
                "/skills - Skills disponiveis\n"
                "/history - Historico de tarefas\n"
                "/help - Ajuda"
            )

        if text == "/help":
            return (
                "Envie qualquer texto para executar como tarefa.\n\n"
                "Comandos:\n"
                "/status - CPU, RAM, disco\n"
                "/doctor - Diagnostico completo\n"
                "/skills - Listar skills\n"
                "/history - Ultimas tarefas\n"
                "/providers - Providers disponiveis"
            )

        if text == "/status":
            return self._get_status()

        if text == "/doctor":
            return self._run_doctor()

        if text == "/skills":
            return self._list_skills()

        if text == "/history":
            return self._get_history()

        if text == "/providers":
            return self._list_providers()

        # Tarefa em linguagem natural
        return self._run_task(text)

    def _get_status(self) -> str:
        """Status do sistema."""
        import shutil
        import psutil
        from pathlib import Path

        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = shutil.disk_usage("/")

        return (
            f"*Status do Sistema*\n\n"
            f"CPU: {cpu}%\n"
            f"RAM: {mem.percent}% ({mem.used // (1024**3)}/{mem.total // (1024**3)} GB)\n"
            f"Disco: {round(disk.used / disk.total * 100, 1)}%"
        )

    def _run_doctor(self) -> str:
        """Roda diagnostico."""
        try:
            from openpy.cli.doctor_cmd import (
                check_directories, check_config, check_python_deps,
                check_provider, check_cli_providers, check_tools,
                check_gateway, check_skills, check_memory,
            )
            checks = [
                check_directories(), check_config(), check_python_deps(),
                check_provider(), check_cli_providers(), check_tools(),
                check_gateway(), check_skills(), check_memory(),
            ]
            lines = ["*Diagnostico OpenPy*\n"]
            errors = 0
            for c in checks:
                status = c.get("status", "")
                icon = {"ok": "✅", "warn": "⚠️", "error": "❌", "info": "ℹ️"}.get(status, "❓")
                lines.append(f"{icon} {c['name']}: {c.get('msg', '')}")
                if status == "error":
                    errors += 1
            lines.append(f"\n{'❌' if errors else '✅'} {errors} erro(s)")
            return "\n".join(lines)
        except Exception as e:
            return f"Erro no doctor: {e}"

    def _list_skills(self) -> str:
        """Lista skills."""
        try:
            from openpy.utils.config import get_skills_path
            from pathlib import Path

            skills_dir = get_skills_path()
            bundled = Path(__file__).parent.parent / "skills"

            skills = []
            for d in [bundled, skills_dir]:
                if d.exists():
                    for f in d.rglob("*.md"):
                        name = str(f.relative_to(d))
                        if name not in [s[0] for s in skills]:
                            skills.append((name, "bundled" if d == bundled else "learned"))

            lines = ["*Skills Disponiveis*\n"]
            for name, source in skills:
                icon = "📦" if source == "bundled" else "🧠"
                lines.append(f"{icon} {name}")
            return "\n".join(lines)
        except Exception as e:
            return f"Erro: {e}"

    def _get_history(self) -> str:
        """Historico de tarefas."""
        try:
            from openpy.core.memory import get_recent_tasks
            tasks = get_recent_tasks(limit=5)
            if not tasks:
                return "Nenhuma tarefa no historico."
            lines = ["*Ultimas Tarefas*\n"]
            for t in tasks:
                status = "✅" if t.get("execution_success") == 1 else "❌" if t.get("execution_success") == 0 else "—"
                raw = t.get("raw_input", "")[:50]
                lines.append(f"{status} {raw}")
            return "\n".join(lines)
        except Exception as e:
            return f"Erro: {e}"

    def _list_providers(self) -> str:
        """Lista providers."""
        try:
            from openpy.core.cli_providers import ALL_CLI_PROVIDERS
            lines = ["*Providers CLI*\n"]
            for p in ALL_CLI_PROVIDERS:
                icon = "✅" if p.is_available() else "—"
                lines.append(f"{icon} {p.name()}")
            return "\n".join(lines)
        except Exception as e:
            return f"Erro: {e}"

    def _run_task(self, text: str) -> str:
        """Executa tarefa via pipeline."""
        try:
            from openpy.core.pipeline import run_task
            import io
            from contextlib import redirect_stdout

            # Capturar output do Rich
            result = run_task(text)

            # Montar resposta
            lines = []
            resp = result.llm_response

            if isinstance(resp, dict) and "error" not in resp:
                diag = resp.get("diagnostic", "")
                if diag:
                    lines.append(f"*Diagnostico:* {diag}")

                risk = resp.get("risk", "")
                if risk:
                    lines.append(f"*Risco:* {risk}")

                steps = resp.get("steps", [])
                if steps:
                    lines.append(f"\n*Plano ({len(steps)} passos):*")
                    for i, s in enumerate(steps, 1):
                        lines.append(f"{i}. {s.get('description', '')}")
                        for cmd in s.get("commands", []):
                            lines.append(f"   `{cmd}`")

                expected = resp.get("expected_success", "")
                if expected:
                    lines.append(f"\n*Esperado:* {expected}")

            elif isinstance(resp, dict) and "error" in resp:
                lines.append(f"❌ {resp['error']}")
            elif isinstance(resp, str):
                lines.append(resp)
            else:
                lines.append(str(resp))

            return "\n".join(lines) or "Tarefa processada."

        except Exception as e:
            return f"Erro ao executar: {e}"


async def run_telegram_polling():
    """Loop principal de polling do Telegram."""
    bot = TelegramBot()

    if not bot.is_configured():
        logger.error("Telegram nao configurado. Execute: openpy onboard")
        return

    logger.info("Telegram bot iniciado (polling)")

    while True:
        try:
            updates = await bot.get_updates()
            for update in updates:
                message = update.get("message", {})
                if not message or "text" not in message:
                    continue

                chat_id = message["chat"]["id"]
                logger.info(f"Mensagem de {chat_id}: {message['text'][:50]}")

                response = await bot.handle_message(message)
                await bot.send_message(chat_id, response)

        except Exception as e:
            logger.error(f"Erro no polling: {e}")
            await asyncio.sleep(5)

        await asyncio.sleep(1)


def start_telegram_bot():
    """Inicia o bot Telegram (blocking)."""
    asyncio.run(run_telegram_polling())
