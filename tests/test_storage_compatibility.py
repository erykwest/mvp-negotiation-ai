import pytest

from core import storage
from core.repository import FileSessionRepository
from core.topic_tree import OTHER_MAIN_TOPIC_ID, build_subtopic, find_main_topic, find_subtopic
from tests.helpers import build_state


def configure_repo(tmp_path, monkeypatch):
    repository = FileSessionRepository(tmp_path)
    monkeypatch.setattr(storage, "_repository", repository)
    return repository


def test_add_dynamic_topic_routes_legacy_sections_into_template_topics(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)
    session_id = "legacy-routing"
    storage.load_state(session_id)

    storage.add_dynamic_topic(
        "company",
        "bonus",
        "Signing bonus",
        "5000 EUR one-off",
        session_id=session_id,
    )

    state = storage.load_state(session_id)
    compensation = find_main_topic(state["topic_tree"], "main-compensation")
    other = find_main_topic(state["topic_tree"], OTHER_MAIN_TOPIC_ID)

    assert compensation is not None
    assert other is not None
    assert any(subtopic.get("title") == "Signing bonus" for subtopic in compensation.get("subtopics", []))
    assert all(subtopic.get("title") != "Signing bonus" for subtopic in other.get("subtopics", []))


def test_edit_dynamic_topic_moves_legacy_section_into_template_topics(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)
    session_id = "legacy-edit-routing"
    state = build_state(current_phase="NEGOTIATION")
    other_topic = find_main_topic(state["topic_tree"], OTHER_MAIN_TOPIC_ID)
    other_topic["subtopics"].append(
        build_subtopic(
            main_topic_id=OTHER_MAIN_TOPIC_ID,
            title="Legacy signing bonus",
            description="Migrated dynamic topic.",
            created_by="candidate",
            phase_created="NEGOTIATION",
            subtopic_id="legacy-dynamic-1",
            positions={
                "candidate": {
                    "value": "5000 EUR one-off",
                    "priority": 3,
                    "deal_breaker": False,
                    "notes": "",
                }
            },
        )
    )
    storage.save_state(state, session_id=session_id)

    storage.edit_dynamic_topic(
        "legacy-dynamic-1",
        "candidate",
        "bonus",
        "Signing bonus",
        "6000 EUR one-off",
        session_id=session_id,
    )

    updated = storage.load_state(session_id)
    main_topic, subtopic = find_subtopic(updated["topic_tree"], "legacy-dynamic-1")

    assert main_topic is not None
    assert main_topic["id"] == "main-compensation"
    assert subtopic is not None
    assert subtopic["positions"]["candidate"]["value"] == "6000 EUR one-off"


def test_save_state_preserves_counterparty_inputs_for_party_view_payload(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)
    session_id = "party-view-roundtrip"
    storage.save_state(build_state(), session_id=session_id)

    party_view = storage.load_party_state("company", session_id)
    _main_topic, base_salary = find_subtopic(party_view["topic_tree"], "sub-base-salary")
    assert base_salary is not None
    base_salary["positions"]["company"]["value"] = "43000 EUR gross"
    base_salary["positions"]["company"]["priority"] = 4

    storage.save_state(party_view, session_id=session_id)

    reloaded = storage.load_state(session_id)
    _main_topic, stored_base_salary = find_subtopic(reloaded["topic_tree"], "sub-base-salary")

    assert stored_base_salary is not None
    assert stored_base_salary["positions"]["company"]["value"] == "43000 EUR gross"
    assert stored_base_salary["positions"]["company"]["priority"] == 4
    assert stored_base_salary["positions"]["candidate"]["value"] == "48000 EUR gross"
    assert stored_base_salary["positions"]["candidate"]["priority"] == 5


@pytest.mark.parametrize(
    ("side", "expected_own_value", "expected_counterparty_value"),
    [
        ("company", "43000 EUR gross", "48000 EUR gross"),
        ("candidate", "47000 EUR gross", "42000 EUR gross"),
    ],
)
def test_save_company_and_candidate_preserve_counterparty_inputs_with_party_tree(
    tmp_path,
    monkeypatch,
    side,
    expected_own_value,
    expected_counterparty_value,
):
    configure_repo(tmp_path, monkeypatch)
    session_id = f"party-view-{side}"
    storage.save_state(build_state(), session_id=session_id)

    party_view = storage.load_party_state(side, session_id)
    _main_topic, base_salary = find_subtopic(party_view["topic_tree"], "sub-base-salary")
    assert base_salary is not None

    if side == "company":
        base_salary["positions"]["company"]["value"] = expected_own_value
        base_salary["positions"]["company"]["priority"] = 4
        storage.save_company(
            {
                "job_description": party_view["job_description"],
                "company": {"name": "TechNova Engineering"},
                "topic_tree": party_view["topic_tree"],
            },
            session_id=session_id,
        )
    else:
        base_salary["positions"]["candidate"]["value"] = expected_own_value
        base_salary["positions"]["candidate"]["priority"] = 4
        storage.save_candidate(
            {
                "candidate": {"name": "Marco Rinaldi"},
                "topic_tree": party_view["topic_tree"],
            },
            session_id=session_id,
        )

    reloaded = storage.load_state(session_id)
    _main_topic, stored_base_salary = find_subtopic(reloaded["topic_tree"], "sub-base-salary")

    assert stored_base_salary is not None
    if side == "company":
        assert stored_base_salary["positions"]["company"]["value"] == expected_own_value
        assert stored_base_salary["positions"]["company"]["priority"] == 4
        assert stored_base_salary["positions"]["candidate"]["value"] == expected_counterparty_value
    else:
        assert stored_base_salary["positions"]["candidate"]["value"] == expected_own_value
        assert stored_base_salary["positions"]["candidate"]["priority"] == 4
        assert stored_base_salary["positions"]["company"]["value"] == expected_counterparty_value
