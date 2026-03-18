from copy import deepcopy

from core.topic_tree import build_empty_topic_tree, build_recruiting_demo_topic_tree, normalize_topic_tree

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

DEFAULT_WORKFLOW = {
    "current_phase": "ALIGNMENT",
    "status": "editing",  # editing | review | closed
}


def build_default_state(session_id: str = "session_001") -> dict:
    return {
        "session_id": session_id,
        "job_description": "",
        "company": {"name": ""},
        "candidate": {"name": ""},
        "priorities": {},
        "dynamic_topics": [],
        "topic_tree": build_empty_topic_tree(),
        "workflow": deepcopy(DEFAULT_WORKFLOW),
        "results": {},
    }


def merge_state_defaults(state: dict | None, session_id: str = "session_001") -> dict:
    merged = build_default_state(session_id=session_id)
    state = state or {}

    merged["session_id"] = state.get("session_id", session_id)
    merged["job_description"] = state.get("job_description", "")
    merged["company"] = dict(state.get("company", {}))
    merged["candidate"] = dict(state.get("candidate", {}))
    merged["priorities"] = deepcopy(state.get("priorities", {}))
    merged["dynamic_topics"] = deepcopy(state.get("dynamic_topics", []))
    raw_topic_tree = state.get("topic_tree")
    if raw_topic_tree:
        merged["topic_tree"] = normalize_topic_tree(raw_topic_tree)
    else:
        merged["topic_tree"] = build_recruiting_demo_topic_tree(
            merged["company"],
            merged["candidate"],
            merged["priorities"],
            merged["dynamic_topics"],
        )
    merged["workflow"] = {
        **DEFAULT_WORKFLOW,
        **deepcopy(state.get("workflow", {})),
    }
    merged["results"] = deepcopy(state.get("results", {}))
    return merged


def get_next_phase(current_phase: str) -> str | None:
    if current_phase not in PHASES:
        raise ValueError(f"Unknown workflow phase: {current_phase}")

    current_index = PHASES.index(current_phase)
    if current_index == len(PHASES) - 1:
        return None
    return PHASES[current_index + 1]


def resettable_workflow_state() -> dict:
    return deepcopy(DEFAULT_WORKFLOW)
