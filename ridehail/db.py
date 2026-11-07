import atexit
import os
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# The driver is private to this module (underscore names): nothing outside
# db.py should import it or receive its objects.
import psycopg as _psycopg
from psycopg.rows import dict_row as _dict_row

__all__ = [
    "describe", "apply_schema", "execute", "fetch_all", "fetch_one",
    "run_in_transaction", "once", "many", "query_to_csv", "close",
    "DatabaseError", "ConfigError", "ConnectionFailed", "SchemaError", "QueryError",
    "Step", "Row", "Params",
]

Params = Sequence[Any] | Mapping[str, Any] | None
Row = dict[str, Any]

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


class DatabaseError(Exception):
    """Base class for every error raised by this module."""


class ConfigError(DatabaseError):
    """Configuration needed to reach the database is missing."""


class ConnectionFailed(DatabaseError):
    """The database could not be reached."""


class SchemaError(DatabaseError):
    """A file in sql/ failed. Nothing from sql/ was applied."""


class QueryError(DatabaseError):
    """A statement failed. Nothing from the failed call was committed."""


@dataclass(frozen=True)
class Step:
    sql: str
    params: Params = None
    rows: Iterable[Params] | None = None


def once(sql: str, params: Params = None) -> Step:
    return Step(sql=sql, params=params)


def many(sql: str, rows: Iterable[Params]) -> Step:
    if isinstance(rows, (str, bytes, Mapping)):
        raise TypeError("many() takes an iterable of rows (tuples or dicts); "
                        "for a single statement use once()")
    return Step(sql=sql, rows=rows)


def describe() -> str:
    """One-line description of the database connection, safe to print."""
    info = _connection().info
    version = info.server_version  # e.g. 160004 for 16.4
    return (f"connected to {info.dbname}@{info.host} "
            f"(PostgreSQL {version // 10000}.{version % 10000})")


def apply_schema() -> list[str]:
    """Run every file in sql/ in file-name order, as one all-or-nothing unit.

    Runs on every pipeline start, so every statement in sql/ must be safe to
    run again on a database that already has it. Returns the file names.
    """
    files = sorted(SQL_DIR.glob("*.sql"))
    conn = _connection()
    try:
        with conn.transaction():
            for path in files:
                try:
                    conn.execute(path.read_text(encoding="utf-8"))
                except _psycopg.Error as exc:
                    raise SchemaError(f"sql/{path.name}: {exc}".strip()) from exc
    except _psycopg.Error as exc:
        raise SchemaError(f"sql/: {exc}".strip()) from exc
    return [path.name for path in files]


def execute(sql: str, params: Params = None) -> int:
    """Run one statement and commit it immediately. Returns rows affected."""
    return run_in_transaction([once(sql, params)])[0]


def fetch_all(sql: str, params: Params = None) -> list[Row]:
    """Run a query and return every row as a dict keyed by column name."""
    conn = _connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    except _psycopg.Error as exc:
        raise QueryError(f"{_label(sql)}: {exc}".strip()) from exc


def fetch_one(sql: str, params: Params = None) -> Row | None:
    """Run a query and return its first row as a dict, or None if there is none."""
    conn = _connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    except _psycopg.Error as exc:
        raise QueryError(f"{_label(sql)}: {exc}".strip()) from exc


def run_in_transaction(steps: Iterable[Step]) -> list[int]:
    """Run the steps in order as one unit: all of them commit, or none does.

    Build steps with once() and many(). Returns the number of rows affected by
    each step, in the same order. If any step fails, everything is rolled back
    and QueryError says which step failed.
    """
    steps = list(steps)
    for step in steps:
        if not isinstance(step, Step):
            raise TypeError("run_in_transaction() takes steps built with "
                            "db.once() or db.many()")
    conn = _connection()
    counts: list[int] = []
    try:
        with conn.transaction(), conn.cursor() as cur:
            for number, step in enumerate(steps, start=1):
                try:
                    if step.rows is None:
                        cur.execute(step.sql, step.params)
                    else:
                        cur.executemany(step.sql, step.rows)
                    counts.append(max(cur.rowcount, 0))
                except _psycopg.Error as exc:
                    where = f"step {number} of {len(steps)}, " if len(steps) > 1 else ""
                    raise QueryError(f"{where}{_label(step.sql)}: {exc}".strip()
                                     + "\n(nothing was committed)") from exc
    except _psycopg.Error as exc:
        raise QueryError(f"commit failed: {exc} (nothing was committed)") from exc
    return counts


def query_to_csv(sql: str, path: Path | str) -> int:
    """Write the result of a SELECT to a CSV file with a header row.

    `sql` is a plain SELECT without parameters. Values are written exactly as
    the database formats them, so NUMERIC(10,2) stays e.g. 1234.50. The file
    is replaced only if the query succeeds. Returns the number of data rows.
    """
    sql = sql.strip().rstrip(";").strip()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    conn = _connection()
    try:
        with conn.cursor() as cur, tmp.open("wb") as out:
            with cur.copy(f"COPY ({sql}) TO STDOUT WITH (FORMAT csv, HEADER)") as copy:
                for chunk in copy:
                    out.write(chunk)
            rows = max(cur.rowcount, 0)
    except _psycopg.Error as exc:
        tmp.unlink(missing_ok=True)
        raise QueryError(f"{_label(sql)}: {exc}".strip()) from exc
    tmp.replace(path)
    return rows


def close() -> None:
    """Close the connection. Safe to call more than once, runs at exit anyway."""
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None


_conn: _psycopg.Connection | None = None


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise ConfigError("DATABASE_URL is not set. Run the pipeline through "
                          "docker compose, which sets it from .env.")
    return url


def _connection() -> _psycopg.Connection:
    global _conn
    if _conn is None or _conn.closed:
        url = _database_url()
        try:
            _conn = _psycopg.connect(
                url,
                autocommit=True,
                connect_timeout=10,
                application_name="ridehail-pipeline",
                options="-c TimeZone=UTC",
                row_factory=_dict_row,
            )
        except _psycopg.Error as exc:
            raise ConnectionFailed(f"cannot connect to the database: {exc}") from exc
    return _conn


def _label(sql: str) -> str:
    for line in sql.splitlines():
        line = line.strip()
        if line and not line.startswith("--"):
            return line if len(line) <= 70 else line[:67] + "..."
    return "(empty statement)"


atexit.register(close)
