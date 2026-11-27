"""Запись сырых вакансий в таблицу raw_vacancies."""

from dataclasses import asdict, dataclass
from typing import Any, Literal

import psycopg
from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb

from vacancy_radar.scraper.extract import JobPosting
from vacancy_radar.scraper.hashing import text_hash

UpsertResult = Literal["inserted", "updated", "unchanged", "duplicate"]

_HASH_CONSTRAINT = "raw_vacancies_hash_key"

_UPSERT_SQL = """
INSERT INTO raw_vacancies (source, external_id, url, raw_text, hash, raw_json)
VALUES (%(source)s, %(external_id)s, %(url)s, %(raw_text)s, %(hash)s, %(raw_json)s)
ON CONFLICT (source, external_id) DO UPDATE
SET url        = EXCLUDED.url,
    raw_text   = EXCLUDED.raw_text,
    hash       = EXCLUDED.hash,
    raw_json   = EXCLUDED.raw_json,
    fetched_at = now()
WHERE raw_vacancies.hash <> EXCLUDED.hash
RETURNING (xmax = 0) AS inserted
"""


@dataclass(frozen=True, slots=True)
class RawVacancy:
    """Строка raw_vacancies. Имена полей = имена колонок."""

    source: str
    external_id: str
    url: str
    raw_text: str
    hash: str  # text_hash(raw_text); создавать через RawVacancy.create
    raw_json: JobPosting

    @classmethod
    def create(
        cls,
        *,
        source: str,
        external_id: str,
        url: str,
        raw_text: str,
        raw_json: JobPosting,
    ) -> "RawVacancy":
        return cls(source, external_id, url, raw_text, text_hash(raw_text), raw_json)


def upsert_raw_vacancy(
    conn: psycopg.Connection[tuple[Any, ...]], vacancy: RawVacancy
) -> UpsertResult:
    """Вставить или обновить вакансию. Что произошло — в результате."""
    params = {**asdict(vacancy), "raw_json": Jsonb(vacancy.raw_json)}
    try:
        with conn.transaction():
            row = conn.execute(_UPSERT_SQL, params).fetchone()
    except UniqueViolation as e:
        if e.diag.constraint_name != _HASH_CONSTRAINT:
            raise
        return "duplicate"
    if row is None:
        return "unchanged"
    return "inserted" if row[0] else "updated"
