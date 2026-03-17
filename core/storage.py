import json
import uuid
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
SESSION_FILE = DATA_DIR / "session_001.json"

PHASES = ["ALIGNMENT", "NEGOTIATION", "CLOSING"]

DEFAULT_STATE = {
    "job_description": "",
    "company": {},
    "candidate": {},
    "priorities": {},
    "dynamic_topics": [],
    "workflow": {
        "current_phase": "ALIGNMENT",
        "status": "editing",   # editing | review | closed
    },
    "results": {},
}


def _merge_defaults(state: dict) -> dict:
    merged = DEFAULT_STATE.copy()
    merged.update(state or {})
    merged["workflow"] = {
        **DEFAULT_STATE["workflow"],
        **(state.get("workflow", {}) if state else {})
    }
    merged["results"] = state.get("results", {}) if state else {}
    merged["dynamic_topics"] = state.get("dynamic_topics", []) if state else []
    return merged


def load_state():
    if not SESSION_FILE.exists():
        save_state(DEFAULT_STATE)
    with open(SESSION_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
    return _merge_defaults(state)


def save_state(state):
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def save_company(payload):
    state = load_state()
    state["job_description"] = payload["job_description"]
    state["company"] = payload["company"]

    state["priorities"] = state.get("priorities", {})
    for k, v in payload["priorities"].items():
        state["priorities"].setdefault(k, {})
        state["priorities"][k]["company"] = v

    save_state(state)


def save_candidate(payload):
    state = load_state()
    state["candidate"] = payload["candidate"]

    state["priorities"] = state.get("priorities", {})
    for k, v in payload["priorities"].items():
        state["priorities"].setdefault(k, {})
        state["priorities"][k]["candidate"] = v

    save_state(state)


def is_ready(state):
    return (
        bool(state.get("job_description"))
        and bool(state.get("company"))
        and bool(state.get("candidate"))
    )


def save_round_result(phase: str, result: dict):
    state = load_state()
    state["results"][phase] = result
    state["workflow"]["status"] = "review"
    save_state(state)


def advance_phase():
    state = load_state()
    current = state["workflow"]["current_phase"]

    if current == "CLOSING":
        state["workflow"]["status"] = "closed"
    else:
        idx = PHASES.index(current)
        state["workflow"]["current_phase"] = PHASES[idx + 1]
        state["workflow"]["status"] = "editing"

    save_state(state)


def reset_workflow():
    state = load_state()
    state["workflow"] = {
        "current_phase": "ALIGNMENT",
        "status": "editing",
    }
    state["results"] = {}
    state["dynamic_topics"] = []
    save_state(state)


def add_dynamic_topic(side: str, section: str, title: str, answer: str):
    state = load_state()
    topic = {
        "id": uuid.uuid4().hex[:8],
        "section": section,
        "title": title.strip(),
        "created_by": side,
        "company_answer": answer.strip() if side == "company" else "",
        "candidate_answer": answer.strip() if side == "candidate" else "",
    }
    state["dynamic_topics"].append(topic)
    save_state(state)


def update_dynamic_topic_answer(topic_id: str, side: str, answer: str):
    state = load_state()
    field = "company_answer" if side == "company" else "candidate_answer"

    for topic in state.get("dynamic_topics", []):
        if topic["id"] == topic_id:
            topic[field] = answer.strip()
            break

    save_state(state)


def edit_dynamic_topic(topic_id: str, side: str, section: str, title: str, answer: str):
    state = load_state()

    for topic in state.get("dynamic_topics", []):
        if topic["id"] == topic_id and topic["created_by"] == side:
            topic["section"] = section.strip()
            topic["title"] = title.strip()
            if side == "company":
                topic["company_answer"] = answer.strip()
            else:
                topic["candidate_answer"] = answer.strip()
            break

    save_state(state)


def delete_dynamic_topic(topic_id: str, side: str):
    state = load_state()
    state["dynamic_topics"] = [
        t for t in state.get("dynamic_topics", [])
        if not (t["id"] == topic_id and t["created_by"] == side)
    ]
    save_state(state)


def dynamic_topics_complete(state=None):
    state = state or load_state()
    for topic in state.get("dynamic_topics", []):
        if not topic.get("company_answer", "").strip():
            return False
        if not topic.get("candidate_answer", "").strip():
            return False
    return True