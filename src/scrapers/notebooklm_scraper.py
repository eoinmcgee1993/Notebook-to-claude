"""
NotebookLM Scraper using Playwright
Extracts notebooks, sources, notes, and chat history
"""

import asyncio
import json
import re
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError
from rich.console import Console

console = Console()

NOTEBOOKLM_URL = "https://notebooklm.google.com"
PROFILE_DIR = Path.home() / ".notebooklm_migrator" / "browser_profile"

NOTEBOOK_SELECTORS = [
    '[data-notebook-id]',
    'mat-card[role="listitem"]',
    '.notebook-card',
    '[aria-label*="notebook" i]',
    'a[href*="/notebook/"]',
]

SOURCE_SELECTORS = [
    '[data-source-id]',
    '.source-item',
    '[aria-label*="source" i]',
    'mat-list-item',
    '.sources-list-item',
]

NOTE_SELECTORS = [
    '.studio-note',
    '[data-note-id]',
    '.note-item',
    '[aria-label*="note" i]',
]

CHAT_MESSAGE_SELECTORS = [
    '.chat-message',
    '.message-bubble',
    '[data-message-id]',
    'message-bubble',
    '.conversation-turn',
]


class NotebookLMScraper:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    async def _get_context(self) -> BrowserContext:
        self.playwright = await async_playwright().start()
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=self.headless,
            viewport={"width": 1280, "height": 900},
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            ignore_https_errors=True,
        )
        return self.context

    async def _wait_for_auth(self, page: Page) -> bool:
        try:
            current_url = page.url
            if "accounts.google.com" in current_url or "signin" in current_url.lower():
                console.print("\n[yellow]Please log in to your Google account in the browser window.[/yellow]")
                console.print("[dim]Waiting for authentication... (timeout: 120 seconds)[/dim]")
                await page.wait_for_url(
                    lambda url: "notebooklm.google.com" in url,
                    timeout=120_000
                )
            return True
        except TimeoutError:
            console.print("[red]Login timeout. Please try again.[/red]")
            return False

    async def _try_selectors(self, page: Page, selectors: list, timeout: int = 5000) -> Optional[list]:
        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=timeout)
                elements = await page.query_selector_all(selector)
                if elements:
                    return elements
            except TimeoutError:
                continue
        return None

    async def get_all_notebooks(self) -> list[dict]:
        context = await self._get_context()
        page = await context.new_page()
        await page.goto(NOTEBOOKLM_URL, wait_until="networkidle")
        await self._wait_for_auth(page)
        console.print("[dim]  Loading notebook list...[/dim]")
        await page.wait_for_timeout(2000)
        notebooks = []
        elements = await self._try_selectors(page, NOTEBOOK_SELECTORS, timeout=10000)
        if not elements:
            elements = await page.query_selector_all('a[href*="notebook"]')
        if not elements:
            console.print("[yellow]Could not auto-detect notebooks. Attempting JS extraction...[/yellow]")
            notebooks = await self._extract_notebooks_via_js(page)
            return notebooks
        for element in elements:
            try:
                title = await element.get_attribute("aria-label") or await element.inner_text() or "Untitled Notebook"
                title = title.strip().replace("\n", " ")[:100]
                href = await element.get_attribute("href") or ""
                notebook_id = self._extract_id_from_url(href)
                notebooks.append({"title": title, "id": notebook_id, "href": href, "element_handle": element})
            except Exception:
                continue
        seen = set()
        unique = []
        for nb in notebooks:
            if nb["title"] not in seen:
                seen.add(nb["title"])
                unique.append(nb)
        return unique

    async def _extract_notebooks_via_js(self, page: Page) -> list[dict]:
        try:
            notebooks = await page.evaluate("""
                () => {
                    const notebooks = [];
                    const candidates = document.querySelectorAll('[class*="notebook"], [class*="NotebookCard"], a[href*="/notebook/"]');
                    candidates.forEach(el => {
                        const title = el.textContent?.trim().split('\\n')[0] || 'Untitled';
                        const href = el.href || el.closest('a')?.href || '';
                        if (title && title.length > 0 && title.length < 200) {
                            notebooks.push({ title, href, id: '' });
                        }
                    });
                    return [...new Map(notebooks.map(n => [n.title, n])).values()];
                }
            """)
            return notebooks
        except Exception:
            return []

    async def extract_notebook(self, notebook: dict) -> dict:
        context = self.context
        page = await context.new_page()
        extracted = {"title": notebook["title"], "id": notebook.get("id", ""), "sources": [], "notes": [], "chat_messages": [], "source_files": []}
        try:
            if notebook.get("href") and "notebooklm" in notebook["href"]:
                url = notebook["href"]
                if not url.startswith("http"):
                    url = f"{NOTEBOOKLM_URL}{url}"
            else:
                url = NOTEBOOKLM_URL
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            extracted["sources"] = await self._extract_sources(page)
            extracted["notes"] = await self._extract_notes(page)
            extracted["chat_messages"] = await self._extract_chat(page)
            extracted["source_files"] = await self._download_source_content(page, extracted["sources"])
        except Exception as e:
            console.print(f"    [yellow]Partial extraction: {e}[/yellow]")
        finally:
            await page.close()
        return extracted

    async def _extract_sources(self, page: Page) -> list[dict]:
        sources = []
        elements = await self._try_selectors(page, SOURCE_SELECTORS, timeout=8000)
        if not elements:
            return await self._extract_sources_via_js(page)
        for element in elements:
            try:
                title = await element.get_attribute("aria-label") or await element.inner_text()
                title = title.strip()[:200]
                if title:
                    source_type = await self._detect_source_type(element)
                    sources.append({"title": title, "type": source_type, "content": ""})
            except Exception:
                continue
        return sources

    async def _extract_sources_via_js(self, page: Page) -> list[dict]:
        try:
            return await page.evaluate("""
                () => {
                    const sources = [];
                    const els = document.querySelectorAll('[class*="source"], [class*="Source"], [aria-label*="source" i]');
                    els.forEach(el => {
                        const text = el.textContent?.trim();
                        if (text && text.length > 0 && text.length < 300) {
                            sources.push({ title: text.split('\\n')[0], type: 'unknown', content: '' });
                        }
                    });
                    return sources;
                }
            """)
        except Exception:
            return []

    async def _extract_notes(self, page: Page) -> list[dict]:
        notes = []
        try:
            studio_btn = await page.query_selector('[aria-label*="Studio" i], [aria-label*="Note" i], button:has-text("Studio")')
            if studio_btn:
                await studio_btn.click()
                await page.wait_for_timeout(1000)
        except Exception:
            pass
        elements = await self._try_selectors(page, NOTE_SELECTORS, timeout=5000)
        if not elements:
            return await self._extract_notes_via_js(page)
        for element in elements:
            try:
                content = await element.inner_text()
                content = content.strip()
                if content:
                    notes.append({"title": content[:80] + ("..." if len(content) > 80 else ""), "content": content})
            except Exception:
                continue
        return notes

    async def _extract_notes_via_js(self, page: Page) -> list[dict]:
        try:
            return await page.evaluate("""
                () => {
                    const notes = [];
                    const els = document.querySelectorAll('[class*="note"], [class*="Note"], [class*="studio"], [class*="Studio"]');
                    els.forEach(el => {
                        const text = el.textContent?.trim();
                        if (text && text.length > 20 && text.length < 10000) {
                            notes.push({ title: text.substring(0, 80), content: text });
                        }
                    });
                    return notes;
                }
            """)
        except Exception:
            return []

    async def _extract_chat(self, page: Page) -> list[dict]:
        messages = []
        elements = await self._try_selectors(page, CHAT_MESSAGE_SELECTORS, timeout=5000)
        if not elements:
            return await self._extract_chat_via_js(page)
        for element in elements:
            try:
                content = await element.inner_text()
                content = content.strip()
                role_attr = await element.get_attribute("data-role") or await element.get_attribute("aria-label") or ""
                role = "assistant" if "model" in role_attr.lower() or "response" in role_attr.lower() else "user"
                if content:
                    messages.append({"role": role, "content": content})
            except Exception:
                continue
        return messages

    async def _extract_chat_via_js(self, page: Page) -> list[dict]:
        try:
            return await page.evaluate("""
                () => {
                    const messages = [];
                    const els = document.querySelectorAll('[class*="message"], [class*="Message"], [class*="chat"], [class*="Chat"]');
                    els.forEach(el => {
                        const text = el.textContent?.trim();
                        if (text && text.length > 10 && text.length < 50000) {
                            messages.push({ role: 'unknown', content: text });
                        }
                    });
                    return messages;
                }
            """)
        except Exception:
            return []

    async def _download_source_content(self, page: Page, sources: list[dict]) -> list[dict]:
        downloaded = []
        for source in sources[:20]:
            try:
                downloaded.append({"title": source["title"], "type": source["type"], "content": source.get("content", ""), "status": "listed"})
            except Exception:
                pass
        return downloaded

    async def _detect_source_type(self, element) -> str:
        try:
            text = await element.inner_text()
            icon_class = await element.get_attribute("class") or ""
            if "pdf" in text.lower() or "pdf" in icon_class.lower():
                return "pdf"
            elif "youtube" in text.lower() or "youtube" in icon_class.lower():
                return "youtube"
            elif "docs.google" in text.lower():
                return "google_doc"
            else:
                return "text"
        except Exception:
            return "unknown"

    def _extract_id_from_url(self, url: str) -> str:
        patterns = [r'/notebook/([a-zA-Z0-9_-]+)', r'notebook_id=([a-zA-Z0-9_-]+)', r'/([a-zA-Z0-9_-]{20,})$']
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return ""

    async def close(self):
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()