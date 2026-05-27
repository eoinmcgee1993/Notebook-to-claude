"""
Environment checker - validates setup before running migration
"""
import os
from rich.console import Console
from rich.table import Table
console = Console()


def check_environment(skip_anthropic: bool = False) -> bool:
    table = Table(title="Environment Check", show_header=True, header_style="bold gold1")
    table.add_column("Dependency", style="bold")
    table.add_column("Status")
    table.add_column("Notes")
    all_ok = True
    import sys
    py_version = sys.version_info
    if py_version >= (3, 9):
        table.add_row("Python 3.9+", "[green]v[/green]", f"{py_version.major}.{py_version.minor}.{py_version.micro}")
    else:
        table.add_row("Python 3.9+", "[red]x[/red]", f"Found {py_version.major}.{py_version.minor} - please upgrade")
        all_ok = False
    try:
        import playwright
        table.add_row("Playwright", "[green]v[/green]", "Installed")
    except ImportError:
        table.add_row("Playwright", "[red]x[/red]", "Run: pip install playwright && playwright install chromium")
        all_ok = False
    if not skip_anthropic:
        try:
            import anthropic
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if api_key:
                table.add_row("Anthropic SDK", "[green]v[/green]", "Installed + API key found")
            else:
                table.add_row("Anthropic SDK", "[yellow]![/yellow]", "Installed but no ANTHROPIC_API_KEY - will use templates")
        except ImportError:
            table.add_row("Anthropic SDK", "[yellow]![/yellow]", "Not installed - run: pip install anthropic (optional)")
    try:
        import rich
        table.add_row("Rich (UI)", "[green]v[/green]", "Installed")
    except ImportError:
        table.add_row("Rich (UI)", "[red]x[/red]", "Run: pip install rich")
        all_ok = False
    console.print(table)
    if not all_ok:
        console.print("\n[red]Please fix the issues above before running the migration.[/red]")
        console.print("[dim]Run: pip install -r requirements.txt && playwright install chromium[/dim]")
    return all_ok