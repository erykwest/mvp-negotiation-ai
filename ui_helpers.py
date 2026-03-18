from pathlib import Path

from core.intraround_loop import normalize_loop_artifact
from core.repository import generate_session_id, normalize_session_id
from core.storage import get_session_file_path


def _as_text(value: object) -> str:
    return str(value or "").strip()


def build_negotiation_loop_summary(state: dict) -> str | None:
    results = state.get("results")
    if not isinstance(results, dict):
        return None

    negotiation_result = results.get("NEGOTIATION")
    if not isinstance(negotiation_result, dict):
        return None

    raw_loop = negotiation_result.get("loop")
    if raw_loop is None:
        return None

    loop = normalize_loop_artifact(raw_loop, phase="NEGOTIATION")
    cycles = loop.get("cycles", [])
    draft_summary = _as_text(loop.get("draft_summary"))
    stop_reason = _as_text(loop.get("stop_reason"))

    if not cycles and not draft_summary and not stop_reason:
        return None

    lines = [
        "### Intra-round loop",
        f"- Status: {loop.get('status', '-')}",
    ]

    max_cycles = loop.get("max_cycles")
    if max_cycles is not None:
        lines.append(f"- Max cycles: {max_cycles}")

    generated_at = _as_text(loop.get("generated_at"))
    if generated_at:
        lines.append(f"- Captured at: {generated_at}")

    if draft_summary:
        lines.extend(["", "#### Outcome", draft_summary])

    if stop_reason:
        lines.extend(["", "#### Stop reason", stop_reason])

    if cycles:
        latest_cycle = cycles[-1]
        latest_cycle_number = latest_cycle.get("cycle", len(cycles))
        company_summary = _as_text(latest_cycle.get("company_turn", {}).get("summary"))
        candidate_summary = _as_text(latest_cycle.get("candidate_turn", {}).get("summary"))
        analyst_reason = _as_text(latest_cycle.get("analyst_decision", {}).get("reason"))

        lines.extend(["", f"#### Transcript summary (cycle {latest_cycle_number})"])
        if company_summary:
            lines.append(f"- Company: {company_summary}")
        if candidate_summary:
            lines.append(f"- Candidate: {candidate_summary}")
        if analyst_reason:
            lines.append(f"- Analyst: {analyst_reason}")
        if not company_summary and not candidate_summary and not analyst_reason:
            lines.append("- No transcript summaries available.")

    return "\n".join(lines)


def get_session_id(st, namespace: str) -> str:
    input_key = f"{namespace}_session_id_input"
    query_value = st.query_params.get("session", "")

    if input_key not in st.session_state:
        st.session_state[input_key] = query_value or generate_session_id()
    elif query_value:
        normalized_query = normalize_session_id(query_value)
        if normalized_query != normalize_session_id(st.session_state[input_key]):
            st.session_state[input_key] = normalized_query

    st.sidebar.subheader("Session")
    session_value = st.sidebar.text_input(
        "Session ID",
        key=input_key,
        help="Use the same Session ID in company, candidate, and admin apps to collaborate on one negotiation.",
    )

    if st.sidebar.button("Generate new session", key=f"{namespace}_new_session"):
        new_session_id = generate_session_id()
        st.session_state[input_key] = new_session_id
        st.query_params["session"] = new_session_id
        st.rerun()

    normalized = normalize_session_id(session_value)
    st.query_params["session"] = normalized

    session_file = Path(get_session_file_path(normalized))
    st.sidebar.code(normalized)
    st.sidebar.caption("Copy this Session ID or share the page URL to keep everyone on the same negotiation.")
    st.sidebar.caption(f"Storage file: `{session_file.as_posix()}`")
    return normalized
