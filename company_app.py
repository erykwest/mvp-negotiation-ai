import streamlit as st
from core.storage import (
    load_state,
    save_company,
    add_dynamic_topic,
    update_dynamic_topic_answer,
    edit_dynamic_topic,
    delete_dynamic_topic,
)

st.set_page_config(page_title="Company", layout="wide")
st.title("Company Interface")

state = load_state()
workflow = state.get("workflow", {})

st.caption(
    f"Fase corrente: {workflow.get('current_phase', 'ALIGNMENT')} · "
    f"Stato: {workflow.get('status', 'editing')}"
)

if workflow.get("status") == "review":
    st.info("Un round è stato completato. Puoi aggiornare i dati in vista del round successivo.")

prio = state.get("priorities", {})
smart_options = ["Nessuno", "Ibrido", "Full remote"]
car_options = ["No", "Sì"]
topic_sections = ["salary", "smart", "bonus", "car", "benefits", "notes"]

with st.form("company_form"):
    job_description = st.text_area(
        "Job description",
        value=state.get("job_description", ""),
        height=180
    )

    company_name = st.text_input(
        "Nome azienda",
        value=state.get("company", {}).get("name", "TechNova Engineering")
    )
    company_salary = st.text_input(
        "RAL offerta",
        value=state.get("company", {}).get("salary", "42000")
    )
    company_smart = st.selectbox(
        "Smart work",
        smart_options,
        index=smart_options.index(state.get("company", {}).get("smart", "Ibrido"))
    )
    company_bonus = st.text_input(
        "Bonus",
        value=state.get("company", {}).get("bonus", "Bonus annuale 8%")
    )
    company_car = st.selectbox(
        "Auto aziendale",
        car_options,
        index=car_options.index(state.get("company", {}).get("car", "Sì"))
    )
    company_benefits = st.text_input(
        "Benefit",
        value=state.get("company", {}).get(
            "benefits",
            "Ticket 8€, assicurazione sanitaria, laptop, telefono"
        )
    )

    st.subheader("Priorità azienda")
    priority_topics = [
        ("salary", "Compenso"),
        ("smart", "Smart work"),
        ("bonus", "Bonus"),
        ("car", "Auto"),
        ("benefits", "Benefit"),
    ]

    values = {}
    for key, label in priority_topics:
        st.caption(label)
        values[key] = st.feedback(
            "stars",
            key=f"company_{key}",
            default=prio.get(key, {}).get("company", 3) - 1
        ) + 1

    submitted = st.form_submit_button("Salva dati azienda")

if submitted:
    save_company(
        {
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
        }
    )
    st.success("Dati azienda salvati.")
    st.rerun()

if workflow.get("current_phase") == "NEGOTIATION":
    st.divider()
    st.subheader("Topic aggiuntivi Round 2")

    if workflow.get("status") == "editing":
        with st.form("company_new_topic"):
            section = st.selectbox("Sezione", topic_sections)
            title = st.text_input("Nuovo topic / subtopic")
            answer = st.text_area("Posizione azienda sul topic")
            add_new = st.form_submit_button("Aggiungi topic")

        if add_new and title.strip() and answer.strip():
            add_dynamic_topic("company", section, title, answer)
            st.success("Topic aggiunto.")
            st.rerun()

        own_topics = [
            t for t in state.get("dynamic_topics", [])
            if t.get("created_by") == "company"
        ]

        if own_topics:
            st.markdown("### I tuoi topic")
        else:
            st.caption("Non hai ancora aggiunto topic.")

        for topic in own_topics:
            with st.expander(f"[{topic['section']}] {topic['title']}"):
                with st.form(f"edit_company_topic_{topic['id']}"):
                    new_section = st.selectbox(
                        "Sezione",
                        topic_sections,
                        index=topic_sections.index(topic["section"])
                    )
                    new_title = st.text_input("Titolo", value=topic["title"])
                    new_answer = st.text_area(
                        "Posizione azienda",
                        value=topic.get("company_answer", "")
                    )

                    col1, col2 = st.columns(2)
                    with col1:
                        save_edit = st.form_submit_button("Salva modifiche")
                    with col2:
                        delete_it = st.form_submit_button("Elimina topic")

                if save_edit and new_title.strip() and new_answer.strip():
                    edit_dynamic_topic(
                        topic["id"],
                        "company",
                        new_section,
                        new_title,
                        new_answer,
                    )
                    st.success("Topic aggiornato.")
                    st.rerun()

                if delete_it:
                    delete_dynamic_topic(topic["id"], "company")
                    st.success("Topic eliminato.")
                    st.rerun()

    elif workflow.get("status") == "review":
        st.info("Ora puoi rispondere a tutti i topic aggiuntivi prima del Round 3.")

        for topic in state.get("dynamic_topics", []):
            with st.expander(f"[{topic['section']}] {topic['title']}"):
                st.caption(f"Creato da: {topic['created_by']}")
                company_answer = st.text_area(
                    "Risposta azienda",
                    value=topic.get("company_answer", ""),
                    key=f"company_topic_review_{topic['id']}"
                )
                st.text_area(
                    "Risposta candidato",
                    value=topic.get("candidate_answer", ""),
                    disabled=True,
                    key=f"company_topic_read_review_{topic['id']}"
                )
                if st.button(
                    "Salva risposta azienda",
                    key=f"save_company_topic_review_{topic['id']}"
                ):
                    update_dynamic_topic_answer(topic["id"], "company", company_answer)
                    st.success("Risposta salvata.")
                    st.rerun()