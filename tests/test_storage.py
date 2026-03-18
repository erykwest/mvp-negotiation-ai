import json

from core import storage
from core.repository import FileSessionRepository
from core.template_loader import load_negotiation_template
from core.topic_tree import OTHER_MAIN_TOPIC_ID, find_main_topic, find_subtopic, get_sorted_main_topics
from core.workflow import WORKFLOW_STATE_ROUND_OPEN, WORKFLOW_STATE_ROUND_REVIEW
from tests.helpers import build_state, build_topic_tree


def configure_repo(tmp_path, monkeypatch):
    repository = FileSessionRepository(tmp_path)
    monkeypatch.setattr(storage, "_repository", repository)
    return repository


def build_legacy_state() -> dict:
    return {
        "session_id": "legacy-session",
        "job_description": "Legacy recruiting setup",
        "company": {
            "name": "LegacyCorp",
            "salary": "42000",
            "smart": "Hybrid",
            "bonus": "Annual bonus",
            "car": "No",
            "benefits": "Meal vouchers",
        },
        "candidate": {
            "name": "Alice",
            "salary": "47000",
            "smart": "Remote-first",
            "bonus": "Sign-on bonus",
            "car": "No",
            "benefits": "Education budget",
        },
        "priorities": {
            "salary": {"company": 5, "candidate": 5},
            "smart": {"company": 3, "candidate": 4},
        },
        "dynamic_topics": [
            {
                "id": "legacy-dynamic-1",
                "section": "bonus",
                "title": "Signing bonus",
                "created_by": "candidate",
                "company_answer": "",
                "candidate_answer": "5000 EUR",
            }
        ],
        "workflow": {"current_phase": "NEGOTIATION", "status": "editing"},
        "results": {},
    }


def test_load_state_creates_default_session_file_with_other_topic(tmp_path, monkeypatch):
    repository = configure_repo(tmp_path, monkeypatch)

    state = storage.load_state("alpha")
    main_topics = state["topic_tree"]["main_topics"]
    template = load_negotiation_template()
    template_section_ids = [section["section_id"] for section in template["sections"]]
    non_other_topics = [topic for topic in get_sorted_main_topics(state["topic_tree"]) if not topic.get("is_other")]
    compensation = find_main_topic(state["topic_tree"], "main-compensation")
    _compensation_topic, base_salary = find_subtopic(state["topic_tree"], "sub-base_salary")

    assert state["session_id"] == "alpha"
    assert repository.session_file("alpha").exists()
    assert state["workflow"]["current_phase"] == "ALIGNMENT"
    assert state["workflow"]["status"] == WORKFLOW_STATE_ROUND_OPEN
    assert len(main_topics) == len(template_section_ids) + 1
    assert [topic["template_section_id"] for topic in non_other_topics] == template_section_ids
    assert compensation is not None
    assert compensation["locked"] is True
    assert base_salary is not None
    assert base_salary["template_topic_id"] == "base_salary"
    assert "shared_topic_tree" in state
    assert "private_inputs" in state
    assert "shared_outputs" in state
    assert state["private_inputs"]["company"]["main_topic_priorities"]["main-compensation"] is None
    assert main_topics[-1]["id"] == OTHER_MAIN_TOPIC_ID
    assert main_topics[-1]["is_other"] is True


def test_load_state_migrates_legacy_state_to_demo_topic_tree(tmp_path, monkeypatch):
    repository = configure_repo(tmp_path, monkeypatch)
    repository.session_file("legacy-session").write_text(
        json.dumps(build_legacy_state(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    state = storage.load_state("legacy-session")
    topic_tree = state["topic_tree"]
    main_topics = get_sorted_main_topics(topic_tree)
    _bonus_topic, signing_bonus = find_subtopic(topic_tree, "legacy-dynamic-1")

    assert state["workflow"]["status"] == WORKFLOW_STATE_ROUND_OPEN
    assert find_main_topic(topic_tree, "main-compensation") is not None
    assert find_main_topic(topic_tree, "main-work_mode") is not None
    assert find_main_topic(topic_tree, "main-benefits") is not None
    assert any(topic["id"] == OTHER_MAIN_TOPIC_ID for topic in main_topics)
    assert signing_bonus is not None
    assert signing_bonus["phase_created"] == "NEGOTIATION"
    assert signing_bonus["positions"]["candidate"]["value"] == "5000 EUR"
    assert main_topics[-1]["id"] == OTHER_MAIN_TOPIC_ID


def test_save_company_and_candidate_persist_canonical_topic_tree(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)
    topic_tree = build_topic_tree()

    storage.save_company(
        {
            "job_description": "Structured negotiation",
            "company": {"name": "TechNova Engineering"},
            "topic_tree": topic_tree,
        },
        session_id="structured-session",
    )
    storage.save_candidate(
        {
            "candidate": {"name": "Marco Rinaldi"},
            "topic_tree": topic_tree,
        },
        session_id="structured-session",
    )

    state = storage.load_state("structured-session")
    compensation = find_main_topic(state["topic_tree"], "main-compensation")
    _main_topic, base_salary = find_subtopic(state["topic_tree"], "sub-base-salary")

    assert storage.is_ready(state) is True
    assert compensation is not None
    assert compensation["priorities"] == {"company": 5, "candidate": 4}
    assert base_salary is not None
    assert base_salary["positions"]["company"]["priority"] == 5
    assert base_salary["positions"]["candidate"]["deal_breaker"] is True
    assert state["shared_topic_tree"]["main_topics"][0]["priorities"]["company"] is None


def test_load_party_state_hides_counterparty_private_inputs(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)
    session_id = "private-boundary"
    storage.save_state(build_state(), session_id=session_id)

    company_view = storage.load_party_state("company", session_id)
    candidate_view = storage.load_party_state("candidate", session_id)
    _main_topic, company_base_salary = find_subtopic(company_view["topic_tree"], "sub-base-salary")
    _main_topic, candidate_base_salary = find_subtopic(candidate_view["topic_tree"], "sub-base-salary")

    assert company_base_salary is not None
    assert candidate_base_salary is not None
    assert company_base_salary["positions"]["company"]["value"] == "42000 EUR gross"
    assert company_base_salary["positions"]["candidate"]["value"] == ""
    assert company_base_salary["positions"]["candidate"]["priority"] is None
    assert candidate_base_salary["positions"]["candidate"]["value"] == "48000 EUR gross"
    assert candidate_base_salary["positions"]["company"]["value"] == ""
    assert candidate_base_salary["positions"]["company"]["priority"] is None


def test_save_round_result_appends_immutable_snapshot(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)
    session_id = "snapshot-session"
    storage.save_state(build_state(), session_id=session_id)

    result = {"company": "A1", "candidate": "B1", "summary": "S1"}
    storage.save_round_result("ALIGNMENT", result, session_id=session_id)
    snapshots = storage.load_round_snapshots(session_id)

    assert len(snapshots) == 1
    assert snapshots[0]["phase"] == "ALIGNMENT"
    assert snapshots[0]["workflow"]["status"] == WORKFLOW_STATE_ROUND_REVIEW
    assert snapshots[0]["result"]["summary"] == "S1"
    assert snapshots[0]["results"]["ALIGNMENT"]["summary"] == "S1"
    assert snapshots[0]["topic_tree"]["main_topics"][0]["subtopics"][0]["positions"]["company"]["value"] == "42000 EUR gross"

    current = storage.load_state(session_id)
    current["workflow"]["status"] = WORKFLOW_STATE_ROUND_OPEN
    storage.save_state(current, session_id=session_id)
    storage.update_subtopic(
        "sub-base-salary",
        "company",
        "43000 EUR gross",
        5,
        False,
        "Updated after snapshot.",
        session_id=session_id,
    )

    reloaded_snapshots = storage.load_round_snapshots(session_id)
    assert reloaded_snapshots[0]["topic_tree"]["main_topics"][0]["subtopics"][0]["positions"]["company"]["value"] == "42000 EUR gross"


def test_save_round_result_rerun_preserves_previous_snapshots(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)
    session_id = "snapshot-rerun"
    storage.save_state(build_state(), session_id=session_id)

    storage.save_round_result("ALIGNMENT", {"company": "A1", "candidate": "B1", "summary": "S1"}, session_id=session_id)
    current = storage.load_state(session_id)
    current["workflow"]["status"] = WORKFLOW_STATE_ROUND_OPEN
    storage.save_state(current, session_id=session_id)
    storage.save_round_result("ALIGNMENT", {"company": "A1b", "candidate": "B1b", "summary": "S1b"}, session_id=session_id)

    snapshots = storage.load_round_snapshots(session_id, phase="ALIGNMENT")
    assert len(snapshots) == 2
    assert snapshots[0]["result"]["summary"] == "S1"
    assert snapshots[1]["result"]["summary"] == "S1b"
    assert snapshots[0]["snapshot_id"] != snapshots[1]["snapshot_id"]


def test_add_main_topic_is_only_allowed_during_setup(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)
    session_id = "governance-session"
    storage.save_state(build_state(current_phase="NEGOTIATION"), session_id=session_id)

    try:
        storage.add_main_topic("Late topic", session_id=session_id)
    except ValueError as exc:
        assert "during setup" in str(exc)
    else:
        raise AssertionError("Expected add_main_topic to be blocked after setup.")


def test_add_main_topic_is_blocked_when_template_structure_is_loaded(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)

    try:
        storage.add_main_topic("Extra section", session_id="template-session")
    except ValueError as exc:
        assert "recruiting template" in str(exc).lower()
    else:
        raise AssertionError("Expected template-driven sessions to block new main topics.")


def test_round2_allows_advancing_to_round3_even_with_counterparty_topics_pending(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)
    session_id = "closing-gate"
    storage.save_state(build_state(current_phase="NEGOTIATION"), session_id=session_id)

    storage.add_subtopic(
        "main-compensation",
        "company",
        "Signing bonus",
        "Round 2 incentive",
        "2000 EUR one-off",
        3,
        False,
        "First proposal",
        session_id=session_id,
    )
    storage.save_round_result(
        "NEGOTIATION",
        {"company": "ok", "candidate": "ok", "summary": "ok"},
        session_id=session_id,
    )

    updated_state = storage.advance_phase(session_id=session_id)
    assert updated_state["workflow"]["current_phase"] == "CLOSING"
    assert updated_state["workflow"]["status"] == WORKFLOW_STATE_ROUND_OPEN


def test_advance_phase_requires_round_review_state(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)
    session_id = "advance-guard"
    storage.save_state(build_state(current_phase="NEGOTIATION"), session_id=session_id)

    try:
        storage.advance_phase(session_id=session_id)
    except ValueError as exc:
        assert "round open" in str(exc).lower()
    else:
        raise AssertionError("Expected advance_phase to require a review-ready round.")


def test_round2_counterparty_cannot_fill_new_subtopic_until_round3(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)
    session_id = "round2-lock"
    storage.save_state(build_state(current_phase="NEGOTIATION"), session_id=session_id)

    storage.add_subtopic(
        "main-compensation",
        "company",
        "Signing bonus",
        "Round 2 incentive",
        "2000 EUR one-off",
        3,
        False,
        "First proposal",
        session_id=session_id,
    )

    state = storage.load_state(session_id)
    negotiation_subtopic = next(
        subtopic
        for topic in state["topic_tree"]["main_topics"]
        for subtopic in topic.get("subtopics", [])
        if subtopic.get("phase_created") == "NEGOTIATION"
    )

    try:
        storage.update_subtopic(
            negotiation_subtopic["id"],
            "candidate",
            "5000 EUR one-off",
            4,
            True,
            "Needed to offset notice period.",
            session_id=session_id,
        )
    except ValueError as exc:
        assert "round 3" in str(exc).lower()
    else:
        raise AssertionError("Counterparty should not be able to fill round 2 subtopics yet.")


def test_round3_counterparty_can_fill_round2_subtopic(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)
    session_id = "round3-unlock"
    storage.save_state(build_state(current_phase="NEGOTIATION"), session_id=session_id)

    storage.add_subtopic(
        "main-compensation",
        "company",
        "Signing bonus",
        "Round 2 incentive",
        "2000 EUR one-off",
        3,
        False,
        "First proposal",
        session_id=session_id,
    )

    current = storage.load_state(session_id)
    current["workflow"]["current_phase"] = "CLOSING"
    current["workflow"]["status"] = WORKFLOW_STATE_ROUND_OPEN
    storage.save_state(current, session_id=session_id)

    updated = storage.load_state(session_id)
    negotiation_subtopic = next(
        subtopic
        for topic in updated["topic_tree"]["main_topics"]
        for subtopic in topic.get("subtopics", [])
        if subtopic.get("phase_created") == "NEGOTIATION"
    )

    final_state = storage.update_subtopic(
        negotiation_subtopic["id"],
        "candidate",
        "5000 EUR one-off",
        4,
        True,
        "Needed to offset notice period.",
        session_id=session_id,
    )

    _, stored_subtopic = find_subtopic(final_state["topic_tree"], negotiation_subtopic["id"])
    assert stored_subtopic is not None
    assert stored_subtopic["positions"]["candidate"]["value"] == "5000 EUR one-off"
    assert stored_subtopic["positions"]["candidate"]["priority"] == 4


def test_load_state_recovers_from_corrupt_json(tmp_path, monkeypatch):
    repository = configure_repo(tmp_path, monkeypatch)
    broken_file = repository.session_file("broken-session")
    broken_file.write_text("{not-valid-json", encoding="utf-8")

    state = storage.load_state("broken-session")

    assert state["session_id"] == "broken-session"
    assert state["workflow"]["current_phase"] == "ALIGNMENT"
    assert broken_file.exists()
    assert broken_file.with_suffix(".corrupt.json").exists()


def test_sessions_are_isolated_with_topic_tree_state(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)
    alpha_state = build_state()
    beta_state = build_state()
    alpha_state["job_description"] = "Alpha negotiation"
    alpha_state["company"]["name"] = "Alpha Corp"
    beta_state["job_description"] = "Beta negotiation"
    beta_state["company"]["name"] = "Beta Corp"

    storage.save_state(alpha_state, session_id="alpha-session")
    storage.save_state(beta_state, session_id="beta-session")

    alpha = storage.load_state("alpha-session")
    beta = storage.load_state("beta-session")

    assert alpha["job_description"] == "Alpha negotiation"
    assert beta["job_description"] == "Beta negotiation"
    assert alpha["company"]["name"] == "Alpha Corp"
    assert beta["company"]["name"] == "Beta Corp"


def test_rewind_phase_goes_back_one_round_and_clears_following_results(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)
    session_id = "rewind-session"
    state = build_state(current_phase="CLOSING", status=WORKFLOW_STATE_ROUND_REVIEW)
    state["results"] = {
        "ALIGNMENT": {"company": "a", "candidate": "b", "summary": "s1"},
        "NEGOTIATION": {"company": "c", "candidate": "d", "summary": "s2"},
        "CLOSING": {"company": "e", "candidate": "f", "summary": "s3"},
    }
    storage.save_state(state, session_id=session_id)

    updated = storage.rewind_phase(session_id=session_id)

    assert updated["workflow"]["current_phase"] == "NEGOTIATION"
    assert updated["workflow"]["status"] == WORKFLOW_STATE_ROUND_OPEN
    assert "ALIGNMENT" in updated["results"]
    assert "NEGOTIATION" not in updated["results"]
    assert "CLOSING" not in updated["results"]


def test_rewind_phase_fails_on_first_round(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)
    session_id = "rewind-first"
    storage.save_state(build_state(current_phase="ALIGNMENT"), session_id=session_id)

    try:
        storage.rewind_phase(session_id=session_id)
    except ValueError as exc:
        assert "cannot go back" in str(exc).lower()
    else:
        raise AssertionError("Expected rewind_phase to fail on first round.")





def test_rfi_flow_blocks_advance_until_answered(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)
    session_id = "rfi-flow"
    storage.save_state(build_state(), session_id=session_id)
    storage.save_round_result("ALIGNMENT", {"company": "ok", "candidate": "ok", "summary": "ok"}, session_id=session_id)

    storage.create_rfi(
        "company",
        "candidate",
        "Please clarify notice period flexibility.",
        session_id=session_id,
    )

    try:
        storage.advance_phase(session_id=session_id)
    except ValueError as exc:
        assert "Open RFI for candidate" in str(exc)
    else:
        raise AssertionError("Expected open RFIs to block round advancement.")

    storage.answer_rfi(
        storage.load_rfis(session_id, phase="ALIGNMENT", status="OPEN")[0]["id"],
        "candidate",
        "Notice can be reduced to 30 days.",
        session_id=session_id,
    )

    updated = storage.advance_phase(session_id=session_id)
    assert updated["workflow"]["current_phase"] == "NEGOTIATION"


def test_round2_rfi_requires_counterparty_new_subtopic(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)
    session_id = "rfi-round2-scope"
    storage.save_state(build_state(current_phase="NEGOTIATION"), session_id=session_id)
    storage.add_subtopic(
        "main-compensation",
        "company",
        "Signing bonus",
        "Round 2 incentive",
        "2000 EUR one-off",
        3,
        False,
        "First proposal",
        session_id=session_id,
    )
    storage.save_round_result("NEGOTIATION", {"company": "ok", "candidate": "ok", "summary": "ok"}, session_id=session_id)

    try:
        storage.create_rfi(
            "company",
            "candidate",
            "Please clarify this topic.",
            subtopic_id="sub-base-salary",
            session_id=session_id,
        )
    except ValueError as exc:
        assert "Round 2 RFIs can only reference subtopics introduced in round 2." in str(exc)
    else:
        raise AssertionError("Expected round 2 RFIs to be limited to new counterparty subtopics.")


def test_summary_generated_suggested_rfi_requires_admin_approval(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)
    session_id = "auto-rfi-approval"
    storage.save_state(build_state(), session_id=session_id)
    summary = """
## RFIs or clarifications needed
- [target:candidate] [scope:Base salary] Can the notice period be reduced below 60 days?
""".strip()

    storage.save_round_result(
        "ALIGNMENT",
        {"company": "ok", "candidate": "ok", "summary": summary},
        session_id=session_id,
    )

    state = storage.load_state(session_id)
    suggestions = state.get("suggested_rfis", [])
    assert len(suggestions) == 1
    assert suggestions[0]["status"] == "SUGGESTED"

    approved = storage.approve_suggested_rfi(suggestions[0]["id"], session_id=session_id)
    approved_rfis = [rfi for rfi in approved["rfis"] if rfi["phase"] == "ALIGNMENT"]
    assert len(approved_rfis) == 1
    assert approved_rfis[0]["requested_by"] == "system"

    try:
        storage.advance_phase(session_id=session_id)
    except ValueError as exc:
        assert "Open RFI for candidate" in str(exc)
    else:
        raise AssertionError("Expected approved suggested RFIs to block round advancement.")


def test_summary_generated_suggested_rfi_can_be_dismissed(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)
    session_id = "auto-rfi-dismiss"
    storage.save_state(build_state(), session_id=session_id)
    summary = """
## RFIs or clarifications needed
- [target:candidate] [scope:Base salary] Can the notice period be reduced below 60 days?
""".strip()

    storage.save_round_result(
        "ALIGNMENT",
        {"company": "ok", "candidate": "ok", "summary": summary},
        session_id=session_id,
    )

    suggested_id = storage.load_state(session_id)["suggested_rfis"][0]["id"]
    dismissed_state = storage.dismiss_suggested_rfi(suggested_id, session_id=session_id)

    assert dismissed_state["suggested_rfis"][0]["status"] == "DISMISSED"
    advanced = storage.advance_phase(session_id=session_id)
    assert advanced["workflow"]["current_phase"] == "NEGOTIATION"
