from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.repository import normalize_session_id
from core.workflow import merge_state_defaults_without_building_default_state

psycopg = None
sql = None
_IMPORT_ERROR: Exception | None = None


DEFAULT_TABLE_NAME = "negotiation_sessions"
DEFAULT_SAMPLE_FIELDS = [
    "session_id",
    "job_description",
    "company.name",
    "candidate.name",
    "workflow.current_phase",
    "workflow.status",
    "rfis",
    "suggested_rfis",
    "round_snapshots",
]


@dataclass(slots=True)
class SessionSnapshot:
    session_id: str
    source: str
    state: dict[str, Any]


def _env(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare local negotiation session JSON files with Supabase/Postgres rows."
    )
    parser.add_argument(
        "--data-dir",
        default=_env("NEGOTIATION_DATA_DIR", default="data"),
        help="Directory containing local session JSON files. Defaults to NEGOTIATION_DATA_DIR or ./data.",
    )
    parser.add_argument(
        "--db-url",
        default=_env("SUPABASE_DB_URL", "DATABASE_URL", "POSTGRES_URL"),
        help="Direct Postgres connection string for the Supabase project.",
    )
    parser.add_argument(
        "--table",
        default=_env("NEGOTIATION_DB_TABLE", default=DEFAULT_TABLE_NAME),
        help=f"Target table to compare. Defaults to {DEFAULT_TABLE_NAME}.",
    )
    parser.add_argument(
        "--sample-fields",
        default=",".join(DEFAULT_SAMPLE_FIELDS),
        help="Comma-separated field paths to compare for sampled content checks.",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=10,
        help="Maximum number of matching sessions to run sample content checks on.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on the number of local files and DB rows to inspect.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-session sample mismatches as they are found.",
    )
    return parser.parse_args(argv)


def _ensure_psycopg() -> None:
    global psycopg, sql, _IMPORT_ERROR

    if psycopg is not None and sql is not None:
        return

    try:  # pragma: no cover - depends on local environment
        import psycopg as psycopg_module
        from psycopg import sql as sql_module
    except ImportError as exc:
        _IMPORT_ERROR = exc
        raise ImportError(
            "psycopg is required for verify_supabase_migration.py. Install `psycopg[binary]`."
        ) from _IMPORT_ERROR

    psycopg = psycopg_module
    sql = sql_module


def _session_files(data_dir: Path) -> list[Path]:
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory does not exist: {data_dir}")
    if not data_dir.is_dir():
        raise NotADirectoryError(f"Data directory is not a directory: {data_dir}")
    return sorted(path for path in data_dir.glob("*.json") if path.is_file())


def _load_json_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object.")
    return payload


def _normalize_local_state(path: Path, raw_state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    normalized_session_id = normalize_session_id(path.stem)
    merged_state = merge_state_defaults_without_building_default_state(
        raw_state,
        session_id=normalized_session_id,
    )
    merged_state["session_id"] = normalized_session_id
    return normalized_session_id, merged_state


def _flatten_value(state: dict[str, Any], field_path: str) -> Any:
    current: Any = state
    for segment in field_path.split("."):
        if isinstance(current, dict) and segment in current:
            current = current[segment]
        else:
            return None
    return current


def _normalize_db_state(payload: Any) -> dict[str, Any] | None:
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


def _load_local_snapshots(files: list[Path]) -> tuple[dict[str, SessionSnapshot], list[str]]:
    snapshots: dict[str, SessionSnapshot] = {}
    errors: list[str] = []

    for path in files:
        try:
            raw_state = _load_json_file(path)
            session_id, state = _normalize_local_state(path, raw_state)
            snapshots[session_id] = SessionSnapshot(session_id=session_id, source=path.name, state=state)
        except Exception as exc:  # noqa: BLE001 - collect all file issues and keep going
            errors.append(f"local:{path.name}: {exc}")

    return snapshots, errors


def _load_db_snapshots(
    connection_string: str,
    table_name: str,
    *,
    limit: int | None = None,
) -> dict[str, SessionSnapshot]:
    query = sql.SQL("SELECT session_id, state FROM {table} ORDER BY session_id").format(
        table=sql.Identifier(table_name)
    )
    if limit is not None:
        query = query + sql.SQL(" LIMIT {limit}").format(limit=sql.Literal(max(limit, 0)))
    snapshots: dict[str, SessionSnapshot] = {}

    with psycopg.connect(connection_string) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            for session_id, raw_state in cursor.fetchall():
                normalized_session_id = normalize_session_id(session_id)
                state = _normalize_db_state(raw_state)
                if state is None:
                    continue
                merged_state = merge_state_defaults_without_building_default_state(
                    state,
                    session_id=normalized_session_id,
                )
                merged_state["session_id"] = normalized_session_id
                snapshots[normalized_session_id] = SessionSnapshot(
                    session_id=normalized_session_id,
                    source=table_name,
                    state=merged_state,
                )

    return snapshots


def _print_list(label: str, values: list[str], limit: int = 20) -> None:
    if not values:
        print(f"{label}: none")
        return

    shown = values[:limit]
    suffix = "" if len(values) <= limit else f" ... (+{len(values) - limit} more)"
    print(f"{label} ({len(values)}): {', '.join(shown)}{suffix}")


def _compare_field_sets(
    local_state: dict[str, Any],
    db_state: dict[str, Any],
    sample_fields: list[str],
) -> list[str]:
    diffs: list[str] = []
    for field_path in sample_fields:
        local_value = _flatten_value(local_state, field_path)
        db_value = _flatten_value(db_state, field_path)
        if local_value != db_value:
            diffs.append(
                f"{field_path}: local={local_value!r} db={db_value!r}"
            )
    return diffs


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    data_dir = Path(args.data_dir)
    db_url = args.db_url
    if not db_url:
        print(
            "Missing Postgres connection string. Set SUPABASE_DB_URL, DATABASE_URL, or POSTGRES_URL.",
            file=sys.stderr,
        )
        return 2

    _ensure_psycopg()

    files = _session_files(data_dir)
    if args.limit is not None:
        files = files[: max(args.limit, 0)]

    local_snapshots, local_errors = _load_local_snapshots(files)
    db_snapshots = _load_db_snapshots(db_url, args.table, limit=args.limit)

    local_ids = set(local_snapshots)
    db_ids = set(db_snapshots)
    missing_in_db = sorted(local_ids - db_ids)
    missing_in_local = sorted(db_ids - local_ids)
    common_ids = sorted(local_ids & db_ids)

    sample_fields = [field.strip() for field in args.sample_fields.split(",") if field.strip()]
    sampled_ids = common_ids[: max(args.sample_limit, 0)]
    sample_diffs: dict[str, list[str]] = {}
    for session_id in sampled_ids:
        diffs = _compare_field_sets(
            local_snapshots[session_id].state,
            db_snapshots[session_id].state,
            sample_fields,
        )
        if diffs:
            sample_diffs[session_id] = diffs

    print(f"Local session files: {len(local_snapshots)}")
    print(f"Database rows: {len(db_snapshots)}")
    print(f"Count mismatch: {'yes' if len(local_snapshots) != len(db_snapshots) else 'no'}")
    _print_list("Missing in DB", missing_in_db)
    _print_list("Missing in local data", missing_in_local)

    if local_errors:
        print(f"Local file errors ({len(local_errors)}):")
        for error in local_errors[:20]:
            print(f"  - {error}")

    if sample_diffs:
        print(f"Sample field mismatches ({len(sample_diffs)} sessions):")
        for session_id, diffs in sample_diffs.items():
            print(f"  - {session_id}")
            for diff in diffs:
                print(f"    - {diff}")
    else:
        print("Sample field mismatches: none")

    if args.verbose:
        print(f"Compared sample fields: {', '.join(sample_fields)}")
        print(f"Sampled sessions: {len(sampled_ids)}")

    has_issues = bool(
        len(local_snapshots) != len(db_snapshots)
        or missing_in_db
        or missing_in_local
        or local_errors
        or sample_diffs
    )
    return 1 if has_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
