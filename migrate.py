#!/usr/bin/env python3
"""
NotebookLM → Claude Projects Migration Tool
by Digital Renaissance

Usage:
    python migrate.py                   # Full migration
    python migrate.py --list            # List notebooks only
    python migrate.py --notebook "Name" # Migrate one notebook
    python migrate.py --output ./export # Custom output directory
"""

import asyncio
import argparse
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

BANNER = """
[bold gold1]
  NLM  →  CLAUDE PROJECTS
  NotebookLM → Claude Projects Migration Tool | by Digital Renaissance
[/bold gold1]
"""

def parse_args():
    parser = argparse.ArgumentParser(
        description="Migrate your NotebookLM notebooks to Claude Projects"
    )
    parser.add_argument("--list", action="store_true", help="List all notebooks without migrating")
    parser.add_argument("--notebook", type=str, help="Migrate a specific notebook by name")
    parser.add_argument("--output", type=str, default="./claude_export", help="Output directory")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (requires prior login)")
    parser.add_argument("--generate-instructions", action="store_true", default=True,
                       help="Generate Claude Project Instructions using AI (requires ANTHROPIC_API_KEY)")
    parser.add_argument("--skip-instructions", action="store_true",
                       help="Skip AI instruction generation, use templates only")
    return parser.parse_args()


async def main():
    console.print(BANNER)
    args = parse_args()
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    console.print(Panel(
        "[bold]What this tool does:[/bold]\n\n"
        "1. Opens NotebookLM in your browser\n"
        "2. Extracts all notebooks, sources, notes, and outputs\n"
        "3. Organises everything into clean folders\n"
        "4. Generates Claude Project Instructions for each notebook\n"
        "5. Creates an upload-ready package per notebook\n\n"
        "[dim]Your data never leaves your machine. No cloud storage.[/dim]",
        title="[bold gold1]Migration Overview[/bold gold1]",
        border_style="gold1"
    ))

    from src.utils.env_check import check_environment
    env_ok = check_environment(skip_anthropic=args.skip_instructions)
    if not env_ok:
        sys.exit(1)

    from src.scrapers.notebooklm_scraper import NotebookLMScraper
    scraper = NotebookLMScraper(headless=args.headless)

    console.print("\n[bold gold1]Step 1:[/bold gold1] Connecting to NotebookLM...")

    try:
        notebooks = await scraper.get_all_notebooks()
    except Exception as e:
        console.print(f"[red]Failed to connect to NotebookLM: {e}[/red]")
        console.print("[dim]Make sure you're logged into Google in the browser that opens.[/dim]")
        sys.exit(1)

    if not notebooks:
        console.print("[yellow]No notebooks found. Make sure you're logged in.[/yellow]")
        sys.exit(0)

    console.print(f"[green]Found {len(notebooks)} notebook(s)[/green]")

    if args.list:
        console.print("\n[bold]Your notebooks:[/bold]")
        for i, nb in enumerate(notebooks, 1):
            console.print(f"  {i}. {nb['title']}")
        return

    if args.notebook:
        notebooks = [nb for nb in notebooks if args.notebook.lower() in nb['title'].lower()]
        if not notebooks:
            console.print(f"[red]No notebook found matching '{args.notebook}'[/red]")
            sys.exit(1)

    from src.exporters.file_organizer import FileOrganizer
    organizer = FileOrganizer(output_path)

    console.print(f"\n[bold gold1]Step 2:[/bold gold1] Extracting notebook contents...")

    all_extracted = []
    for i, notebook in enumerate(notebooks, 1):
        console.print(f"\n  [{i}/{len(notebooks)}] [bold]{notebook['title']}[/bold]")
        try:
            extracted = await scraper.extract_notebook(notebook)
            all_extracted.append(extracted)
            console.print(f"    [green]✓[/green] {len(extracted.get('sources', []))} sources, "
                         f"{len(extracted.get('notes', []))} notes, "
                         f"{len(extracted.get('chat_messages', []))} chat messages")
        except Exception as e:
            console.print(f"    [red]✗ Failed: {e}[/red]")

    await scraper.close()

    console.print(f"\n[bold gold1]Step 3:[/bold gold1] Organising files...")
    for extracted in all_extracted:
        folder = organizer.organize(extracted)
        console.print(f"  [green]✓[/green] {extracted['title']} → {folder}")

    if not args.skip_instructions:
        console.print(f"\n[bold gold1]Step 4:[/bold gold1] Generating Claude Project Instructions...")
        from src.generators.project_instructions import InstructionsGenerator
        generator = InstructionsGenerator()

        for extracted in all_extracted:
            try:
                instructions = await generator.generate(extracted)
                organizer.save_instructions(extracted['title'], instructions)
                console.print(f"  [green]✓[/green] Instructions generated for '{extracted['title']}'")
            except Exception as e:
                console.print(f"  [yellow]⚠[/yellow] Using template for '{extracted['title']}': {e}")
                organizer.save_template_instructions(extracted['title'])

    console.print(Panel(
        f"[bold green]Migration complete![/bold green]\n\n"
        f"[bold]{len(all_extracted)} notebook(s)[/bold] exported to:\n"
        f"[bold gold1]{output_path.absolute()}[/bold gold1]\n\n"
        "Each folder contains:\n"
        "  • All source files ready to upload\n"
        "  • NOTES.md with your saved notes\n"
        "  • KEY_OUTPUTS.md with saved chat responses\n"
        "  • PROJECT_INSTRUCTIONS.md for Claude Projects\n"
        "  • UPLOAD_GUIDE.md with step-by-step instructions\n\n"
        "[dim]Open UPLOAD_GUIDE.md in any folder to get started.[/dim]",
        title="[bold gold1]Done[/bold gold1]",
        border_style="green"
    ))


if __name__ == "__main__":
    asyncio.run(main())