from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4


def normalize_round_snapshots(round_snapshots: list[dict] | None) -> list[dict]:
    normalized: list[dict] = []
    for index, snapshot in enumerate(round_snapshots or [], start=1):
        if not isinstance(snapshot, dict):
            continue
        normalized.append(
            {
                "snapshot_id": str(snapshot.get("snapshot_id") or f"snap-{uuid4().hex[:12]}"),
                "sequence": int(snapshot.get("sequence", index)),
                "phase": str(snapshot.get("phase", "")).strip(),
                "captured_at": str(snapshot.get("captured_at", "")),
                "workflow": deepcopy(snapshot.get("workflow", {})),
                "job_description": snapshot.get("job_description", ""),
                "company": deepcopy(snapshot.get("company", {})),
                "candidate": deepcopy(snapshot.get("candidate", {})),
                "shared_topic_tree": deepcopy(snapshot.get("shared_topic_tree", {})),
                "private_inputs": deepcopy(snapshot.get("private_inputs", {})),
                "topic_tree": deepcopy(snapshot.get("topic_tree", {})),
                "result": deepcopy(snapshot.get("result", {})),
                "results": deepcopy(snapshot.get("results", {})),
                "shared_outputs": deepcopy(snapshot.get("shared_outputs", {})),
            }
        )
    return normalized


def build_round_snapshot(state: dict, phase: str, result: dict, sequence: int) -> dict:
    return {
        "snapshot_id": f"snap-{uuid4().hex[:12]}",
        "sequence": sequence,
        "phase": phase,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "workflow": deepcopy(state.get("workflow", {})),
        "job_description": state.get("job_description", ""),
        "company": deepcopy(state.get("company", {})),
        "candidate": deepcopy(state.get("candidate", {})),
        "shared_topic_tree": deepcopy(state.get("shared_topic_tree", {})),
        "private_inputs": deepcopy(state.get("private_inputs", {})),
        "topic_tree": deepcopy(state.get("topic_tree", {})),
        "result": deepcopy(result),
        "results": deepcopy(state.get("results", {})),
        "shared_outputs": deepcopy(state.get("shared_outputs", {})),
    }


def append_round_snapshot(state: dict, phase: str, result: dict) -> dict:
    snapshots = normalize_round_snapshots(state.get("round_snapshots"))
    snapshot = build_round_snapshot(state, phase, result, sequence=len(snapshots) + 1)
    snapshots.append(snapshot)
    state["round_snapshots"] = snapshots
    return snapshot


def get_round_snapshots(state: dict, phase: str | None = None) -> list[dict]:
    snapshots = normalize_round_snapshots(state.get("round_snapshots"))
    if phase is None:
        return snapshots
    return [snapshot for snapshot in snapshots if snapshot.get("phase") == phase]


def get_latest_round_snapshot(state: dict, phase: str) -> dict | None:
    snapshots = get_round_snapshots(state, phase=phase)
    if not snapshots:
        return None
    return snapshots[-1]
