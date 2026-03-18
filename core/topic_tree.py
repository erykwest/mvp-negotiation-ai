from copy import deepcopy
from uuid import uuid4

OTHER_MAIN_TOPIC_ID = "main-other"
OTHER_MAIN_TOPIC_TITLE = "Other"
POSITION_SIDES = ("company", "candidate")
VALID_PRIORITY_VALUES = {1, 2, 3, 4, 5}

LEGACY_TOPIC_PRESET = [
    ("salary", "Compensation", "Compensation and salary terms"),
    ("smart", "Smart work", "Remote and hybrid work expectations"),
    ("bonus", "Bonus", "Variable compensation and incentives"),
    ("car", "Car", "Company car or mobility support"),
    ("benefits", "Benefits", "Additional benefits and perks"),
]


def build_position(
    value: str = "",
    priority: int | None = None,
    deal_breaker: bool = False,
    notes: str = "",
) -> dict:
    return {
        "value": str(value or "").strip(),
        "priority": priority if priority in VALID_PRIORITY_VALUES else None,
        "deal_breaker": bool(deal_breaker),
        "notes": str(notes or "").strip(),
    }


def build_main_topic(
    title: str,
    description: str = "",
    created_by: str = "company",
    phase_created: str = "ALIGNMENT",
    order: int = 0,
    is_other: bool = False,
    main_topic_id: str | None = None,
    priorities: dict | None = None,
    subtopics: list | None = None,
) -> dict:
    topic_priorities = priorities or {}
    return {
        "id": main_topic_id or f"main-{uuid4().hex[:8]}",
        "title": title.strip(),
        "description": description.strip(),
        "created_by": created_by,
        "phase_created": phase_created,
        "order": int(order),
        "is_other": bool(is_other),
        "priorities": {
            "company": topic_priorities.get("company") if topic_priorities.get("company") in VALID_PRIORITY_VALUES else None,
            "candidate": topic_priorities.get("candidate") if topic_priorities.get("candidate") in VALID_PRIORITY_VALUES else None,
        },
        "subtopics": deepcopy(subtopics or []),
    }


def build_subtopic(
    main_topic_id: str,
    title: str,
    description: str = "",
    created_by: str = "company",
    phase_created: str = "ALIGNMENT",
    status: str = "active",
    positions: dict | None = None,
    subtopic_id: str | None = None,
) -> dict:
    incoming_positions = positions or {}
    return {
        "id": subtopic_id or f"sub-{uuid4().hex[:8]}",
        "main_topic_id": main_topic_id,
        "title": title.strip(),
        "description": description.strip(),
        "created_by": created_by,
        "phase_created": phase_created,
        "status": status,
        "positions": {
            "company": build_position(**incoming_positions.get("company", {})),
            "candidate": build_position(**incoming_positions.get("candidate", {})),
        },
    }


def build_other_main_topic(order: int = 9999) -> dict:
    return build_main_topic(
        title=OTHER_MAIN_TOPIC_TITLE,
        description="Catch-all category for new subtopics that do not fit existing main topics.",
        created_by="system",
        phase_created="ALIGNMENT",
        order=order,
        is_other=True,
        main_topic_id=OTHER_MAIN_TOPIC_ID,
        priorities={"company": None, "candidate": None},
        subtopics=[],
    )


def build_empty_topic_tree() -> dict:
    return {"main_topics": [build_other_main_topic()]}


def normalize_topic_tree(topic_tree: dict | None) -> dict:
    if not topic_tree or not isinstance(topic_tree, dict):
        return build_empty_topic_tree()

    normalized_topics = []
    for main_topic in topic_tree.get("main_topics", []):
        raw_subtopics = main_topic.get("subtopics", [])
        topic = build_main_topic(
            title=main_topic.get("title", ""),
            description=main_topic.get("description", ""),
            created_by=main_topic.get("created_by", "company"),
            phase_created=main_topic.get("phase_created", "ALIGNMENT"),
            order=main_topic.get("order", 0),
            is_other=main_topic.get("is_other", False),
            main_topic_id=main_topic.get("id"),
            priorities=main_topic.get("priorities", {}),
            subtopics=[],
        )
        topic["subtopics"] = [
            build_subtopic(
                main_topic_id=topic["id"],
                title=subtopic.get("title", ""),
                description=subtopic.get("description", ""),
                created_by=subtopic.get("created_by", "company"),
                phase_created=subtopic.get("phase_created", "ALIGNMENT"),
                status=subtopic.get("status", "active"),
                positions=subtopic.get("positions", {}),
                subtopic_id=subtopic.get("id"),
            )
            for subtopic in raw_subtopics
        ]
        normalized_topics.append(topic)

    normalized_tree = {"main_topics": normalized_topics}
    return ensure_other_main_topic(normalized_tree)


def ensure_other_main_topic(topic_tree: dict) -> dict:
    normalized_topics = deepcopy(topic_tree.get("main_topics", []))
    other_topic = None
    for topic in normalized_topics:
        if topic.get("id") == OTHER_MAIN_TOPIC_ID or topic.get("is_other"):
            other_topic = topic
            break

    if other_topic is None:
        max_order = max([topic.get("order", 0) for topic in normalized_topics], default=0)
        normalized_topics.append(build_other_main_topic(order=max_order + 1))
    else:
        other_topic["id"] = OTHER_MAIN_TOPIC_ID
        other_topic["title"] = OTHER_MAIN_TOPIC_TITLE
        other_topic["is_other"] = True

    normalized_topics.sort(key=_main_topic_sort_key)
    return {"main_topics": normalized_topics}


def _main_topic_sort_key(main_topic: dict) -> tuple[int, int, str]:
    return (
        1 if main_topic.get("is_other") else 0,
        int(main_topic.get("order", 0)),
        main_topic.get("title", "").lower(),
    )


def get_sorted_main_topics(topic_tree: dict) -> list[dict]:
    return sorted(topic_tree.get("main_topics", []), key=_main_topic_sort_key)


def find_main_topic(topic_tree: dict, main_topic_id: str) -> dict | None:
    for main_topic in topic_tree.get("main_topics", []):
        if main_topic.get("id") == main_topic_id:
            return main_topic
    return None


def find_subtopic(topic_tree: dict, subtopic_id: str) -> tuple[dict | None, dict | None]:
    for main_topic in topic_tree.get("main_topics", []):
        for subtopic in main_topic.get("subtopics", []):
            if subtopic.get("id") == subtopic_id:
                return main_topic, subtopic
    return None, None


def has_non_other_topics(topic_tree: dict) -> bool:
    return any(not main_topic.get("is_other") for main_topic in topic_tree.get("main_topics", []))


def main_topic_requires_priority(main_topic: dict) -> bool:
    return bool(main_topic.get("subtopics"))


def topic_tree_positions_complete(topic_tree: dict) -> bool:
    for main_topic in topic_tree.get("main_topics", []):
        for subtopic in main_topic.get("subtopics", []):
            for side in POSITION_SIDES:
                position = subtopic.get("positions", {}).get(side, {})
                if not str(position.get("value", "")).strip():
                    return False
                if position.get("priority") not in VALID_PRIORITY_VALUES:
                    return False
    return True


def remove_negotiation_subtopics(topic_tree: dict) -> dict:
    updated_tree = normalize_topic_tree(topic_tree)
    for main_topic in updated_tree.get("main_topics", []):
        main_topic["subtopics"] = [
            subtopic
            for subtopic in main_topic.get("subtopics", [])
            if subtopic.get("phase_created") != "NEGOTIATION"
        ]
    return ensure_other_main_topic(updated_tree)


def build_recruiting_demo_topic_tree(
    company: dict | None,
    candidate: dict | None,
    priorities: dict | None,
    dynamic_topics: list | None,
) -> dict:
    company = company or {}
    candidate = candidate or {}
    priorities = priorities or {}
    dynamic_topics = dynamic_topics or []

    topic_tree = build_empty_topic_tree()
    main_topics = []
    for order, (key, title, description) in enumerate(LEGACY_TOPIC_PRESET):
        company_value = str(company.get(key, "")).strip()
        candidate_value = str(candidate.get(key, "")).strip()
        company_priority = priorities.get(key, {}).get("company")
        candidate_priority = priorities.get(key, {}).get("candidate")

        if not any([company_value, candidate_value, company_priority, candidate_priority]):
            continue

        main_topic_id = f"main-demo-{key}"
        subtopic = build_subtopic(
            main_topic_id=main_topic_id,
            title=f"{title} baseline",
            description="Migrated from the legacy recruiting preset.",
            created_by="company",
            phase_created="ALIGNMENT",
            subtopic_id=f"sub-demo-{key}",
            positions={
                "company": {
                    "value": company_value,
                    "priority": company_priority,
                    "deal_breaker": False,
                    "notes": "",
                },
                "candidate": {
                    "value": candidate_value,
                    "priority": candidate_priority,
                    "deal_breaker": False,
                    "notes": "",
                },
            },
        )
        main_topics.append(
            build_main_topic(
                title=title,
                description=description,
                created_by="company",
                phase_created="ALIGNMENT",
                order=order,
                is_other=False,
                main_topic_id=main_topic_id,
                priorities={
                    "company": company_priority,
                    "candidate": candidate_priority,
                },
                subtopics=[subtopic],
            )
        )

    topic_tree["main_topics"] = main_topics + topic_tree["main_topics"]
    topic_tree = ensure_other_main_topic(topic_tree)

    for legacy_topic in dynamic_topics:
        target_main_topic_id = f"main-demo-{legacy_topic.get('section', '')}"
        if find_main_topic(topic_tree, target_main_topic_id) is None:
            target_main_topic_id = OTHER_MAIN_TOPIC_ID

        company_answer = str(legacy_topic.get("company_answer", "")).strip()
        candidate_answer = str(legacy_topic.get("candidate_answer", "")).strip()
        positions = {
            "company": {
                "value": company_answer,
                "priority": 3 if company_answer else None,
                "deal_breaker": False,
                "notes": "",
            },
            "candidate": {
                "value": candidate_answer,
                "priority": 3 if candidate_answer else None,
                "deal_breaker": False,
                "notes": "",
            },
        }
        subtopic = build_subtopic(
            main_topic_id=target_main_topic_id,
            title=legacy_topic.get("title", "Migrated topic"),
            description="Migrated from legacy round 2 dynamic topics.",
            created_by=legacy_topic.get("created_by", "company"),
            phase_created="NEGOTIATION",
            subtopic_id=legacy_topic.get("id"),
            positions=positions,
        )
        main_topic = find_main_topic(topic_tree, target_main_topic_id)
        if main_topic is not None:
            main_topic["subtopics"].append(subtopic)

    return ensure_other_main_topic(topic_tree)


def format_main_topic_label(main_topic: dict) -> str:
    return main_topic.get("title", "Untitled topic")


def format_subtopic_label(subtopic: dict) -> str:
    return subtopic.get("title", "Untitled subtopic")
