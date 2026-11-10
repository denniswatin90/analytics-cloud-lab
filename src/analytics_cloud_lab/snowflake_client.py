"""A small, testable wrapper around the Snowflake Python connector."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .config import SnowflakeSettings

log = logging.getLogger(__name__)


class SnowflakeClient:
    """Context-managed Snowflake connection with convenience helpers.

    Usage:
        with SnowflakeClient(SnowflakeSettings.from_env()) as sf:
            rows = sf.query("select current_version() as v")
    """

    def __init__(self, settings: SnowflakeSettings):
        self.settings = settings
        self._conn = None

    # --- lifecycle -------------------------------------------------------
    def connect(self) -> SnowflakeClient:
        import snowflake.connector  # imported lazily so tests run without it

        log.info("Connecting to Snowflake account %s as %s", self.settings.account, self.settings.user)
        self._conn = snowflake.connector.connect(**self.settings.as_connector_kwargs())
        return self

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> SnowflakeClient:
        return self.connect()

    def __exit__(self, *exc) -> None:
        self.close()

    @property
    def conn(self):
        if self._conn is None:
            raise RuntimeError("Not connected. Use `with SnowflakeClient(...) as sf:`")
        return self._conn

    # --- queries ---------------------------------------------------------
    def query(self, sql: str, params: dict | tuple | None = None) -> list[dict[str, Any]]:
        """Run a SELECT and return rows as dicts (column names upper-case)."""
        from snowflake.connector import DictCursor

        with self.conn.cursor(DictCursor) as cur:
            log.debug("SQL: %s | params=%s", sql, params)
            cur.execute(sql, params)
            return list(cur.fetchall())

    def execute(self, sql: str, params: dict | tuple | None = None) -> str | None:
        """Run a statement and return its query id (useful for Query Profile)."""
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.sfqid

    def execute_file(self, path: str | Path) -> None:
        """Run every statement in a .sql file."""
        text = Path(path).read_text(encoding="utf-8")
        for cur in self.conn.execute_string(text, remove_comments=True):
            log.info("Ran statement, query id %s", cur.sfqid)

    def put(self, local_path: str | Path, stage_path: str) -> None:
        """Upload a local file to an internal stage, e.g. '@RAW.LAB_STAGE/sessions/'."""
        local = Path(local_path).resolve().as_posix()
        self.execute(f"PUT 'file://{local}' {stage_path} AUTO_COMPRESS=TRUE OVERWRITE=TRUE")
