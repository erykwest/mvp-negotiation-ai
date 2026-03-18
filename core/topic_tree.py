from copy import deepcopy
from uuid import uuid4

from core.template_loader import load_negotiation_template

OTHER_MAIN_TOPIC_ID = "main-other"
OTHER_MAIN_TOPIC_TITLE = "Other"
POSITION_SIDES = ("company", "candidate")
VALID_PRIORITY_VALUES = {1, 2, 3, 4, 5}

LEGACY_FIELD_TO_TEMPLATE_TOPIC = {
    "salary": ("compensation", "base_salary"),
    "bonus": ("compensation", "bonus"),
    "smart": ("work_mode", "remote_hybrid_mode"),
    "car": ("benefits", "mobility_support"),
    "benefits": ("benefits", "health_welfare"),
}

LEGACY_DYNAMIC_SECTION_TO_TEMPLATE_SECTION = {
    "salary": "compensation",
    "bonus": "compensation",
    "smart": "work_mode",
    "car": "benefits",
    "benefits": "benefits",
}


def _main_topic_id_for_section_id(section_id: str) -> str:
    return f"main-{section_id}"


def _subtopic_id_for_topic_id(topic_id: str) -> str:
    return f"sub-{topic_id}"


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
    template_section_id: str | None = None,
    allow_extra_topics: bool = True,
    locked: bool = False,
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
        "template_section_id": str(template_section_id).strip() if template_section_id else None,
        "allow_extra_topics": bool(allow_extra_topics),
        "locked": bool(locked),
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
    template_topic_id: str | None = None,
    canonical_name: str | None = None,
    value_type: str | None = None,
    unit: str | None = None,
    locked: bool = False,
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
        "template_topic_id": str(template_topic_id).strip() if template_topic_id else None,
        "canonical_name": str(canonical_name).strip() if canonical_name else None,
        "value_type": str(value_type).strip() if value_type else None,
        "unit": str(unit).strip() if unit else None,
        "locked": bool(locked),
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
            template_section_id=main_topic.get("template_section_id"),
            allow_extra_topics=main_topic.get("allow_extra_topics", True),
            locked=main_topic.get("locked", False),
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
                template_topic_id=subtopic.get("template_topic_id"),
                canonical_name=subtopic.get("canonical_name"),
                value_type=subtopic.get("value_type"),
                unit=subtopic.get("unit"),
                locked=subtopic.get("locked", False),
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


def has_locked_template_structure(topic_tree: dict) -> bool:
    return any(
        main_topic.get("locked") and not main_topic.get("is_other")
        for main_topic in topic_tree.get("main_topics", [])
    )


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


def build_topic_tree_from_template(template: dict | None = None) -> dict:
    template = template or load_negotiation_template()

    main_topics = []
    for order, section in enumerate(template.get("sections", [])):
        section_id = str(section.get("section_id") or f"section-{order}").strip()
        main_topic_id = _main_topic_id_for_section_id(section_id)
        subtopics = []

        for index, topic in enumerate(section.get("topics", [])):
            topic_id = str(topic.get("topic_id") or f"{section_id}-topic-{index}").strip()
            subtopics.append(
                build_subtopic(
                    main_topic_id=main_topic_id,
                    title=topic.get("label", "Untitled topic"),
                    description=topic.get("description", ""),
                    created_by="company",
                    phase_created="ALIGNMENT",
                    subtopic_id=_subtopic_id_for_topic_id(topic_id),
                    template_topic_id=topic_id,
                    canonical_name=topic.get("canonical_name"),
                    value_type=topic.get("value_type"),
                    unit=topic.get("unit"),
                    locked=True,
                )
            )

        main_topics.append(
            build_main_topic(
                title=section.get("label", "Untitled section"),
                description=section.get("description", ""),
                created_by="company",
                phase_created="ALIGNMENT",
                order=order,
                is_other=False,
                main_topic_id=main_topic_id,
                priorities={"company": None, "candidate": None},
                template_section_id=section_id,
                allow_extra_topics=section.get("allow_extra_topics", True),
                locked=True,
                subtopics=subtopics,
            )
        )

    return ensure_other_main_topic({"main_topics": main_topics})


def legacy_topic_inputs_present(
    company: dict | None,
    candidate: dict | None,
    priorities: dict | None,
    dynamic_topics: list | None,
) -> bool:
    company = company or {}
    candidate = candidate or {}
    priorities = priorities or {}
    dynamic_topics = dynamic_topics or []
    legacy_keys = LEGACY_FIELD_TO_TEMPLATE_TOPIC.keys()

    return bool(dynamic_topics) or any(
        [
            any(str(company.get(key, "")).strip() for key in legacy_keys),
            any(str(candidate.get(key, "")).strip() for key in legacy_keys),
            any(priorities.get(key) for key in legacy_keys),
        ]
    )


def resolve_template_main_topic_id(section_key: str | None) -> str:
    normalized_key = str(section_key or "").strip().lower()
    if not normalized_key or normalized_key == "other":
        return OTHER_MAIN_TOPIC_ID

    resolved_section_id = LEGACY_DYNAMIC_SECTION_TO_TEMPLATE_SECTION.get(normalized_key, normalized_key)
    return _main_topic_id_for_section_id(resolved_section_id)


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

    topic_tree = build_topic_tree_from_template()
    populated_template_subtopics: set[str] = set()

    for key, (section_id, topic_id) in LEGACY_FIELD_TO_TEMPLATE_TOPIC.items():
        company_value = str(company.get(key, "")).strip()
        candidate_value = str(candidate.get(key, "")).strip()
        company_priority = priorities.get(key, {}).get("company")
        candidate_priority = priorities.get(key, {}).get("candidate")

        if not any([company_value, candidate_value, company_priority, candidate_priority]):
            continue

        main_topic_id = _main_topic_id_for_section_id(section_id)
        subtopic_id = _subtopic_id_for_topic_id(topic_id)
        main_topic = find_main_topic(topic_tree, main_topic_id)
        _existing_main_topic, subtopic = find_subtopic(topic_tree, subtopic_id)
        if main_topic is None or subtopic is None:
            continue

        main_topic["priorities"]["company"] = company_priority if company_priority in VALID_PRIORITY_VALUES else None
        main_topic["priorities"]["candidate"] = candidate_priority if candidate_priority in VALID_PRIORITY_VALUES else None
        subtopic["positions"]["company"] = build_position(
            value=company_value,
            priority=company_priority,
            deal_breaker=False,
            notes="",
        )
        subtopic["positions"]["candidate"] = build_position(
            value=candidate_value,
            priority=candidate_priority,
            deal_breaker=False,
            notes="",
        )
        populated_template_subtopics.add(subtopic_id)

    for legacy_topic in dynamic_topics:
        target_main_topic_id = resolve_template_main_topic_id(legacy_topic.get("section"))
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

    for main_topic in topic_tree.get("main_topics", []):
        if main_topic.get("locked"):
            main_topic["subtopics"] = [
                subtopic
                for subtopic in main_topic.get("subtopics", [])
                if not subtopic.get("locked") or subtopic.get("id") in populated_template_subtopics
            ]

    topic_tree["main_topics"] = [
        main_topic
        for main_topic in topic_tree.get("main_topics", [])
        if main_topic.get("is_other") or main_topic.get("subtopics")
    ]

    return ensure_other_main_topic(topic_tree)


def format_main_topic_label(main_topic: dict) -> str:
    return main_topic.get("title", "Untitled topic")


def format_subtopic_label(subtopic: dict) -> str:
    return subtopic.get("title", "Untitled subtopic")
