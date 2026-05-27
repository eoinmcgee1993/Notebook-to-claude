# NotebookLM → Claude Projects Migration Tool

**The only tool that moves everything out of NotebookLM and into Claude Projects in one command.**

![Python](https://img.shields.io/badge/Python-3.9+-gold?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-gold?style=flat-square)
![Playwright](https://img.shields.io/badge/Powered_by-Playwright-gold?style=flat-square)

---

## The Problem

NotebookLM has no export. Your research, notes, sources, and outputs are locked inside Google's walled garden with no way out. If you want to move to Claude Projects (which runs circles around NotebookLM for active work), you're looking at hours of manual copying.

This tool solves that entirely.

## What It Does

Run one command. Get a clean, upload-ready folder for every notebook you own.

Each folder contains:
- All your sources (PDFs saved, text sources extracted)
- `NOTES.md` with everything from your Studio notes
- `KEY_OUTPUTS.md` with your saved chat responses
- `PROJECT_INSTRUCTIONS.md` — AI-generated system prompt tailored to your notebook's content
- `UPLOAD_GUIDE.md` — step-by-step instructions for setting up the Claude Project

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/mcgeezer81/notebooklm-to-claude.git
cd notebooklm-to-claude

# 2. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 3. Add your Anthropic API key (optional — for AI-generated instructions)
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 4. Run the migration
python migrate.py
```

A browser window opens. Log in to your Google account if prompted. The tool does the rest.

## Options

```bash
# List all your notebooks without migrating
python migrate.py --list

# Migrate a specific notebook
python migrate.py --notebook "My Research Project"

# Custom output directory
python migrate.py --output ~/Desktop/claude_projects

# Skip AI instruction generation (uses templates)
python migrate.py --skip-instructions
```

## Output Structure

```
claude_export/
  My_Research_Project/
    ├── PROJECT_INSTRUCTIONS.md   ← paste into Claude Project settings
    ├── NOTES.md                  ← your Studio notes
    ├── KEY_OUTPUTS.md            ← saved chat responses
    ├── UPLOAD_GUIDE.md           ← step-by-step upload instructions
    ├── MIGRATION_LOG.json        ← technical extraction record
    └── sources/
        ├── SOURCES_INDEX.md
        ├── source_1.pdf
        ├── source_2.txt
        └── ...
```

## Requirements

- Python 3.9+
- A Google account with NotebookLM notebooks
- Anthropic API key (optional — only for AI-generated Project Instructions)

## Important Notes

**Privacy:** Your data never leaves your machine. The tool runs a local browser session and writes everything to your local filesystem. No cloud storage, no third-party servers.

**Selector stability:** NotebookLM is a React SPA with no official API. If Google updates their UI and the auto-extraction breaks, sources will be listed with placeholder files. The tool tells you clearly what it found and what needs manual attention.

**Chat history:** NotebookLM does not expose chat history in a structured way. The tool extracts what is visible in the current session. Older chats may not be accessible.

## Why Claude Projects Wins

NotebookLM is a reading room. Claude Projects is a workshop.

NotebookLM summarises what you already have. Claude Projects helps you build what comes next. It generates copy, maps out strategies, writes blueprints, connects to your actual tools (GitHub, Canva, Adobe), and remembers your context across every conversation.

If your work requires output, not just comprehension, Claude Projects is the right tool.

---

## Premium Resources

The open source tool is free. If you want to go further:

**[The Complete Migration Guide + Project Instructions Templates →](https://digitalrena1ssance.gumroad.com)**

Includes:
- 8 pre-written Project Instructions templates (research, client work, content, personal knowledge base, and more)
- Video walkthrough of the full migration process
- Claude Projects setup guide for power users
- Troubleshooting guide for common extraction issues

---

## Contributing

Pull requests welcome. If NotebookLM updates their UI and selectors break, open an issue with the updated selector and the fix will be merged fast.

## License

MIT — use it, fork it, sell services around it.

---

*Built by [Digital Renaissance](https://digital-renaissance.tech) | Chiang Mai, Thailand*