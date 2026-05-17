"""
OpenPy LLM Engine — Cliente multi-provider via litellm.
"""

import json
from typing import Optional

from openpy.utils.config import load_config


# Mapeamento de tipo de provider → prefixo litellm
PROVIDER_PREFIX_MAP = {
    "openai-compatible": "openai",
    "openai": "openai",
    "anthropic": "anthropic",
    "google": "gemini",
    "ollama": "ollama",
    "groq": "groq",
    "together": "together_ai",
    "deepseek": "deepseek",
    "mistral": "mistral",
    "nvidia-nim": "nvidia_nim",
    "openrouter": "openrouter",
}


def _resolve_model_name(model: str, provider_type: str, base_url: str) -> str:
    """
    Resolve o nome do modelo para o formato que litellm espera.

    litellm precisa de prefixo: 'openai/modelo', 'anthropic/modelo', etc.
    Se o modelo já tem prefixo (contém '/'), usa como está.
    """
    # Se já tem prefixo (ex: 'openai/gpt-4o'), usa direto
    if "/" in model:
        return model

    # Para providers com base_url customizada, usar prefixo 'openai'
    # pois litellm trata qualquer API OpenAI-compatible com esse prefixo
    if base_url and provider_type == "openai-compatible":
        return f"openai/{model}"

    # Mapear pelo tipo do provider
    prefix = PROVIDER_PREFIX_MAP.get(provider_type, "openai")
    return f"{prefix}/{model}"


def call_llm(prompt: str, model_override: Optional[str] = None) -> dict | str:
    """
    Chama o LLM configurado e retorna a resposta.

    Tenta parsear como JSON. Se não for JSON, retorna texto.
    """
    config = load_config()
    provider = config.providers.default

    raw_model = model_override or provider.model
    if not raw_model:
        return {"error": "Nenhum modelo configurado. Execute: openpy onboard"}

    try:
        import litellm
        litellm.suppress_debug_info = True

        # Resolver nome do modelo com prefixo correto
        model = _resolve_model_name(raw_model, provider.type, provider.base_url)

        # Configurar chamada
        kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": provider.temperature,
            "max_tokens": provider.max_tokens,
        }

        if provider.base_url:
            kwargs["api_base"] = provider.base_url

        if provider.api_key:
            kwargs["api_key"] = provider.api_key

        response = litellm.completion(**kwargs)
        content = response.choices[0].message.content

        # Tentar parsear como JSON
        try:
            # Extrair JSON de dentro de markdown code blocks se necessário
            cleaned = content.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            return content

    except ImportError:
        return {"error": "litellm não instalado. Execute: pip install litellm"}
    except Exception as e:
        error_msg = str(e)
        # Mensagens mais amigáveis para erros comuns
        if "Connection refused" in error_msg or "ConnectError" in error_msg:
            return {"error": f"Nao foi possivel conectar ao provider em {provider.base_url}. Verifique se o servico esta rodando."}
        return {"error": f"Erro na chamada LLM: {error_msg}"}
