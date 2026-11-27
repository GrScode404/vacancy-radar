"""Подключение к Postgres."""

import os
from typing import Any

import psycopg

# DATABASE_URL берётся из окружения, .env подгружает `uv run --env-file .env`.
# Намеренно без python-dotenv / pydantic-settings: ради одной переменной
# зависимость не нужна. Перейти на pydantic-settings, когда настроек станет больше.
_DATABASE_URL_ENV = "DATABASE_URL"


def connect() -> psycopg.Connection[tuple[Any, ...]]:
    """Подключение к базе проекта. Нет DATABASE_URL — RuntimeError."""
    url = os.environ.get(_DATABASE_URL_ENV, "").strip()
    if not url:
        raise RuntimeError(
            f"{_DATABASE_URL_ENV} не задан: запускай через "
            "`uv run --env-file .env …` или цели make"
        )
    return psycopg.connect(url)
