"""OpenPy Memory CLI — Gerenciar memória do agente."""

import typer
from rich.console import Console
from rich.table import Table

console = Console(force_terminal=True)
memory_app = typer.Typer()


@memory_app.command("status")
def memory_status():
    """Mostra status da memoria (SQLite + ChromaDB)."""
    from openpy.utils.config import get_data_path

    db_path = get_data_path() / "openpy.sqlite3"
    chroma_path = get_data_path() / "chroma"

    console.print("[bold]Status da Memoria[/bold]\n")
    console.print(f"  SQLite: {'[green]Ativo[/green]' if db_path.exists() else '[red]Nao inicializado[/red]'}")
    console.print(f"  ChromaDB: {'[green]Ativo[/green]' if chroma_path.exists() else '[dim]Nao inicializado[/dim]'}")

    if db_path.exists():
        size_mb = db_path.stat().st_size / (1024 * 1024)
        console.print(f"  SQLite tamanho: {size_mb:.2f} MB")

        # Mostrar estatísticas
        try:
            from openpy.core.memory import get_task_stats, get_learned_skills_stats

            stats = get_task_stats()
            console.print(f"\n  Tarefas executadas: {stats['total_tasks']}")
            console.print(f"  Tarefas bem-sucedidas: {stats['successful_tasks']}")
            console.print(f"  Taxa de sucesso: {stats['success_rate']}%")

            if stats["top_categories"]:
                console.print("\n  Categorias mais usadas:")
                for cat in stats["top_categories"][:5]:
                    console.print(f"    {cat['category']}: {cat['count']}x")

            skills_stats = get_learned_skills_stats()
            console.print(f"\n  Skills aprendidas: {skills_stats['total_learned']}")
        except Exception:
            pass


@memory_app.command("history")
def memory_history(
    limit: int = typer.Option(10, "--limit", "-n", help="Numero de tarefas"),
):
    """Mostra historico de tarefas recentes."""
    from openpy.core.memory import get_recent_tasks

    tasks = get_recent_tasks(limit=limit)
    if not tasks:
        console.print("[dim]Nenhuma tarefa no historico.[/dim]")
        return

    table = Table(title="Historico de Tarefas", show_lines=True)
    table.add_column("ID", style="dim")
    table.add_column("Input")
    table.add_column("Categoria")
    table.add_column("Resultado")
    table.add_column("Duracao")

    for t in tasks:
        raw = t["raw_input"][:40] + "..." if len(t.get("raw_input", "")) > 40 else t.get("raw_input", "")
        success = t.get("execution_success")
        status = "[green]OK[/green]" if success == 1 else "[red]Falha[/red]" if success == 0 else "[dim]---[/dim]"
        duration = f"{t.get('execution_duration_ms', 0)}ms" if t.get("execution_duration_ms") else "---"
        table.add_row(t["id"][:8], raw, t.get("category", "---"), status, duration)

    console.print(table)


@memory_app.command("search")
def memory_search(query: str = typer.Argument(..., help="Termo de busca")):
    """Busca na memoria por texto."""
    from openpy.core.memory import search_memories

    results = search_memories(query)
    if not results:
        console.print(f"[dim]Nenhum resultado para '{query}'[/dim]")
        return

    for r in results:
        console.print(f"  [{r['type']}] {r['content'][:80]}...")


@memory_app.command("clear")
def memory_clear(confirm: bool = typer.Option(False, "--confirm", help="Confirmar limpeza")):
    """Limpa todas as memorias."""
    if not confirm:
        console.print("[red]Use --confirm para confirmar a limpeza de memorias.[/red]")
        return

    from openpy.utils.config import get_data_path
    db_path = get_data_path() / "openpy.sqlite3"
    if db_path.exists():
        db_path.unlink()
        console.print("[green]Memoria limpa.[/green]")
    else:
        console.print("[dim]Nada para limpar.[/dim]")
