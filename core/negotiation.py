from core.llm_client import (
    DEFAULT_MODEL_NAME,
    LLM_ERROR_PREFIX,
    BaseLLMClient,
    ask_llm,
    format_llm_error_message,
    is_llm_error,
)
from core.topic_tree import get_sorted_main_topics, normalize_topic_tree
from core.validation import validate_state_for_round


def format_topic_tree_for_prompt(topic_tree: dict) -> str:
    normalized_tree = normalize_topic_tree(topic_tree)
    lines = []
    for main_topic in get_sorted_main_topics(normalized_tree):
        if main_topic.get("is_other") and not main_topic.get("subtopics"):
            continue

        lines.append(
            f"## {main_topic['title']} "
            f"(company priority: {main_topic['priorities'].get('company', '-')}/5, "
            f"candidate priority: {main_topic['priorities'].get('candidate', '-')}/5)"
        )
        if main_topic.get("description"):
            lines.append(main_topic["description"])

        for subtopic in main_topic.get("subtopics", []):
            company_position = subtopic.get("positions", {}).get("company", {})
            candidate_position = subtopic.get("positions", {}).get("candidate", {})
            lines.extend(
                [
                    f"- {subtopic['title']}",
                    f"  - Description: {subtopic.get('description', '-') or '-'}",
                    f"  - Company: {company_position.get('value', '-') or '-'}",
                    f"  - Company priority: {company_position.get('priority', '-')}/5",
                    f"  - Company deal breaker: {'yes' if company_position.get('deal_breaker') else 'no'}",
                    f"  - Company notes: {company_position.get('notes', '-') or '-'}",
                    f"  - Candidate: {candidate_position.get('value', '-') or '-'}",
                    f"  - Candidate priority: {candidate_position.get('priority', '-')}/5",
                    f"  - Candidate deal breaker: {'yes' if candidate_position.get('deal_breaker') else 'no'}",
                    f"  - Candidate notes: {candidate_position.get('notes', '-') or '-'}",
                    f"  - Created in phase: {subtopic.get('phase_created', '-')}",
                ]
            )

        lines.append("")

    return "\n".join(lines).strip() or "No topics configured."


def build_company_prompt(data: dict, phase: str) -> str:
    return f"""
PHASE: {phase}

ROLE:
You are the company's negotiator.
Protect the company's interests without closing the door on a reasonable agreement.

NEGOTIATION SUBJECT:
{data["job_description"]}

PARTIES:
- Company: {data.get("company", {}).get("name", "-")}
- Candidate: {data.get("candidate", {}).get("name", "-")}

TOPIC TREE:
{format_topic_tree_for_prompt(data.get("topic_tree", {}))}

INSTRUCTIONS:
- Write in a concise, professional tone.
- Highlight what is acceptable, negotiable, and critical.
- Give more weight to topics and subtopics with higher priority.
- Pay close attention to deal breakers.
- Do not invent missing facts.
- Maximum 250 words.
""".strip()


def build_candidate_prompt(data: dict, phase: str) -> str:
    return f"""
PHASE: {phase}

ROLE:
You are the candidate's negotiator.
Maximize the overall value of the offer without breaking the negotiation unnecessarily.

NEGOTIATION SUBJECT:
{data["job_description"]}

PARTIES:
- Company: {data.get("company", {}).get("name", "-")}
- Candidate: {data.get("candidate", {}).get("name", "-")}

TOPIC TREE:
{format_topic_tree_for_prompt(data.get("topic_tree", {}))}

INSTRUCTIONS:
- Write in a concise, professional tone.
- Highlight what is acceptable, negotiable, and critical.
- Give more weight to topics and subtopics with higher priority.
- Pay close attention to deal breakers.
- Do not invent missing facts.
- Maximum 250 words.
""".strip()


def build_summary_prompt(phase: str, company_response: str, candidate_response: str) -> str:
    return f"""
PHASE: {phase}

You are a neutral analyst.
Read both negotiation positions and produce ONLY a structured markdown report.

COMPANY POSITION:
{company_response}

CANDIDATE POSITION:
{candidate_response}

REQUIRED OUTPUT:

## Round objective
(max 2 lines)

## Aligned points
- ...

## Conflicts
- ...

## Company concessions or openings
- ...

## Candidate concessions or openings
- ...

## RFIs or clarifications needed
- ...

## Recommended next move
(max 3 lines)

RULES:
- no introduction
- no greetings
- no long narrative
- maximum 180 words
""".strip()


def safe_ask(
    prompt: str,
    model: str = DEFAULT_MODEL_NAME,
    client: BaseLLMClient | None = None,
) -> str:
    try:
        return ask_llm(prompt, model=model, client=client)
    except Exception as exc:
        return format_llm_error_message(str(exc))


def collect_round_errors(result: dict) -> list[str]:
    errors = []
    for field in ("company", "candidate", "summary"):
        content = result.get(field, "")
        if is_llm_error(content):
            errors.append(f"{field.title()} response failed: {content[len(LLM_ERROR_PREFIX):].strip()}")
    return errors


def run_single_round(
    data: dict,
    phase: str,
    client: BaseLLMClient | None = None,
    model: str = DEFAULT_MODEL_NAME,
) -> dict:
    errors = validate_state_for_round(data, phase)
    if errors:
        raise ValueError("; ".join(errors))

    company_prompt = build_company_prompt(data, phase)
    candidate_prompt = build_candidate_prompt(data, phase)

    company_response = safe_ask(company_prompt, model=model, client=client)
    candidate_response = safe_ask(candidate_prompt, model=model, client=client)

    summary_prompt = build_summary_prompt(phase, company_response, candidate_response)
    summary_response = safe_ask(summary_prompt, model=model, client=client)

    return {
        "company": company_response,
        "candidate": candidate_response,
        "summary": summary_response,
    }


def run_rounds(
    data: dict,
    client: BaseLLMClient | None = None,
    model: str = DEFAULT_MODEL_NAME,
) -> dict:
    phases = ["ALIGNMENT", "NEGOTIATION", "CLOSING"]
    results = {}

    for phase in phases:
        results[phase] = run_single_round(data, phase, client=client, model=model)

    return results
