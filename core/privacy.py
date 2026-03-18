from copy import deepcopy

from core.topic_tree import POSITION_SIDES, VALID_PRIORITY_VALUES, build_position, normalize_topic_tree


def build_empty_private_inputs() -> dict:
    return {
        side: {
            "main_topic_priorities": {},
            "subtopic_positions": {},
        }
        for side in POSITION_SIDES
    }


def normalize_private_inputs(private_inputs: dict | None) -> dict:
    normalized = build_empty_private_inputs()
    private_inputs = private_inputs or {}

    for side in POSITION_SIDES:
        side_inputs = private_inputs.get(side, {})
        for main_topic_id, priority in (side_inputs.get("main_topic_priorities", {}) or {}).items():
            normalized[side]["main_topic_priorities"][str(main_topic_id)] = (
                priority if priority in VALID_PRIORITY_VALUES else None
            )
        for subtopic_id, position in (side_inputs.get("subtopic_positions", {}) or {}).items():
            normalized[side]["subtopic_positions"][str(subtopic_id)] = build_position(**(position or {}))

    return normalized


def extract_shared_topic_tree(topic_tree: dict | None) -> dict:
    shared_tree = normalize_topic_tree(topic_tree)
    for main_topic in shared_tree.get("main_topics", []):
        main_topic["priorities"] = {side: None for side in POSITION_SIDES}
        for subtopic in main_topic.get("subtopics", []):
            subtopic["positions"] = {
                side: build_position()
                for side in POSITION_SIDES
            }
    return shared_tree


def extract_private_inputs(topic_tree: dict | None) -> dict:
    normalized_tree = normalize_topic_tree(topic_tree)
    private_inputs = build_empty_private_inputs()

    for main_topic in normalized_tree.get("main_topics", []):
        for side in POSITION_SIDES:
            private_inputs[side]["main_topic_priorities"][main_topic["id"]] = main_topic.get("priorities", {}).get(side)

        for subtopic in main_topic.get("subtopics", []):
            for side in POSITION_SIDES:
                private_inputs[side]["subtopic_positions"][subtopic["id"]] = build_position(
                    **(subtopic.get("positions", {}).get(side, {}) or {})
                )

    return normalize_private_inputs(private_inputs)


def merge_topic_tree_with_private_inputs(shared_topic_tree: dict | None, private_inputs: dict | None) -> dict:
    merged_tree = normalize_topic_tree(shared_topic_tree)
    normalized_private_inputs = normalize_private_inputs(private_inputs)

    for main_topic in merged_tree.get("main_topics", []):
        for side in POSITION_SIDES:
            main_topic["priorities"][side] = normalized_private_inputs[side]["main_topic_priorities"].get(main_topic["id"])

        for subtopic in main_topic.get("subtopics", []):
            subtopic["positions"] = {
                side: deepcopy(
                    normalized_private_inputs[side]["subtopic_positions"].get(subtopic["id"], build_position())
                )
                for side in POSITION_SIDES
            }

    return merged_tree


def build_party_topic_tree_view(state: dict, side: str) -> dict:
    if side not in POSITION_SIDES:
        raise ValueError(f"Unknown negotiation side: {side}")

    shared_topic_tree = state.get("shared_topic_tree") or extract_shared_topic_tree(state.get("topic_tree"))
    private_inputs = build_empty_private_inputs()
    normalized_private_inputs = normalize_private_inputs(state.get("private_inputs"))
    private_inputs[side] = deepcopy(normalized_private_inputs[side])
    return merge_topic_tree_with_private_inputs(shared_topic_tree, private_inputs)


def synchronize_privacy_state(state: dict, prefer_topic_tree: bool = False) -> dict:
    synchronized = deepcopy(state)
    full_topic_tree = synchronized.get("topic_tree")

    if prefer_topic_tree or (
        synchronized.get("shared_topic_tree") is None and synchronized.get("private_inputs") is None
    ):
        synchronized["topic_tree"] = normalize_topic_tree(full_topic_tree)
        synchronized["shared_topic_tree"] = extract_shared_topic_tree(synchronized["topic_tree"])
        synchronized["private_inputs"] = extract_private_inputs(synchronized["topic_tree"])
    else:
        synchronized["shared_topic_tree"] = normalize_topic_tree(
            synchronized.get("shared_topic_tree") or extract_shared_topic_tree(full_topic_tree)
        )
        synchronized["private_inputs"] = normalize_private_inputs(
            synchronized.get("private_inputs") or extract_private_inputs(full_topic_tree)
        )

    synchronized["topic_tree"] = merge_topic_tree_with_private_inputs(
        synchronized["shared_topic_tree"],
        synchronized["private_inputs"],
    )

    synchronized["results"] = deepcopy(synchronized.get("results", {}))
    synchronized["shared_outputs"] = deepcopy(synchronized.get("shared_outputs", {}))
    if not synchronized["shared_outputs"]:
        synchronized["shared_outputs"] = {"results": deepcopy(synchronized["results"])}
    elif not synchronized["results"]:
        synchronized["results"] = deepcopy(synchronized["shared_outputs"].get("results", {}))
    else:
        synchronized["shared_outputs"]["results"] = deepcopy(synchronized["results"])

    synchronized["shared_outputs"].setdefault("results", deepcopy(synchronized["results"]))
    return synchronized
