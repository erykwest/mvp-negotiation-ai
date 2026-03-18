from core.llm_client import is_llm_error
from core.intraround_loop import NEGOTIATION_PHASE
from core.rfis import get_rfis
from core.topic_tree import (
    OTHER_MAIN_TOPIC_ID,
    POSITION_SIDES,
    VALID_PRIORITY_VALUES,
    has_non_other_topics,
    main_topic_requires_priority,
    normalize_topic_tree,
    topic_tree_positions_complete,
)
from core.workflow import (
    PHASES,
    WORKFLOW_EVENT_ADVANCE_PHASE,
    normalize_workflow,
    validate_workflow_transition,
)


def dynamic_topics_complete(state: dict) -> bool:
    return topic_tree_positions_complete(normalize_topic_tree(state.get("topic_tree")))


def _validate_topic_tree_structure(state: dict) -> list[str]:
    errors: list[str] = []
    topic_tree = normalize_topic_tree(state.get("topic_tree"))
    main_topics = topic_tree.get("main_topics", [])

    if not any(main_topic.get("id") == OTHER_MAIN_TOPIC_ID and main_topic.get("is_other") for main_topic in main_topics):
        errors.append("The topic tree must include the hardcoded 'Other' main topic.")

    if not has_non_other_topics(topic_tree):
        errors.append("At least one initial main topic is required in addition to 'Other'.")

    for main_topic in main_topics:
        title = main_topic.get("title", "").strip() or "Untitled main topic"
        if not main_topic.get("is_other") and main_topic.get("phase_created") != "ALIGNMENT":
            errors.append(f"Main topic '{title}' must be created during setup.")
        if not main_topic.get("is_other") and main_topic.get("created_by") != "company":
            errors.append(f"Main topic '{title}' must be created by company.")
        if not main_topic.get("is_other") and not main_topic.get("subtopics"):
            errors.append(f"Main topic '{title}' must contain at least one subtopic.")

        if main_topic_requires_priority(main_topic):
            for side in POSITION_SIDES:
                if main_topic.get("priorities", {}).get(side) not in VALID_PRIORITY_VALUES:
                    errors.append(f"Main topic '{title}' is missing a valid {side} priority.")

        for subtopic in main_topic.get("subtopics", []):
            subtopic_title = subtopic.get("title", "").strip() or "Untitled subtopic"
            if subtopic.get("phase_created") not in {"ALIGNMENT", "NEGOTIATION"}:
                errors.append(f"Subtopic '{subtopic_title}' has an invalid creation phase.")

    return errors


def _subtopic_requires_completion(subtopic: dict, phase: str) -> bool:
    created_in = subtopic.get("phase_created")
    if created_in == "ALIGNMENT":
        return True
    if created_in == "NEGOTIATION":
        return phase == "CLOSING"
    return True


def _validate_subtopic_positions_for_phase(state: dict, phase: str) -> list[str]:
    errors: list[str] = []
    topic_tree = normalize_topic_tree(state.get("topic_tree"))
    for main_topic in topic_tree.get("main_topics", []):
        for subtopic in main_topic.get("subtopics", []):
            subtopic_title = subtopic.get("title", "").strip() or "Untitled subtopic"
            creator = subtopic.get("created_by")
            requires_full_completion = _subtopic_requires_completion(subtopic, phase)

            for side in POSITION_SIDES:
                position = subtopic.get("positions", {}).get(side, {})
                has_value = bool(str(position.get("value", "")).strip())
                has_priority = position.get("priority") in VALID_PRIORITY_VALUES

                if requires_full_completion:
                    if not has_value:
                        errors.append(f"Subtopic '{subtopic_title}' is missing {side} value.")
                    if not has_priority:
                        errors.append(f"Subtopic '{subtopic_title}' is missing valid {side} priority.")
                elif side == creator:
                    if not has_value:
                        errors.append(f"Subtopic '{subtopic_title}' is missing {side} value.")
                    if not has_priority:
                        errors.append(f"Subtopic '{subtopic_title}' is missing valid {side} priority.")
    return errors


def validate_state_basics(state: dict) -> list[str]:
    errors: list[str] = []

    if not state.get("job_description", "").strip():
        errors.append("Job description is required.")

    if not str(state.get("company", {}).get("name", "")).strip():
        errors.append("Company name is required.")

    if not str(state.get("candidate", {}).get("name", "")).strip():
        errors.append("Candidate name is required.")

    errors.extend(_validate_topic_tree_structure(state))
    return errors


def validate_state_for_round(state: dict, phase: str) -> list[str]:
    if phase not in PHASES:
        return [f"Unknown phase: {phase}"]

    errors = validate_state_basics(state)
    errors.extend(_validate_subtopic_positions_for_phase(state, phase))
    return errors


def validate_transition(state: dict, event: str = WORKFLOW_EVENT_ADVANCE_PHASE) -> list[str]:
    errors = validate_state_basics(state)
    workflow = normalize_workflow(state.get("workflow"))
    errors.extend(validate_workflow_transition(workflow, event))

    if errors:
        return errors

    if event == WORKFLOW_EVENT_ADVANCE_PHASE:
        current_phase = workflow.get("current_phase", "")
        current_result = state.get("results", {}).get(current_phase)
        errors.extend(validate_review_readiness(state, current_phase, current_result))

    return errors


def validate_review_readiness(state: dict, phase: str, result: dict | None) -> list[str]:
    errors: list[str] = []

    if not result:
        errors.append(f"No saved result found for phase {phase}.")
        return errors

    for field in ("company", "candidate", "summary"):
        value = result.get(field, "")
        if is_llm_error(value):
            errors.append(f"{field.title()} response failed and must be rerun before continuing.")

    unresolved_rfis = get_rfis(state, phase=phase, status="OPEN")
    for rfi in unresolved_rfis:
        target_side = rfi.get("target_side", "-")
        question = rfi.get("question", "").strip() or "Untitled RFI"
        errors.append(f"Open RFI for {target_side}: {question}")

    errors.extend(validate_intraround_loop(result.get("loop"), phase))

    return errors


def validate_intraround_loop(loop: object, phase: str) -> list[str]:
    if phase != NEGOTIATION_PHASE or loop is None:
        return []

    if not isinstance(loop, dict):
        return ["NEGOTIATION result contains a malformed intra-round loop artifact."]

    errors: list[str] = []
    for field in ("status", "stop_reason"):
        value = loop.get(field)
        if value is not None and not isinstance(value, str):
            errors.append(f"NEGOTIATION loop artifact field '{field}' must be a string.")

    for field in ("agreements", "open_issues", "suggested_rfis", "cycles"):
        value = loop.get(field)
        if value is not None and not isinstance(value, list):
            errors.append(f"NEGOTIATION loop artifact field '{field}' must be a list.")

    return errors


def validate_report_inputs(state: dict, results: dict) -> list[str]:
    errors = validate_state_basics(state)

    if not results:
        errors.append("At least one round result is required to build a report.")

    for phase, result in results.items():
        if phase not in PHASES:
            errors.append(f"Unknown report phase: {phase}")
            continue

        for field in ("company", "candidate", "summary"):
            if not str(result.get(field, "")).strip():
                errors.append(f"Report result for {phase} is missing '{field}'.")
            elif is_llm_error(result.get(field, "")):
                errors.append(f"Report result for {phase} contains an LLM failure in '{field}'.")

        errors.extend(validate_intraround_loop(result.get("loop"), phase))

    return errors
