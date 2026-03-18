import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import streamlit as st

from core.negotiation import run_rounds

st.title("02 - Legacy rounds")
st.caption("Legacy prototype page. Prefer the role-based apps for current workflows.")

data = st.session_state.get("negotiation_data")

if not data:
    st.warning("Complete page 01 - Input first.")
    st.stop()

st.subheader("Input summary")
st.json(data, expanded=False)

if st.button("Start negotiation"):
    with st.spinner("Running rounds..."):
        results = run_rounds(data)
        st.session_state["round_results"] = results
    st.success("Rounds completed.")
    st.rerun()

results = st.session_state.get("round_results")

if results:
    for round_name, round_content in results.items():
        st.markdown(f"## {round_name}")
        st.markdown("### Company")
        st.write(round_content["company"])
        st.markdown("### Candidate")
        st.write(round_content["candidate"])
        st.markdown("### Summary")
        st.write(round_content["summary"])
