import streamlit as st
from core.storage import load_state, save_company

st.set_page_config(page_title="Company", layout="wide")
st.title("Company Interface")

state = load_state()
workflow = state.get("workflow", {})
st.caption(f"Fase corrente: {workflow.get('current_phase', 'ALIGNMENT')} · Stato: {workflow.get('status', 'editing')}")
if workflow.get("status") == "review":
    st.info("Un round è stato completato. Puoi aggiornare i dati in vista del round successivo.")
prio = state.get("priorities", {})
smart_options = ["Nessuno", "Ibrido", "Full remote"]
car_options = ["No", "Sì"]

with st.form("company_form"):
    job_description = st.text_area("Job description", value=state.get("job_description", ""), height=180)
    company_name = st.text_input("Nome azienda", value=state.get("company", {}).get("name", "TechNova Engineering"))
    company_salary = st.text_input("RAL offerta", value=state.get("company", {}).get("salary", "42000"))
    company_smart = st.selectbox("Smart work", smart_options, index=smart_options.index(state.get("company", {}).get("smart", "Ibrido")))
    company_bonus = st.text_input("Bonus", value=state.get("company", {}).get("bonus", "Bonus annuale 8%"))
    company_car = st.selectbox("Auto aziendale", car_options, index=car_options.index(state.get("company", {}).get("car", "Sì")))
    company_benefits = st.text_input("Benefit", value=state.get("company", {}).get("benefits", "Ticket 8€, assicurazione sanitaria, laptop, telefono"))

    st.subheader("Priorità azienda")
    topics = [("salary","Compenso"),("smart","Smart work"),("bonus","Bonus"),("car","Auto"),("benefits","Benefit")]
    values = {}
    for k, label in topics:
        st.caption(label)
        values[k] = st.feedback("stars", key=f"company_{k}", default=prio.get(k, {}).get("company", 3)-1) + 1

    submitted = st.form_submit_button("Salva dati azienda")

if submitted:
    save_company({
        "job_description": job_description,
        "company": {
            "name": company_name,
            "salary": company_salary,
            "smart": company_smart,
            "bonus": company_bonus,
            "car": company_car,
            "benefits": company_benefits,
        },
        "priorities": values,
    })
    st.success("Dati azienda salvati.")