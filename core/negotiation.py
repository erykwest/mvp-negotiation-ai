import json
from copy import deepcopy
from datetime import datetime, timezone

from core.llm_client import (
    DEFAULT_MODEL_NAME,
    LLM_ERROR_PREFIX,
    BaseLLMClient,
    ask_llm,
    format_llm_error_message,
    is_llm_error,
)
from core.rfis import get_answered_rfis_before_phase
from core.topic_tree import get_sorted_main_topics, normalize_topic_tree
from core.validation import validate_state_for_round
from core.workflow import PHASES

INTRAROUND_LOOP_MAX_CYCLES_DEFAULT = 3
INTRAROUND_LOOP_STATUS_COMPLETED = "completed"
INTRAROUND_LOOP_STATUS_FAILED = "failed"
INTRAROUND_LOOP_STATUS_SKIPPED = "skipped"
INTRAROUND_LOOP_ACTION_CONTINUE = "continue"
INTRAROUND_LOOP_ACTION_STOP = "stop"
INTRAROUND_LOOP_ACTION_NEEDS_RFI = "needs_rfi"


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


def format_answered_rfis_for_prompt(data: dict, phase: str) -> str:
    answered_rfis = get_answered_rfis_before_phase(data, phase)
    if not answered_rfis:
        return "No prior RFIs."

    lines = []
    for rfi in answered_rfis:
        subtopic_scope = f" ({rfi['subtopic_title']})" if rfi.get("subtopic_title") else ""
        lines.extend(
            [
                f"- [{rfi.get('phase', '-')}] {rfi.get('requested_by', '-')} -> {rfi.get('target_side', '-')}{subtopic_scope}",
                f"  Question: {rfi.get('question', '-') or '-'}",
                f"  Answer: {rfi.get('response', '-') or '-'}",
            ]
        )
    return "\n".join(lines)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compact_lines(items: list[str]) -> list[str]:
    return [str(item).strip() for item in items if str(item).strip()]


def _extract_json_object(text: str) -> dict | None:
    raw = str(text or "").strip()
    if not raw:
        return None

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None

    return parsed if isinstance(parsed, dict) else None


def _normalize_loop_text_or_json(value: str | dict | None) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        parsed = _extract_json_object(value)
        if parsed is not None:
            return parsed
        return {"message": value.strip()}
    return {}


def _normalize_loop_list(value: object) -> list[str]:
    if isinstance(value, list):
        return _compact_lines([str(item) for item in value])
    if isinstance(value, str):
        if value.strip().lower() == "- none":
            return []
        return _compact_lines([line.lstrip("- ").strip() for line in value.splitlines()])
    return []


def _normalize_loop_suggested_rfis(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []

    normalized: list[dict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        target_side = str(item.get("target_side", "")).strip().lower()
        scope = str(item.get("scope", item.get("subtopic_title", "general"))).strip()
        if not question or target_side not in {"company", "candidate"}:
            continue
        normalized.append(
            {
                "target_side": target_side,
                "scope": scope or "general",
                "question": question,
            }
        )
    return normalized


def _merge_loop_items(base: list[str], extra: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for item in [*base, *extra]:
        normalized = str(item).strip()
        if not normalized or normalized.lower() in {"none", "- none"}:
            continue
        if normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        merged.append(normalized)
    return merged


def format_loop_context_for_prompt(loop: dict | None) -> str:
    if not loop:
        return "No intra-round loop executed."

    lines = [
        f"Loop status: {loop.get('status', '-')}",
        f"Stop reason: {loop.get('stop_reason', '-')}",
    ]
    if loop.get("agreements"):
        lines.append("Agreements:")
        lines.extend(f"- {item}" for item in _compact_lines(loop.get("agreements", [])))
    if loop.get("open_issues"):
        lines.append("Open issues:")
        lines.extend(f"- {item}" for item in _compact_lines(loop.get("open_issues", [])))
    if loop.get("cycles"):
        lines.append("Transcript:")
        for cycle in loop.get("cycles", []):
            company_turn = cycle.get("company_turn", {}).get("message") or cycle.get("company_turn", {}).get("raw", "")
            candidate_turn = cycle.get("candidate_turn", {}).get("message") or cycle.get("candidate_turn", {}).get("raw", "")
            analyst_reason = cycle.get("analyst_decision", {}).get("reason", "")
            lines.append(
                f"- Cycle {cycle.get('cycle', '-')}: company={company_turn or '-'} | "
                f"candidate={candidate_turn or '-'} | analyst={analyst_reason or '-'}"
            )
    return "\n".join(lines).strip()


def build_company_loop_prompt(data: dict, phase: str, cycle: int, loop: dict | None, side: str) -> str:
    role = "company" if side == "company" else "candidate"
    return f"""
PHASE: {phase}

ROLE:
You are the {role} negotiator in an intra-round negotiation loop.
Be concise, concrete, and focus on converging on the remaining open issues.

LOOP STATE:
{format_loop_context_for_prompt(loop)}

CURRENT CYCLE:
{cycle}

NEGOTIATION SUBJECT:
{data["job_description"]}

PARTIES:
- Company: {data.get("company", {}).get("name", "-")}
- Candidate: {data.get("candidate", {}).get("name", "-")}

TOPIC TREE:
{format_topic_tree_for_prompt(data.get("topic_tree", {}))}

RESOLVED RFIS FROM PREVIOUS ROUNDS:
{format_answered_rfis_for_prompt(data, phase)}

INSTRUCTIONS:
- Respond with JSON only.
- Use keys `message`, `agreements`, `open_issues`, `suggested_rfis`.
- Keep `message` under 120 words.
- `agreements` and `open_issues` must be arrays of short strings.
- `suggested_rfis` must be an array of objects with `target_side`, `scope`, and `question`.
""".strip()


def build_analyst_loop_prompt(
    data: dict,
    phase: str,
    cycle: int,
    company_turn: dict,
    candidate_turn: dict,
    loop: dict | None,
) -> str:
    return f"""
PHASE: {phase}

ROLE:
You are the neutral loop analyst.
Decide whether the loop should continue, stop, or raise RFIs.

LOOP STATE:
{format_loop_context_for_prompt(loop)}

CURRENT CYCLE:
{cycle}

COMPANY TURN:
{company_turn.get("message") or company_turn.get("raw") or "-"}

CANDIDATE TURN:
{candidate_turn.get("message") or candidate_turn.get("raw") or "-"}

INSTRUCTIONS:
- Respond with JSON only.
- Use keys `action`, `reason`, `agreements`, `open_issues`, `suggested_rfis`.
- `action` must be one of `continue`, `stop`, or `needs_rfi`.
- Prefer `stop` when the cycle converges or the round is sufficiently clear.
- Prefer `needs_rfi` when a blocking clarification is still missing.
- `suggested_rfis` must be an array of objects with `target_side`, `scope`, and `question`.
""".strip()


def _normalize_loop_cycle_payload(raw_payload: str | dict | None) -> dict:
    parsed = _normalize_loop_text_or_json(raw_payload)
    return {
        "message": str(parsed.get("message", raw_payload or "")).strip(),
        "agreements": _normalize_loop_list(parsed.get("agreements")),
        "open_issues": _normalize_loop_list(parsed.get("open_issues")),
        "suggested_rfis": _normalize_loop_suggested_rfis(parsed.get("suggested_rfis")),
        "raw": raw_payload if isinstance(raw_payload, str) else json.dumps(parsed, ensure_ascii=False),
    }


def _normalize_loop_decision(raw_payload: str | dict | None) -> dict:
    parsed = _normalize_loop_text_or_json(raw_payload)
    action = str(parsed.get("action", INTRAROUND_LOOP_ACTION_STOP)).strip().lower()
    if action not in {
        INTRAROUND_LOOP_ACTION_CONTINUE,
        INTRAROUND_LOOP_ACTION_STOP,
        INTRAROUND_LOOP_ACTION_NEEDS_RFI,
    }:
        action = INTRAROUND_LOOP_ACTION_STOP
    return {
        "action": action,
        "reason": str(parsed.get("reason", "")).strip(),
        "agreements": _normalize_loop_list(parsed.get("agreements")),
        "open_issues": _normalize_loop_list(parsed.get("open_issues")),
        "suggested_rfis": _normalize_loop_suggested_rfis(parsed.get("suggested_rfis")),
        "raw": raw_payload if isinstance(raw_payload, str) else json.dumps(parsed, ensure_ascii=False),
    }


def run_intraround_negotiation_loop(
    data: dict,
    client: BaseLLMClient | None = None,
    model: str = DEFAULT_MODEL_NAME,
    max_cycles: int = INTRAROUND_LOOP_MAX_CYCLES_DEFAULT,
) -> dict:
    loop = {
        "enabled": True,
        "phase": "NEGOTIATION",
        "status": "running",
        "max_cycles": int(max_cycles),
        "cycles": [],
        "stop_reason": "",
        "agreements": [],
        "open_issues": [],
        "suggested_rfis": [],
        "draft_summary": "",
        "generated_at": _utc_now_iso(),
    }

    if max_cycles <= 0:
        loop["status"] = INTRAROUND_LOOP_STATUS_SKIPPED
        loop["stop_reason"] = "max_cycles"
        return loop

    for cycle_number in range(1, max_cycles + 1):
        company_prompt = build_company_loop_prompt(data, "NEGOTIATION", cycle_number, loop, "company")
        candidate_prompt = build_company_loop_prompt(data, "NEGOTIATION", cycle_number, loop, "candidate")
        company_turn_raw = safe_ask(company_prompt, model=model, client=client)
        candidate_turn_raw = safe_ask(candidate_prompt, model=model, client=client)

        company_turn = _normalize_loop_cycle_payload(company_turn_raw)
        candidate_turn = _normalize_loop_cycle_payload(candidate_turn_raw)
        analyst_prompt = build_analyst_loop_prompt(
            data,
            "NEGOTIATION",
            cycle_number,
            company_turn,
            candidate_turn,
            loop,
        )
        analyst_raw = safe_ask(analyst_prompt, model=model, client=client)
        analyst_decision = _normalize_loop_decision(analyst_raw)

        cycle = {
            "cycle": cycle_number,
            "company_turn": company_turn,
            "candidate_turn": candidate_turn,
            "analyst_decision": analyst_decision,
        }
        loop["cycles"].append(cycle)
        loop["agreements"] = _merge_loop_items(loop["agreements"], company_turn["agreements"])
        loop["agreements"] = _merge_loop_items(loop["agreements"], candidate_turn["agreements"])
        loop["agreements"] = _merge_loop_items(loop["agreements"], analyst_decision["agreements"])
        loop["open_issues"] = _merge_loop_items(loop["open_issues"], company_turn["open_issues"])
        loop["open_issues"] = _merge_loop_items(loop["open_issues"], candidate_turn["open_issues"])
        loop["open_issues"] = _merge_loop_items(loop["open_issues"], analyst_decision["open_issues"])
        loop["suggested_rfis"].extend(company_turn["suggested_rfis"])
        loop["suggested_rfis"].extend(candidate_turn["suggested_rfis"])
        loop["suggested_rfis"].extend(analyst_decision["suggested_rfis"])
        loop["draft_summary"] = analyst_decision.get("reason", "").strip() or loop["draft_summary"]

        if is_llm_error(company_turn_raw) or is_llm_error(candidate_turn_raw) or is_llm_error(analyst_raw):
            loop["status"] = INTRAROUND_LOOP_STATUS_FAILED
            loop["stop_reason"] = "llm_error"
            return loop

        action = analyst_decision["action"]
        if action == INTRAROUND_LOOP_ACTION_CONTINUE:
            continue
        if action == INTRAROUND_LOOP_ACTION_NEEDS_RFI:
            loop["status"] = INTRAROUND_LOOP_STATUS_COMPLETED
            loop["stop_reason"] = "needs_rfi"
            return loop

        loop["status"] = INTRAROUND_LOOP_STATUS_COMPLETED
        loop["stop_reason"] = analyst_decision["reason"] or "converged"
        return loop

    loop["status"] = INTRAROUND_LOOP_STATUS_COMPLETED
    loop["stop_reason"] = "max_cycles"
    return loop


def build_company_prompt(data: dict, phase: str, loop: dict | None = None) -> str:
    loop_section = ""
    if loop and phase == "NEGOTIATION":
        loop_section = f"""

INTRA-ROUND LOOP:
{format_loop_context_for_prompt(loop)}
""".rstrip()

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

RESOLVED RFIS FROM PREVIOUS ROUNDS:
{format_answered_rfis_for_prompt(data, phase)}
{loop_section}

INSTRUCTIONS:
- Write in a concise, professional tone.
- Highlight what is acceptable, negotiable, and critical.
- Give more weight to topics and subtopics with higher priority.
- Pay close attention to deal breakers.
- Do not invent missing facts.
- Maximum 250 words.
""".strip()


def build_candidate_prompt(data: dict, phase: str, loop: dict | None = None) -> str:
    loop_section = ""
    if loop and phase == "NEGOTIATION":
        loop_section = f"""

INTRA-ROUND LOOP:
{format_loop_context_for_prompt(loop)}
""".rstrip()

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

RESOLVED RFIS FROM PREVIOUS ROUNDS:
{format_answered_rfis_for_prompt(data, phase)}
{loop_section}

INSTRUCTIONS:
- Write in a concise, professional tone.
- Highlight what is acceptable, negotiable, and critical.
- Give more weight to topics and subtopics with higher priority.
- Pay close attention to deal breakers.
- Do not invent missing facts.
- Maximum 250 words.
""".strip()


def build_summary_prompt(
    phase: str,
    company_response: str,
    candidate_response: str,
    loop: dict | None = None,
) -> str:
    loop_section = ""
    if loop and phase == "NEGOTIATION":
        loop_section = f"""

INTRA-ROUND LOOP:
{format_loop_context_for_prompt(loop)}
""".rstrip()

    return f"""
PHASE: {phase}

You are a neutral analyst.
Read both negotiation positions and produce ONLY a structured markdown report.

COMPANY POSITION:
{company_response}

CANDIDATE POSITION:
{candidate_response}
{loop_section}

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
- Write `- none` if no clarification is needed.
- Otherwise use one bullet per item with this exact format:
  - [target:company|candidate] [scope:general|<subtopic title>] <single clarification question>
- In round 2, include only clarifications about new topics introduced in round 2 by the target side.

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

    loop = None
    if phase == "NEGOTIATION":
        try:
            loop = run_intraround_negotiation_loop(data, client=client, model=model)
        except Exception as exc:
            loop = {
                "enabled": True,
                "phase": "NEGOTIATION",
                "status": INTRAROUND_LOOP_STATUS_FAILED,
                "max_cycles": INTRAROUND_LOOP_MAX_CYCLES_DEFAULT,
                "cycles": [],
                "stop_reason": "llm_error",
                "agreements": [],
                "open_issues": [],
                "suggested_rfis": [],
                "draft_summary": str(exc),
                "generated_at": _utc_now_iso(),
            }

    company_prompt = build_company_prompt(data, phase, loop=loop)
    candidate_prompt = build_candidate_prompt(data, phase, loop=loop)

    company_response = safe_ask(company_prompt, model=model, client=client)
    candidate_response = safe_ask(candidate_prompt, model=model, client=client)

    summary_prompt = build_summary_prompt(phase, company_response, candidate_response, loop=loop)
    summary_response = safe_ask(summary_prompt, model=model, client=client)

    result = {
        "company": company_response,
        "candidate": candidate_response,
        "summary": summary_response,
    }
    if loop is not None:
        result["loop"] = loop
    return result


def run_rounds(
    data: dict,
    client: BaseLLMClient | None = None,
    model: str = DEFAULT_MODEL_NAME,
) -> dict:
    phases = PHASES
    results = {}

    for phase in phases:
        results[phase] = run_single_round(data, phase, client=client, model=model)

    return results
