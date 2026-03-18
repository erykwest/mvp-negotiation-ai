import core.storage as storage
from core.intraround_loop import build_loop_artifact, build_loop_cycle
from core.llm_client import BaseLLMClient, LLMRequest
from core.negotiation import run_single_round
from core.repository import FileSessionRepository
from core.report import build_report
from core.storage import (
    add_subtopic,
    advance_phase,
    load_party_state,
    load_round_snapshots,
    load_state,
    reset_workflow,
    rewind_phase,
    save_candidate,
    save_company,
    save_round_result,
    update_main_topic_priority,
    update_subtopic,
)
from core.topic_tree import find_main_topic, find_subtopic
from core.workflow import WORKFLOW_STATE_ROUND_REVIEW
from tests.helpers import build_topic_tree
from ui_helpers import build_negotiation_loop_summary


class SequencedClient(BaseLLMClient):
    def __init__(self):
        self.counter = 0

    def complete(self, request: LLMRequest) -> str:
        self.counter += 1
        return f"mock-response-{self.counter}"


def _build_negotiation_loop() -> dict:
    return build_loop_artifact(
        enabled=True,
        phase="NEGOTIATION",
        status="COMPLETED",
        max_cycles=2,
        cycles=[
            build_loop_cycle(
                cycle=1,
                company_turn={
                    "summary": "Company keeps base salary firm but opens to a one-off bonus.",
                    "prompt": "company raw prompt should stay hidden",
                    "response": "company raw response should stay hidden",
                },
                candidate_turn={
                    "summary": "Candidate keeps remote policy and asks for a signing bonus.",
                    "prompt": "candidate raw prompt should stay hidden",
                    "response": "candidate raw response should stay hidden",
                },
                analyst_decision={
                    "reason": "Continue to a second cycle; the gap is narrowing.",
                },
            ),
            build_loop_cycle(
                cycle=2,
                company_turn={
                    "summary": "Company accepts the signing bonus discussion.",
                },
                candidate_turn={
                    "summary": "Candidate accepts the revised package structure.",
                },
                analyst_decision={
                    "reason": "Stop: sufficient convergence reached for the round.",
                },
            ),
        ],
        stop_reason="Agreement reached in the intra-round loop.",
        draft_summary="The negotiation converged on compensation and a signing bonus.",
    )


def _prepare_loop_session(tmp_path, monkeypatch) -> str:
    monkeypatch.setattr(storage, "_repository", FileSessionRepository(tmp_path))
    session_id = "intraround-loop"
    client = SequencedClient()
    topic_tree = build_topic_tree()

    save_company(
        {
            "job_description": "Senior BIM coordinator role",
            "company": {"name": "TechNova Engineering"},
            "topic_tree": topic_tree,
        },
        session_id=session_id,
    )
    save_candidate(
        {
            "candidate": {"name": "Marco Rinaldi"},
            "topic_tree": topic_tree,
        },
        session_id=session_id,
    )

    state = load_state(session_id)
    compensation = find_main_topic(state["topic_tree"], "main-compensation")
    if compensation is None:
        compensation = next(topic for topic in state["topic_tree"]["main_topics"] if not topic.get("is_other"))
    compensation_id = compensation["id"]

    update_main_topic_priority(compensation_id, "company", 5, session_id=session_id)
    update_main_topic_priority(compensation_id, "candidate", 4, session_id=session_id)

    state = load_state(session_id)
    _main_topic, base_salary = find_subtopic(state["topic_tree"], "sub-base-salary")
    if base_salary is None:
        _main_topic, base_salary = find_subtopic(
            state["topic_tree"], state["topic_tree"]["main_topics"][0]["subtopics"][0]["id"]
        )

    update_subtopic(
        base_salary["id"],
        "candidate",
        "48000 EUR gross",
        5,
        True,
        "Below this range the move is not viable.",
        session_id=session_id,
    )

    alignment_state = load_state(session_id)
    alignment = run_single_round(alignment_state, "ALIGNMENT", client=client)
    save_round_result("ALIGNMENT", alignment, session_id=session_id)
    advance_phase(session_id=session_id)

    add_subtopic(
        compensation_id,
        "candidate",
        "Signing bonus",
        "One-off incentive discussed in round 2.",
        "5000 EUR one-off",
        4,
        True,
        "Needed to offset notice period.",
        session_id=session_id,
    )

    negotiation_state = load_state(session_id)
    negotiation = run_single_round(negotiation_state, "NEGOTIATION", client=client)
    negotiation["loop"] = _build_negotiation_loop()
    save_round_result("NEGOTIATION", negotiation, session_id=session_id)
    advance_phase(session_id=session_id)

    return session_id


def test_negotiation_loop_is_visible_to_party_views_and_flow_continues(tmp_path, monkeypatch):
    session_id = _prepare_loop_session(tmp_path, monkeypatch)

    company_summary = build_negotiation_loop_summary(load_party_state("company", session_id))
    candidate_summary = build_negotiation_loop_summary(load_party_state("candidate", session_id))

    assert company_summary == candidate_summary
    assert company_summary is not None
    assert "### Intra-round loop" in company_summary
    assert "#### Transcript summary (cycle 2)" in company_summary
    assert "Company accepts the signing bonus discussion." in company_summary
    assert "Candidate accepts the revised package structure." in company_summary
    assert "company raw response should stay hidden" not in company_summary
    assert "candidate raw response should stay hidden" not in company_summary
    assert "company raw prompt should stay hidden" not in company_summary
    assert "candidate raw prompt should stay hidden" not in company_summary

    # Round 2 can close even if the counterparty has not completed newly added subtopics yet.
    current_state = load_state(session_id)
    negotiation_subtopic = next(
        subtopic
        for topic in current_state["topic_tree"]["main_topics"]
        for subtopic in topic.get("subtopics", [])
        if subtopic.get("phase_created") == "NEGOTIATION"
    )
    update_subtopic(
        negotiation_subtopic["id"],
        "company",
        "2000 EUR one-off",
        3,
        False,
        "Possible if base salary stays flat.",
        session_id=session_id,
    )

    closing_state = load_state(session_id)
    closing = run_single_round(closing_state, "CLOSING", client=SequencedClient())
    save_round_result("CLOSING", closing, session_id=session_id)

    final_state = load_state(session_id)
    report = build_report(final_state, final_state["results"])

    assert final_state["workflow"]["current_phase"] == "CLOSING"
    assert final_state["workflow"]["status"] == WORKFLOW_STATE_ROUND_REVIEW
    assert set(final_state["results"].keys()) == {"ALIGNMENT", "NEGOTIATION", "CLOSING"}
    assert final_state["results"]["NEGOTIATION"]["loop"]["status"] == "COMPLETED"
    assert len(final_state["round_snapshots"]) == 3
    assert "mock-response-9" in report
    assert "Signing bonus" in report
    assert "Private priorities, deal breakers, and notes" in report
    assert "Snapshot captured:" in report
    assert "Main topic priority - company: 5/5" not in report


def test_negotiation_loop_is_removed_after_rewind_and_reset(tmp_path, monkeypatch):
    session_id = _prepare_loop_session(tmp_path, monkeypatch)

    pre_rewind_state = load_state(session_id)
    assert build_negotiation_loop_summary(load_party_state("company", session_id)) is not None
    assert pre_rewind_state["results"]["NEGOTIATION"]["loop"]["status"] == "COMPLETED"

    rewind_phase(session_id=session_id)
    rewound_state = load_state(session_id)

    assert rewound_state["workflow"]["current_phase"] == "NEGOTIATION"
    assert "NEGOTIATION" not in rewound_state["results"]
    assert build_negotiation_loop_summary(load_party_state("company", session_id)) is None

    reset_workflow(session_id=session_id)
    reset_state = load_state(session_id)

    assert reset_state["workflow"]["current_phase"] == "ALIGNMENT"
    assert reset_state["results"] == {}
    assert load_round_snapshots(session_id) == []
    assert build_negotiation_loop_summary(load_party_state("company", session_id)) is None
