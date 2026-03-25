from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.repository import normalize_session_id
from core.workflow import merge_state_defaults_without_building_default_state


DEFAULT_TABLE_NAME = "negotiation_sessions"
DEFAULT_TIMEOUT_SECONDS = 30.0


@dataclass(slots=True)
class MigrationResult:
    session_id: str
    source_file: Path
    status: str
    message: str = ""


def _env(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate local negotiation session JSON files into Supabase/Postgres."
    )
    parser.add_argument(
        "--data-dir",
        default=_env("NEGOTIATION_DATA_DIR", default="data"),
        help="Directory containing local session JSON files. Defaults to NEGOTIATION_DATA_DIR or ./data.",
    )
    parser.add_argument(
        "--supabase-url",
        default=_env("SUPABASE_URL"),
        help="Supabase project URL, for example https://<project-ref>.supabase.co.",
    )
    parser.add_argument(
        "--supabase-key",
        default=_env(
            "SUPABASE_SERVICE_ROLE_KEY",
            "SUPABASE_SERVICE_KEY",
            "SUPABASE_ANON_KEY",
            "SUPABASE_KEY",
        ),
        help="Supabase API key. Use the service-role key for migrations.",
    )
    parser.add_argument(
        "--table",
        default=_env("SUPABASE_TABLE_NAME", default=DEFAULT_TABLE_NAME),
        help=f"Target Supabase table. Defaults to {DEFAULT_TABLE_NAME}.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(_env("SUPABASE_TIMEOUT_SECONDS", default=str(DEFAULT_TIMEOUT_SECONDS))),
        help="HTTP timeout in seconds for each Supabase request.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on the number of session files to migrate.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load and normalize the files, but do not write to Supabase.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print one line per migrated session and any normalization warnings.",
    )
    return parser.parse_args(argv)


def _session_files(data_dir: Path) -> list[Path]:
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory does not exist: {data_dir}")
    if not data_dir.is_dir():
        raise NotADirectoryError(f"Data directory is not a directory: {data_dir}")
    return sorted(path for path in data_dir.glob("*.json") if path.is_file())


def _load_json_file(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Session file must contain a JSON object.")
    return payload


def _normalize_state(path: Path, raw_state: dict) -> tuple[str, dict, list[str]]:
    warnings: list[str] = []
    normalized_session_id = normalize_session_id(path.stem)
    file_session_id = normalize_session_id(raw_state.get("session_id"))
    if file_session_id != normalized_session_id:
        warnings.append(
            f"session_id mismatch: file stem={normalized_session_id!r}, payload={file_session_id!r}; using file stem"
        )

    merged_state = merge_state_defaults_without_building_default_state(
        raw_state,
        session_id=normalized_session_id,
    )
    merged_state["session_id"] = normalized_session_id
    return normalized_session_id, merged_state, warnings


def _build_supabase_url(base_url: str, table: str) -> str:
    return f"{base_url.rstrip('/')}/rest/v1/{table.lstrip('/')}"


def _upsert_session(
    http: requests.Session,
    base_url: str,
    api_key: str,
    table: str,
    session_id: str,
    state: dict,
    timeout: float,
) -> None:
    response = http.post(
        _build_supabase_url(base_url, table),
        params={"on_conflict": "session_id"},
        headers={
            "apikey": api_key,
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        data=json.dumps({"session_id": session_id, "state": state}, ensure_ascii=False),
        timeout=timeout,
    )
    if response.status_code not in {200, 201, 204}:
        detail = response.text.strip() or response.reason
        raise RuntimeError(f"Supabase upsert failed for {session_id}: {response.status_code} {detail}")


def _iter_results(
    files: Iterable[Path],
    *,
    http: requests.Session | None,
    base_url: str | None,
    api_key: str | None,
    table: str,
    timeout: float,
    dry_run: bool,
    verbose: bool,
) -> tuple[list[MigrationResult], int]:
    results: list[MigrationResult] = []
    failure_count = 0

    for path in files:
        try:
            raw_state = _load_json_file(path)
            session_id, state, warnings = _normalize_state(path, raw_state)
            if dry_run:
                status = "dry-run"
            else:
                assert http is not None
                assert base_url is not None
                assert api_key is not None
                _upsert_session(http, base_url, api_key, table, session_id, state, timeout)
                status = "upserted"
            message = "; ".join(warnings)
            results.append(MigrationResult(session_id=session_id, source_file=path, status=status, message=message))
        except Exception as exc:  # noqa: BLE001 - script should continue with other files
            failure_count += 1
            results.append(
                MigrationResult(
                    session_id=normalize_session_id(path.stem),
                    source_file=path,
                    status="failed",
                    message=str(exc),
                )
            )

    if verbose:
        for result in results:
            line = f"{result.status}: {result.source_file.name} -> {result.session_id}"
            if result.message:
                line += f" ({result.message})"
            print(line)

    return results, failure_count


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    data_dir = Path(args.data_dir)
    files = _session_files(data_dir)
    if args.limit is not None:
        files = files[: max(args.limit, 0)]

    if not files:
        print(f"No session files found in {data_dir}")
        return 0

    if args.dry_run:
        results, failure_count = _iter_results(
            files,
            http=None,
            base_url=None,
            api_key=None,
            table=args.table,
            timeout=args.timeout,
            dry_run=True,
            verbose=args.verbose or args.dry_run,
        )
    else:
        base_url = args.supabase_url
        api_key = args.supabase_key
        if not base_url:
            print("Missing Supabase URL. Set SUPABASE_URL or pass --supabase-url.", file=sys.stderr)
            return 2
        if not api_key:
            print(
                "Missing Supabase API key. Set SUPABASE_SERVICE_ROLE_KEY (recommended) or pass --supabase-key.",
                file=sys.stderr,
            )
            return 2
        with requests.Session() as http:
            results, failure_count = _iter_results(
                files,
                http=http,
                base_url=base_url,
                api_key=api_key,
                table=args.table,
                timeout=args.timeout,
                dry_run=False,
                verbose=args.verbose,
            )

    success_count = len(results) - failure_count
    print(
        f"{'Dry run' if args.dry_run else 'Migration'} complete: {success_count} succeeded, {failure_count} failed."
    )

    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
