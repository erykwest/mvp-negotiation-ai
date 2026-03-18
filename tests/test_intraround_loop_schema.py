from core.intraround_loop import (
    LOOP_ACTION_NEEDS_RFI,
    LOOP_STATUS_DISABLED,
    LOOP_STATUS_RUNNING,
    NEGOTIATION_PHASE,
    attach_loop_artifact,
    build_loop_artifact,
    build_loop_cycle,
    build_loop_turn,
    normalize_loop_artifact,
    normalize_round_result,
)
from core.rfis import build_suggested_rfi


def test_normalize_missing_loop_returns_disabled_negotiation_artifact():
    artifact = normalize_loop_artifact(None)

    assert artifact["enabled"] is False
    assert artifact["phase"] == NEGOTIATION_PHASE
    assert artifact["status"] == LOOP_STATUS_DISABLED
    assert artifact["max_cycles"] == 0
    assert artifact["cycles"] == []
    assert artifact["agreements"] == []
    assert artifact["open_issues"] == []
    assert artifact["suggested_rfis"] == []
    assert artifact["draft_summary"] == ""
    assert artifact["generated_at"]


def test_normalize_loop_artifact_coerces_nested_cycle_payloads():
    suggested_rfi = build_suggested_rfi(
        phase="NEGOTIATION",
        target_side="candidate",
        question="Can the signing bonus be tied to probation completion?",
        subtopic_title="Signing bonus",
    )
    raw = build_loop_artifact(
        enabled=True,
        phase="NEGOTIATION",
        status="running",
        max_cycles="5",
        cycles=[
            {
                "cycle": "2",
                "company_turn": {"prompt": "p", "response": "company turn", "extra": 1},
                "candidate_turn": "candidate turn",
                "analyst_decision": {
                    "action": LOOP_ACTION_NEEDS_RFI,
                    "reason": 123,
                    "agreements": ("salary", "benefits"),
                    "open_issues": {"issue": "notice"},
                    "suggested_rfis": [suggested_rfi],
                },
            }
        ],
        stop_reason=12,
        agreements=("salary",),
        open_issues={"issue": "notice"},
        suggested_rfis=[suggested_rfi],
        draft_summary={"text": "draft"},
        generated_at="2026-03-19T10:00:00+00:00",
    )

    normalized = normalize_loop_artifact(raw)

    assert normalized["enabled"] is True
    assert normalized["status"] == LOOP_STATUS_RUNNING
    assert normalized["max_cycles"] == 5
    assert normalized["cycles"][0]["cycle"] == 2
    assert normalized["cycles"][0]["company_turn"]["response"] == "company turn"
    assert normalized["cycles"][0]["candidate_turn"]["content"] == "candidate turn"
    assert normalized["cycles"][0]["analyst_decision"]["action"] == LOOP_ACTION_NEEDS_RFI
    assert normalized["cycles"][0]["analyst_decision"]["reason"] == "123"
    assert normalized["cycles"][0]["analyst_decision"]["suggested_rfis"][0]["question"] == suggested_rfi["question"]
    assert normalized["agreements"] == ["salary"]
    assert normalized["open_issues"] == []
    assert normalized["suggested_rfis"][0]["target_side"] == "candidate"
    assert normalized["draft_summary"] == "{'text': 'draft'}"
    assert normalized["generated_at"] == "2026-03-19T10:00:00+00:00"


def test_normalize_non_negotiation_loop_disables_execution_and_round_result_stays_backward_compatible():
    raw_loop = {
        "enabled": True,
        "phase": "ALIGNMENT",
        "status": "RUNNING",
        "max_cycles": 4,
        "cycles": [build_loop_cycle(cycle=1, company_turn=build_loop_turn(response="ok"))],
    }

    normalized = normalize_loop_artifact(raw_loop, phase="ALIGNMENT")
    legacy_result = {"company": "ok", "candidate": "ok", "summary": "done"}
    attached_result = attach_loop_artifact(legacy_result, raw_loop, phase="ALIGNMENT")
    normalized_legacy_result = normalize_round_result(legacy_result)

    assert normalized["enabled"] is False
    assert normalized["phase"] == "ALIGNMENT"
    assert normalized["status"] == LOOP_STATUS_DISABLED
    assert normalized["max_cycles"] == 0
    assert normalized["cycles"] == []
    assert "loop" in attached_result
    assert attached_result["loop"]["enabled"] is False
    assert "loop" not in normalized_legacy_result
