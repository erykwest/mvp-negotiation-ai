import streamlit as st
from core.storage import (
    load_state,
    save_candidate,
    add_dynamic_topic,
    update_dynamic_topic_answer,
    edit_dynamic_topic,
    delete_dynamic_topic,
)

st.set_page_config(page_title="Candidate", layout="wide")
st.title("Candidate Interface")

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

with st.form("candidate_form"):
    st.info("La job description arriva dall'interfaccia azienda.")
    st.text_area(
        "Job description",
        value=state.get("job_description", ""),
        height=180,
        disabled=True
    )

    candidate_name = st.text_input(
        "Nome candidato",
        value=state.get("candidate", {}).get("name", "Marco Rinaldi")
    )
    candidate_salary = st.text_input(
        "RAL desiderata",
        value=state.get("candidate", {}).get("salary", "48000")
    )
    candidate_smart = st.selectbox(
        "Smart work desiderato",
        smart_options,
        index=smart_options.index(state.get("candidate", {}).get("smart", "Full remote"))
    )
    candidate_bonus = st.text_input(
        "Bonus desiderato",
        value=state.get("candidate", {}).get("bonus", "Bonus performance 10%")
    )
    candidate_car = st.selectbox(
        "Auto aziendale desiderata",
        car_options,
        index=car_options.index(state.get("candidate", {}).get("car", "Sì"))
    )
    candidate_benefits = st.text_input(
        "Benefit desiderati",
        value=state.get("candidate", {}).get(
            "benefits",
            "Ticket 8€, formazione, assicurazione, auto uso promiscuo"
        )
    )

    st.subheader("Priorità candidato")
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
            key=f"candidate_{key}",
            default=prio.get(key, {}).get("candidate", 3) - 1
        ) + 1

    submitted = st.form_submit_button("Salva dati candidato")

if submitted:
    save_candidate(
        {
            "candidate": {
                "name": candidate_name,
                "salary": candidate_salary,
                "smart": candidate_smart,
                "bonus": candidate_bonus,
                "car": candidate_car,
                "benefits": candidate_benefits,
            },
            "priorities": values,
        }
    )
    st.success("Dati candidato salvati.")
    st.rerun()

if workflow.get("current_phase") == "NEGOTIATION":
    st.divider()
    st.subheader("Topic aggiuntivi Round 2")

    if workflow.get("status") == "editing":
        with st.form("candidate_new_topic"):
            section = st.selectbox("Sezione", topic_sections)
            title = st.text_input("Nuovo topic / subtopic")
            answer = st.text_area("Posizione candidato sul topic")
            add_new = st.form_submit_button("Aggiungi topic")

        if add_new and title.strip() and answer.strip():
            add_dynamic_topic("candidate", section, title, answer)
            st.success("Topic aggiunto.")
            st.rerun()

        own_topics = [
            t for t in state.get("dynamic_topics", [])
            if t.get("created_by") == "candidate"
        ]

        if own_topics:
            st.markdown("### I tuoi topic")
        else:
            st.caption("Non hai ancora aggiunto topic.")

        for topic in own_topics:
            with st.expander(f"[{topic['section']}] {topic['title']}"):
                with st.form(f"edit_candidate_topic_{topic['id']}"):
                    new_section = st.selectbox(
                        "Sezione",
                        topic_sections,
                        index=topic_sections.index(topic["section"])
                    )
                    new_title = st.text_input("Titolo", value=topic["title"])
                    new_answer = st.text_area(
                        "Posizione candidato",
                        value=topic.get("candidate_answer", "")
                    )

                    col1, col2 = st.columns(2)
                    with col1:
                        save_edit = st.form_submit_button("Salva modifiche")
                    with col2:
                        delete_it = st.form_submit_button("Elimina topic")

                if save_edit and new_title.strip() and new_answer.strip():
                    edit_dynamic_topic(
                        topic["id"],
                        "candidate",
                        new_section,
                        new_title,
                        new_answer,
                    )
                    st.success("Topic aggiornato.")
                    st.rerun()

                if delete_it:
                    delete_dynamic_topic(topic["id"], "candidate")
                    st.success("Topic eliminato.")
                    st.rerun()

    elif workflow.get("status") == "review":
        st.info("Ora puoi rispondere a tutti i topic aggiuntivi prima del Round 3.")

        for topic in state.get("dynamic_topics", []):
            with st.expander(f"[{topic['section']}] {topic['title']}"):
                st.caption(f"Creato da: {topic['created_by']}")
                candidate_answer = st.text_area(
                    "Risposta candidato",
                    value=topic.get("candidate_answer", ""),
                    key=f"candidate_topic_review_{topic['id']}"
                )
                st.text_area(
                    "Risposta azienda",
                    value=topic.get("company_answer", ""),
                    disabled=True,
                    key=f"candidate_topic_read_review_{topic['id']}"
                )
                if st.button(
                    "Salva risposta candidato",
                    key=f"save_candidate_topic_review_{topic['id']}"
                ):
                    update_dynamic_topic_answer(topic["id"], "candidate", candidate_answer)
                    st.success("Risposta salvata.")
                    st.rerun()