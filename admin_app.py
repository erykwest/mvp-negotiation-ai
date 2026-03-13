import streamlit as st
from core.storage import (
    load_state,
    is_ready,
    save_round_result,
    advance_phase,
    reset_workflow,
)
from core.negotiation import run_single_round
from core.report import build_report

PHASE_LABELS = {
    "ALIGNMENT": "ROUND 1 · ALIGNMENT",
    "NEGOTIATION": "ROUND 2 · NEGOTIATION",
    "CLOSING": "ROUND 3 · CLOSING",
}

st.set_page_config(page_title="Admin", layout="wide")
st.title("Admin / Negotiation Runner")

state = load_state()
workflow = state["workflow"]
current_phase = workflow["current_phase"]
status = workflow["status"]
results = state.get("results", {})

st.subheader("Oggetto della negoziazione")
st.info(state.get("job_description", "Nessuna job description"))

with st.expander("Dati grezzi sessione", expanded=False):
    st.json(state, expanded=False)

if not is_ready(state):
    st.warning("Manca ancora una delle due compilazioni.")
    st.stop()

st.markdown(f"### Fase corrente: **{PHASE_LABELS.get(current_phase, current_phase)}**")
st.caption(f"Stato workflow: {status}")

col1, col2 = st.columns(2)

with col1:
    if status == "editing":
        if st.button(f"Esegui {PHASE_LABELS.get(current_phase, current_phase)}"):
            with st.spinner("Round in corso..."):
                result = run_single_round(state, current_phase)
                save_round_result(current_phase, result)
            st.rerun()

with col2:
    if st.button("Reset workflow"):
        reset_workflow()
        st.rerun()

if status == "review":
    st.success("Round completato. Ora gli umani possono aggiornare input e priorità prima del round successivo.")

    current_result = load_state()["results"].get(current_phase)
    if current_result:
        with st.expander(f"{PHASE_LABELS.get(current_phase, current_phase)} · risultato corrente", expanded=True):
            st.markdown(current_result["summary"])

    if current_phase != "CLOSING":
        if st.button("Apri round successivo"):
            advance_phase()
            st.rerun()
    else:
        st.info("Closing completato. Puoi scaricare il report finale.")

if results:
    st.markdown("## Round eseguiti")
    for phase in ["ALIGNMENT", "NEGOTIATION", "CLOSING"]:
        if phase not in results:
            continue

        with st.expander(PHASE_LABELS[phase], expanded=False):
            st.markdown(results[phase]["summary"])

    report = build_report(load_state(), results)
    st.download_button(
        "Scarica report",
        report,
        "negotiation_report.md",
        "text/markdown",
    )