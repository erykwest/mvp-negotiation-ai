from copy import deepcopy

from core.privacy import synchronize_privacy_state
from core.snapshots import normalize_round_snapshots
from core.topic_tree import (
    build_recruiting_demo_topic_tree,
    build_topic_tree_from_template,
    legacy_topic_inputs_present,
    normalize_topic_tree,
)

PHASES = ["ALIGNMENT", "NEGOTIATION", "CLOSING"]

PHASE_LABELS = {
    "ALIGNMENT": "ROUND 1 - ALIGNMENT",
    "NEGOTIATION": "ROUND 2 - NEGOTIATION",
    "CLOSING": "ROUND 3 - CLOSING",
}

TOPIC_SECTIONS = ["salary", "smart", "bonus", "car", "benefits", "notes"]

PRIORITY_TOPICS = [
    ("salary", "Compensation"),
    ("smart", "Smart work"),
    ("bonus", "Bonus"),
    ("car", "Car"),
    ("benefits", "Benefits"),
]

WORKFLOW_STATE_ROUND_OPEN = "ROUND_OPEN"
WORKFLOW_STATE_ROUND_REVIEW = "ROUND_REVIEW"
WORKFLOW_STATE_COMPLETED = "COMPLETED"

WORKFLOW_STATES = [
    WORKFLOW_STATE_ROUND_OPEN,
    WORKFLOW_STATE_ROUND_REVIEW,
    WORKFLOW_STATE_COMPLETED,
]

WORKFLOW_STATE_LABELS = {
    WORKFLOW_STATE_ROUND_OPEN: "Round open",
    WORKFLOW_STATE_ROUND_REVIEW: "Round in review",
    WORKFLOW_STATE_COMPLETED: "Workflow completed",
}

LEGACY_WORKFLOW_STATES = {
    "editing": WORKFLOW_STATE_ROUND_OPEN,
    "review": WORKFLOW_STATE_ROUND_REVIEW,
    "closed": WORKFLOW_STATE_COMPLETED,
}

WORKFLOW_EVENT_SAVE_ROUND_RESULT = "SAVE_ROUND_RESULT"
WORKFLOW_EVENT_ADVANCE_PHASE = "ADVANCE_PHASE"
WORKFLOW_EVENT_REWIND_PHASE = "REWIND_PHASE"
WORKFLOW_EVENT_RESET = "RESET_WORKFLOW"

WORKFLOW_EVENT_LABELS = {
    WORKFLOW_EVENT_SAVE_ROUND_RESULT: "save the current round result",
    WORKFLOW_EVENT_ADVANCE_PHASE: "advance to the next round",
    WORKFLOW_EVENT_REWIND_PHASE: "go back one round",
    WORKFLOW_EVENT_RESET: "reset the workflow",
}

WORKFLOW_EVENT_ALLOWED_STATES = {
    WORKFLOW_EVENT_SAVE_ROUND_RESULT: {WORKFLOW_STATE_ROUND_OPEN},
    WORKFLOW_EVENT_ADVANCE_PHASE: {WORKFLOW_STATE_ROUND_REVIEW},
    WORKFLOW_EVENT_REWIND_PHASE: {
        WORKFLOW_STATE_ROUND_OPEN,
        WORKFLOW_STATE_ROUND_REVIEW,
        WORKFLOW_STATE_COMPLETED,
    },
    WORKFLOW_EVENT_RESET: {
        WORKFLOW_STATE_ROUND_OPEN,
        WORKFLOW_STATE_ROUND_REVIEW,
        WORKFLOW_STATE_COMPLETED,
    },
}

DEFAULT_WORKFLOW = {
    "current_phase": "ALIGNMENT",
    "status": WORKFLOW_STATE_ROUND_OPEN,
}


def normalize_workflow_status(status: str | None) -> str:
    raw_status = str(status or DEFAULT_WORKFLOW["status"]).strip()
    if not raw_status:
        return DEFAULT_WORKFLOW["status"]

    normalized = LEGACY_WORKFLOW_STATES.get(raw_status, raw_status)
    if normalized not in WORKFLOW_STATES:
        return DEFAULT_WORKFLOW["status"]
    return normalized


def normalize_workflow(workflow: dict | None) -> dict:
    raw_workflow = deepcopy(workflow or {})
    current_phase = str(raw_workflow.get("current_phase") or DEFAULT_WORKFLOW["current_phase"]).strip()
    if not current_phase:
        current_phase = DEFAULT_WORKFLOW["current_phase"]

    return {
        **raw_workflow,
        "current_phase": current_phase,
        "status": normalize_workflow_status(raw_workflow.get("status")),
    }


def workflow_state_label(status: str | None) -> str:
    normalized = normalize_workflow_status(status)
    return WORKFLOW_STATE_LABELS.get(normalized, normalized)


def is_round_open(workflow: dict | None) -> bool:
    return normalize_workflow(workflow).get("status") == WORKFLOW_STATE_ROUND_OPEN


def is_round_review(workflow: dict | None) -> bool:
    return normalize_workflow(workflow).get("status") == WORKFLOW_STATE_ROUND_REVIEW


def is_workflow_completed(workflow: dict | None) -> bool:
    return normalize_workflow(workflow).get("status") == WORKFLOW_STATE_COMPLETED


def validate_workflow_transition(workflow: dict | None, event: str) -> list[str]:
    normalized_workflow = normalize_workflow(workflow)
    current_phase = normalized_workflow.get("current_phase")
    current_status = normalized_workflow.get("status")
    errors: list[str] = []

    if current_phase not in PHASES:
        errors.append(f"Unknown workflow phase: {current_phase}")
        return errors

    allowed_states = WORKFLOW_EVENT_ALLOWED_STATES.get(event)
    if allowed_states is None:
        errors.append(f"Unknown workflow event: {event}")
        return errors

    if current_status not in allowed_states:
        errors.append(
            f"Cannot {WORKFLOW_EVENT_LABELS[event]} while workflow state is "
            f"'{workflow_state_label(current_status)}'."
        )

    if event == WORKFLOW_EVENT_REWIND_PHASE and current_phase == PHASES[0]:
        errors.append("Already at the first round; cannot go back further.")

    return errors


def mark_round_review(workflow: dict | None, phase: str) -> dict:
    normalized_workflow = normalize_workflow(workflow)
    errors = validate_workflow_transition(normalized_workflow, WORKFLOW_EVENT_SAVE_ROUND_RESULT)
    if errors:
        raise ValueError("; ".join(errors))

    current_phase = normalized_workflow.get("current_phase")
    if phase != current_phase:
        raise ValueError(
            f"Cannot save a result for phase {phase} while workflow is on phase {current_phase}."
        )

    normalized_workflow["status"] = WORKFLOW_STATE_ROUND_REVIEW
    return normalized_workflow


def get_next_phase(current_phase: str) -> str | None:
    if current_phase not in PHASES:
        raise ValueError(f"Unknown workflow phase: {current_phase}")

    current_index = PHASES.index(current_phase)
    if current_index == len(PHASES) - 1:
        return None
    return PHASES[current_index + 1]


def advance_workflow(workflow: dict | None) -> dict:
    normalized_workflow = normalize_workflow(workflow)
    errors = validate_workflow_transition(normalized_workflow, WORKFLOW_EVENT_ADVANCE_PHASE)
    if errors:
        raise ValueError("; ".join(errors))

    next_phase = get_next_phase(normalized_workflow["current_phase"])
    if next_phase is None:
        normalized_workflow["status"] = WORKFLOW_STATE_COMPLETED
    else:
        normalized_workflow["current_phase"] = next_phase
        normalized_workflow["status"] = WORKFLOW_STATE_ROUND_OPEN
    return normalized_workflow


def rewind_workflow(workflow: dict | None) -> dict:
    normalized_workflow = normalize_workflow(workflow)
    errors = validate_workflow_transition(normalized_workflow, WORKFLOW_EVENT_REWIND_PHASE)
    if errors:
        raise ValueError("; ".join(errors))

    current_index = PHASES.index(normalized_workflow["current_phase"])
    normalized_workflow["current_phase"] = PHASES[current_index - 1]
    normalized_workflow["status"] = WORKFLOW_STATE_ROUND_OPEN
    return normalized_workflow


def resettable_workflow_state() -> dict:
    return normalize_workflow(DEFAULT_WORKFLOW)


def build_default_state(session_id: str = "session_001") -> dict:
    return synchronize_privacy_state(
        {
            "session_id": session_id,
            "job_description": "",
            "company": {"name": ""},
            "candidate": {"name": ""},
            "priorities": {},
            "dynamic_topics": [],
            "topic_tree": build_topic_tree_from_template(),
            "workflow": resettable_workflow_state(),
            "results": {},
            "round_snapshots": [],
        }
    )


def merge_state_defaults_without_building_default_state(state: dict | None, session_id: str = "session_001") -> dict:
    state = state or {}

    merged = {
        "session_id": state.get("session_id", session_id),
        "job_description": state.get("job_description", ""),
        "company": dict(state.get("company", {})),
        "candidate": dict(state.get("candidate", {})),
        "priorities": deepcopy(state.get("priorities", {})),
        "dynamic_topics": deepcopy(state.get("dynamic_topics", [])),
        "workflow": normalize_workflow(state.get("workflow")),
        "results": deepcopy(state.get("results", {})),
        "round_snapshots": normalize_round_snapshots(state.get("round_snapshots")),
        "shared_topic_tree": deepcopy(state.get("shared_topic_tree")),
        "private_inputs": deepcopy(state.get("private_inputs")),
        "shared_outputs": deepcopy(state.get("shared_outputs", {})),
    }

    raw_topic_tree = state.get("topic_tree")
    prefer_topic_tree = raw_topic_tree is not None
    if raw_topic_tree:
        merged["topic_tree"] = normalize_topic_tree(raw_topic_tree)
    elif legacy_topic_inputs_present(
        merged["company"],
        merged["candidate"],
        merged["priorities"],
        merged["dynamic_topics"],
    ):
        merged["topic_tree"] = build_recruiting_demo_topic_tree(
            merged["company"],
            merged["candidate"],
            merged["priorities"],
            merged["dynamic_topics"],
        )
    else:
        merged["topic_tree"] = build_topic_tree_from_template()

    return synchronize_privacy_state(merged, prefer_topic_tree=prefer_topic_tree)


def merge_state_defaults(state: dict | None, session_id: str = "session_001") -> dict:
    return merge_state_defaults_without_building_default_state(state, session_id=session_id)
