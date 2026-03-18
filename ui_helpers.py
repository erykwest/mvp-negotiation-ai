from pathlib import Path

from core.repository import generate_session_id, normalize_session_id
from core.storage import get_session_file_path


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
