from copy import deepcopy
from datetime import datetime, timezone

from core.rfis import normalize_suggested_rfis

NEGOTIATION_PHASE = "NEGOTIATION"

LOOP_STATUS_DISABLED = "DISABLED"
LOOP_STATUS_READY = "READY"
LOOP_STATUS_RUNNING = "RUNNING"
LOOP_STATUS_COMPLETED = "COMPLETED"
LOOP_STATUS_FAILED = "FAILED"

LOOP_STATUSES = {
    LOOP_STATUS_DISABLED,
    LOOP_STATUS_READY,
    LOOP_STATUS_RUNNING,
    LOOP_STATUS_COMPLETED,
    LOOP_STATUS_FAILED,
}

LOOP_ACTION_CONTINUE = "continue"
LOOP_ACTION_STOP = "stop"
LOOP_ACTION_NEEDS_RFI = "needs_rfi"

LOOP_ACTIONS = {
    LOOP_ACTION_CONTINUE,
    LOOP_ACTION_STOP,
    LOOP_ACTION_NEEDS_RFI,
}

DEFAULT_LOOP_MAX_CYCLES = 3


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_text(value: object) -> str:
    return str(value or "").strip()


def _normalize_text_list(values: object) -> list[str]:
    if not isinstance(values, (list, tuple, set)):
        return []

    normalized: list[str] = []
    for value in values:
        text = _as_text(value)
        if text:
            normalized.append(text)
    return normalized


def _normalize_phase(phase: object | None) -> str:
    text = _as_text(phase).upper()
    return text or NEGOTIATION_PHASE


def build_loop_turn(
    *,
    content: str = "",
    prompt: str = "",
    response: str = "",
    summary: str = "",
    messages: list[object] | None = None,
    structured: dict | None = None,
) -> dict:
    return {
        "content": _as_text(content or response or summary),
        "prompt": _as_text(prompt),
        "response": _as_text(response),
        "summary": _as_text(summary),
        "messages": [deepcopy(message) for message in messages or []],
        "structured": deepcopy(structured or {}),
    }


def normalize_loop_turn(turn: object | None) -> dict:
    if isinstance(turn, str):
        return build_loop_turn(content=turn, response=turn, summary=turn)
    if not isinstance(turn, dict):
        return build_loop_turn()

    messages = turn.get("messages", [])
    if not isinstance(messages, list):
        messages = [messages]

    structured = turn.get("structured", {})
    if not isinstance(structured, dict):
        structured = {}

    return build_loop_turn(
        content=turn.get("content", turn.get("response", turn.get("summary", ""))),
        prompt=turn.get("prompt", ""),
        response=turn.get("response", turn.get("content", "")),
        summary=turn.get("summary", turn.get("response", "")),
        messages=messages,
        structured=structured,
    )


def build_analyst_decision(
    *,
    action: str = LOOP_ACTION_CONTINUE,
    reason: str = "",
    agreements: list[object] | None = None,
    open_issues: list[object] | None = None,
    suggested_rfis: list[dict] | None = None,
) -> dict:
    normalized_action = _as_text(action).lower()
    if normalized_action not in LOOP_ACTIONS:
        normalized_action = LOOP_ACTION_CONTINUE

    return {
        "action": normalized_action,
        "reason": _as_text(reason),
        "agreements": _normalize_text_list(agreements),
        "open_issues": _normalize_text_list(open_issues),
        "suggested_rfis": normalize_suggested_rfis(suggested_rfis),
    }


def normalize_analyst_decision(decision: object | None) -> dict:
    if isinstance(decision, str):
        return build_analyst_decision(reason=decision)
    if not isinstance(decision, dict):
        return build_analyst_decision()

    return build_analyst_decision(
        action=decision.get("action", LOOP_ACTION_CONTINUE),
        reason=decision.get("reason", ""),
        agreements=decision.get("agreements", []),
        open_issues=decision.get("open_issues", []),
        suggested_rfis=decision.get("suggested_rfis", []),
    )


def build_loop_cycle(
    *,
    cycle: int = 1,
    company_turn: dict | str | None = None,
    candidate_turn: dict | str | None = None,
    analyst_decision: dict | str | None = None,
) -> dict:
    return {
        "cycle": max(1, int(cycle or 1)),
        "company_turn": normalize_loop_turn(company_turn),
        "candidate_turn": normalize_loop_turn(candidate_turn),
        "analyst_decision": normalize_analyst_decision(analyst_decision),
    }


def normalize_loop_cycle(cycle: object | None) -> dict:
    if not isinstance(cycle, dict):
        return build_loop_cycle()

    raw_cycle = cycle.get("cycle", 1)
    try:
        normalized_cycle = int(raw_cycle)
    except (TypeError, ValueError):
        normalized_cycle = 1

    return build_loop_cycle(
        cycle=normalized_cycle,
        company_turn=cycle.get("company_turn"),
        candidate_turn=cycle.get("candidate_turn"),
        analyst_decision=cycle.get("analyst_decision"),
    )


def build_loop_artifact(
    *,
    enabled: bool = False,
    phase: str = NEGOTIATION_PHASE,
    status: str = LOOP_STATUS_DISABLED,
    max_cycles: int = DEFAULT_LOOP_MAX_CYCLES,
    cycles: list[dict] | None = None,
    stop_reason: str = "",
    agreements: list[object] | None = None,
    open_issues: list[object] | None = None,
    suggested_rfis: list[dict] | None = None,
    draft_summary: str = "",
    generated_at: str | None = None,
) -> dict:
    normalized_phase = _normalize_phase(phase)
    normalized_status = _as_text(status).upper()
    if normalized_status not in LOOP_STATUSES:
        normalized_status = LOOP_STATUS_DISABLED if not enabled else LOOP_STATUS_READY

    normalized_max_cycles = max(0, int(max_cycles or 0))
    return {
        "enabled": bool(enabled),
        "phase": normalized_phase,
        "status": normalized_status,
        "max_cycles": normalized_max_cycles,
        "cycles": [normalize_loop_cycle(item) for item in cycles or []],
        "stop_reason": _as_text(stop_reason),
        "agreements": _normalize_text_list(agreements),
        "open_issues": _normalize_text_list(open_issues),
        "suggested_rfis": normalize_suggested_rfis(suggested_rfis),
        "draft_summary": _as_text(draft_summary),
        "generated_at": _as_text(generated_at) or _utc_now_iso(),
    }


def normalize_loop_artifact(loop: object | None, phase: object | None = None) -> dict:
    normalized_phase = _normalize_phase(phase if phase is not None else (loop.get("phase") if isinstance(loop, dict) else None))
    if not isinstance(loop, dict):
        return build_loop_artifact(enabled=False, phase=normalized_phase, status=LOOP_STATUS_DISABLED, max_cycles=0, cycles=[])

    if normalized_phase != NEGOTIATION_PHASE:
        return build_loop_artifact(
            enabled=False,
            phase=normalized_phase,
            status=LOOP_STATUS_DISABLED,
            max_cycles=0,
            cycles=[],
            stop_reason="",
            agreements=[],
            open_issues=[],
            suggested_rfis=[],
            draft_summary="",
            generated_at=loop.get("generated_at"),
        )

    enabled = bool(loop.get("enabled", False)) and normalized_phase == NEGOTIATION_PHASE
    status = _as_text(loop.get("status", LOOP_STATUS_DISABLED)).upper()
    if status not in LOOP_STATUSES:
        status = LOOP_STATUS_DISABLED if not enabled else LOOP_STATUS_READY

    max_cycles_value = loop.get("max_cycles", DEFAULT_LOOP_MAX_CYCLES)
    try:
        normalized_max_cycles = max(0, int(max_cycles_value))
    except (TypeError, ValueError):
        normalized_max_cycles = DEFAULT_LOOP_MAX_CYCLES
    return build_loop_artifact(
        enabled=enabled,
        phase=normalized_phase,
        status=status,
        max_cycles=normalized_max_cycles,
        cycles=loop.get("cycles", []),
        stop_reason=loop.get("stop_reason", ""),
        agreements=loop.get("agreements", []),
        open_issues=loop.get("open_issues", []),
        suggested_rfis=loop.get("suggested_rfis", []),
        draft_summary=loop.get("draft_summary", ""),
        generated_at=loop.get("generated_at"),
    )


def attach_loop_artifact(result: dict | None, loop: object | None, phase: object | None = None) -> dict:
    normalized_result = deepcopy(result or {})
    normalized_result["loop"] = normalize_loop_artifact(loop, phase=phase or normalized_result.get("phase"))
    return normalized_result


def normalize_round_result(result: dict | None, phase: object | None = None) -> dict:
    normalized_result = deepcopy(result or {})
    if "loop" in normalized_result and normalized_result["loop"] is not None:
        normalized_result["loop"] = normalize_loop_artifact(normalized_result.get("loop"), phase=phase or normalized_result.get("phase"))
    return normalized_result
