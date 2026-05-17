"""
OpenPy Memory — Banco de memória operacional (SQLite).

Armazena:
- Sessões (conversas/interações)
- Histórico de tarefas (input, classificação, resultado, duração)
- Skills aprendidas (referências)
- Contexto persistente entre sessões

Equivalente ao memory system do Claude Code + OpenClaw.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from openpy.utils.config import get_data_path


DB_NAME = "openpy.sqlite3"


def _get_db_path() -> Path:
    return get_data_path() / DB_NAME


def _get_connection() -> sqlite3.Connection:
    """Retorna conexão com auto-criação do schema."""
    db_path = _get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection):
    """Cria tabelas se não existirem."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            total_tasks INTEGER DEFAULT 0,
            successful_tasks INTEGER DEFAULT 0,
            metadata TEXT DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS task_history (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            created_at TEXT NOT NULL,
            raw_input TEXT NOT NULL,
            category TEXT,
            confidence REAL,
            classification_method TEXT,
            harness_mode TEXT,
            model_used TEXT,
            risk_level TEXT,
            approved INTEGER,
            execution_success INTEGER,
            execution_duration_ms INTEGER,
            steps_total INTEGER DEFAULT 0,
            steps_completed INTEGER DEFAULT 0,
            skill_learned TEXT,
            llm_response TEXT,
            error TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );

        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            source_task_id TEXT,
            tags TEXT DEFAULT '[]',
            importance INTEGER DEFAULT 5,
            FOREIGN KEY (source_task_id) REFERENCES task_history(id)
        );

        CREATE TABLE IF NOT EXISTS learned_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            category TEXT NOT NULL,
            file_path TEXT NOT NULL,
            source_task_id TEXT,
            keywords TEXT DEFAULT '[]',
            times_used INTEGER DEFAULT 0,
            last_used_at TEXT,
            FOREIGN KEY (source_task_id) REFERENCES task_history(id)
        );

        CREATE INDEX IF NOT EXISTS idx_task_category ON task_history(category);
        CREATE INDEX IF NOT EXISTS idx_task_session ON task_history(session_id);
        CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
        CREATE INDEX IF NOT EXISTS idx_skills_category ON learned_skills(category);
    """)
    conn.commit()


# ============================================================================
# Sessions
# ============================================================================

def create_session() -> str:
    """Cria nova sessão e retorna o ID."""
    import uuid
    session_id = str(uuid.uuid4())[:12]
    conn = _get_connection()
    conn.execute(
        "INSERT INTO sessions (id, started_at) VALUES (?, ?)",
        (session_id, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return session_id


def end_session(session_id: str):
    """Finaliza uma sessão."""
    conn = _get_connection()
    conn.execute(
        "UPDATE sessions SET ended_at = ? WHERE id = ?",
        (datetime.now().isoformat(), session_id),
    )
    conn.commit()
    conn.close()


# ============================================================================
# Task History
# ============================================================================

def save_task(
    task_id: str,
    session_id: Optional[str],
    raw_input: str,
    classification: dict,
    harness_mode: str,
    model_used: str,
    validation: dict,
    execution_success: Optional[bool] = None,
    execution_duration_ms: Optional[int] = None,
    steps_total: int = 0,
    steps_completed: int = 0,
    skill_learned: Optional[str] = None,
    llm_response: Any = None,
    error: Optional[str] = None,
):
    """Salva uma tarefa no histórico."""
    conn = _get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO task_history
        (id, session_id, created_at, raw_input, category, confidence,
         classification_method, harness_mode, model_used, risk_level,
         approved, execution_success, execution_duration_ms,
         steps_total, steps_completed, skill_learned, llm_response, error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        task_id, session_id, datetime.now().isoformat(),
        raw_input, classification.get("category"),
        classification.get("confidence"),
        classification.get("method"),
        harness_mode, model_used,
        validation.get("risk"),
        1 if validation.get("approved") else 0,
        1 if execution_success else (0 if execution_success is not None else None),
        execution_duration_ms,
        steps_total, steps_completed,
        skill_learned,
        json.dumps(llm_response, ensure_ascii=False) if llm_response else None,
        error,
    ))

    # Atualizar contadores da sessão
    if session_id:
        conn.execute(
            "UPDATE sessions SET total_tasks = total_tasks + 1 WHERE id = ?",
            (session_id,),
        )
        if execution_success:
            conn.execute(
                "UPDATE sessions SET successful_tasks = successful_tasks + 1 WHERE id = ?",
                (session_id,),
            )

    conn.commit()
    conn.close()


def get_recent_tasks(limit: int = 20) -> list[dict]:
    """Retorna tarefas recentes."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM task_history ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_task_stats() -> dict:
    """Retorna estatísticas de tarefas."""
    conn = _get_connection()
    total = conn.execute("SELECT COUNT(*) FROM task_history").fetchone()[0]
    successful = conn.execute("SELECT COUNT(*) FROM task_history WHERE execution_success = 1").fetchone()[0]
    categories = conn.execute(
        "SELECT category, COUNT(*) as cnt FROM task_history GROUP BY category ORDER BY cnt DESC LIMIT 10"
    ).fetchall()
    conn.close()

    return {
        "total_tasks": total,
        "successful_tasks": successful,
        "success_rate": round(successful / total * 100, 1) if total > 0 else 0,
        "top_categories": [{"category": r[0], "count": r[1]} for r in categories],
    }


# ============================================================================
# Memories (context extraction)
# ============================================================================

def save_memory(
    content: str,
    memory_type: str = "observation",
    source_task_id: Optional[str] = None,
    tags: list[str] = None,
    importance: int = 5,
):
    """Salva uma memória extraída."""
    conn = _get_connection()
    conn.execute(
        "INSERT INTO memories (created_at, type, content, source_task_id, tags, importance) VALUES (?, ?, ?, ?, ?, ?)",
        (
            datetime.now().isoformat(),
            memory_type,
            content,
            source_task_id,
            json.dumps(tags or []),
            importance,
        ),
    )
    conn.commit()
    conn.close()


def search_memories(query: str, limit: int = 10) -> list[dict]:
    """Busca memórias por texto (LIKE). Semântica virá com ChromaDB."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM memories WHERE content LIKE ? ORDER BY importance DESC, created_at DESC LIMIT ?",
        (f"%{query}%", limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ============================================================================
# Learned Skills tracking
# ============================================================================

def register_learned_skill(
    category: str,
    file_path: str,
    source_task_id: Optional[str] = None,
    keywords: list[str] = None,
):
    """Registra uma skill aprendida no banco."""
    conn = _get_connection()
    conn.execute(
        "INSERT INTO learned_skills (created_at, category, file_path, source_task_id, keywords) VALUES (?, ?, ?, ?, ?)",
        (
            datetime.now().isoformat(),
            category,
            file_path,
            source_task_id,
            json.dumps(keywords or []),
        ),
    )
    conn.commit()
    conn.close()


def get_learned_skills_stats() -> dict:
    """Estatísticas de skills aprendidas."""
    conn = _get_connection()
    total = conn.execute("SELECT COUNT(*) FROM learned_skills").fetchone()[0]
    by_category = conn.execute(
        "SELECT category, COUNT(*) as cnt FROM learned_skills GROUP BY category ORDER BY cnt DESC"
    ).fetchall()
    most_used = conn.execute(
        "SELECT category, file_path, times_used FROM learned_skills ORDER BY times_used DESC LIMIT 5"
    ).fetchall()
    conn.close()

    return {
        "total_learned": total,
        "by_category": [{"category": r[0], "count": r[1]} for r in by_category],
        "most_used": [{"category": r[0], "path": r[1], "uses": r[2]} for r in most_used],
    }
