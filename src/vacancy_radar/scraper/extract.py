"""Извлечение вакансии из HTML-страницы Хабр Карьеры."""

import json
import re
from typing import Any

from bs4 import BeautifulSoup

JobPosting = dict[str, Any]

_BLOCK_TAGS = ("p", "li", "h1", "h2", "h3", "h4", "h5", "h6")
_WHITESPACE = re.compile(r"\s+")


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


def html_to_text(html: str) -> str:
    """HTML описания → текст: один блок на строку, пункты списка с «- »."""
    soup = BeautifulSoup(html, "html.parser")

    # 1. Пробелы из исходника (\n, \xa0, табы) → один пробел.
    #    type(node)(...) сохраняет тип узла: комментарий остаётся комментарием.
    for node in soup.find_all(string=True):
        node.replace_with(type(node)(_WHITESPACE.sub(" ", node)))

    # 2. Наши переносы строк.
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for tag in soup.find_all(_BLOCK_TAGS):
        if tag.name == "li":
            tag.insert(0, "- ")
        tag.append("\n")

    # 3. Текст без разделителя: strong/em/a не рвут предложения.
    # 4. Чистим каждую строку, выкидываем пустые и пустые пункты списка.
    lines = (_WHITESPACE.sub(" ", line).strip() for line in soup.get_text().split("\n"))
    return "\n".join(line for line in lines if line not in ("", "-"))
