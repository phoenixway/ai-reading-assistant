from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .config import settings

SCHEMA = r"""
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS books (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  author TEXT,
  source_type TEXT NOT NULL,
  source_ref TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status TEXT NOT NULL DEFAULT 'ready'
);

CREATE TABLE IF NOT EXISTS spans (
  id TEXT PRIMARY KEY,
  book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
  pos INTEGER NOT NULL,
  chapter INTEGER NOT NULL DEFAULT 1,
  scene INTEGER NOT NULL DEFAULT 1,
  para INTEGER NOT NULL,
  tok_len INTEGER NOT NULL,
  text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_spans_book_pos ON spans(book_id, pos);
CREATE VIRTUAL TABLE IF NOT EXISTS spans_fts USING fts5(
  span_id UNINDEXED, book_id UNINDEXED, text, tokenize='unicode61'
);

CREATE TABLE IF NOT EXISTS segments (
  id TEXT PRIMARY KEY,
  book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
  idx INTEGER NOT NULL,
  chapter INTEGER NOT NULL DEFAULT 1,
  start_pos INTEGER NOT NULL,
  end_pos INTEGER NOT NULL,
  tok_len INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending'
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_segments_book_idx ON segments(book_id, idx);

CREATE TABLE IF NOT EXISTS segment_spans (
  seg_id TEXT NOT NULL REFERENCES segments(id) ON DELETE CASCADE,
  span_id TEXT NOT NULL REFERENCES spans(id) ON DELETE CASCADE,
  local_no INTEGER NOT NULL,
  PRIMARY KEY(seg_id, span_id)
);

CREATE TABLE IF NOT EXISTS observations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
  seg_id TEXT NOT NULL,
  pos INTEGER NOT NULL,
  tag TEXT NOT NULL,
  kind TEXT NOT NULL,
  subj TEXT,
  obj TEXT,
  payload TEXT NOT NULL,
  source TEXT,
  epistemic TEXT NOT NULL DEFAULT 'EXPLICIT',
  focal_hint TEXT,
  fact_key TEXT,
  spans TEXT NOT NULL DEFAULT '',
  raw_line TEXT
);
CREATE INDEX IF NOT EXISTS ix_obs_book_pos ON observations(book_id, pos);
CREATE INDEX IF NOT EXISTS ix_obs_book_tag ON observations(book_id, tag);
CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts USING fts5(
  obs_id UNINDEXED, book_id UNINDEXED, payload, tokenize='unicode61'
);

CREATE TABLE IF NOT EXISTS summaries (
  seg_id TEXT PRIMARY KEY,
  book_id INTEGER NOT NULL,
  level TEXT NOT NULL DEFAULT 'segment',
  ref TEXT NOT NULL,
  pos_start INTEGER NOT NULL,
  pos_end INTEGER NOT NULL,
  text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entities (
  id TEXT NOT NULL,
  book_id INTEGER NOT NULL,
  canonical TEXT NOT NULL,
  type TEXT NOT NULL DEFAULT 'character',
  status TEXT NOT NULL DEFAULT 'provisional',
  first_pos INTEGER,
  last_pos INTEGER,
  PRIMARY KEY(book_id, id)
);
CREATE TABLE IF NOT EXISTS aliases (
  book_id INTEGER NOT NULL,
  norm TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  form TEXT NOT NULL,
  PRIMARY KEY(book_id, norm, entity_id)
);

CREATE TABLE IF NOT EXISTS details (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id INTEGER NOT NULL,
  label TEXT NOT NULL,
  norm TEXT NOT NULL,
  first_span TEXT,
  introduced_pos INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'dangling',
  resolved_pos INTEGER,
  resolved_span TEXT
);
CREATE INDEX IF NOT EXISTS ix_details_book_status ON details(book_id, status);

CREATE TABLE IF NOT EXISTS threads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  opened_pos INTEGER NOT NULL,
  closed_pos INTEGER,
  status TEXT NOT NULL DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS transitions (
  seg_id TEXT PRIMARY KEY,
  book_id INTEGER NOT NULL,
  present TEXT,
  loc TEXT,
  situation TEXT
);

CREATE TABLE IF NOT EXISTS annotations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id INTEGER NOT NULL,
  target_level TEXT,
  target_ref TEXT,
  pos INTEGER,
  note TEXT,
  kind TEXT,
  obs_id INTEGER
);

CREATE TABLE IF NOT EXISTS run_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  seg_id TEXT NOT NULL,
  profile TEXT NOT NULL,
  model TEXT,
  reasoning TEXT,
  parsed INTEGER,
  ignored INTEGER,
  quarantined INTEGER,
  no_span INTEGER,
  density REAL,
  span_validity REAL,
  contract_pass INTEGER,
  elapsed REAL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quarantine (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  seg_id TEXT,
  raw TEXT,
  reason TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

def connect(path: Path | None = None) -> sqlite3.Connection:
    db_path = path or settings.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con

def init_db(path: Path | None = None) -> None:
    with connect(path) as con:
        con.executescript(SCHEMA)

@contextmanager
def tx(path: Path | None = None):
    con = connect(path)
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
