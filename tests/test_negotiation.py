from core.llm_client import BaseLLMClient, LLMRequest
from core.negotiation import (
    build_candidate_prompt,
    build_company_prompt,
    build_summary_prompt,
    collect_round_errors,
    run_single_round,
)
from core.validation import validate_review_readiness
from tests.helpers import build_state, build_topic_tree


class StubClient(BaseLLMClient):
    def __init__(self):
        self.prompts = []

    def complete(self, request: LLMRequest) -> str:
        self.prompts.append(request.prompt)
        return f"response-{len(self.prompts)}"


class FailingClient(BaseLLMClient):
    def complete(self, request: LLMRequest) -> str:
        raise RuntimeError("provider unavailable")


def test_prompt_builders_include_topic_tree_context():
    state = build_state(topic_tree=build_topic_tree(include_round2_subtopic=True, round2_creator="candidate"))

    company_prompt = build_company_prompt(state, "NEGOTIATION")
    candidate_prompt = build_candidate_prompt(state, "ALIGNMENT")
    summary_prompt = build_summary_prompt("ALIGNMENT", "company text", "candidate text")

    assert "TOPIC TREE" in company_prompt
    assert "Compensation" in company_prompt
    assert "Base salary" in company_prompt
    assert "Candidate deal breaker: yes" in company_prompt
    assert "Required to offset notice period." in company_prompt
    assert "ROUND 2 EXTRA TOPICS" not in company_prompt
    assert "Work setup" in candidate_prompt
    assert "company text" in summary_prompt
    assert "candidate text" in summary_prompt


def test_run_single_round_uses_injected_client():
    state = build_state()
    client = StubClient()

    result = run_single_round(state, "ALIGNMENT", client=client)

    assert result == {
        "company": "response-1",
        "candidate": "response-2",
        "summary": "response-3",
    }
    assert len(client.prompts) == 3
    assert "ROLE:\nYou are the company's negotiator." in client.prompts[0]
    assert "Main topic priority" not in client.prompts[0]
    assert "company priority: 5/5" in client.prompts[0]


def test_review_readiness_blocks_advancing_after_llm_failure():
    state = build_state()

    result = run_single_round(state, "ALIGNMENT", client=FailingClient())
    errors = collect_round_errors(result)
    review_errors = validate_review_readiness(state, "ALIGNMENT", result)

    assert len(errors) == 3
    assert any("provider unavailable" in error for error in errors)
    assert any("Company response failed" in error for error in review_errors)