import streamlit as st

st.title("01 · Input negoziazione")

if st.button("Carica dati demo"):
    st.session_state["demo_data"] = {
        "job_description": "TechNova cerca un BIM Coordinator senior per progetti industriali. Ruolo ibrido, coordinamento modelli, clash detection, ACC, supporto al team di progettazione e interfaccia con PM.",
        "company_name": "TechNova Engineering",
        "company_salary": "42000",
        "company_smart": "Ibrido",
        "company_bonus": "Bonus annuale 8%",
        "company_car": "Sì",
        "company_benefits": "Ticket 8€, assicurazione sanitaria, laptop, telefono",
        "candidate_name": "Marco Rinaldi",
        "candidate_salary": "48000",
        "candidate_smart": "Full remote",
        "candidate_bonus": "Bonus performance 10%",
        "candidate_car": "Sì",
        "candidate_benefits": "Ticket 8€, formazione, assicurazione, auto uso promiscuo",
        "priorities": {
            "salary": {"company": 3, "candidate": 5},
            "smart": {"company": 3, "candidate": 4},
            "bonus": {"company": 2, "candidate": 3},
            "car": {"company": 2, "candidate": 4},
            "benefits": {"company": 3, "candidate": 4},
        },
    }
    st.rerun()

demo = st.session_state.get("demo_data", {})
demo_priorities = demo.get("priorities", {})

smart_options = ["Nessuno", "Ibrido", "Full remote"]
car_options = ["No", "Sì"]

with st.form("negotiation_form"):
    st.subheader("Documento comune")
    job_description = st.text_area(
        "Job description / contesto comune",
        value=demo.get("job_description", ""),
        height=180,
        placeholder="Inserisci il contesto comune della negoziazione...",
    )

    st.subheader("Azienda")
    company_name = st.text_input(
        "Nome azienda",
        value=demo.get("company_name", "Azienda")
    )
    company_salary = st.text_input(
        "RAL offerta",
        value=demo.get("company_salary", "40000")
    )
    company_smart = st.selectbox(
        "Smart work",
        smart_options,
        index=smart_options.index(demo.get("company_smart", "Ibrido"))
    )
    company_bonus = st.text_input(
        "Bonus",
        value=demo.get("company_bonus", "Bonus annuale")
    )
    company_car = st.selectbox(
        "Auto aziendale",
        car_options,
        index=car_options.index(demo.get("company_car", "No"))
    )
    company_benefits = st.text_input(
        "Benefit",
        value=demo.get("company_benefits", "Ticket, assicurazione")
    )

    st.subheader("Candidato")
    candidate_name = st.text_input(
        "Nome candidato",
        value=demo.get("candidate_name", "Candidato")
    )
    candidate_salary = st.text_input(
        "RAL desiderata",
        value=demo.get("candidate_salary", "45000")
    )
    candidate_smart = st.selectbox(
        "Smart work desiderato",
        smart_options,
        index=smart_options.index(demo.get("candidate_smart", "Ibrido"))
    )
    candidate_bonus = st.text_input(
        "Bonus desiderato",
        value=demo.get("candidate_bonus", "Bonus performance")
    )
    candidate_car = st.selectbox(
        "Auto aziendale desiderata",
        car_options,
        index=car_options.index(demo.get("candidate_car", "No"))
    )
    candidate_benefits = st.text_input(
        "Benefit desiderati",
        value=demo.get("candidate_benefits", "Ticket, formazione")
    )

    st.subheader("Priorità topic (1–5)")

    topics = [
        ("salary", "Compenso"),
        ("smart", "Smart work"),
        ("bonus", "Bonus"),
        ("car", "Auto aziendale"),
        ("benefits", "Benefit"),
    ]

    for topic_key, topic_label in topics:
        col1, col2 = st.columns(2)

        with col1:
            st.caption(f"{topic_label} · Priorità azienda")
            st.feedback(
                "stars",
                key=f"prio_company_{topic_key}",
                default=demo_priorities.get(topic_key, {}).get("company", 3) - 1,
            )

        with col2:
            st.caption(f"{topic_label} · Priorità candidato")
            st.feedback(
                "stars",
                key=f"prio_candidate_{topic_key}",
                default=demo_priorities.get(topic_key, {}).get("candidate", 3) - 1,
            )

    submitted = st.form_submit_button("Salva input")

if submitted:
    st.session_state["negotiation_data"] = {
        "job_description": job_description,
        "company": {
            "name": company_name,
            "salary": company_salary,
            "smart": company_smart,
            "bonus": company_bonus,
            "car": company_car,
            "benefits": company_benefits,
        },
        "candidate": {
            "name": candidate_name,
            "salary": candidate_salary,
            "smart": candidate_smart,
            "bonus": candidate_bonus,
            "car": candidate_car,
            "benefits": candidate_benefits,
        },
        "priorities": {
            "salary": {
                "company": st.session_state.get("prio_company_salary", 2) + 1,
                "candidate": st.session_state.get("prio_candidate_salary", 2) + 1,
            },
            "smart": {
                "company": st.session_state.get("prio_company_smart", 2) + 1,
                "candidate": st.session_state.get("prio_candidate_smart", 2) + 1,
            },
            "bonus": {
                "company": st.session_state.get("prio_company_bonus", 2) + 1,
                "candidate": st.session_state.get("prio_candidate_bonus", 2) + 1,
            },
            "car": {
                "company": st.session_state.get("prio_company_car", 2) + 1,
                "candidate": st.session_state.get("prio_candidate_car", 2) + 1,
            },
            "benefits": {
                "company": st.session_state.get("prio_company_benefits", 2) + 1,
                "candidate": st.session_state.get("prio_candidate_benefits", 2) + 1,
            },
        },
    }
    st.success("Input salvato. Vai alla pagina 02 · Rounds.")