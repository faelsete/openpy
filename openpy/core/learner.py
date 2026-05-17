"""
OpenPy Learner — Auto-geração de skills a partir de tarefas bem-sucedidas.

Inspirado no extractMemories do Claude Code.
Após uma tarefa ser executada com sucesso e verificada:
1. Extrai o padrão (intenção, comandos, verificação)
2. Gera um arquivo .md de skill
3. Atualiza o classificador com novas keywords
4. Indexa para busca semântica futura

O agente NUNCA esquece. Toda tarefa bem-sucedida vira aprendizado.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from openpy.core.contracts import TaskResult
from openpy.core.executor import ExecutionResult
from openpy.utils.config import get_skills_path, load_config


def learn_from_success(
    task_result: TaskResult,
    execution_result: ExecutionResult,
) -> Optional[str]:
    """
    Extrai aprendizado de uma tarefa bem-sucedida.

    Gera um arquivo .md de skill automaticamente.
    Retorna o caminho da skill criada, ou None.
    """
    if not execution_result.overall_success:
        return None

    if not isinstance(task_result.llm_response, dict):
        return None

    category = task_result.classification.get("category", "learned.general")
    raw_input = task_result.raw_input
    llm_response = task_result.llm_response
    steps = llm_response.get("steps", [])

    if not steps:
        return None

    # Gerar conteúdo da skill
    skill_content = _generate_skill_md(
        category=category,
        raw_input=raw_input,
        steps=steps,
        llm_response=llm_response,
        execution_result=execution_result,
    )

    # Salvar skill
    skill_path = _save_learned_skill(category, raw_input, skill_content)

    # Atualizar keywords do classificador
    _update_classifier_keywords(category, raw_input)

    return str(skill_path)


def _generate_skill_md(
    category: str,
    raw_input: str,
    steps: list[dict],
    llm_response: dict,
    execution_result: ExecutionResult,
) -> str:
    """Gera o conteúdo Markdown da skill aprendida."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Extrair comandos bem-sucedidos
    successful_commands = []
    verification_commands = []
    for step_result in execution_result.steps_results:
        if step_result.success:
            for cmd_info in step_result.commands_executed:
                if cmd_info["success"]:
                    successful_commands.append(cmd_info["command"])

    for step in steps:
        verification_commands.extend(step.get("verification", []))

    # Montar Markdown
    lines = [
        f"# Skill Aprendida: {category}",
        f"",
        f"> Gerada automaticamente em {timestamp}",
        f"> Input original: \"{raw_input}\"",
        f"",
        f"## Contexto",
        f"",
        f"{llm_response.get('diagnostic', 'Tarefa executada com sucesso.')}",
        f"",
    ]

    # Comandos que funcionaram
    if successful_commands:
        lines.append("## Comandos Validados")
        lines.append("")
        lines.append("```bash")
        for cmd in successful_commands:
            lines.append(f"{cmd}")
        lines.append("```")
        lines.append("")

    # Verificação
    if verification_commands:
        lines.append("## Verificação")
        lines.append("")
        lines.append("```bash")
        for cmd in verification_commands:
            lines.append(f"{cmd}")
        lines.append("```")
        lines.append("")

    # Steps detalhados
    if steps:
        lines.append("## Passos")
        lines.append("")
        for i, step in enumerate(steps):
            desc = step.get("description", f"Passo {i+1}")
            lines.append(f"{i+1}. {desc}")
            for cmd in step.get("commands", []):
                lines.append(f"   - `{cmd}`")
        lines.append("")

    # Riscos
    risk = llm_response.get("risk", "unknown")
    if risk in ("high", "critical"):
        lines.append("## Riscos")
        lines.append("")
        lines.append(f"- Nível de risco: **{risk}**")
        rollbacks = [s.get("rollback", "") for s in steps if s.get("rollback")]
        if rollbacks:
            lines.append("- Rollback:")
            for rb in rollbacks:
                lines.append(f"  - {rb}")
        lines.append("")

    # Metadados
    lines.append("## Metadados")
    lines.append("")
    lines.append(f"- Categoria: `{category}`")
    lines.append(f"- Modelo usado: `{getattr(execution_result, 'model_used', 'unknown')}`")
    lines.append(f"- Tempo de execução: {execution_result.total_duration_ms}ms")
    lines.append(f"- Steps: {execution_result.steps_completed}/{execution_result.total_steps}")
    lines.append("")

    return "\n".join(lines)


def _save_learned_skill(category: str, raw_input: str, content: str) -> Path:
    """Salva a skill aprendida no diretório de skills."""
    skills_dir = get_skills_path() / "learned"
    skills_dir.mkdir(parents=True, exist_ok=True)

    # Gerar nome único baseado na categoria e timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitizar categoria para nome de arquivo
    safe_name = category.replace(".", "_").replace("/", "_")
    filename = f"{safe_name}_{timestamp}.md"

    skill_path = skills_dir / filename
    skill_path.write_text(content, encoding="utf-8")

    return skill_path


def _update_classifier_keywords(category: str, raw_input: str):
    """
    Extrai novas keywords do input e registra para o classificador.

    Salva em ~/.openpy/data/learned_keywords.json para persistência.
    """
    from openpy.utils.config import get_data_path

    keywords_file = get_data_path() / "learned_keywords.json"

    # Carregar existentes
    existing = {}
    if keywords_file.exists():
        try:
            existing = json.loads(keywords_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}

    # Extrair palavras significativas do input (> 3 chars, sem stopwords)
    stopwords = {
        "esse", "esta", "este", "isso", "aqui", "para", "como", "porque",
        "quando", "onde", "quem", "qual", "meu", "minha", "seus", "suas",
        "que", "com", "por", "uma", "dos", "das", "nos", "nas", "não",
        "mais", "muito", "todo", "toda", "cada", "pode", "fazer", "quero",
    }

    words = raw_input.lower().split()
    new_keywords = [w for w in words if len(w) > 3 and w not in stopwords]

    if category not in existing:
        existing[category] = []

    # Adicionar keywords novas sem duplicar
    for kw in new_keywords:
        if kw not in existing[category]:
            existing[category].append(kw)

    # Salvar
    keywords_file.parent.mkdir(parents=True, exist_ok=True)
    keywords_file.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
