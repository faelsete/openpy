"""OpenPy Skills CLI — Gerenciar skills."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()
skills_app = typer.Typer()


def _find_skills() -> list[dict]:
    """Encontra todas as skills disponíveis (bundled + user)."""
    skills = []
    # Bundled
    bundled_dir = Path(__file__).parent.parent / "skills"
    if bundled_dir.exists():
        for md in bundled_dir.rglob("*.md"):
            rel = md.relative_to(bundled_dir)
            skills.append({"name": str(rel), "source": "bundled", "path": str(md), "size": md.stat().st_size})

    # User
    from openpy.utils.config import get_skills_path
    user_dir = get_skills_path()
    if user_dir.exists():
        for md in user_dir.rglob("*.md"):
            rel = md.relative_to(user_dir)
            name = str(rel)
            if not any(s["name"] == name for s in skills):
                skills.append({"name": name, "source": "user", "path": str(md), "size": md.stat().st_size})

    return skills


@skills_app.command("list")
def skills_list():
    """Lista todas as skills disponíveis."""
    skills = _find_skills()

    if not skills:
        console.print("[yellow]Nenhuma skill encontrada. Execute 'openpy onboard' para instalar.[/yellow]")
        return

    table = Table(title="📚 Skills Disponíveis", show_lines=True)
    table.add_column("Nome", style="bold")
    table.add_column("Fonte")
    table.add_column("Tamanho")

    for s in sorted(skills, key=lambda x: x["name"]):
        source_icon = "📦" if s["source"] == "bundled" else "👤"
        size_kb = s["size"] / 1024
        table.add_row(s["name"], f"{source_icon} {s['source']}", f"{size_kb:.1f} KB")

    console.print(table)


@skills_app.command("add")
def skills_add(path: str = typer.Argument(..., help="Caminho do arquivo .md da skill")):
    """Adiciona uma skill customizada."""
    import shutil
    from openpy.utils.config import get_skills_path

    src = Path(path)
    if not src.exists():
        console.print(f"[red]Arquivo não encontrado: {path}[/red]")
        raise typer.Exit(1)

    dest = get_skills_path() / src.name
    shutil.copy2(src, dest)
    console.print(f"[green]✅ Skill adicionada: {dest}[/green]")


@skills_app.command("show")
def skills_show(name: str = typer.Argument(..., help="Nome da skill para visualizar")):
    """Mostra conteúdo de uma skill."""
    from rich.markdown import Markdown

    skills = _find_skills()
    match = next((s for s in skills if name in s["name"]), None)
    if not match:
        console.print(f"[red]Skill não encontrada: {name}[/red]")
        return

    content = Path(match["path"]).read_text(encoding="utf-8")
    console.print(Markdown(content))
