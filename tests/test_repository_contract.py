from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pytest

from core.repository import FileSessionRepository, SessionRepository, normalize_session_id
from core.workflow import build_default_state


@dataclass(frozen=True)
class RepositoryCase:
    name: str
    build: Callable[[Path], SessionRepository]
    seed_raw_state: Callable[[SessionRepository, str, object], None] | None = None
    session_exists: Callable[[SessionRepository, str], bool] | None = None
    recovery_artifact: Callable[[SessionRepository, str], Path] | None = None


def _build_file_repository(tmp_path: Path) -> FileSessionRepository:
    return FileSessionRepository(tmp_path)


def _seed_file_raw_state(repository: SessionRepository, session_id: str, payload: object) -> None:
    file_repository = repository
    assert isinstance(file_repository, FileSessionRepository)

    session_file = file_repository.session_file(session_id)
    session_file.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(payload, str):
        session_file.write_text(payload, encoding="utf-8")
        return

    session_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _file_session_exists(repository: SessionRepository, session_id: str) -> bool:
    file_repository = repository
    assert isinstance(file_repository, FileSessionRepository)
    return file_repository.session_file(session_id).exists()


def _file_recovery_artifact(repository: SessionRepository, session_id: str) -> Path:
    file_repository = repository
    assert isinstance(file_repository, FileSessionRepository)
    return file_repository.session_file(session_id).with_suffix(".corrupt.json")


REPOSITORY_CASES = [
    RepositoryCase(
        name="file",
        build=_build_file_repository,
        seed_raw_state=_seed_file_raw_state,
        session_exists=_file_session_exists,
        recovery_artifact=_file_recovery_artifact,
    ),
]


@pytest.fixture(params=REPOSITORY_CASES, ids=lambda case: case.name)
def repository_case(request: pytest.FixtureRequest, tmp_path: Path) -> RepositoryCase:
    case: RepositoryCase = request.param
    return case


@pytest.fixture
def repository(repository_case: RepositoryCase, tmp_path: Path) -> SessionRepository:
    return repository_case.build(tmp_path)


def test_missing_session_load_creates_default_state(repository_case: RepositoryCase, repository: SessionRepository) -> None:
    raw_session_id = "  fresh / negotiation  "
    normalized_session_id = normalize_session_id(raw_session_id)

    state = repository.load(raw_session_id)

    assert state == build_default_state(normalized_session_id)
    assert state["session_id"] == normalized_session_id
    if repository_case.session_exists is not None:
        assert repository_case.session_exists(repository, raw_session_id)


def test_session_id_normalization_is_applied_on_save_and_load(
    repository: SessionRepository,
) -> None:
    raw_session_id = "  sales / hiring-2026  "
    normalized_session_id = normalize_session_id(raw_session_id)

    state = build_default_state(normalized_session_id)
    state["job_description"] = "Hiring plan"
    state["company"]["name"] = "TechNova"
    state["results"]["ALIGNMENT"] = {"summary": "aligned"}

    saved_state = repository.save(raw_session_id, state)
    loaded_state = repository.load(f" {raw_session_id} ")

    assert saved_state["session_id"] == normalized_session_id
    assert loaded_state == saved_state


def test_save_and_load_roundtrip_preserves_canonical_state(repository: SessionRepository) -> None:
    raw_session_id = "roundtrip-session"

    state = build_default_state(raw_session_id)
    state["job_description"] = "Senior negotiation workflow"
    state["company"]["name"] = "Acme Corp"
    state["candidate"]["name"] = "Marta Rossi"
    state["results"]["NEGOTIATION"] = {"summary": "roundtrip preserved"}
    state["rfis"].append(
        {
            "id": "rfi-1",
            "phase": "ALIGNMENT",
            "requested_by": "company",
            "target_side": "candidate",
            "status": "OPEN",
            "question": "Can we clarify scope?",
        }
    )

    saved_state = repository.save(raw_session_id, state)
    loaded_state = repository.load(raw_session_id)

    assert loaded_state == saved_state


def test_load_merges_defaults_into_partial_payload(repository_case: RepositoryCase, repository: SessionRepository) -> None:
    raw_session_id = "partial-session"
    normalized_session_id = normalize_session_id(raw_session_id)
    partial_state = {
        "session_id": raw_session_id,
        "company": {"name": "Partial Corp"},
    }

    assert repository_case.seed_raw_state is not None
    repository_case.seed_raw_state(repository, raw_session_id, partial_state)

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


@pytest.mark.parametrize(
    ("payload_name", "raw_payload"),
    [
        ("invalid-json", "{not-json"),
        ("non-object", ["unexpected", "list"]),
    ],
)
def test_load_recovers_from_corrupt_and_non_object_payloads(
    repository_case: RepositoryCase,
    repository: SessionRepository,
    payload_name: str,
    raw_payload: object,
) -> None:
    raw_session_id = f"broken-{payload_name}"
    normalized_session_id = normalize_session_id(raw_session_id)

    assert repository_case.seed_raw_state is not None
    repository_case.seed_raw_state(repository, raw_session_id, raw_payload)

    recovered_state = repository.load(raw_session_id)

    assert recovered_state == build_default_state(normalized_session_id)
    if repository_case.session_exists is not None:
        assert repository_case.session_exists(repository, raw_session_id)
    if repository_case.recovery_artifact is not None:
        assert repository_case.recovery_artifact(repository, raw_session_id).exists()
