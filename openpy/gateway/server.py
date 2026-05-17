"""
OpenPy Gateway Server — FastAPI daemon.

Ponto central do ecossistema. Gerencia routing, sessões, channels.
"""

import argparse
import sys
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from openpy import __version__
from openpy.utils.config import ensure_directories, load_config


# ============================================================================
# Lifespan
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup e shutdown do gateway."""
    ensure_directories()
    config = load_config()
    print(f"🧬 OpenPy Gateway v{__version__} iniciando...")
    print(f"   Provider: {config.providers.default.type}/{config.providers.default.model}")
    print(f"   Harness: {config.agent.harness_mode}")
    print(f"   Autonomia: {config.agent.autonomy_level}")
    yield
    print("🧬 OpenPy Gateway finalizando...")


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="OpenPy Gateway",
    description="Ecossistema operacional agêntico",
    version=__version__,
    lifespan=lifespan,
)


# ============================================================================
# Models
# ============================================================================

class TaskRequest(BaseModel):
    input: str
    model: str | None = None
    harness: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime: str
    provider: str
    harness_mode: str


# ============================================================================
# Routes
# ============================================================================

_start_time = datetime.now()


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check do gateway."""
    config = load_config()
    uptime = str(datetime.now() - _start_time).split(".")[0]
    return HealthResponse(
        status="healthy",
        version=__version__,
        uptime=uptime,
        provider=f"{config.providers.default.type}/{config.providers.default.model}",
        harness_mode=config.agent.harness_mode,
    )


@app.post("/task")
async def create_task(request: TaskRequest):
    """Submete uma tarefa para o pipeline."""
    from openpy.core.pipeline import run_task

    try:
        result = run_task(
            request.input,
            model_override=request.model,
            harness_override=request.harness,
        )
        return JSONResponse(content={
            "task_id": result.task_id,
            "classification": result.classification,
            "validation": result.validation,
            "response": result.llm_response if isinstance(result.llm_response, (dict, str)) else str(result.llm_response),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config")
async def get_config():
    """Retorna configuração atual (sem secrets)."""
    config = load_config()
    data = config.model_dump()
    # Mascarar secrets
    if data.get("providers", {}).get("default", {}).get("api_key"):
        data["providers"]["default"]["api_key"] = "***"
    if data.get("channels", {}).get("telegram", {}).get("token"):
        data["channels"]["telegram"]["token"] = "***"
    return data


@app.get("/skills")
async def list_skills():
    """Lista skills disponíveis."""
    from openpy.cli.skills_cmd import _find_skills
    return _find_skills()


@app.get("/status")
async def system_status():
    """Status do sistema."""
    import shutil
    import psutil
    from pathlib import Path
    # Cross-platform disk root
    disk_root = str(Path.home().anchor)
    disk = shutil.disk_usage(disk_root)
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "memory": {
            "total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
            "used_percent": psutil.virtual_memory().percent,
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 1),
            "used_percent": round(disk.used / disk.total * 100, 1),
        },
    }


# ============================================================================
# Runner
# ============================================================================

def run_server(port: int | None = None):
    """Inicia o servidor FastAPI."""
    import uvicorn
    config = load_config()
    actual_port = port or config.gateway.port
    uvicorn.run(
        app,
        host=config.gateway.host,
        port=actual_port,
        log_level="info",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()
    run_server(port=args.port)
