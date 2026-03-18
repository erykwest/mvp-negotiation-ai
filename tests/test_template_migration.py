import pytest

from core.template_loader import load_negotiation_template
from core.topic_tree import (
    build_recruiting_demo_topic_tree,
    build_topic_tree_from_template,
    find_main_topic,
    find_subtopic,
    validate_recruiting_template_contract,
)


def test_build_topic_tree_from_template_rejects_template_section_drift(monkeypatch):
    drifted_template = load_negotiation_template()
    drifted_template["sections"] = [
        section for section in drifted_template["sections"] if section["section_id"] != "benefits"
    ]

    monkeypatch.setattr(
        "core.topic_tree.load_negotiation_template",
        lambda template_id="recruiting_v1": drifted_template,
    )

    with pytest.raises(ValueError) as excinfo:
        build_topic_tree_from_template()

    assert "benefits" in str(excinfo.value).lower()
    assert "missing" in str(excinfo.value).lower()


def test_validate_recruiting_template_contract_rejects_topic_id_drift():
    drifted_template = load_negotiation_template()
    benefits_section = next(
        section for section in drifted_template["sections"] if section["section_id"] == "benefits"
    )
    benefits_section["topics"] = [
        topic for topic in benefits_section["topics"] if topic["topic_id"] != "health_welfare"
    ]

    with pytest.raises(ValueError) as excinfo:
        validate_recruiting_template_contract(drifted_template)

    assert "health_welfare" in str(excinfo.value)


def test_legacy_migration_preserves_strongest_section_priority_signal():
    topic_tree = build_recruiting_demo_topic_tree(
        company={"car": "Company car", "benefits": "Welfare budget"},
        candidate={"car": "Car allowance", "benefits": "Health plan"},
        priorities={
            "car": {"company": 2, "candidate": 4},
            "benefits": {"company": 5, "candidate": 3},
        },
        dynamic_topics=[],
    )

    benefits_section = find_main_topic(topic_tree, "main-benefits")
    _benefits_topic, mobility_support = find_subtopic(topic_tree, "sub-mobility_support")
    _benefits_topic, health_welfare = find_subtopic(topic_tree, "sub-health_welfare")

    assert benefits_section is not None
    assert benefits_section["priorities"] == {"company": 5, "candidate": 4}
    assert mobility_support is not None
    assert mobility_support["positions"]["company"]["value"] == "Company car"
    assert mobility_support["positions"]["candidate"]["value"] == "Car allowance"
    assert health_welfare is not None
    assert health_welfare["positions"]["company"]["value"] == "Welfare budget"
    assert health_welfare["positions"]["candidate"]["value"] == "Health plan"
