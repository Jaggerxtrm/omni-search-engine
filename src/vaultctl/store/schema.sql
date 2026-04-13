PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY,
  root TEXT NOT NULL,
  include_glob TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY,
  source_id TEXT NOT NULL,
  rel_path TEXT NOT NULL,
  abs_path TEXT NOT NULL,
  title TEXT NOT NULL,
  status TEXT,
  body TEXT NOT NULL,
  heading_path TEXT NOT NULL DEFAULT '',
  tags_text TEXT NOT NULL DEFAULT '',
  mtime REAL NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(source_id, rel_path),
  FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS document_tags (
  document_id INTEGER NOT NULL,
  tag TEXT NOT NULL,
  UNIQUE(document_id, tag),
  FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS document_links (
  document_id INTEGER NOT NULL,
  target TEXT NOT NULL,
  UNIQUE(document_id, target),
  FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sections (
  id INTEGER PRIMARY KEY,
  document_id INTEGER NOT NULL,
  heading_path TEXT NOT NULL,
  body TEXT NOT NULL,
  FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE VIRTUAL TABLE IF NOT EXISTS sections_fts USING fts5(
  title,
  heading_path,
  tags_text,
  body,
  source_id UNINDEXED,
  rel_path UNINDEXED,
  tokenize='unicode61 remove_diacritics 2'
);
