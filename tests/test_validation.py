from core.validation import (
    validate_review_readiness,
    validate_state_basics,
    validate_state_for_round,
    validate_transition,
)
from core.workflow import WORKFLOW_STATE_ROUND_REVIEW
from tests.helpers import build_state, build_topic_tree


def test_validate_state_basics_requires_initial_main_topic_beyond_other():
    state = build_state(topic_tree={"main_topics": []})

    errors = validate_state_basics(state)

    assert "At least one initial main topic is required in addition to 'Other'." in errors


def test_negotiation_round_allows_new_subtopic_with_creator_side_only():
    state = build_state(
        topic_tree=build_topic_tree(include_round2_subtopic=True, round2_creator="candidate"),
        current_phase="NEGOTIATION",
    )

    errors = validate_state_for_round(state, "NEGOTIATION")

    assert errors == []


def test_transition_requires_round_review_state_before_advancing():
    state = build_state(current_phase="NEGOTIATION")

    errors = validate_transition(state)

    assert any("round open" in error.lower() for error in errors)


def test_transition_accepts_review_state_with_saved_result():
    state = build_state(
        current_phase="NEGOTIATION",
        status=WORKFLOW_STATE_ROUND_REVIEW,
        results={"NEGOTIATION": {"company": "ok", "candidate": "ok", "summary": "ok"}},
    )

    errors = validate_transition(state)

    assert errors == []


def test_review_readiness_allows_opening_round3_with_round2_counterparty_topics_pending():
    state = build_state(
        topic_tree=build_topic_tree(include_round2_subtopic=True, round2_creator="candidate"),
        current_phase="NEGOTIATION",
        status=WORKFLOW_STATE_ROUND_REVIEW,
    )
    result = {"company": "ok", "candidate": "ok", "summary": "ok"}

    errors = validate_review_readiness(state, "NEGOTIATION", result)

    assert errors == []


def test_closing_phase_requires_both_sides_to_complete_round2_subtopics():
    state = build_state(
        topic_tree=build_topic_tree(include_round2_subtopic=True, round2_creator="candidate"),
        current_phase="CLOSING",
    )

    errors = validate_state_for_round(state, "CLOSING")

    assert "Subtopic 'Signing bonus' is missing company value." in errors
    assert "Subtopic 'Signing bonus' is missing valid company priority." in errors
