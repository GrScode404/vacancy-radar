CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS raw_vacancies (
    id           bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source       text        NOT NULL,
    external_id  text        NOT NULL,
    url          text        NOT NULL,
    published_at timestamptz,
    fetched_at   timestamptz NOT NULL DEFAULT now(),
    raw_text     text        NOT NULL,
    hash         text        NOT NULL,

    CONSTRAINT raw_vacancies_source_external_id_key UNIQUE (source, external_id),
    CONSTRAINT raw_vacancies_hash_key UNIQUE (hash)
);