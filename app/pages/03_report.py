import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import streamlit as st

from core.report import build_report

st.title("03 - Legacy final report")
st.caption("Legacy prototype page. Prefer the role-based apps for current workflows.")

data = st.session_state.get("negotiation_data")
results = st.session_state.get("round_results")

if not data:
    st.warning("Initial inputs are missing.")
    st.stop()

if not results:
    st.warning("Round results are missing. Run page 02 - Rounds first.")
    st.stop()

report = build_report(data, results)

st.subheader("Final report")
st.markdown(report)

st.download_button(
    "Download report .md",
    data=report,
    file_name="negotiation_report.md",
    mime="text/markdown",
)
