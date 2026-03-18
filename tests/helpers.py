from copy import deepcopy

from core.topic_tree import build_main_topic, build_subtopic, normalize_topic_tree


def build_topic_tree(include_round2_subtopic: bool = False, round2_creator: str = "company") -> dict:
    compensation_id = "main-compensation"
    flexibility_id = "main-flexibility"
    main_topics = [
        build_main_topic(
            title="Compensation",
            description="Economic package and variable compensation.",
            created_by="company",
            phase_created="ALIGNMENT",
            order=0,
            main_topic_id=compensation_id,
            priorities={"company": 5, "candidate": 4},
            subtopics=[
                build_subtopic(
                    main_topic_id=compensation_id,
                    title="Base salary",
                    description="Annual gross salary.",
                    created_by="company",
                    phase_created="ALIGNMENT",
                    subtopic_id="sub-base-salary",
                    positions={
                        "company": {
                            "value": "42000 EUR gross",
                            "priority": 5,
                            "deal_breaker": False,
                            "notes": "Budget approved for this range.",
                        },
                        "candidate": {
                            "value": "48000 EUR gross",
                            "priority": 5,
                            "deal_breaker": True,
                            "notes": "Below this range the move is not viable.",
                        },
                    },
                ),
            ],
        ),
        build_main_topic(
            title="Work setup",
            description="Remote work and office presence.",
            created_by="company",
            phase_created="ALIGNMENT",
            order=1,
            main_topic_id=flexibility_id,
            priorities={"company": 3, "candidate": 5},
            subtopics=[
                build_subtopic(
                    main_topic_id=flexibility_id,
                    title="Remote policy",
                    description="Weekly office attendance.",
                    created_by="company",
                    phase_created="ALIGNMENT",
                    subtopic_id="sub-remote-policy",
                    positions={
                        "company": {
                            "value": "Three office days per week",
                            "priority": 3,
                            "deal_breaker": False,
                            "notes": "",
                        },
                        "candidate": {
                            "value": "Maximum two office days per week",
                            "priority": 4,
                            "deal_breaker": False,
                            "notes": "Long commute on Fridays.",
                        },
                    },
                ),
            ],
        ),
    ]

    if include_round2_subtopic:
        round2_positions = {
            "company": {
                "value": "Signing bonus of 2k" if round2_creator == "company" else "",
                "priority": 3 if round2_creator == "company" else None,
                "deal_breaker": False,
                "notes": "First proposal" if round2_creator == "company" else "",
            },
            "candidate": {
                "value": "Signing bonus of 5k" if round2_creator == "candidate" else "",
                "priority": 4 if round2_creator == "candidate" else None,
                "deal_breaker": True if round2_creator == "candidate" else False,
                "notes": "Required to offset notice period." if round2_creator == "candidate" else "",
            },
        }
        main_topics[0]["subtopics"].append(
            build_subtopic(
                main_topic_id=compensation_id,
                title="Signing bonus",
                description="One-off incentive discussed in round 2.",
                created_by=round2_creator,
                phase_created="NEGOTIATION",
                subtopic_id="sub-signing-bonus",
                positions=round2_positions,
            )
        )

    return normalize_topic_tree({"main_topics": main_topics})


def build_state(
    *,
    topic_tree: dict | None = None,
    current_phase: str = "ALIGNMENT",
    status: str = "editing",
    results: dict | None = None,
) -> dict:
    return {
        "session_id": "test-session",
        "job_description": "Senior BIM coordinator for a strategic infrastructure program.",
        "company": {"name": "TechNova Engineering"},
        "candidate": {"name": "Marco Rinaldi"},
        "priorities": {},
        "dynamic_topics": [],
        "topic_tree": deepcopy(topic_tree or build_topic_tree()),
        "workflow": {"current_phase": current_phase, "status": status},
        "results": deepcopy(results or {}),
    }