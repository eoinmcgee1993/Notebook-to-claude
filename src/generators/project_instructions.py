"""
Project Instructions Generator
Uses Claude to generate smart Project Instructions for each migrated notebook
"""
import os
import anthropic
from rich.console import Console
console = Console()


def get_template_instructions(title: str) -> str:
    """Fallback template when API is unavailable"""
    return f"""# Project Instructions: {title}

## Purpose
This project contains research and notes migrated from NotebookLM.

## Your Role
You are a knowledgeable research assistant with deep context on everything in the uploaded documents.
When I ask questions, draw on the knowledge files to give specific, accurate answers.
Always cite which source your information comes from when relevant.

## How to Handle My Requests

When I ask you to **summarise**: Give me a structured overview with the four most important themes.
When I ask you to **analyse**: Break it down into four key dimensions and give your assessment.
When I ask you to **create**: Use the tone, terminology, and frameworks from the source documents.
When I ask you to **find something**: Search the documents first, then tell me which source it came from.

## Output Standards
- Be specific, not generic
- Use language and terminology from the source documents
- Structure outputs clearly
- Flag if something cannot be found in the documents

## About This Project
Migrated from NotebookLM notebook: **{title}**
"""


class InstructionsGenerator:
    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")
        self.client = anthropic.Anthropic(api_key=api_key)

    async def generate(self, extracted: dict) -> str:
        title = extracted.get("title", "Untitled Notebook")
        sources = extracted.get("sources", [])
        notes = extracted.get("notes", [])
        messages = extracted.get("chat_messages", [])
        source_list = "\n".join([f"- {s.get('title', 'Unknown')} ({s.get('type', 'unknown')})" for s in sources[:15]])
        note_preview = notes[0].get("content", "")[:500] if notes else ""
        chat_preview = ""
        if messages:
            for msg in messages[:4]:
                chat_preview += f"{msg.get('role','unknown').upper()}: {msg.get('content','')[:200]}\n\n"
        prompt = f"""You are an expert at writing Claude Project Instructions (system prompts).

A user is migrating a NotebookLM notebook called "{title}" to Claude Projects.

Sources ({len(sources)} total):\n{source_list or 'No sources detected'}
Sample note: {note_preview or 'No notes found'}
Sample chat: {chat_preview or 'No chat history found'}

Write professional Claude Project Instructions. Define the purpose, give Claude a clear role, specify how to handle different request types, and set output standards. Format as clean Markdown. Under 500 words. Start directly with the instructions."""
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text