import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import streamlit as st
from core.negotiation import run_rounds

st.title("02 · Rounds")

data = st.session_state.get("negotiation_data")

if not data:
    st.warning("Compila prima la pagina 01 · Input.")
    st.stop()

st.subheader("Riepilogo input")
st.json(data, expanded=False)

if st.button("Avvia negoziazione"):
    with st.spinner("Esecuzione round in corso..."):
        results = run_rounds(data)
        st.session_state["round_results"] = results
    st.success("Round completati.")
    st.rerun()

results = st.session_state.get("round_results")

if results:
    for round_name, round_content in results.items():
        st.markdown(f"## {round_name}")
        st.markdown("### Azienda")
        st.write(round_content["company"])
        st.markdown("### Candidato")
        st.write(round_content["candidate"])
        st.markdown("### Sintesi")
        st.write(round_content["summary"])