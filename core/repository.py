import json
import os
from datetime import datetime
from pathlib import Path
from typing import Protocol

from core.workflow import build_default_state, merge_state_defaults_without_building_default_state


def normalize_session_id(session_id: str | None) -> str:
    raw = (session_id or "session_001").strip()
    if not raw:
        return "session_001"

    safe = []
    for char in raw:
        if char.isalnum() or char in {"-", "_"}:
            safe.append(char)
        else:
            safe.append("_")
    normalized = "".join(safe).strip("_")
    return normalized or "session_001"


def generate_session_id(prefix: str = "session") -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return normalize_session_id(f"{prefix}-{timestamp}")


class SessionRepository(Protocol):
    """Minimal persistence contract to preserve across future storage backends."""

    def load(self, session_id: str | None) -> dict:
        ...

    def save(self, session_id: str | None, state: dict) -> dict:
        ...


class FileSessionRepository:
    """File-backed repository used by the prototype and the current compatibility API."""

    def __init__(self, data_dir: str | os.PathLike | None = None):
        resolved_dir = data_dir or os.environ.get("NEGOTIATION_DATA_DIR", "data")
        self.data_dir = Path(resolved_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def session_file(self, session_id: str | None) -> Path:
        normalized = normalize_session_id(session_id)
        return self.data_dir / f"{normalized}.json"

    def load(self, session_id: str | None) -> dict:
        normalized = normalize_session_id(session_id)
        session_file = self.session_file(normalized)
        if not session_file.exists():
            default_state = build_default_state(session_id=normalized)
            with session_file.open("w", encoding="utf-8") as handle:
                json.dump(default_state, handle, ensure_ascii=False, indent=2)
            return default_state

        try:
            with session_file.open("r", encoding="utf-8") as handle:
                state = json.load(handle)
            if not isinstance(state, dict):
                raise ValueError("Session file must contain a JSON object.")
        except (json.JSONDecodeError, OSError, ValueError):
            backup_file = session_file.with_suffix(".corrupt.json")
            if session_file.exists():
                session_file.replace(backup_file)
            state = build_default_state(session_id=normalized)
            with session_file.open("w", encoding="utf-8") as handle:
                json.dump(state, handle, ensure_ascii=False, indent=2)

        return merge_state_defaults_without_building_default_state(state, session_id=normalized)

    def save(self, session_id: str | None, state: dict) -> dict:
        normalized = normalize_session_id(session_id or state.get("session_id"))
        session_file = self.session_file(normalized)
        merged_state = merge_state_defaults_without_building_default_state(state, session_id=normalized)
        with session_file.open("w", encoding="utf-8") as handle:
            json.dump(merged_state, handle, ensure_ascii=False, indent=2)
        return merged_state
