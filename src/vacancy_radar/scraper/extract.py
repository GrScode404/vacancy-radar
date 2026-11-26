"""Извлечение вакансии из HTML-страницы Хабр Карьеры."""

import json
from typing import Any

from bs4 import BeautifulSoup

JobPosting = dict[str, Any]


def extract_job_posting(html: str) -> JobPosting | None:
    """Достаёт из страницы JSON-LD с типом JobPosting. Нет такого блока — None."""
    # намеренно не использовал lxml, чтобы не было лишних зависимостей
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.get_text())
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                return item
    return None
