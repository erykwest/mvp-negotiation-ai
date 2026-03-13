import streamlit as st
from core.storage import load_state, save_candidate

st.set_page_config(page_title="Candidate", layout="wide")
st.title("Candidate Interface")

state = load_state()
workflow = state.get("workflow", {})
st.caption(f"Fase corrente: {workflow.get('current_phase', 'ALIGNMENT')} · Stato: {workflow.get('status', 'editing')}")
if workflow.get("status") == "review":
    st.info("Un round è stato completato. Puoi aggiornare i dati in vista del round successivo.")
prio = state.get("priorities", {})
smart_options = ["Nessuno", "Ibrido", "Full remote"]
car_options = ["No", "Sì"]

with st.form("candidate_form"):
    st.info("La job description arriva dall'interfaccia azienda.")
    st.text_area("Job description", value=state.get("job_description", ""), height=180, disabled=True)

    candidate_name = st.text_input("Nome candidato", value=state.get("candidate", {}).get("name", "Marco Rinaldi"))
    candidate_salary = st.text_input("RAL desiderata", value=state.get("candidate", {}).get("salary", "48000"))
    candidate_smart = st.selectbox("Smart work desiderato", smart_options, index=smart_options.index(state.get("candidate", {}).get("smart", "Full remote")))
    candidate_bonus = st.text_input("Bonus desiderato", value=state.get("candidate", {}).get("bonus", "Bonus performance 10%"))
    candidate_car = st.selectbox("Auto aziendale desiderata", car_options, index=car_options.index(state.get("candidate", {}).get("car", "Sì")))
    candidate_benefits = st.text_input("Benefit desiderati", value=state.get("candidate", {}).get("benefits", "Ticket 8€, formazione, assicurazione, auto uso promiscuo"))

    st.subheader("Priorità candidato")
    topics = [("salary","Compenso"),("smart","Smart work"),("bonus","Bonus"),("car","Auto"),("benefits","Benefit")]
    values = {}
    for k, label in topics:
        st.caption(label)
        values[k] = st.feedback("stars", key=f"candidate_{k}", default=prio.get(k, {}).get("candidate", 3)-1) + 1

    submitted = st.form_submit_button("Salva dati candidato")

if submitted:
    save_candidate({
        "candidate": {
            "name": candidate_name,
            "salary": candidate_salary,
            "smart": candidate_smart,
            "bonus": candidate_bonus,
            "car": candidate_car,
            "benefits": candidate_benefits,
        },
        "priorities": values,
    })
    st.success("Dati candidato salvati.")