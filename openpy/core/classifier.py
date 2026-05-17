"""
OpenPy Classifier — Classificador determinístico de intenção.

Primeiro tenta keywords/aliases (sem LLM).
Só chama LLM se a confiança for baixa.
Alimentado pelo Learner: skills aprendidas viram keywords novas.
"""

import json
import re
from typing import Optional


# ============================================================================
# Mapa de keywords → categoria
# ============================================================================

KEYWORD_MAP: dict[str, list[str]] = {
    "sysadmin.firewall": [
        "porta", "portas", "firewall", "iptables", "ufw", "nftables",
        "abrir porta", "fechar porta", "liberar porta",
    ],
    "sysadmin.diagnostico": [
        "servidor", "diagnostico", "diagnóstico", "arruma", "consertar",
        "verificar servidor", "health check", "status do servidor",
        "tá tudo uma merda", "servidor caiu", "servidor lento",
    ],
    "sysadmin.packages": [
        "instalar", "instala", "apt install", "apt-get", "pacote",
        "atualizar pacotes", "update", "upgrade",
    ],
    "devops.docker": [
        "docker", "container", "compose", "dockerfile", "volume",
        "docker compose", "docker não sobe", "container não inicia",
    ],
    "devops.nginx": [
        "nginx", "proxy reverso", "reverse proxy", "ssl", "certificado",
        "https", "domínio", "virtual host",
    ],
    "webops.performance": [
        "site lento", "performance", "lento", "demora", "cache",
        "otimizar", "velocidade", "pagespeed", "lighthouse",
    ],
    "media.audio_transcription": [
        "transcrever", "transcreve", "áudio", "audio", "whisper",
        "speech to text", "legendar", "subtitle",
    ],
    "media.video_generation": [
        "gerar vídeo", "gera vídeo", "vídeo", "video", "renderizar",
        "animar", "animação",
    ],
    "media.image_editing": [
        "imagem", "foto", "redimensionar", "cortar", "resize",
        "converter imagem", "thumbnail",
    ],
    "marketing.creative_prompts": [
        "prompt", "campanha", "ads", "meta ads", "google ads",
        "criativo", "copy", "headline", "texto publicitário",
    ],
    "coding.python": [
        "python", "script", "pip", "virtualenv", "django", "flask",
    ],
    "coding.web": [
        "html", "css", "javascript", "react", "node", "frontend",
    ],
    "linux.filesystem": [
        "arquivo", "pasta", "diretório", "permissão", "chmod", "chown",
        "mover", "copiar", "deletar arquivo",
    ],
    "linux.network": [
        "rede", "ip", "dns", "ping", "traceroute", "ssh", "conexão",
    ],
    "general.conversation": [
        "olá", "oi", "bom dia", "boa tarde", "boa noite",
        "como vai", "obrigado", "valeu",
    ],
}


def _load_learned_keywords() -> dict[str, list[str]]:
    """Carrega keywords aprendidas de tarefas anteriores."""
    try:
        from openpy.utils.config import get_data_path
        keywords_file = get_data_path() / "learned_keywords.json"
        if keywords_file.exists():
            return json.loads(keywords_file.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _get_merged_keywords() -> dict[str, list[str]]:
    """Combina keywords builtin + aprendidas."""
    merged = {k: list(v) for k, v in KEYWORD_MAP.items()}

    learned = _load_learned_keywords()
    for category, keywords in learned.items():
        if category not in merged:
            merged[category] = []
        for kw in keywords:
            if kw not in merged[category]:
                merged[category].append(kw)

    return merged


def classify_intent(raw_input: str) -> dict:
    """
    Classifica a intenção do input do usuário.

    Primeiro tenta por keywords (determinístico).
    Inclui keywords aprendidas de tarefas anteriores.
    Retorna categoria, confiança e método usado.
    """
    text = raw_input.lower().strip()

    # Combinar keywords builtin + aprendidas
    all_keywords = _get_merged_keywords()

    # Tentar classificação por keywords
    best_match: Optional[str] = None
    best_score = 0

    for category, keywords in all_keywords.items():
        score = 0
        for keyword in keywords:
            if keyword in text:
                # Bonus para matches mais longos (mais específicos)
                score += len(keyword.split())

        if score > best_score:
            best_score = score
            best_match = category

    if best_match and best_score >= 1:
        confidence = min(1.0, best_score / 3)
        # Skills aprendidas recebem label adicional
        method = "keyword_match"
        if best_match not in KEYWORD_MAP:
            method = "learned_match"
        return {
            "category": best_match,
            "confidence": round(confidence, 2),
            "method": method,
            "keywords_matched": best_score,
        }

    # Fallback: categoria genérica (LLM decidirá)
    return {
        "category": "general.task",
        "confidence": 0.3,
        "method": "fallback",
        "keywords_matched": 0,
    }

