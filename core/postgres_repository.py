import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

from core.repository import normalize_session_id
from core.workflow import build_default_state, merge_state_defaults_without_building_default_state

try:
    import psycopg
    from psycopg import sql
except ImportError as exc:  # pragma: no cover - import guard for optional dependency
    psycopg = None
    sql = None
    _IMPORT_ERROR = exc
else:  # pragma: no cover - exercised indirectly when dependency is installed
    _IMPORT_ERROR = None


DEFAULT_TABLE_NAME = "negotiation_sessions"


@dataclass(frozen=True)
class PostgresRepositoryConfig:
    connection_string: str
    table_name: str = DEFAULT_TABLE_NAME


def _parse_state(payload: Any) -> dict | None:
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, (bytes, bytearray, memoryview)):
        payload = bytes(payload).decode("utf-8")
    if isinstance(payload, str):
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


class PostgresSessionRepository:
    """Postgres-backed repository with the same session contract as the file backend."""

    def __init__(
        self,
        connection_string: str | None = None,
        *,
        table_name: str | None = None,
    ) -> None:
        if psycopg is None or sql is None:  # pragma: no cover - depends on local environment
            raise ImportError(
                "psycopg is required for PostgresSessionRepository. Install `psycopg[binary]`."
            ) from _IMPORT_ERROR

        resolved_connection_string = (
            connection_string
            or os.environ.get("SUPABASE_DB_URL")
            or os.environ.get("DATABASE_URL")
            or os.environ.get("POSTGRES_URL")
        )
        if not resolved_connection_string:
            raise ValueError(
                "A Postgres connection string is required. Set SUPABASE_DB_URL, DATABASE_URL, or POSTGRES_URL."
            )

        self.config = PostgresRepositoryConfig(
            connection_string=resolved_connection_string,
            table_name=(table_name or os.environ.get("NEGOTIATION_DB_TABLE") or DEFAULT_TABLE_NAME),
        )

    @contextmanager
    def _connect(self) -> Iterator[Any]:
        with psycopg.connect(self.config.connection_string) as connection:
            yield connection

    def _fetch_state(self, connection: Any, normalized_session_id: str) -> dict | None:
        query = sql.SQL("SELECT state FROM {table} WHERE session_id = %s").format(
            table=sql.Identifier(self.config.table_name)
        )
        with connection.cursor() as cursor:
            cursor.execute(query, (normalized_session_id,))
            row = cursor.fetchone()
        if not row:
            return None

        state = _parse_state(row[0])
        if state is None:
            return None
        return merge_state_defaults_without_building_default_state(state, session_id=normalized_session_id)

    def _upsert_state(self, connection: Any, normalized_session_id: str, state: dict) -> dict:
        merged_state = merge_state_defaults_without_building_default_state(state, session_id=normalized_session_id)
        query = sql.SQL(
            """
            INSERT INTO {table} (session_id, state)
            VALUES (%s, %s::jsonb)
            ON CONFLICT (session_id)
            DO UPDATE SET
                state = EXCLUDED.state,
                updated_at = NOW()
            RETURNING state
            """
        ).format(table=sql.Identifier(self.config.table_name))

        with connection.cursor() as cursor:
            cursor.execute(query, (normalized_session_id, json.dumps(merged_state, ensure_ascii=False)))
            row = cursor.fetchone()
        connection.commit()
        if row and row[0] is not None:
            parsed = _parse_state(row[0])
            if parsed is not None:
                return merge_state_defaults_without_building_default_state(
                    parsed,
                    session_id=normalized_session_id,
                )
        return merged_state

    def load(self, session_id: str | None) -> dict:
        normalized_session_id = normalize_session_id(session_id)
        with self._connect() as connection:
            state = self._fetch_state(connection, normalized_session_id)
            if state is not None:
                return state

            default_state = build_default_state(session_id=normalized_session_id)
            return self._upsert_state(connection, normalized_session_id, default_state)

    def save(self, session_id: str | None, state: dict) -> dict:
        normalized_session_id = normalize_session_id(session_id or state.get("session_id"))
        with self._connect() as connection:
            return self._upsert_state(connection, normalized_session_id, state)
