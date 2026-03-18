import os
from copy import deepcopy
from pathlib import Path

from core.privacy import build_party_topic_tree_view, synchronize_privacy_state
from core.repository import (
    FileSessionRepository,
    SessionRepository,
    generate_session_id,
    normalize_session_id,
)
from core.snapshots import append_round_snapshot, get_round_snapshots
from core.topic_tree import (
    OTHER_MAIN_TOPIC_ID,
    build_main_topic,
    build_recruiting_demo_topic_tree,
    build_subtopic,
    find_main_topic,
    find_subtopic,
    get_sorted_main_topics,
    has_locked_template_structure,
    normalize_topic_tree,
    remove_negotiation_subtopics,
    topic_tree_positions_complete,
)
from core.validation import (
    dynamic_topics_complete as validate_dynamic_topics_complete,
    validate_state_basics,
    validate_transition,
)
from core.workflow import (
    PHASES,
    WORKFLOW_EVENT_ADVANCE_PHASE,
    WORKFLOW_STATE_ROUND_OPEN,
    advance_workflow,
    is_round_open,
    mark_round_review,
    normalize_workflow,
    resettable_workflow_state,
    rewind_workflow,
)

DEFAULT_SESSION_ID = "session_001"
DATA_DIR = Path(os.environ.get("NEGOTIATION_DATA_DIR", "data"))
SESSION_FILE = DATA_DIR / f"{DEFAULT_SESSION_ID}.json"

_repository: SessionRepository = FileSessionRepository(DATA_DIR)


def get_current_session_id(session_id: str | None = None) -> str:
    return normalize_session_id(session_id or os.environ.get("NEGOTIATION_SESSION_ID", DEFAULT_SESSION_ID))


def create_session_id(prefix: str = "session") -> str:
    return generate_session_id(prefix=prefix)


def get_session_file_path(session_id: str | None = None) -> Path:
    return _repository.session_file(get_current_session_id(session_id))


def load_state(session_id: str | None = None) -> dict:
    return _repository.load(get_current_session_id(session_id))


def load_party_state(side: str, session_id: str | None = None) -> dict:
    state = load_state(session_id)
    party_state = deepcopy(state)
    party_state["topic_tree"] = build_party_topic_tree_view(state, side)
    party_state["private_inputs"] = {
        side: deepcopy(state.get("private_inputs", {}).get(side, {}))
    }
    return party_state


def load_round_snapshots(session_id: str | None = None, phase: str | None = None) -> list[dict]:
    state = load_state(session_id)
    return get_round_snapshots(state, phase=phase)


def save_state(state: dict, session_id: str | None = None) -> dict:
    resolved_session_id = get_current_session_id(session_id or state.get("session_id"))
    return _repository.save(resolved_session_id, synchronize_privacy_state(state, prefer_topic_tree=True))


def _sync_topic_tree_from_legacy(state: dict) -> None:
    state["topic_tree"] = build_recruiting_demo_topic_tree(
        state.get("company", {}),
        state.get("candidate", {}),
        state.get("priorities", {}),
        state.get("dynamic_topics", []),
    )


def _current_phase(state: dict) -> str:
    return normalize_workflow(state.get("workflow")).get("current_phase", "ALIGNMENT")


def _current_status(state: dict) -> str:
    return normalize_workflow(state.get("workflow")).get("status", WORKFLOW_STATE_ROUND_OPEN)


def _can_manage_initial_structure(state: dict, side: str) -> bool:
    return side == "company" and _current_phase(state) == "ALIGNMENT" and is_round_open(state.get("workflow"))


def _can_add_subtopic(state: dict, side: str) -> bool:
    if not is_round_open(state.get("workflow")):
        return False
    if _current_phase(state) == "ALIGNMENT":
        return side == "company"
    if _current_phase(state) == "NEGOTIATION":
        return side in {"company", "candidate"}
    return False


def _can_edit_subtopic_structure(state: dict, side: str, subtopic: dict) -> bool:
    if not is_round_open(state.get("workflow")):
        return False
    if subtopic.get("created_by") != side:
        return False
    current_phase = _current_phase(state)
    subtopic_phase = subtopic.get("phase_created")
    if current_phase == "ALIGNMENT":
        return side == "company" and subtopic_phase == "ALIGNMENT"
    if current_phase == "NEGOTIATION":
        return subtopic_phase == "NEGOTIATION"
    return False


def _can_edit_subtopic_position(state: dict, side: str, subtopic: dict) -> bool:
    if not is_round_open(state.get("workflow")):
        return False

    current_phase = _current_phase(state)
    subtopic_phase = subtopic.get("phase_created")
    created_by = subtopic.get("created_by")

    if current_phase == "ALIGNMENT":
        return True

    if current_phase == "NEGOTIATION":
        # In round 2, only the creator can fill newly introduced subtopics.
        if subtopic_phase == "NEGOTIATION" and created_by != side:
            return False
        return True

    if current_phase == "CLOSING":
        return True

    return False


def save_company(payload: dict, session_id: str | None = None) -> dict:
    state = load_state(session_id)
    if "job_description" in payload:
        state["job_description"] = payload["job_description"]

    if "company" in payload:
        state["company"] = {
            **state.get("company", {}),
            **payload["company"],
        }

    if "topic_tree" in payload:
        state["topic_tree"] = normalize_topic_tree(payload["topic_tree"])
    else:
        legacy_priorities = payload.get("priorities", {})
        legacy_company_payload = payload.get("company", {})
        legacy_company_keys = {"salary", "smart", "bonus", "car", "benefits"}
        if legacy_priorities or any(key in legacy_company_payload for key in legacy_company_keys):
            state["priorities"] = state.get("priorities", {})
            for key, value in legacy_priorities.items():
                state["priorities"].setdefault(key, {})
                state["priorities"][key]["company"] = value
            _sync_topic_tree_from_legacy(state)

    return save_state(state, session_id)


def save_candidate(payload: dict, session_id: str | None = None) -> dict:
    state = load_state(session_id)
    if "candidate" in payload:
        state["candidate"] = {
            **state.get("candidate", {}),
            **payload["candidate"],
        }

    if "topic_tree" in payload:
        state["topic_tree"] = normalize_topic_tree(payload["topic_tree"])
    else:
        legacy_priorities = payload.get("priorities", {})
        legacy_candidate_payload = payload.get("candidate", {})
        legacy_candidate_keys = {"salary", "smart", "bonus", "car", "benefits"}
        if legacy_priorities or any(key in legacy_candidate_payload for key in legacy_candidate_keys):
            state["priorities"] = state.get("priorities", {})
            for key, value in legacy_priorities.items():
                state["priorities"].setdefault(key, {})
                state["priorities"][key]["candidate"] = value
            _sync_topic_tree_from_legacy(state)

    return save_state(state, session_id)


def is_ready(state: dict) -> bool:
    return not validate_state_basics(state)


def save_round_result(phase: str, result: dict, session_id: str | None = None) -> dict:
    if phase not in PHASES:
        raise ValueError(f"Unknown phase: {phase}")

    state = load_state(session_id)
    state["results"][phase] = result
    state["workflow"] = mark_round_review(state.get("workflow"), phase)
    append_round_snapshot(state, phase, result)
    return save_state(state, session_id)


def advance_phase(session_id: str | None = None) -> dict:
    state = load_state(session_id)
    errors = validate_transition(state, event=WORKFLOW_EVENT_ADVANCE_PHASE)
    if errors:
        raise ValueError("; ".join(errors))

    state["workflow"] = advance_workflow(state.get("workflow"))
    return save_state(state, session_id)


def rewind_phase(session_id: str | None = None) -> dict:
    state = load_state(session_id)
    current = normalize_workflow(state.get("workflow")).get("current_phase")
    if current not in PHASES:
        raise ValueError(f"Unknown phase: {current}")
    current_index = PHASES.index(current)
    state["workflow"] = rewind_workflow(state.get("workflow"))

    # Going back is a test/debug action: clear results from the reopened round onward.
    for phase in PHASES[current_index - 1 :]:
        state.get("results", {}).pop(phase, None)

    return save_state(state, session_id)


def reset_workflow(session_id: str | None = None) -> dict:
    state = load_state(session_id)
    state["workflow"] = resettable_workflow_state()
    state["results"] = {}
    state["round_snapshots"] = []
    state["dynamic_topics"] = []
    state["topic_tree"] = remove_negotiation_subtopics(state.get("topic_tree", {}))
    return save_state(state, session_id)


def add_main_topic(
    title: str,
    description: str = "",
    order: int | None = None,
    session_id: str | None = None,
) -> dict:
    state = load_state(session_id)
    if not _can_manage_initial_structure(state, "company"):
        raise ValueError("Main topics can only be managed by company during setup.")
    if has_locked_template_structure(state.get("topic_tree", {})):
        raise ValueError("Main topics are defined by the recruiting template.")

    topic_tree = normalize_topic_tree(state.get("topic_tree"))
    existing_orders = [topic.get("order", 0) for topic in topic_tree.get("main_topics", []) if not topic.get("is_other")]
    next_order = max(existing_orders, default=-1) + 1 if order is None else int(order)
    topic_tree["main_topics"].append(
        build_main_topic(
            title=title,
            description=description,
            created_by="company",
            phase_created="ALIGNMENT",
            order=next_order,
        )
    )
    state["topic_tree"] = normalize_topic_tree(topic_tree)
    return save_state(state, session_id)


def update_main_topic(
    main_topic_id: str,
    title: str,
    description: str,
    order: int,
    session_id: str | None = None,
) -> dict:
    state = load_state(session_id)
    if not _can_manage_initial_structure(state, "company"):
        raise ValueError("Main topics can only be managed by company during setup.")

    main_topic = find_main_topic(state.get("topic_tree", {}), main_topic_id)
    if main_topic is None or main_topic.get("is_other"):
        raise ValueError("Main topic not found or cannot be edited.")
    if main_topic.get("locked"):
        raise ValueError("Template main topics cannot be edited.")

    main_topic["title"] = title.strip()
    main_topic["description"] = description.strip()
    main_topic["order"] = int(order)
    state["topic_tree"] = normalize_topic_tree(state.get("topic_tree"))
    return save_state(state, session_id)


def delete_main_topic(main_topic_id: str, session_id: str | None = None) -> dict:
    state = load_state(session_id)
    if not _can_manage_initial_structure(state, "company"):
        raise ValueError("Main topics can only be managed by company during setup.")

    main_topic = find_main_topic(state.get("topic_tree", {}), main_topic_id)
    if main_topic is not None and main_topic.get("locked"):
        raise ValueError("Template main topics cannot be deleted.")

    topic_tree = normalize_topic_tree(state.get("topic_tree"))
    topic_tree["main_topics"] = [
        main_topic
        for main_topic in topic_tree.get("main_topics", [])
        if not (main_topic.get("id") == main_topic_id and not main_topic.get("is_other"))
    ]
    state["topic_tree"] = normalize_topic_tree(topic_tree)
    return save_state(state, session_id)


def update_main_topic_priority(
    main_topic_id: str,
    side: str,
    priority: int | None,
    session_id: str | None = None,
) -> dict:
    state = load_state(session_id)
    main_topic = find_main_topic(state.get("topic_tree", {}), main_topic_id)
    if main_topic is None:
        raise ValueError("Main topic not found.")
    main_topic["priorities"][side] = priority
    state["topic_tree"] = normalize_topic_tree(state.get("topic_tree"))
    return save_state(state, session_id)


def add_subtopic(
    main_topic_id: str,
    side: str,
    title: str,
    description: str,
    value: str,
    priority: int | None,
    deal_breaker: bool = False,
    notes: str = "",
    session_id: str | None = None,
) -> dict:
    state = load_state(session_id)
    if not _can_add_subtopic(state, side):
        raise ValueError("Subtopics cannot be added in the current phase.")

    main_topic = find_main_topic(state.get("topic_tree", {}), main_topic_id)
    if main_topic is None:
        raise ValueError("Main topic not found.")

    phase_created = _current_phase(state)
    new_subtopic = build_subtopic(
        main_topic_id=main_topic_id,
        title=title,
        description=description,
        created_by=side,
        phase_created=phase_created,
        positions={
            side: {
                "value": value,
                "priority": priority,
                "deal_breaker": deal_breaker,
                "notes": notes,
            }
        },
    )
    main_topic.setdefault("subtopics", []).append(new_subtopic)
    state["topic_tree"] = normalize_topic_tree(state.get("topic_tree"))
    return save_state(state, session_id)


def update_subtopic(
    subtopic_id: str,
    side: str,
    value: str,
    priority: int | None,
    deal_breaker: bool,
    notes: str,
    title: str | None = None,
    description: str | None = None,
    session_id: str | None = None,
) -> dict:
    state = load_state(session_id)
    main_topic, subtopic = find_subtopic(state.get("topic_tree", {}), subtopic_id)
    if subtopic is None or main_topic is None:
        raise ValueError("Subtopic not found.")
    if not _can_edit_subtopic_position(state, side, subtopic):
        raise ValueError("This subtopic can be completed by your side only in round 3.")

    subtopic["positions"][side]["value"] = str(value or "").strip()
    subtopic["positions"][side]["priority"] = priority
    subtopic["positions"][side]["deal_breaker"] = bool(deal_breaker)
    subtopic["positions"][side]["notes"] = str(notes or "").strip()

    if title is not None or description is not None:
        if not _can_edit_subtopic_structure(state, side, subtopic):
            raise ValueError("Subtopic structure cannot be edited in the current phase.")
        subtopic["title"] = str(title or subtopic.get("title", "")).strip()
        subtopic["description"] = str(description or subtopic.get("description", "")).strip()

    state["topic_tree"] = normalize_topic_tree(state.get("topic_tree"))
    return save_state(state, session_id)


def delete_subtopic(subtopic_id: str, side: str, session_id: str | None = None) -> dict:
    state = load_state(session_id)
    main_topic, subtopic = find_subtopic(state.get("topic_tree", {}), subtopic_id)
    if subtopic is None or main_topic is None:
        raise ValueError("Subtopic not found.")
    if not _can_edit_subtopic_structure(state, side, subtopic):
        raise ValueError("Subtopic cannot be deleted in the current phase.")

    main_topic["subtopics"] = [
        existing_subtopic
        for existing_subtopic in main_topic.get("subtopics", [])
        if existing_subtopic.get("id") != subtopic_id
    ]
    state["topic_tree"] = normalize_topic_tree(state.get("topic_tree"))
    return save_state(state, session_id)


def add_dynamic_topic(
    side: str,
    section: str,
    title: str,
    answer: str,
    session_id: str | None = None,
) -> dict:
    state = load_state(session_id)
    topic_tree = normalize_topic_tree(state.get("topic_tree"))
    target_main_topic_id = OTHER_MAIN_TOPIC_ID
    for main_topic in get_sorted_main_topics(topic_tree):
        if main_topic.get("title", "").lower().startswith(str(section or "").lower()):
            target_main_topic_id = main_topic["id"]
            break
    return add_subtopic(
        main_topic_id=target_main_topic_id,
        side=side,
        title=title,
        description="Migrated legacy dynamic topic.",
        value=answer,
        priority=3,
        deal_breaker=False,
        notes="",
        session_id=session_id,
    )


def update_dynamic_topic_answer(
    topic_id: str,
    side: str,
    answer: str,
    session_id: str | None = None,
) -> dict:
    state = load_state(session_id)
    _main_topic, subtopic = find_subtopic(state.get("topic_tree", {}), topic_id)
    existing_priority = None
    existing_deal_breaker = False
    existing_notes = ""
    if subtopic:
        position = subtopic.get("positions", {}).get(side, {})
        existing_priority = position.get("priority")
        existing_deal_breaker = position.get("deal_breaker", False)
        existing_notes = position.get("notes", "")
    return update_subtopic(
        topic_id,
        side,
        answer,
        existing_priority,
        existing_deal_breaker,
        existing_notes,
        session_id=session_id,
    )


def edit_dynamic_topic(topic_id: str, side: str, section: str, title: str, answer: str, session_id: str | None = None) -> dict:
    state = load_state(session_id)
    main_topic, subtopic = find_subtopic(state.get("topic_tree", {}), topic_id)
    if main_topic is None or subtopic is None:
        raise ValueError("Legacy topic not found.")

    target_main_topic_id = main_topic["id"]
    for topic in get_sorted_main_topics(state.get("topic_tree", {})):
        if topic.get("title", "").lower().startswith(str(section or "").lower()):
            target_main_topic_id = topic["id"]
            break

    if target_main_topic_id != main_topic["id"]:
        main_topic["subtopics"] = [
            existing_subtopic
            for existing_subtopic in main_topic.get("subtopics", [])
            if existing_subtopic.get("id") != topic_id
        ]
        destination_main_topic = find_main_topic(state.get("topic_tree", {}), target_main_topic_id)
        if destination_main_topic is not None:
            subtopic["main_topic_id"] = target_main_topic_id
            destination_main_topic.setdefault("subtopics", []).append(subtopic)

    existing_position = subtopic.get("positions", {}).get(side, {})
    return update_subtopic(
        topic_id,
        side,
        answer,
        existing_position.get("priority"),
        existing_position.get("deal_breaker", False),
        existing_position.get("notes", ""),
        title=title,
        description=subtopic.get("description", ""),
        session_id=session_id,
    )


def delete_dynamic_topic(topic_id: str, side: str, session_id: str | None = None) -> dict:
    return delete_subtopic(topic_id, side, session_id=session_id)


def dynamic_topics_complete(state: dict | None = None, session_id: str | None = None) -> bool:
    resolved_state = state or load_state(session_id)
    topic_tree = resolved_state.get("topic_tree", {})
    if topic_tree:
        return topic_tree_positions_complete(topic_tree)
    return validate_dynamic_topics_complete(resolved_state)
