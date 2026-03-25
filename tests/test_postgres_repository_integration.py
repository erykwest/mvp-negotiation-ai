from __future__ import annotations

import json
import os
import uuid
from contextlib import contextmanager

import pytest

try:
    import psycopg
except ImportError:  # pragma: no cover - integration test depends on optional runtime deps
    psycopg = None

from core.postgres_repository import PostgresSessionRepository
from core.repository import normalize_session_id
from core.workflow import build_default_state


POSTGRES_CONNECTION_STRING_ENV_VARS = ("SUPABASE_DB_URL", "DATABASE_URL", "POSTGRES_URL")


def _get_connection_string() -> str | None:
    for env_name in POSTGRES_CONNECTION_STRING_ENV_VARS:
        value = os.environ.get(env_name)
        if value and value.strip():
            return value.strip()
    return None


POSTGRES_CONNECTION_STRING = _get_connection_string()

if POSTGRES_CONNECTION_STRING is None:
    pytestmark = pytest.mark.skip(reason="No Postgres connection string environment variable is set.")
elif psycopg is None:
    pytestmark = pytest.mark.skip(reason="psycopg is not installed.")


@contextmanager
def _temporary_repository_table(connection_string: str):
    table_name = f"negotiation_sessions_test_{uuid.uuid4().hex}"
    with psycopg.connect(connection_string) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                create table {table_name} (
                  session_id text primary key,
                  state jsonb not null,
                  created_at timestamptz not null default now(),
                  updated_at timestamptz not null default now(),
                  constraint {table_name}_session_id_not_blank check (btrim(session_id) <> ''),
                  constraint {table_name}_state_is_object check (jsonb_typeof(state) = 'object')
                )
                """
            )
        connection.commit()

    try:
        yield table_name
    finally:
        with psycopg.connect(connection_string) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"drop table if exists {table_name}")
            connection.commit()


@pytest.fixture
def repository():
    if POSTGRES_CONNECTION_STRING is None or psycopg is None:
        pytest.skip("Postgres integration environment is not configured.")

    with _temporary_repository_table(POSTGRES_CONNECTION_STRING) as table_name:
        yield PostgresSessionRepository(
            POSTGRES_CONNECTION_STRING,
            table_name=table_name,
        )


def test_missing_session_load_creates_default_state(repository):
    raw_session_id = "  postgres / fresh-session  "
    normalized_session_id = normalize_session_id(raw_session_id)

    state = repository.load(raw_session_id)

    assert state == build_default_state(normalized_session_id)
    assert state["session_id"] == normalized_session_id


def test_save_and_load_roundtrip(repository):
    raw_session_id = "postgres-roundtrip-session"
    normalized_session_id = normalize_session_id(raw_session_id)

    state = build_default_state(normalized_session_id)
    state["job_description"] = "Postgres integration roundtrip"
    state["company"]["name"] = "Supabase Co"
    state["candidate"]["name"] = "Marta Rossi"
    state["results"]["NEGOTIATION"] = {"summary": "roundtrip preserved"}

    saved_state = repository.save(raw_session_id, state)
    loaded_state = repository.load(f" {raw_session_id} ")

    assert saved_state["session_id"] == normalized_session_id
    assert loaded_state == saved_state


def test_load_merges_defaults_into_partial_payload(repository):
    raw_session_id = "postgres-partial-session"
    normalized_session_id = normalize_session_id(raw_session_id)
    partial_state = {
        "session_id": raw_session_id,
        "company": {"name": "Partial Corp"},
    }

    with psycopg.connect(POSTGRES_CONNECTION_STRING) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"insert into {repository.config.table_name} (session_id, state) values (%s, %s::jsonb)",
                (normalized_session_id, json.dumps(partial_state, ensure_ascii=False)),
            )
        connection.commit()

    loaded_state = repository.load(raw_session_id)
    default_state = build_default_state(normalized_session_id)

    assert loaded_state["session_id"] == normalized_session_id
    assert loaded_state["company"]["name"] == "Partial Corp"
    assert loaded_state["workflow"] == default_state["workflow"]
    assert loaded_state["topic_tree"] == default_state["topic_tree"]
    assert loaded_state["round_snapshots"] == default_state["round_snapshots"]
    assert loaded_state["rfis"] == default_state["rfis"]
    assert loaded_state["suggested_rfis"] == default_state["suggested_rfis"]
    assert loaded_state["shared_topic_tree"] == default_state["shared_topic_tree"]
    assert loaded_state["private_inputs"] == default_state["private_inputs"]
    assert loaded_state["shared_outputs"] == default_state["shared_outputs"]
