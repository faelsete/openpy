"""
OpenPy Contracts — Schemas de dados do pipeline.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class TaskContract:
    """Contrato de uma tarefa no pipeline."""
    task_id: str
    raw_input: str
    category: str
    risk: str = "unknown"
    needs_confirmation: bool = True
    diagnostic_commands: list[str] = field(default_factory=list)
    execution_commands: list[str] = field(default_factory=list)
    verification_commands: list[str] = field(default_factory=list)
    rollback: str = ""
    expected_success: str = ""
    notes: str = ""


@dataclass
class TaskResult:
    """Resultado completo de uma tarefa processada."""
    task_id: str
    raw_input: str
    classification: dict
    harness_mode: str
    model_used: str
    llm_response: Any
    validation: dict
    execution_result: Optional[dict] = None
    verification_result: Optional[dict] = None
    human_rating: Optional[str] = None
