from copy import deepcopy
from datetime import datetime, timezone
import re
from uuid import uuid4

from core.topic_tree import POSITION_SIDES, find_subtopic, normalize_topic_tree

RFI_STATUS_OPEN = "OPEN"
RFI_STATUS_ANSWERED = "ANSWERED"
RFI_STATUSES = {RFI_STATUS_OPEN, RFI_STATUS_ANSWERED}
SUGGESTED_RFI_STATUS_SUGGESTED = "SUGGESTED"
SUGGESTED_RFI_STATUS_APPROVED = "APPROVED"
SUGGESTED_RFI_STATUS_DISMISSED = "DISMISSED"
SUGGESTED_RFI_STATUSES = {
    SUGGESTED_RFI_STATUS_SUGGESTED,
    SUGGESTED_RFI_STATUS_APPROVED,
    SUGGESTED_RFI_STATUS_DISMISSED,
}
RFI_REQUESTERS = set(POSITION_SIDES) | {"system", "admin"}
RFI_SUPPORTED_PHASES = ("ALIGNMENT", "NEGOTIATION")
PHASE_SEQUENCE = {"ALIGNMENT": 0, "NEGOTIATION": 1, "CLOSING": 2}
SUMMARY_RFI_SECTION_PATTERN = re.compile(
    r"^##\s*RFIs or clarifications needed\s*$([\s\S]*?)(?=^##\s|\Z)",
    flags=re.IGNORECASE | re.MULTILINE,
)
SUMMARY_RFI_BULLET_PATTERN = re.compile(
    r"^-\s*\[target:(company|candidate)\]\s*\[scope:([^\]]+)\]\s*(.+?)\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_rfi(
    *,
    phase: str,
    requested_by: str,
    target_side: str,
    question: str,
    subtopic_id: str | None = None,
    subtopic_title: str = "",
    status: str = RFI_STATUS_OPEN,
    response: str = "",
    rfi_id: str | None = None,
    created_at: str | None = None,
    answered_at: str = "",
) -> dict:
    normalized_status = status if status in RFI_STATUSES else RFI_STATUS_OPEN
    normalized_requested_by = requested_by if requested_by in RFI_REQUESTERS else "system"
    normalized_target_side = target_side if target_side in POSITION_SIDES else "candidate"

    return {
        "id": str(rfi_id or f"rfi-{uuid4().hex[:12]}"),
        "phase": str(phase or "").strip(),
        "status": normalized_status,
        "requested_by": normalized_requested_by,
        "target_side": normalized_target_side,
        "question": str(question or "").strip(),
        "response": str(response or "").strip(),
        "subtopic_id": str(subtopic_id).strip() if subtopic_id else None,
        "subtopic_title": str(subtopic_title or "").strip(),
        "created_at": str(created_at or _utc_now_iso()),
        "answered_at": str(answered_at or "").strip(),
    }


def build_suggested_rfi(
    *,
    phase: str,
    target_side: str,
    question: str,
    subtopic_id: str | None = None,
    subtopic_title: str = "",
    status: str = SUGGESTED_RFI_STATUS_SUGGESTED,
    source_summary: str = "",
    suggested_id: str | None = None,
    created_at: str | None = None,
    resolved_at: str = "",
) -> dict:
    normalized_status = status if status in SUGGESTED_RFI_STATUSES else SUGGESTED_RFI_STATUS_SUGGESTED
    normalized_target_side = target_side if target_side in POSITION_SIDES else "candidate"

    return {
        "id": str(suggested_id or f"srfi-{uuid4().hex[:12]}"),
        "phase": str(phase or "").strip(),
        "status": normalized_status,
        "requested_by": "system",
        "target_side": normalized_target_side,
        "question": str(question or "").strip(),
        "subtopic_id": str(subtopic_id).strip() if subtopic_id else None,
        "subtopic_title": str(subtopic_title or "").strip(),
        "source_summary": str(source_summary or "").strip(),
        "created_at": str(created_at or _utc_now_iso()),
        "resolved_at": str(resolved_at or "").strip(),
    }


def normalize_rfis(rfis: list[dict] | None) -> list[dict]:
    normalized: list[dict] = []
    for item in rfis or []:
        if not isinstance(item, dict):
            continue
        normalized.append(
            build_rfi(
                phase=item.get("phase", ""),
                requested_by=item.get("requested_by", "company"),
                target_side=item.get("target_side", "candidate"),
                question=item.get("question", ""),
                subtopic_id=item.get("subtopic_id"),
                subtopic_title=item.get("subtopic_title", ""),
                status=item.get("status", RFI_STATUS_OPEN),
                response=item.get("response", ""),
                rfi_id=item.get("id"),
                created_at=item.get("created_at"),
                answered_at=item.get("answered_at", ""),
            )
        )
    return normalized


def normalize_suggested_rfis(suggested_rfis: list[dict] | None) -> list[dict]:
    normalized: list[dict] = []
    for item in suggested_rfis or []:
        if not isinstance(item, dict):
            continue
        normalized.append(
            build_suggested_rfi(
                phase=item.get("phase", ""),
                target_side=item.get("target_side", "candidate"),
                question=item.get("question", ""),
                subtopic_id=item.get("subtopic_id"),
                subtopic_title=item.get("subtopic_title", ""),
                status=item.get("status", SUGGESTED_RFI_STATUS_SUGGESTED),
                source_summary=item.get("source_summary", ""),
                suggested_id=item.get("id"),
                created_at=item.get("created_at"),
                resolved_at=item.get("resolved_at", ""),
            )
        )
    return normalized


def get_rfis(
    state: dict,
    *,
    phase: str | None = None,
    status: str | None = None,
    requested_by: str | None = None,
    target_side: str | None = None,
    subtopic_id: str | None = None,
) -> list[dict]:
    rfis = normalize_rfis(state.get("rfis"))
    filtered: list[dict] = []
    for rfi in rfis:
        if phase is not None and rfi.get("phase") != phase:
            continue
        if status is not None and rfi.get("status") != status:
            continue
        if requested_by is not None and rfi.get("requested_by") != requested_by:
            continue
        if target_side is not None and rfi.get("target_side") != target_side:
            continue
        if subtopic_id is not None and rfi.get("subtopic_id") != subtopic_id:
            continue
        filtered.append(deepcopy(rfi))
    return filtered


def get_rfi_by_id(state: dict, rfi_id: str) -> dict | None:
    for rfi in normalize_rfis(state.get("rfis")):
        if rfi.get("id") == rfi_id:
            return deepcopy(rfi)
    return None


def get_suggested_rfis(
    state: dict,
    *,
    phase: str | None = None,
    status: str | None = None,
    target_side: str | None = None,
    subtopic_id: str | None = None,
) -> list[dict]:
    suggestions = normalize_suggested_rfis(state.get("suggested_rfis"))
    filtered: list[dict] = []
    for suggestion in suggestions:
        if phase is not None and suggestion.get("phase") != phase:
            continue
        if status is not None and suggestion.get("status") != status:
            continue
        if target_side is not None and suggestion.get("target_side") != target_side:
            continue
        if subtopic_id is not None and suggestion.get("subtopic_id") != subtopic_id:
            continue
        filtered.append(deepcopy(suggestion))
    return filtered


def get_suggested_rfi_by_id(state: dict, suggested_rfi_id: str) -> dict | None:
    for suggestion in normalize_suggested_rfis(state.get("suggested_rfis")):
        if suggestion.get("id") == suggested_rfi_id:
            return deepcopy(suggestion)
    return None


def has_open_rfis(state: dict, *, phase: str | None = None) -> bool:
    return bool(get_rfis(state, phase=phase, status=RFI_STATUS_OPEN))


def get_answered_rfis_before_phase(state: dict, phase: str) -> list[dict]:
    if phase not in PHASE_SEQUENCE:
        return []

    current_index = PHASE_SEQUENCE[phase]
    answered: list[dict] = []
    for rfi in get_rfis(state, status=RFI_STATUS_ANSWERED):
        rfi_phase = rfi.get("phase")
        if PHASE_SEQUENCE.get(rfi_phase, current_index + 1) < current_index:
            answered.append(rfi)
    return answered


def _find_subtopic_by_title(topic_tree: dict, title: str) -> tuple[dict | None, dict | None]:
    normalized_title = str(title or "").strip().lower()
    if not normalized_title or normalized_title == "general":
        return None, None

    normalized_tree = normalize_topic_tree(topic_tree)
    for main_topic in normalized_tree.get("main_topics", []):
        for subtopic in main_topic.get("subtopics", []):
            if str(subtopic.get("title", "")).strip().lower() == normalized_title:
                return main_topic, subtopic
    return None, None


def _suggestion_matches_existing_rfi(
    suggestion: dict,
    rfis: list[dict],
    suggested_rfis: list[dict],
) -> bool:
    normalized_question = str(suggestion.get("question", "")).strip().lower()
    normalized_target_side = suggestion.get("target_side")
    normalized_subtopic_id = suggestion.get("subtopic_id")

    for record in [*rfis, *suggested_rfis]:
        if str(record.get("question", "")).strip().lower() != normalized_question:
            continue
        if record.get("target_side") != normalized_target_side:
            continue
        if record.get("subtopic_id") != normalized_subtopic_id:
            continue
        if record.get("status") in {
            RFI_STATUS_OPEN,
            RFI_STATUS_ANSWERED,
            SUGGESTED_RFI_STATUS_SUGGESTED,
            SUGGESTED_RFI_STATUS_APPROVED,
        }:
            return True
    return False


def extract_suggested_rfis_from_summary(summary: str, phase: str, topic_tree: dict, state: dict | None = None) -> list[dict]:
    if phase not in RFI_SUPPORTED_PHASES:
        return []

    summary_text = str(summary or "").strip()
    if not summary_text:
        return []

    section_match = SUMMARY_RFI_SECTION_PATTERN.search(summary_text)
    if not section_match:
        return []

    section_text = section_match.group(1).strip()
    if not section_text or re.search(r"^-\s*none\s*$", section_text, flags=re.IGNORECASE | re.MULTILINE):
        return []

    existing_rfis = get_rfis(state or {})
    existing_suggested_rfis = get_suggested_rfis(state or {})
    suggestions: list[dict] = []

    for match in SUMMARY_RFI_BULLET_PATTERN.finditer(section_text):
        target_side = match.group(1).lower()
        scope = match.group(2).strip()
        question = match.group(3).strip()
        if not question:
            continue

        _main_topic, subtopic = _find_subtopic_by_title(topic_tree, scope)
        subtopic_id = subtopic.get("id") if subtopic else None
        subtopic_title = subtopic.get("title", "") if subtopic else ""

        if phase == "NEGOTIATION":
            if subtopic is None:
                continue
            if subtopic.get("phase_created") != "NEGOTIATION":
                continue
            if subtopic.get("created_by") != target_side:
                continue

        suggestion = build_suggested_rfi(
            phase=phase,
            target_side=target_side,
            question=question,
            subtopic_id=subtopic_id,
            subtopic_title=subtopic_title if subtopic else ("" if scope.lower() == "general" else scope),
            source_summary=match.group(0).strip(),
        )
        if _suggestion_matches_existing_rfi(suggestion, existing_rfis, existing_suggested_rfis + suggestions):
            continue
        suggestions.append(suggestion)

    return suggestions
