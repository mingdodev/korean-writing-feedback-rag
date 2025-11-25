CREATE USER grammar WITH PASSWORD 'grammarpassword';

CREATE DATABASE grammar OWNER grammar;

GRANT ALL PRIVILEGES ON DATABASE grammar TO grammar;

\connect grammar;

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS grammar_items (
    id           INTEGER PRIMARY KEY,
    headword     TEXT NOT NULL,
    pos          TEXT,
    topic        TEXT,
    meaning      TEXT,
    form_info    TEXT,
    constraints  TEXT
);

CREATE INDEX IF NOT EXISTS idx_grammar_items_headword_trgm
    ON grammar_items
    USING GIN (headword gin_trgm_ops);