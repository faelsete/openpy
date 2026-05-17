"""
OpenPy Config — Sistema de configuração centralizado.

Usa JSON puro + Pydantic para validação de schema.
Arquivo: ~/.openpy/openpy.json
"""

import json
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================================
# Paths
# ============================================================================

def get_openpy_home() -> Path:
    """Retorna o diretório base do OpenPy (~/.openpy)."""
    return Path(os.environ.get("OPENPY_HOME", Path.home() / ".openpy"))


def get_config_path() -> Path:
    """Retorna o caminho do arquivo de configuração."""
    return get_openpy_home() / "openpy.json"


def get_workspace_path() -> Path:
    """Retorna o diretório de workspace."""
    return get_openpy_home() / "workspace"


def get_data_path() -> Path:
    """Retorna o diretório de dados persistentes."""
    return get_openpy_home() / "data"


def get_logs_path() -> Path:
    """Retorna o diretório de logs."""
    return get_openpy_home() / "logs"


def get_skills_path() -> Path:
    """Retorna o diretório de skills customizadas."""
    return get_openpy_home() / "skills"


# ============================================================================
# Config Models (Pydantic)
# ============================================================================

class GatewayTunnelConfig(BaseModel):
    provider: str = Field(default="ngrok", description="Provedor de tunnel (ngrok, cloudflared)")
    token: str = Field(default="", description="Token do provedor")
    enabled: bool = Field(default=False)


class GatewayConfig(BaseModel):
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=18790)
    auth_token: str = Field(default="", description="Token para autenticação da API")
    tunnel: GatewayTunnelConfig = Field(default_factory=GatewayTunnelConfig)


class TelegramChannelConfig(BaseModel):
    token: str = Field(default="", description="Bot token do @BotFather")
    allowed_users: list[int] = Field(default_factory=list, description="IDs permitidos")
    shortcuts: bool = Field(default=True, description="Habilitar atalhos (/status, /exec, etc)")
    enabled: bool = Field(default=False)


class DiscordChannelConfig(BaseModel):
    token: str = Field(default="")
    dm_policy: str = Field(default="pairing")
    enabled: bool = Field(default=False)


class ChannelsConfig(BaseModel):
    telegram: TelegramChannelConfig = Field(default_factory=TelegramChannelConfig)
    discord: DiscordChannelConfig = Field(default_factory=DiscordChannelConfig)


class ProviderConfig(BaseModel):
    type: str = Field(default="openai-compatible", description="openai-compatible, anthropic, openai")
    base_url: str = Field(default="", description="URL base da API")
    api_key: str = Field(default="", description="Chave da API")
    model: str = Field(default="", description="Nome do modelo")
    temperature: float = Field(default=0.3)
    max_tokens: int = Field(default=4096)


class ProvidersConfig(BaseModel):
    default: ProviderConfig = Field(default_factory=ProviderConfig)
    fallback: Optional[ProviderConfig] = Field(default=None)


class AgentConfig(BaseModel):
    harness_mode: str = Field(default="strong", description="plain|strong|xhigh|brutal")
    autonomy_level: str = Field(default="normal", description="safe_read|normal|risky|full")
    max_retries: int = Field(default=3)
    execution_timeout: int = Field(default=120, description="Timeout em segundos")
    workspace: str = Field(default="")
    language: str = Field(default="pt-BR", description="Idioma principal")


class MemorySemanticConfig(BaseModel):
    provider: str = Field(default="chromadb")
    consolidation_interval_minutes: int = Field(default=15)
    full_index_interval_hours: int = Field(default=1)


class MemoryConfig(BaseModel):
    semantic: MemorySemanticConfig = Field(default_factory=MemorySemanticConfig)


class SessionConfig(BaseModel):
    max_context_tokens: int = Field(default=32000)
    auto_compact: bool = Field(default=True)
    memory_extraction_interval: int = Field(default=5, description="A cada N turnos")


class OpenPyConfig(BaseModel):
    """Schema principal de configuração do OpenPy."""
    version: str = Field(default="1")
    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    channels: ChannelsConfig = Field(default_factory=ChannelsConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    session: SessionConfig = Field(default_factory=SessionConfig)


# ============================================================================
# Load / Save
# ============================================================================

_cached_config: Optional[OpenPyConfig] = None


def load_config(force_reload: bool = False) -> OpenPyConfig:
    """Carrega configuração do disco. Usa cache em memória."""
    global _cached_config
    if _cached_config is not None and not force_reload:
        return _cached_config

    config_path = get_config_path()
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            _cached_config = OpenPyConfig(**data)
        except (json.JSONDecodeError, Exception) as e:
            from rich.console import Console
            Console(stderr=True).print(f"[red]⚠ Erro ao carregar config: {e}[/red]")
            _cached_config = OpenPyConfig()
    else:
        _cached_config = OpenPyConfig()

    # Preenche workspace se vazio
    if not _cached_config.agent.workspace:
        _cached_config.agent.workspace = str(get_workspace_path())

    return _cached_config


def save_config(config: OpenPyConfig) -> None:
    """Salva configuração no disco."""
    global _cached_config
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(config.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    _cached_config = config


def ensure_directories() -> None:
    """Cria todos os diretórios necessários."""
    for path_fn in [get_openpy_home, get_workspace_path, get_data_path, get_logs_path, get_skills_path]:
        path_fn().mkdir(parents=True, exist_ok=True)
