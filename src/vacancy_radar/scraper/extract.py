"""Извлечение вакансии из HTML-страницы Хабр Карьеры."""

import json
import logging
import re
from typing import Any
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

JobPosting = dict[str, Any]

logger = logging.getLogger(__name__)

_HABR_HOST = "career.habr.com"
_BLOCK_TAGS = ("p", "li", "h1", "h2", "h3", "h4", "h5", "h6")
_WHITESPACE = re.compile(r"\s+")
_CURRENCY_ALIASES = {"RUR": "RUB"}  # RUR — устаревший код рубля
_UNIT_TEXT = {"HOUR": "в час", "DAY": "в день", "WEEK": "в неделю", "YEAR": "в год"}


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


def _text(value: Any) -> str | None:
    """Строка без лишних пробелов; None, если значения по сути нет."""
    if not isinstance(value, str):
        return None
    return _WHITESPACE.sub(" ", value).strip() or None


def _as_list(value: Any) -> list[Any]:
    """Один объект → список из одного; None → пустой список."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _company(posting: JobPosting) -> str | None:
    for key in ("hiringOrganization", "identifier"):
        org = posting.get(key)
        if isinstance(org, dict) and (name := _text(org.get("name"))):
            return name
    return None


def _place(place: Any) -> str | None:
    """Одно место из jobLocation → «Город, Страна» (что из этого есть)."""
    if not isinstance(place, dict):
        return None
    address = place.get("address")
    if isinstance(address, str):
        return _text(address)
    if not isinstance(address, dict):
        return None
    country = address.get("addressCountry")
    if isinstance(country, dict):
        country = country.get("name")
    parts = [_text(address.get("addressLocality")), _text(country)]
    return ", ".join(p for p in parts if p) or None


def _locations(posting: JobPosting) -> str | None:
    places = (_place(p) for p in _as_list(posting.get("jobLocation")))
    unique = dict.fromkeys(p for p in places if p)  # убирает повторы, сохраняя порядок
    return "; ".join(unique) or None


def _amount(value: Any) -> int | None:
    # bool — подкласс int в Python, True не должно стать зарплатой 1
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return round(value) if value > 0 else None


def _salary(posting: JobPosting) -> str | None:
    salary = posting.get("baseSalary")
    if not isinstance(salary, dict):
        return None
    value = salary.get("value")
    if not isinstance(value, dict):
        return None
    low, high = _amount(value.get("minValue")), _amount(value.get("maxValue"))

    if low is not None and high is not None:
        if low > high:
            logger.warning("baseSalary: minValue %s > maxValue %s", low, high)
            return None
        amount = str(low) if low == high else f"{low}–{high}"
    elif low is not None:
        amount = f"от {low}"
    elif high is not None:
        amount = f"до {high}"
    else:
        return None

    currency = _text(salary.get("currency"))
    if currency:
        currency = _CURRENCY_ALIASES.get(currency, currency)
    unit = _text(value.get("unitText"))
    period = None if unit in (None, "MONTH") else _UNIT_TEXT.get(unit, unit)
    return " ".join(p for p in ("Зарплата:", amount, currency, period) if p)


def build_raw_text(posting: JobPosting) -> str | None:
    """Текст вакансии для базы. None — нет должности или описания (пропустить)."""
    title = _text(posting.get("title"))
    description = posting.get("description")
    body = html_to_text(description) if isinstance(description, str) else ""
    if not title or not body:
        return None

    header = [title]
    if company := _company(posting):
        header.append(f"Компания: {company}")
    if locations := _locations(posting):
        header.append(f"Город: {locations}")
    if "TELECOMMUTE" in _as_list(posting.get("jobLocationType")):
        header.append("Формат работы: можно удалённо")
    if salary := _salary(posting):
        header.append(salary)
    return "\n".join(header) + "\n\n" + body


def external_id_from_url(url: str) -> str | None:
    """Id вакансии из URL вида https://career.habr.com/vacancies/<цифры>, иначе None."""
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or parts.hostname != _HABR_HOST:
        return None

    segments = [s for s in parts.path.split("/") if s]
    if len(segments) != 2 or segments[0] != "vacancies":
        return None

    vacancy_id = segments[1]
    if not (vacancy_id.isascii() and vacancy_id.isdigit()):
        return None
    return vacancy_id


def posting_identifier(posting: JobPosting) -> str | None:
    """identifier.value из JSON-LD как строка, иначе None."""
    identifier = posting.get("identifier")
    if not isinstance(identifier, dict):
        return None
    value = identifier.get("value")
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    return str(value).strip() or None
