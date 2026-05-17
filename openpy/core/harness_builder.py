"""
OpenPy Harness Builder — Monta prompt completo com harness.

Modos: plain, strong, xhigh, brutal
Strong é o padrão (validado por benchmarks).

Integra skills, ferramentas, e contrato de resposta JSON.
"""

from typing import Optional


def build_harness(
    raw_input: str,
    core_skill: str,
    specific_skill: str,
    classification: dict,
    mode: str = "strong",
    tools_prompt: Optional[str] = None,
) -> str:
    """Monta o prompt completo com harness aplicado."""

    if mode == "plain":
        return _build_plain(raw_input)
    elif mode == "strong":
        return _build_strong(raw_input, core_skill, specific_skill, classification, tools_prompt)
    elif mode == "xhigh":
        return _build_xhigh(raw_input, core_skill, specific_skill, classification, tools_prompt)
    elif mode == "brutal":
        return _build_brutal(raw_input, core_skill, specific_skill, classification, tools_prompt)
    else:
        return _build_strong(raw_input, core_skill, specific_skill, classification, tools_prompt)


def _build_plain(raw_input: str) -> str:
    """Sem harness — modelo cru."""
    return raw_input


def _build_strong(raw_input: str, core: str, skill: str, classification: dict, tools_prompt: Optional[str] = None) -> str:
    """Modo Strong — harness principal validado."""

    tools_section = ""
    if tools_prompt:
        tools_section = f"""
=== FERRAMENTAS DISPONÍVEIS ===
{tools_prompt}

Você pode incluir "tool_calls" no JSON de resposta para usar ferramentas.
Para comandos shell, use a ferramenta "shell" ao invés de listar comandos diretamente.
"""

    return f"""=== INSTRUÇÕES OBRIGATÓRIAS (CORE) ===
{core}

=== SKILL ESPECÍFICA: {classification['category']} ===
{skill}
{tools_section}
=== CONTRATO DE RESPOSTA ===
Você DEVE responder em JSON válido com esta estrutura:

{{
  "intent": "{classification['category']}",
  "diagnostic": "Diagnóstico inicial do problema",
  "risk": "low|medium|high|critical",
  "needs_confirmation": true/false,
  "steps": [
    {{
      "description": "O que será feito",
      "commands": ["comando1", "comando2"],
      "verification": ["comando de verificação"],
      "rollback": "como reverter se der errado"
    }}
  ],
  "tool_calls": [
    {{"tool": "shell", "params": {{"command": "ls -la"}}}}
  ],
  "expected_success": "Como saber se funcionou",
  "next_blocker": "Próximo problema provável após resolver este"
}}

=== ANÁLISE OBRIGATÓRIA ANTES DE RESPONDER ===
1. Qual é a FINALIDADE REAL deste pedido?
2. Qual é o OBJETO CENTRAL?
3. Existe PEGADINHA LITERAL?
4. Quantas CAMADAS tem este problema?
5. Qual é a AÇÃO MÍNIMA CORRETA?

=== PEDIDO DO USUÁRIO ===
{raw_input}
"""


def _build_xhigh(raw_input: str, core: str, skill: str, classification: dict, tools_prompt: Optional[str] = None) -> str:
    """Modo XHigh — cadeia lógica mais pesada."""
    base = _build_strong(raw_input, core, skill, classification, tools_prompt)
    return base + """

=== ANÁLISE EXTENDIDA (XHIGH) ===
Antes de responder, analise CADA ponto abaixo:

6. Quais são os RISCOS de cada comando proposto?
7. Existe uma ALTERNATIVA mais segura?
8. Qual é a DEPENDÊNCIA entre os passos?
9. O que acontece se um passo FALHAR no meio?
10. Existe algum EFEITO COLATERAL não óbvio?
"""


def _build_brutal(raw_input: str, core: str, skill: str, classification: dict, tools_prompt: Optional[str] = None) -> str:
    """Modo Brutal — XHigh + revisão adversarial."""
    base = _build_xhigh(raw_input, core, skill, classification, tools_prompt)
    return base + """

=== REVISÃO ADVERSARIAL (BRUTAL) ===
Agora REVISE sua resposta:

- Algum comando pode causar DANO IRREVERSÍVEL?
- Algum passo pode ser SIMPLIFICADO?
- Você está sendo VERBOSO demais?
- A resposta funciona em um SISTEMA LIMPO?
- Existe QUALQUER RAZÃO para NÃO executar isso?

Se encontrar problemas na revisão, CORRIJA a resposta.
"""
