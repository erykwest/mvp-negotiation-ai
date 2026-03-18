from __future__ import annotations

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
from core.rfis import build_suggested_rfi
from core.topic_tree import POSITION_SIDES, find_subtopic, normalize_topic_tree
from core.validation import validate_state_for_round

INTRAROUND_PHASE = "NEGOTIATION"
DEFAULT_MAX_CYCLES = 3

ANALYST_ACTION_CONTINUE = "continue"
ANALYST_ACTION_STOP = "stop"
ANALYST_ACTION_NEEDS_RFI = "needs_rfi"
ANALYST_ACTIONS = {
    ANALYST_ACTION_CONTINUE,
    ANALYST_ACTION_STOP,
    ANALYST_ACTION_NEEDS_RFI,
}

STOP_REASON_CONVERGED = "converged"
STOP_REASON_MAX_CYCLES = "max_cycles"
STOP_REASON_NEEDS_RFI = "needs_rfi"
STOP_REASON_LLM_ERROR = "llm_error"
STOP_REASONS = {
    STOP_REASON_CONVERGED,
    STOP_REASON_MAX_CYCLES,
    STOP_REASON_NEEDS_RFI,
    STOP_REASON_LLM_ERROR,
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dedupe_dicts(items: list[dict], key_fields: tuple[str, ...]) -> list[dict]:
    seen: set[tuple[str, ...]] = set()
    deduped: list[dict] = []
    for item in items:
        key = tuple(str(item.get(field, "")).strip().lower() for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _topic_tree_digest(topic_tree: dict | None) -> list[dict]:
    normalized = normalize_topic_tree(topic_tree)
    digest: list[dict] = []
    for main_topic in normalized.get("main_topics", []):
        digest.append(
            {
                "id": main_topic.get("id"),
                "title": main_topic.get("title", ""),
                "locked": bool(main_topic.get("locked", False)),
                "subtopics": [
                    {
                        "id": subtopic.get("id"),
                        "title": subtopic.get("title", ""),
                        "created_by": subtopic.get("created_by", ""),
                        "phase_created": subtopic.get("phase_created", ""),
                    }
                    for subtopic in main_topic.get("subtopics", [])
                ],
            }
        )
    return digest


def _history_digest(loop_artifact: dict) -> list[dict]:
    digest: list[dict] = []
    for cycle in loop_artifact.get("cycles", []):
        digest.append(
            {
                "cycle": cycle.get("cycle"),
                "company": cycle.get("company_turn", {}).get("parsed", {}),
                "candidate": cycle.get("candidate_turn", {}).get("parsed", {}),
                "analyst": cycle.get("analyst_decision", {}).get("parsed", {}),
            }
        )
    return digest


def _json_prompt(payload: dict) -> str:
    return "Return JSON only.\n" + json.dumps(payload, ensure_ascii=False, indent=2)


def _build_role_prompt(
    *,
    role: str,
    phase: str,
    cycle: int,
    data: dict,
    loop_artifact: dict,
) -> str:
    return _json_prompt(
        {
            "task": "intra-round negotiation turn",
            "role": role,
            "phase": phase,
            "cycle": cycle,
            "context": {
                "job_description": data.get("job_description", ""),
                "company": data.get("company", {}),
                "candidate": data.get("candidate", {}),
                "topic_tree": _topic_tree_digest(data.get("topic_tree")),
                "previous_cycles": _history_digest(loop_artifact),
                "open_issues": loop_artifact.get("open_issues", []),
                "agreements": loop_artifact.get("agreements", []),
            },
            "output_schema": {
                "message": "string",
                "agreements": ["string"],
                "open_issues": ["string"],
                "proposals": ["string"],
            },
            "rules": [
                "Respond with a single JSON object.",
                "Keep the message concise and negotiation-oriented.",
                "Do not mutate state or invent new topics.",
            ],
        }
    )


def _build_analyst_prompt(
    *,
    phase: str,
    cycle: int,
    data: dict,
    loop_artifact: dict,
    company_turn: dict,
    candidate_turn: dict,
) -> str:
    return _json_prompt(
        {
            "task": "analyst decision for intra-round negotiation",
            "role": "analyst",
            "phase": phase,
            "cycle": cycle,
            "context": {
                "job_description": data.get("job_description", ""),
                "company": data.get("company", {}),
                "candidate": data.get("candidate", {}),
                "topic_tree": _topic_tree_digest(data.get("topic_tree")),
                "previous_cycles": _history_digest(loop_artifact),
                "open_issues": loop_artifact.get("open_issues", []),
                "agreements": loop_artifact.get("agreements", []),
            },
            "latest_turns": {
                "company": company_turn,
                "candidate": candidate_turn,
            },
            "output_schema": {
                "action": "continue|stop|needs_rfi",
                "reason": "converged|max_cycles|needs_rfi|llm_error",
                "summary": "string",
                "agreements": ["string"],
                "open_issues": ["string"],
                "suggested_rfis": [
                    {
                        "target_side": "company|candidate",
                        "subtopic_id": "string",
                        "subtopic_title": "string",
                        "question": "string",
                    }
                ],
            },
            "rules": [
                "Respond with a single JSON object.",
                "Use needs_rfi only if a clarification is genuinely required.",
                "In round 2, suggested RFIs must target NEGOTIATION subtopics introduced by the target side.",
            ],
        }
    )


def _parse_json_response(response_text: str, context: str) -> tuple[dict | None, str | None]:
    if is_llm_error(response_text):
        return None, response_text

    raw = str(response_text or "").strip()
    if not raw:
        return None, format_llm_error_message(f"{context} returned an empty response.")

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, format_llm_error_message(f"{context} did not return valid JSON: {exc}")

    if not isinstance(parsed, dict):
        return None, format_llm_error_message(f"{context} must return a JSON object.")

    return parsed, None


def _call_structured_llm(
    *,
    prompt: str,
    context: str,
    client: BaseLLMClient | None = None,
    model: str = DEFAULT_MODEL_NAME,
) -> tuple[dict | None, str | None, str]:
    try:
        response_text = ask_llm(prompt, model=model, client=client)
    except Exception as exc:
        error_text = format_llm_error_message(str(exc))
        return None, error_text, ""

    parsed, error_text = _parse_json_response(response_text, context)
    return parsed, error_text, response_text


def _normalize_turn_payload(payload: dict | None) -> dict:
    payload = payload or {}
    return {
        "message": str(payload.get("message", "")).strip(),
        "agreements": [str(item).strip() for item in payload.get("agreements", []) if str(item).strip()],
        "open_issues": [str(item).strip() for item in payload.get("open_issues", []) if str(item).strip()],
        "proposals": [str(item).strip() for item in payload.get("proposals", []) if str(item).strip()],
    }


def _normalize_analyst_payload(payload: dict | None) -> dict:
    payload = payload or {}
    action = str(payload.get("action", "")).strip().lower()
    reason = str(payload.get("reason", "")).strip().lower()
    summary = str(payload.get("summary", "")).strip()
    agreements = [str(item).strip() for item in payload.get("agreements", []) if str(item).strip()]
    open_issues = [str(item).strip() for item in payload.get("open_issues", []) if str(item).strip()]
    suggested_rfis = payload.get("suggested_rfis", [])
    if action not in ANALYST_ACTIONS:
        action = ANALYST_ACTION_CONTINUE
    if reason not in STOP_REASONS:
        if action == ANALYST_ACTION_NEEDS_RFI:
            reason = STOP_REASON_NEEDS_RFI
        elif action == ANALYST_ACTION_STOP:
            reason = STOP_REASON_CONVERGED
        else:
            reason = STOP_REASON_MAX_CYCLES
    return {
        "action": action,
        "reason": reason,
        "summary": summary,
        "agreements": agreements,
        "open_issues": open_issues,
        "suggested_rfis": suggested_rfis if isinstance(suggested_rfis, list) else [],
    }


def _normalize_suggested_rfis_for_phase(
    *,
    phase: str,
    data: dict,
    suggested_rfis: list[dict],
) -> list[dict]:
    if phase != INTRAROUND_PHASE:
        return []

    topic_tree = normalize_topic_tree(data.get("topic_tree"))
    normalized: list[dict] = []

    for suggestion in suggested_rfis or []:
        if not isinstance(suggestion, dict):
            continue

        target_side = str(suggestion.get("target_side", "")).strip().lower()
        subtopic_id = str(suggestion.get("subtopic_id", "")).strip()
        subtopic_title = str(suggestion.get("subtopic_title", "")).strip()
        question = str(suggestion.get("question", "")).strip()

        if target_side not in POSITION_SIDES:
            continue
        if not subtopic_id or not question:
            continue

        main_topic, subtopic = find_subtopic(topic_tree, subtopic_id)
        if subtopic is None or main_topic is None:
            continue
        if subtopic.get("phase_created") != INTRAROUND_PHASE:
            continue
        if subtopic.get("created_by") != target_side:
            continue

        normalized.append(
            build_suggested_rfi(
                phase=phase,
                target_side=target_side,
                question=question,
                subtopic_id=subtopic_id,
                subtopic_title=subtopic_title or subtopic.get("title", ""),
                source_summary=str(suggestion.get("source_summary", "")).strip(),
            )
        )

    return _dedupe_dicts(normalized, ("target_side", "subtopic_id", "question"))


def build_empty_loop_artifact(
    *,
    phase: str,
    max_cycles: int = DEFAULT_MAX_CYCLES,
) -> dict:
    return {
        "enabled": phase == INTRAROUND_PHASE,
        "phase": phase,
        "status": "idle" if phase != INTRAROUND_PHASE else "ready",
        "max_cycles": int(max_cycles),
        "cycles": [],
        "stop_reason": "",
        "agreements": [],
        "open_issues": [],
        "suggested_rfis": [],
        "draft_summary": "",
        "generated_at": "",
        "completed_at": "",
        "error": "",
    }


def normalize_loop_artifact(loop: dict | None, *, phase: str, max_cycles: int = DEFAULT_MAX_CYCLES) -> dict:
    if not isinstance(loop, dict):
        return build_empty_loop_artifact(phase=phase, max_cycles=max_cycles)

    normalized_cycles: list[dict] = []
    for index, cycle in enumerate(loop.get("cycles", []) or [], start=1):
        if not isinstance(cycle, dict):
            continue
        normalized_cycles.append(
            {
                "cycle": int(cycle.get("cycle", index)),
                "company_turn": {
                    "raw": str(cycle.get("company_turn", {}).get("raw", "")),
                    "parsed": deepcopy(cycle.get("company_turn", {}).get("parsed", {})),
                    "error": str(cycle.get("company_turn", {}).get("error", "")),
                },
                "candidate_turn": {
                    "raw": str(cycle.get("candidate_turn", {}).get("raw", "")),
                    "parsed": deepcopy(cycle.get("candidate_turn", {}).get("parsed", {})),
                    "error": str(cycle.get("candidate_turn", {}).get("error", "")),
                },
                "analyst_decision": {
                    "raw": str(cycle.get("analyst_decision", {}).get("raw", "")),
                    "parsed": deepcopy(cycle.get("analyst_decision", {}).get("parsed", {})),
                    "error": str(cycle.get("analyst_decision", {}).get("error", "")),
                },
            }
        )

    normalized = build_empty_loop_artifact(
        phase=str(loop.get("phase", phase)),
        max_cycles=int(loop.get("max_cycles", max_cycles)),
    )
    normalized.update(
        {
            "enabled": bool(loop.get("enabled", phase == INTRAROUND_PHASE)),
            "status": str(loop.get("status", normalized["status"])),
            "cycles": normalized_cycles,
            "stop_reason": str(loop.get("stop_reason", "")),
            "agreements": [str(item).strip() for item in loop.get("agreements", []) if str(item).strip()],
            "open_issues": [str(item).strip() for item in loop.get("open_issues", []) if str(item).strip()],
            "suggested_rfis": normalize_suggested_rfis_for_phase(
                phase=str(loop.get("phase", phase)),
                data={"topic_tree": loop.get("topic_tree", {})},
                suggested_rfis=loop.get("suggested_rfis", []) if isinstance(loop.get("suggested_rfis", []), list) else [],
            ),
            "draft_summary": str(loop.get("draft_summary", "")),
            "generated_at": str(loop.get("generated_at", "")),
            "completed_at": str(loop.get("completed_at", "")),
            "error": str(loop.get("error", "")),
        }
    )
    return normalized


def _accumulate_strings(existing: list[str], new_items: list[str]) -> list[str]:
    combined = [str(item).strip() for item in existing if str(item).strip()]
    combined.extend(str(item).strip() for item in new_items if str(item).strip())
    return list(dict.fromkeys(combined))


def _append_cycle(
    loop_artifact: dict,
    *,
    cycle_number: int,
    company_turn: dict,
    candidate_turn: dict,
    analyst_decision: dict,
    company_raw: str,
    candidate_raw: str,
    analyst_raw: str,
) -> dict:
    loop_artifact["cycles"].append(
        {
            "cycle": cycle_number,
            "company_turn": {
                "raw": company_raw,
                "parsed": company_turn,
                "error": "",
            },
            "candidate_turn": {
                "raw": candidate_raw,
                "parsed": candidate_turn,
                "error": "",
            },
            "analyst_decision": {
                "raw": analyst_raw,
                "parsed": analyst_decision,
                "error": "",
            },
        }
    )
    return loop_artifact


def run_intraround_loop(
    data: dict,
    phase: str,
    client: BaseLLMClient | None = None,
    model: str = DEFAULT_MODEL_NAME,
    max_cycles: int = DEFAULT_MAX_CYCLES,
) -> dict:
    if phase != INTRAROUND_PHASE:
        raise ValueError("Intra-round loop is only supported for NEGOTIATION.")
    if max_cycles < 1:
        raise ValueError("max_cycles must be at least 1.")

    validation_errors = validate_state_for_round(data, phase)
    if validation_errors:
        raise ValueError("; ".join(validation_errors))

    loop_artifact = build_empty_loop_artifact(phase=phase, max_cycles=max_cycles)
    loop_artifact["generated_at"] = _utc_now_iso()
    aggregated_agreements: list[str] = []
    aggregated_open_issues: list[str] = []
    aggregated_suggested_rfis: list[dict] = []

    for cycle in range(1, max_cycles + 1):
        company_prompt = _build_role_prompt(
            role="company",
            phase=phase,
            cycle=cycle,
            data=data,
            loop_artifact=loop_artifact,
        )
        company_parsed, company_error, company_raw = _call_structured_llm(
            prompt=company_prompt,
            context=f"company turn for cycle {cycle}",
            client=client,
            model=model,
        )
        if company_error:
            loop_artifact["status"] = "error"
            loop_artifact["stop_reason"] = STOP_REASON_LLM_ERROR
            loop_artifact["error"] = company_error
            loop_artifact["completed_at"] = _utc_now_iso()
            loop_artifact["cycles"].append(
                {
                    "cycle": cycle,
                    "company_turn": {"raw": company_raw, "parsed": {}, "error": company_error},
                    "candidate_turn": {"raw": "", "parsed": {}, "error": ""},
                    "analyst_decision": {"raw": "", "parsed": {}, "error": ""},
                }
            )
            return loop_artifact

        candidate_prompt = _build_role_prompt(
            role="candidate",
            phase=phase,
            cycle=cycle,
            data=data,
            loop_artifact=loop_artifact,
        )
        candidate_parsed, candidate_error, candidate_raw = _call_structured_llm(
            prompt=candidate_prompt,
            context=f"candidate turn for cycle {cycle}",
            client=client,
            model=model,
        )
        if candidate_error:
            loop_artifact["status"] = "error"
            loop_artifact["stop_reason"] = STOP_REASON_LLM_ERROR
            loop_artifact["error"] = candidate_error
            loop_artifact["completed_at"] = _utc_now_iso()
            loop_artifact["cycles"].append(
                {
                    "cycle": cycle,
                    "company_turn": {"raw": company_raw, "parsed": _normalize_turn_payload(company_parsed), "error": ""},
                    "candidate_turn": {"raw": candidate_raw, "parsed": {}, "error": candidate_error},
                    "analyst_decision": {"raw": "", "parsed": {}, "error": ""},
                }
            )
            return loop_artifact

        analyst_prompt = _build_analyst_prompt(
            phase=phase,
            cycle=cycle,
            data=data,
            loop_artifact=loop_artifact,
            company_turn=_normalize_turn_payload(company_parsed),
            candidate_turn=_normalize_turn_payload(candidate_parsed),
        )
        analyst_parsed, analyst_error, analyst_raw = _call_structured_llm(
            prompt=analyst_prompt,
            context=f"analyst decision for cycle {cycle}",
            client=client,
            model=model,
        )
        if analyst_error:
            loop_artifact["status"] = "error"
            loop_artifact["stop_reason"] = STOP_REASON_LLM_ERROR
            loop_artifact["error"] = analyst_error
            loop_artifact["completed_at"] = _utc_now_iso()
            _append_cycle(
                loop_artifact,
                cycle_number=cycle,
                company_turn=_normalize_turn_payload(company_parsed),
                candidate_turn=_normalize_turn_payload(candidate_parsed),
                analyst_decision={},
                company_raw=company_raw,
                candidate_raw=candidate_raw,
                analyst_raw=analyst_raw,
            )
            loop_artifact["cycles"][-1]["analyst_decision"]["error"] = analyst_error
            return loop_artifact

        normalized_company_turn = _normalize_turn_payload(company_parsed)
        normalized_candidate_turn = _normalize_turn_payload(candidate_parsed)
        normalized_analyst_turn = _normalize_analyst_payload(analyst_parsed)
        normalized_suggested_rfis = _normalize_suggested_rfis_for_phase(
            phase=phase,
            data=data,
            suggested_rfis=normalized_analyst_turn.get("suggested_rfis", []),
        )

        aggregated_agreements = _accumulate_strings(
            aggregated_agreements,
            normalized_company_turn["agreements"]
            + normalized_candidate_turn["agreements"]
            + normalized_analyst_turn["agreements"],
        )
        aggregated_open_issues = _accumulate_strings(
            aggregated_open_issues,
            normalized_company_turn["open_issues"]
            + normalized_candidate_turn["open_issues"]
            + normalized_analyst_turn["open_issues"],
        )
        aggregated_suggested_rfis = _dedupe_dicts(
            aggregated_suggested_rfis + normalized_suggested_rfis,
            ("target_side", "subtopic_id", "question"),
        )

        loop_artifact = _append_cycle(
            loop_artifact,
            cycle_number=cycle,
            company_turn=normalized_company_turn,
            candidate_turn=normalized_candidate_turn,
            analyst_decision=normalized_analyst_turn,
            company_raw=company_raw,
            candidate_raw=candidate_raw,
            analyst_raw=analyst_raw,
        )
        loop_artifact["agreements"] = aggregated_agreements
        loop_artifact["open_issues"] = aggregated_open_issues
        loop_artifact["suggested_rfis"] = aggregated_suggested_rfis
        loop_artifact["draft_summary"] = normalized_analyst_turn.get("summary", "")

        analyst_action = normalized_analyst_turn.get("action")
        analyst_reason = normalized_analyst_turn.get("reason")

        if analyst_action == ANALYST_ACTION_NEEDS_RFI:
            loop_artifact["status"] = "completed"
            loop_artifact["stop_reason"] = STOP_REASON_NEEDS_RFI
            loop_artifact["completed_at"] = _utc_now_iso()
            return loop_artifact

        if analyst_action == ANALYST_ACTION_STOP:
            loop_artifact["status"] = "completed"
            loop_artifact["stop_reason"] = analyst_reason if analyst_reason in STOP_REASONS else STOP_REASON_CONVERGED
            loop_artifact["completed_at"] = _utc_now_iso()
            return loop_artifact

        if cycle >= max_cycles:
            loop_artifact["status"] = "completed"
            loop_artifact["stop_reason"] = STOP_REASON_MAX_CYCLES
            loop_artifact["completed_at"] = _utc_now_iso()
            return loop_artifact

    loop_artifact["status"] = "completed"
    loop_artifact["stop_reason"] = STOP_REASON_MAX_CYCLES
    loop_artifact["completed_at"] = _utc_now_iso()
    return loop_artifact
