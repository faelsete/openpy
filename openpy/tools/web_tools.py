"""
OpenPy Web Tools — Busca e fetch de URLs.

Equivalente ao WebSearch/WebFetch do Claude Code.
"""

from openpy.tools.base import BaseTool, ToolResult, ToolRisk, ToolSpec


class WebFetchTool(BaseTool):
    """Busca conteúdo de uma URL."""

    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="web_fetch",
            description="Busca o conteúdo de uma URL (HTTP GET)",
            risk=ToolRisk.SAFE_READ,
            parameters={
                "url": {"type": "string", "description": "URL para buscar", "required": True},
                "headers": {"type": "object", "description": "Headers HTTP extras", "required": False},
            },
            examples=['web_fetch(url="https://api.github.com/repos/owner/repo")'],
        )

    async def execute(self, url: str, headers: dict = None, **kwargs) -> ToolResult:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                h = {"User-Agent": "OpenPy/0.1"}
                if headers:
                    h.update(headers)
                response = await client.get(url, headers=h)

                return ToolResult(
                    success=response.status_code < 400,
                    output=response.text[:10000],  # Limitar output
                    data={
                        "status_code": response.status_code,
                        "content_type": response.headers.get("content-type", ""),
                        "size": len(response.content),
                    },
                )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class SystemInfoTool(BaseTool):
    """Informações do sistema (CPU, RAM, disco, rede, processos)."""

    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="system_info",
            description="Coleta informações do sistema (CPU, RAM, disco, rede, processos)",
            risk=ToolRisk.SAFE_READ,
            parameters={
                "section": {
                    "type": "string",
                    "description": "Seção: all, cpu, memory, disk, network, processes",
                    "required": False,
                },
            },
            examples=['system_info()', 'system_info(section="memory")'],
        )

    async def execute(self, section: str = "all", **kwargs) -> ToolResult:
        import psutil
        import platform
        import shutil
        from pathlib import Path

        info = {}

        if section in ("all", "cpu"):
            info["cpu"] = {
                "percent": psutil.cpu_percent(interval=0.5),
                "count": psutil.cpu_count(),
                "count_physical": psutil.cpu_count(logical=False),
            }

        if section in ("all", "memory"):
            mem = psutil.virtual_memory()
            info["memory"] = {
                "total_gb": round(mem.total / (1024**3), 1),
                "used_gb": round(mem.used / (1024**3), 1),
                "percent": mem.percent,
            }

        if section in ("all", "disk"):
            disk_root = str(Path.home().anchor)
            disk = shutil.disk_usage(disk_root)
            info["disk"] = {
                "total_gb": round(disk.total / (1024**3), 1),
                "used_gb": round(disk.used / (1024**3), 1),
                "percent": round(disk.used / disk.total * 100, 1),
            }

        if section in ("all", "network"):
            addrs = psutil.net_if_addrs()
            info["network"] = {
                iface: [a.address for a in addr_list if a.family.name == "AF_INET"]
                for iface, addr_list in addrs.items()
            }

        if section in ("all", "processes"):
            procs = []
            for p in sorted(psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]),
                            key=lambda x: x.info.get("cpu_percent", 0) or 0, reverse=True)[:10]:
                procs.append(p.info)
            info["top_processes"] = procs

        if section == "all":
            info["platform"] = {
                "system": platform.system(),
                "release": platform.release(),
                "python": platform.python_version(),
                "hostname": platform.node(),
            }

        import json
        output = json.dumps(info, indent=2, ensure_ascii=False, default=str)
        return ToolResult(success=True, output=output, data=info)
