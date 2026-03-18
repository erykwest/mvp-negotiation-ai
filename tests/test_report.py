from core.report import build_report
from tests.helpers import build_state, build_topic_tree


def test_build_report_includes_topic_hierarchy_and_round2_subtopics():
    state = build_state(
        topic_tree=build_topic_tree(include_round2_subtopic=True, round2_creator="candidate"),
        current_phase="CLOSING",
        status="review",
    )
    state["round_snapshots"] = [
        {
            "snapshot_id": "snap-report-1",
            "sequence": 1,
            "phase": "NEGOTIATION",
            "captured_at": "2026-03-18T12:00:00+00:00",
        }
    ]
    results = {
        "ALIGNMENT": {"company": "A1", "candidate": "B1", "summary": "S1"},
        "NEGOTIATION": {"company": "A2", "candidate": "B2", "summary": "S2"},
    }

    report = build_report(state, results)

    assert "# Negotiation Report" in report
    assert "Session: `test-session`" in report
    assert "## Topic structure" in report
    assert "### Compensation" in report
    assert "Private priorities, deal breakers, and notes" in report
    assert "Subtopic: Signing bonus" in report
    assert "Phase created: NEGOTIATION" in report
    assert "Main topic priority - company: 5/5" not in report
    assert "Company notes" not in report
    assert "ROUND 2 - NEGOTIATION" in report
    assert "Snapshot captured: `2026-03-18T12:00:00+00:00`" in report

def test_build_report_includes_answered_rfis():
    state = build_state(current_phase="NEGOTIATION", status="review")
    state["rfis"] = [
        {
            "id": "rfi-1",
            "phase": "ALIGNMENT",
            "status": "ANSWERED",
            "requested_by": "candidate",
            "target_side": "company",
            "question": "Can the salary review happen after 6 months?",
            "response": "Yes, if objectives are met.",
            "subtopic_id": "sub-base-salary",
            "subtopic_title": "Base salary",
            "created_at": "2026-03-18T11:00:00+00:00",
            "answered_at": "2026-03-18T11:15:00+00:00",
        }
    ]
    results = {
        "ALIGNMENT": {"company": "A1", "candidate": "B1", "summary": "S1"},
    }

    report = build_report(state, results)

    assert "RFIs and clarifications" in report
    assert "Can the salary review happen after 6 months?" in report
    assert "Response: Yes, if objectives are met." in report
