from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

from rpg.config import DATABASE_URL

_BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
SQL_DIR = _BUNDLE_ROOT / "sql"


def connect() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _execute_script(conn: psycopg.Connection, sql_text: str) -> None:
    """Run a SQL file one statement at a time (psycopg executes a single command)."""
    statement: list[str] = []
    for line in sql_text.splitlines():
        if line.strip().startswith("--"):
            continue
        statement.append(line)
        if line.rstrip().endswith(";"):
            chunk = "\n".join(statement).strip()
            if chunk:
                conn.execute(chunk)
            statement = []
    leftover = "\n".join(statement).strip()
    if leftover:
        conn.execute(leftover)


def initialize_schema(conn: psycopg.Connection) -> None:
    """Apply schema + seed when tables are missing (safe for local Docker volumes)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'characters'
            ) AS ready
            """
        )
        ready = cur.fetchone()["ready"]
    if ready:
        _migrate_character_quests(conn)
        _migrate_item_sales(conn)
        return
    _execute_script(conn, (SQL_DIR / "schema.sql").read_text(encoding="utf-8"))
    _execute_script(conn, (SQL_DIR / "seed.sql").read_text(encoding="utf-8"))
    conn.commit()


def _migrate_character_quests(conn: psycopg.Connection) -> None:
    """Allow multiple quest runs in databases created by older versions."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'character_quests'
                  AND column_name = 'id'
            ) AS migrated
            """
        )
        if not cur.fetchone()["migrated"]:
            cur.execute("ALTER TABLE character_quests ADD COLUMN id BIGSERIAL")
            cur.execute(
                "ALTER TABLE character_quests DROP CONSTRAINT IF EXISTS character_quests_pkey"
            )
            cur.execute("ALTER TABLE character_quests ADD PRIMARY KEY (id)")
    conn.commit()


def _migrate_item_sales(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS item_sales (
                id SERIAL PRIMARY KEY,
                character_id INTEGER NOT NULL REFERENCES characters (id) ON DELETE CASCADE,
                equipment_id INTEGER NOT NULL REFERENCES equipment (id),
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                unit_price INTEGER NOT NULL CHECK (unit_price >= 0),
                sold_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_item_sales_character_sold_at
            ON item_sales (character_id, sold_at DESC)
            """
        )
    conn.commit()
