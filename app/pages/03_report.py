import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import streamlit as st
from core.report import build_report

st.title("03 · Report finale")

data = st.session_state.get("negotiation_data")
results = st.session_state.get("round_results")

if not data:
    st.warning("Mancano gli input iniziali.")
    st.stop()

if not results:
    st.warning("Mancano i risultati dei round. Esegui prima la pagina 02 · Rounds.")
    st.stop()

report = build_report(data, results)

st.subheader("Report finale")
st.markdown(report)

st.download_button(
    "Scarica report .md",
    data=report,
    file_name="negotiation_report.md",
    mime="text/markdown",
)