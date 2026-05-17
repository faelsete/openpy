"""
OpenPy Skill Loader — Carrega CORE_ALWAYS.md + skill específica.
"""

from pathlib import Path
from typing import Optional

from openpy.utils.config import get_skills_path


def _find_skill_file(category: str) -> Optional[Path]:
    """Encontra arquivo de skill pela categoria."""
    # Tentar nos bundled primeiro
    bundled_dir = Path(__file__).parent.parent / "skills"
    user_dir = get_skills_path()

    # Converter "sysadmin.firewall" → "sysadmin/firewall.md"
    parts = category.split(".")
    if len(parts) >= 2:
        relative = f"{parts[0]}/{parts[1]}.md"
    else:
        relative = f"{parts[0]}.md"

    # Procurar em ambos diretórios
    for base in [user_dir, bundled_dir]:
        candidate = base / relative
        if candidate.exists():
            return candidate

    # Tentar com underscore: "sysadmin_firewall.md"
    flat_name = category.replace(".", "_") + ".md"
    for base in [user_dir, bundled_dir]:
        candidate = base / flat_name
        if candidate.exists():
            return candidate

    return None


def load_skill(category: str) -> tuple[str, str]:
    """
    Carrega CORE_ALWAYS.md + skill da categoria.

    Retorna (core_content, skill_content).
    """
    bundled_dir = Path(__file__).parent.parent / "skills"
    user_dir = get_skills_path()

    # Carregar CORE_ALWAYS.md
    core_content = ""
    for base in [user_dir, bundled_dir]:
        core_path = base / "core" / "CORE_ALWAYS.md"
        if core_path.exists():
            core_content = core_path.read_text(encoding="utf-8")
            break

    if not core_content:
        core_content = _default_core()

    # Carregar skill específica
    skill_content = ""
    skill_file = _find_skill_file(category)
    if skill_file:
        skill_content = skill_file.read_text(encoding="utf-8")

    return core_content, skill_content


def _default_core() -> str:
    """Core padrão caso não haja arquivo."""
    return """# CORE — Regras obrigatórias

Você é um operador técnico. Siga estas regras SEMPRE:

1. Identifique a FINALIDADE REAL do pedido
2. Identifique o OBJETO CENTRAL
3. Verifique se há PEGADINHA LITERAL
4. Analise as CAMADAS do problema
5. Defina a AÇÃO MÍNIMA CORRETA
6. Planeje a VERIFICAÇÃO
7. Antecipe o PRÓXIMO BLOQUEIO PROVÁVEL

NUNCA responda com texto genérico.
NUNCA execute sem planejar.
SEMPRE responda em formato estruturado.
"""
