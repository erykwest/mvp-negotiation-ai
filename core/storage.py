import json
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
    return bool(state.get("job_description")) and bool(state.get("company")) and bool(state.get("candidate"))

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
    save_state(state)