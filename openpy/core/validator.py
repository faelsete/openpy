"""
OpenPy Validator — Analisa risco e decide se precisa confirmação.
"""

import re

# Padrões perigosos
DESTRUCTIVE_PATTERNS = [
    r"rm\s+-rf", r"rm\s+-r\s+/", r"mkfs\.", r"dd\s+if=",
    r"format\s+", r"fdisk", r"wipefs",
    r"DROP\s+TABLE", r"DROP\s+DATABASE", r"TRUNCATE",
    r"docker\s+system\s+prune\s+-a",
]

RISKY_PATTERNS = [
    r"sudo\s+", r"su\s+-", r"chmod\s+777",
    r"iptables", r"ufw\s+(allow|deny|delete)", r"nft\s+",
    r"systemctl\s+(stop|restart|disable|mask)",
    r"apt\s+(install|remove|purge|autoremove)",
    r"pip\s+install", r"npm\s+install\s+-g",
    r"curl\s+.*\|\s*(bash|sh)", r"wget\s+.*\|\s*(bash|sh)",
    r"passwd\s+", r"usermod\s+", r"useradd\s+", r"userdel\s+",
    r"docker\s+rm\s+", r"docker\s+rmi\s+",
    r"nginx\s+-s\s+stop",
    r"\.env", r"ssh-keygen", r"authorized_keys",
]

SAFE_READ_COMMANDS = {
    "ls", "cat", "head", "tail", "grep", "find", "wc",
    "df", "free", "uptime", "whoami", "hostname", "uname",
    "docker ps", "docker images", "docker compose ps",
    "systemctl status", "systemctl list-units",
    "journalctl", "dmesg", "top", "htop", "ps",
    "pwd", "which", "type", "file", "stat",
    "ip addr", "ip route", "ss", "netstat",
    "curl -I", "ping -c",
}


def classify_risk(commands: list[str]) -> str:
    """Classifica risco de uma lista de comandos."""
    all_text = " ".join(commands).lower()

    for pattern in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, all_text, re.IGNORECASE):
            return "destructive"

    for pattern in RISKY_PATTERNS:
        if re.search(pattern, all_text, re.IGNORECASE):
            return "risky"

    # Verificar se é safe read
    for cmd in commands:
        base = cmd.strip().split()[0] if cmd.strip() else ""
        is_safe = any(cmd.strip().startswith(safe) for safe in SAFE_READ_COMMANDS)
        if not is_safe:
            return "normal"

    return "safe_read"


def validate_response(llm_response: dict | str, autonomy_level: str) -> dict:
    """
    Valida a resposta do LLM e decide se precisa confirmação.

    Retorna dict com risk, approved, reason.
    """
    # Extrair comandos da resposta
    commands = []
    if isinstance(llm_response, dict):
        # Buscar comandos em vários formatos possíveis
        for key in ["commands", "execution_commands", "diagnostic_commands", "verification_commands"]:
            if key in llm_response and isinstance(llm_response[key], list):
                commands.extend(llm_response[key])

        # Buscar em steps
        if "steps" in llm_response and isinstance(llm_response["steps"], list):
            for step in llm_response["steps"]:
                if isinstance(step, dict) and "commands" in step:
                    commands.extend(step["commands"])

        risk_declared = llm_response.get("risk", "unknown")
    else:
        risk_declared = "unknown"

    # Classificar risco real dos comandos
    if commands:
        risk_actual = classify_risk(commands)
    else:
        risk_actual = "safe_read"

    # Usar o risco mais alto entre declarado e detectado
    risk_order = ["safe_read", "normal", "risky", "destructive"]
    risk_declared_idx = risk_order.index(risk_declared) if risk_declared in risk_order else 0
    risk_actual_idx = risk_order.index(risk_actual)
    final_risk = risk_order[max(risk_declared_idx, risk_actual_idx)]

    # Decidir se precisa confirmação baseado no nível de autonomia
    autonomy_order = {"safe_read": 0, "normal": 1, "risky": 2, "full": 3}
    risk_threshold = {"safe_read": 0, "normal": 1, "risky": 2, "destructive": 3}

    auto_level = autonomy_order.get(autonomy_level, 1)
    risk_level = risk_threshold.get(final_risk, 1)

    approved = risk_level <= auto_level

    return {
        "risk": final_risk,
        "approved": approved,
        "needs_confirmation": not approved,
        "commands_found": len(commands),
        "risk_declared": risk_declared,
        "risk_detected": risk_actual,
        "reason": f"Risco {final_risk}, autonomia {autonomy_level}" + (" → requer confirmação" if not approved else " → aprovado"),
    }
