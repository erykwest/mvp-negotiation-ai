from copy import deepcopy
from datetime import datetime, timezone

from core.rfis import build_rfi, normalize_rfis
from core.storage import load_state, save_state
from core.topic_tree import build_subtopic, find_main_topic, find_subtopic, normalize_topic_tree
from core.workflow import build_default_state, is_round_review, normalize_workflow

MAIN_TOPIC_IDS = {
    "role_responsibilities": "main-role_responsibilities",
    "compensation": "main-compensation",
    "work_mode": "main-work_mode",
    "benefits": "main-benefits",
    "tools_equipment": "main-tools_equipment",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


ROUND_1_PRESET = {
    "job_description": (
        "TechNova Engineering is hiring a Product Manager to lead an AI-assisted negotiation MVP. "
        "The role combines product strategy, workflow design, experimentation, and close partnership "
        "with engineering and operations in a hybrid Milan-based setup."
    ),
    "company_name": "TechNova Engineering",
    "candidate_name": "Marco Rinaldi",
    "main_priorities": {
        "company": {
            MAIN_TOPIC_IDS["role_responsibilities"]: 4,
            MAIN_TOPIC_IDS["compensation"]: 5,
            MAIN_TOPIC_IDS["work_mode"]: 3,
            MAIN_TOPIC_IDS["benefits"]: 3,
            MAIN_TOPIC_IDS["tools_equipment"]: 2,
        },
        "candidate": {
            MAIN_TOPIC_IDS["role_responsibilities"]: 5,
            MAIN_TOPIC_IDS["compensation"]: 5,
            MAIN_TOPIC_IDS["work_mode"]: 4,
            MAIN_TOPIC_IDS["benefits"]: 3,
            MAIN_TOPIC_IDS["tools_equipment"]: 2,
        },
    },
    "subtopics": {
        "sub-job_title": {
            "company": {
                "value": "Senior AI Negotiation Product Manager",
                "priority": 4,
                "deal_breaker": False,
                "notes": "Role title can be aligned with the internal career framework.",
            },
            "candidate": {
                "value": "Principal Product Manager, AI Negotiation",
                "priority": 5,
                "deal_breaker": False,
                "notes": "The title should reflect strategic ownership and external seniority.",
            },
        },
        "sub-seniority_level": {
            "company": {
                "value": "Senior individual contributor with mentoring expectations",
                "priority": 4,
                "deal_breaker": False,
                "notes": "People management is not required in the first year.",
            },
            "candidate": {
                "value": "Staff-level scope with roadmap and stakeholder ownership",
                "priority": 4,
                "deal_breaker": False,
                "notes": "Looking for visible cross-functional influence from the start.",
            },
        },
        "sub-main_responsibilities": {
            "company": {
                "value": "Own product discovery, define negotiation flows, and coordinate rollout KPIs.",
                "priority": 5,
                "deal_breaker": False,
                "notes": "Success is measured on adoption and measurable reduction in manual work.",
            },
            "candidate": {
                "value": "End-to-end product ownership with room to shape roadmap and experiment design.",
                "priority": 5,
                "deal_breaker": True,
                "notes": "Needs a broad mandate, not just delivery ownership.",
            },
        },
        "sub-base_salary": {
            "company": {
                "value": "EUR 68,000 gross annual salary",
                "priority": 5,
                "deal_breaker": False,
                "notes": "The band is aligned with current internal equity.",
            },
            "candidate": {
                "value": "EUR 78,000 gross annual salary",
                "priority": 5,
                "deal_breaker": True,
                "notes": "Target package should reflect AI product specialization.",
            },
        },
        "sub-bonus": {
            "company": {
                "value": "Up to 8% annual performance bonus",
                "priority": 3,
                "deal_breaker": False,
                "notes": "Bonus is tied to company and individual performance.",
            },
            "candidate": {
                "value": "10% annual bonus with transparent success metrics",
                "priority": 3,
                "deal_breaker": False,
                "notes": "Wants clear payout criteria rather than discretionary wording.",
            },
        },
        "sub-salary_review": {
            "company": {
                "value": "Formal review after 12 months based on impact and market alignment",
                "priority": 4,
                "deal_breaker": False,
                "notes": "The company can discuss an informal midpoint check-in.",
            },
            "candidate": {
                "value": "Written review after 6 months with salary adjustment path defined upfront",
                "priority": 4,
                "deal_breaker": True,
                "notes": "An early review is important if scope ramps up quickly.",
            },
        },
        "sub-remote_hybrid_mode": {
            "company": {
                "value": "Hybrid setup with 3 days per week in the Milan office",
                "priority": 3,
                "deal_breaker": False,
                "notes": "The team works best with regular in-person product rituals.",
            },
            "candidate": {
                "value": "Hybrid setup with no more than 2 office days per week",
                "priority": 4,
                "deal_breaker": True,
                "notes": "A tighter commute schedule is needed for family logistics.",
            },
        },
        "sub-weekly_presence": {
            "company": {
                "value": "3 office days per week, concentrated on collaboration-heavy days",
                "priority": 3,
                "deal_breaker": False,
                "notes": "Quarterly planning weeks may require an extra day on site.",
            },
            "candidate": {
                "value": "1 or 2 office days per week with advance planning",
                "priority": 4,
                "deal_breaker": False,
                "notes": "Can flex up occasionally if agreed ahead of time.",
            },
        },
        "sub-working_hours_flexibility": {
            "company": {
                "value": "Core hours 10:00-16:00 with flexibility around them",
                "priority": 2,
                "deal_breaker": False,
                "notes": "The role includes recurring stakeholder sessions in the afternoon.",
            },
            "candidate": {
                "value": "Flexible start between 8:00 and 10:30 with outcome-based coordination",
                "priority": 3,
                "deal_breaker": False,
                "notes": "Prefers autonomy as long as shared rituals are protected.",
            },
        },
        "sub-health_welfare": {
            "company": {
                "value": "Standard health insurance, meal vouchers, and welfare platform access",
                "priority": 2,
                "deal_breaker": False,
                "notes": "Current package mirrors the rest of the product organization.",
            },
            "candidate": {
                "value": "Enhanced health coverage including family support and wellbeing budget",
                "priority": 3,
                "deal_breaker": False,
                "notes": "Healthcare breadth matters more than cash-equivalent perks.",
            },
        },
        "sub-time_off": {
            "company": {
                "value": "25 vacation days plus standard company leave policies",
                "priority": 2,
                "deal_breaker": False,
                "notes": "Additional unpaid flexibility can be discussed case by case.",
            },
            "candidate": {
                "value": "26 vacation days and 2 extra personal days",
                "priority": 3,
                "deal_breaker": False,
                "notes": "Would value a small buffer for personal commitments.",
            },
        },
        "sub-mobility_support": {
            "company": {
                "value": "Public transport reimbursement or office parking access",
                "priority": 2,
                "deal_breaker": False,
                "notes": "Mobility support can be optimized around commute pattern.",
            },
            "candidate": {
                "value": "Public transport reimbursement plus occasional rental car coverage",
                "priority": 2,
                "deal_breaker": False,
                "notes": "Useful for customer or workshop travel when needed.",
            },
        },
        "sub-hardware": {
            "company": {
                "value": "MacBook Pro and company phone if needed",
                "priority": 2,
                "deal_breaker": False,
                "notes": "Standard onboarding hardware is available immediately.",
            },
            "candidate": {
                "value": "MacBook Pro 16-inch with external monitor support",
                "priority": 2,
                "deal_breaker": False,
                "notes": "The setup should support workshops, analysis, and prototyping.",
            },
        },
        "sub-software_access": {
            "company": {
                "value": "Full access to product analytics, collaboration, and approved AI tooling",
                "priority": 2,
                "deal_breaker": False,
                "notes": "Access is granted during onboarding with standard security checks.",
            },
            "candidate": {
                "value": "Access to premium AI tools and fast-track prototyping stack from day one",
                "priority": 2,
                "deal_breaker": False,
                "notes": "Fast experimentation depends on immediate tool availability.",
            },
        },
        "sub-training_support": {
            "company": {
                "value": "EUR 1,500 yearly training budget and internal mentoring",
                "priority": 2,
                "deal_breaker": False,
                "notes": "Budget can be used for targeted courses and events.",
            },
            "candidate": {
                "value": "EUR 3,000 yearly learning budget plus one relevant conference",
                "priority": 3,
                "deal_breaker": False,
                "notes": "Continuous learning is important in fast-moving AI product work.",
            },
        },
    },
}

ROUND_2_SIDE_OVERRIDES = {
    "company": {
        "main_priorities": {
            MAIN_TOPIC_IDS["compensation"]: 5,
            MAIN_TOPIC_IDS["work_mode"]: 4,
            MAIN_TOPIC_IDS["tools_equipment"]: 3,
        },
        "subtopics": {
            "sub-base_salary": {
                "value": "EUR 72,000 gross annual salary",
                "priority": 5,
                "deal_breaker": False,
                "notes": "The company can stretch upward if the package mix stays balanced.",
            },
            "sub-salary_review": {
                "value": "Formal review after 9 months, with a written midpoint checkpoint after 6 months",
                "priority": 4,
                "deal_breaker": False,
                "notes": "This is the main flexibility lever in the current band.",
            },
            "sub-remote_hybrid_mode": {
                "value": "Hybrid setup with 2 fixed office days and optional third day for workshops",
                "priority": 4,
                "deal_breaker": False,
                "notes": "The company is moving toward a slightly more flexible cadence.",
            },
        },
        "new_subtopics": [
            {
                "id": "sub-test-company-signing-bonus",
                "main_topic_id": MAIN_TOPIC_IDS["compensation"],
                "title": "Signing Bonus Structure",
                "description": "Bridge element to reduce the gap on fixed salary expectations.",
                "value": "EUR 8,000 sign-on bonus paid 50% at start and 50% after probation",
                "priority": 4,
                "deal_breaker": False,
                "notes": "Intended as a one-off accelerator rather than recurring compensation.",
            },
            {
                "id": "sub-test-company-home-office-budget",
                "main_topic_id": MAIN_TOPIC_IDS["tools_equipment"],
                "title": "Home Office Budget",
                "description": "Dedicated setup support for remote productivity.",
                "value": "Up to EUR 1,200 one-off home office setup budget",
                "priority": 3,
                "deal_breaker": False,
                "notes": "Can cover desk, chair, lighting, and peripherals.",
            },
        ],
        "rfis": [
            {
                "id": "rfi-test-negotiation-company-signing-bonus",
                "phase": "NEGOTIATION",
                "requested_by": "company",
                "target_side": "candidate",
                "subtopic_id": "sub-test-candidate-growth-path",
                "subtopic_title": "Growth Path After 6 Months",
                "question": "Would a documented growth checkpoint work if it is tied to agreed roadmap outcomes rather than an automatic title change?",
                "status": "ANSWERED",
                "response": "Yes, as long as the checkpoint criteria and expected scope indicators are written down from the start.",
            },
        ],
    },
    "candidate": {
        "main_priorities": {
            MAIN_TOPIC_IDS["role_responsibilities"]: 5,
            MAIN_TOPIC_IDS["work_mode"]: 5,
            MAIN_TOPIC_IDS["compensation"]: 4,
        },
        "subtopics": {
            "sub-base_salary": {
                "value": "EUR 76,000 gross annual salary",
                "priority": 4,
                "deal_breaker": True,
                "notes": "Candidate is trading some fixed salary for a clearer growth path and flexibility.",
            },
            "sub-weekly_presence": {
                "value": "1 office day per week on average, with planned exceptions for workshops",
                "priority": 5,
                "deal_breaker": True,
                "notes": "This becomes more important after understanding the role travel rhythm.",
            },
            "sub-training_support": {
                "value": "EUR 3,000 yearly learning budget plus at least one industry conference",
                "priority": 3,
                "deal_breaker": False,
                "notes": "Learning support remains useful but is no longer one of the top priorities.",
            },
        },
        "new_subtopics": [
            {
                "id": "sub-test-candidate-growth-path",
                "main_topic_id": MAIN_TOPIC_IDS["role_responsibilities"],
                "title": "Growth Path After 6 Months",
                "description": "Checkpoint to align early impact with future scope expansion.",
                "value": "Written checkpoint after 6 months to evaluate transition toward lead-level scope",
                "priority": 4,
                "deal_breaker": False,
                "notes": "The candidate wants the path documented, even if the final title change comes later.",
            },
            {
                "id": "sub-test-candidate-work-from-abroad",
                "main_topic_id": MAIN_TOPIC_IDS["benefits"],
                "title": "Work From Abroad Window",
                "description": "Short annual allowance for temporary work from another EU country.",
                "value": "Up to 20 working days per year from EU countries with prior approval",
                "priority": 3,
                "deal_breaker": False,
                "notes": "This is mainly about flexibility for family logistics and extended stays.",
            },
        ],
        "rfis": [
            {
                "id": "rfi-test-negotiation-candidate-home-office",
                "phase": "NEGOTIATION",
                "requested_by": "candidate",
                "target_side": "company",
                "subtopic_id": "sub-test-company-home-office-budget",
                "subtopic_title": "Home Office Budget",
                "question": "Can the home office budget also cover an ergonomic chair and external monitor bought in the first 90 days?",
                "status": "ANSWERED",
                "response": "Yes, both items are eligible as long as they stay within the budget cap and policy.",
            },
        ],
    },
}


def _merge_position(position: dict, updates: dict) -> None:
    position["value"] = str(updates.get("value", position.get("value", ""))).strip()
    position["priority"] = updates.get("priority", position.get("priority"))
    position["deal_breaker"] = bool(updates.get("deal_breaker", position.get("deal_breaker", False)))
    position["notes"] = str(updates.get("notes", position.get("notes", ""))).strip()


def _apply_main_priorities(topic_tree: dict, side: str, priorities: dict[str, int]) -> None:
    for main_topic_id, priority in priorities.items():
        main_topic = find_main_topic(topic_tree, main_topic_id)
        if main_topic is not None:
            main_topic.setdefault("priorities", {})[side] = priority


def _apply_round_1_shared_content(state: dict) -> dict:
    state["job_description"] = ROUND_1_PRESET["job_description"]
    state["company"] = {**state.get("company", {}), "name": ROUND_1_PRESET["company_name"]}
    state["candidate"] = {**state.get("candidate", {}), "name": ROUND_1_PRESET["candidate_name"]}

    topic_tree = normalize_topic_tree(state.get("topic_tree"))
    for side, priorities in ROUND_1_PRESET["main_priorities"].items():
        _apply_main_priorities(topic_tree, side, priorities)

    for subtopic_id, side_payloads in ROUND_1_PRESET["subtopics"].items():
        _main_topic, subtopic = find_subtopic(topic_tree, subtopic_id)
        if subtopic is None:
            continue
        for side, payload in side_payloads.items():
            _merge_position(subtopic["positions"][side], payload)

    state["topic_tree"] = normalize_topic_tree(topic_tree)
    return state


def _upsert_negotiation_subtopic(topic_tree: dict, side: str, payload: dict) -> None:
    main_topic = find_main_topic(topic_tree, payload["main_topic_id"])
    if main_topic is None:
        return

    _existing_main_topic, existing_subtopic = find_subtopic(topic_tree, payload["id"])
    if existing_subtopic is None:
        existing_subtopic = build_subtopic(
            main_topic_id=payload["main_topic_id"],
            title=payload["title"],
            description=payload.get("description", ""),
            created_by=side,
            phase_created="NEGOTIATION",
            subtopic_id=payload["id"],
            positions={
                side: {
                    "value": payload["value"],
                    "priority": payload["priority"],
                    "deal_breaker": payload.get("deal_breaker", False),
                    "notes": payload.get("notes", ""),
                }
            },
        )
        main_topic.setdefault("subtopics", []).append(existing_subtopic)
        return

    existing_subtopic["title"] = payload["title"]
    existing_subtopic["description"] = payload.get("description", "")
    existing_subtopic["created_by"] = side
    existing_subtopic["phase_created"] = "NEGOTIATION"
    _merge_position(
        existing_subtopic["positions"][side],
        {
            "value": payload["value"],
            "priority": payload["priority"],
            "deal_breaker": payload.get("deal_breaker", False),
            "notes": payload.get("notes", ""),
        },
    )


def _upsert_rfis(existing_rfis: list[dict], preset_rfis: list[dict]) -> list[dict]:
    rfis_by_id = {rfi.get("id"): deepcopy(rfi) for rfi in existing_rfis}
    now = _utc_now_iso()
    for payload in preset_rfis:
        answered = payload.get("status") == "ANSWERED"
        rfis_by_id[payload["id"]] = build_rfi(
            phase=payload["phase"],
            requested_by=payload["requested_by"],
            target_side=payload["target_side"],
            question=payload["question"],
            subtopic_id=payload.get("subtopic_id"),
            subtopic_title=payload.get("subtopic_title", ""),
            status=payload.get("status", "OPEN"),
            response=payload.get("response", ""),
            rfi_id=payload["id"],
            created_at=now,
            answered_at=now if answered else "",
        )
    return list(rfis_by_id.values())


def _round_2_rfis_allowed(state: dict) -> bool:
    workflow = normalize_workflow(state.get("workflow"))
    return workflow.get("current_phase") == "NEGOTIATION" and is_round_review(workflow)


def _safe_upsert_round_2_rfis(state: dict, side: str) -> dict:
    if not _round_2_rfis_allowed(state):
        return state

    topic_tree = normalize_topic_tree(state.get("topic_tree"))
    eligible_payloads: list[dict] = []
    for payload in ROUND_2_SIDE_OVERRIDES[side]["rfis"]:
        subtopic_id = payload.get("subtopic_id")
        if not subtopic_id:
            eligible_payloads.append(payload)
            continue
        _main_topic, subtopic = find_subtopic(topic_tree, subtopic_id)
        if subtopic is None:
            continue
        eligible_payloads.append(
            {
                **payload,
                "subtopic_title": subtopic.get("title", payload.get("subtopic_title", "")),
            }
        )

    if not eligible_payloads:
        return state

    state["rfis"] = _upsert_rfis(normalize_rfis(state.get("rfis")), eligible_payloads)
    return state


def apply_session_preset(side: str, preset_name: str, session_id: str | None = None) -> dict:
    normalized_side = str(side or "").strip().lower()
    normalized_preset = str(preset_name or "").strip().lower()
    if normalized_side not in {"company", "candidate"}:
        raise ValueError("Unknown preset side.")
    if normalized_preset not in {"round1", "round2"}:
        raise ValueError("Unknown preset.")

    if normalized_preset == "round1":
        state = build_default_state(session_id=session_id or "session_001")
        state = _apply_round_1_shared_content(state)
        return save_state(state, session_id)

    state = load_state(session_id)
    workflow = normalize_workflow(state.get("workflow"))
    if workflow.get("current_phase") != "NEGOTIATION":
        raise ValueError("Round 2 preset can only be loaded while the workflow is on round 2.")

    overrides = ROUND_2_SIDE_OVERRIDES[normalized_side]
    topic_tree = normalize_topic_tree(state.get("topic_tree"))
    _apply_main_priorities(topic_tree, normalized_side, overrides["main_priorities"])

    for subtopic_id, payload in overrides["subtopics"].items():
        _main_topic, subtopic = find_subtopic(topic_tree, subtopic_id)
        if subtopic is None:
            continue
        _merge_position(subtopic["positions"][normalized_side], payload)

    for new_subtopic in overrides["new_subtopics"]:
        _upsert_negotiation_subtopic(topic_tree, normalized_side, new_subtopic)

    state["topic_tree"] = normalize_topic_tree(topic_tree)
    state = _safe_upsert_round_2_rfis(state, normalized_side)
    return save_state(state, session_id)
