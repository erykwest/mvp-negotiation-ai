import streamlit as st

st.title("01 - Legacy input")
st.caption("Legacy prototype page. Prefer the role-based apps for current workflows.")

if st.button("Load demo data"):
    st.session_state["demo_data"] = {
        "job_description": (
            "TechNova is hiring a senior BIM Coordinator for industrial projects. "
            "Hybrid role covering model coordination, clash detection, ACC, support for the design team, "
            "and collaboration with project managers."
        ),
        "company_name": "TechNova Engineering",
        "company_salary": "42000",
        "company_smart": "Hybrid",
        "company_bonus": "Annual bonus 8%",
        "company_car": "Yes",
        "company_benefits": "Meal tickets, health insurance, laptop, phone",
        "candidate_name": "Marco Rinaldi",
        "candidate_salary": "48000",
        "candidate_smart": "Full remote",
        "candidate_bonus": "Performance bonus 10%",
        "candidate_car": "Yes",
        "candidate_benefits": "Meal tickets, training, insurance, mixed-use car",
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

smart_options = ["None", "Hybrid", "Full remote"]
car_options = ["No", "Yes"]

with st.form("negotiation_form"):
    st.subheader("Shared document")
    job_description = st.text_area(
        "Job description / shared context",
        value=demo.get("job_description", ""),
        height=180,
        placeholder="Enter the shared negotiation context...",
    )

    st.subheader("Company")
    company_name = st.text_input("Company name", value=demo.get("company_name", "Company"))
    company_salary = st.text_input("Offered salary", value=demo.get("company_salary", "40000"))
    company_smart = st.selectbox(
        "Smart work",
        smart_options,
        index=smart_options.index(demo.get("company_smart", "Hybrid")),
    )
    company_bonus = st.text_input("Bonus", value=demo.get("company_bonus", "Annual bonus"))
    company_car = st.selectbox(
        "Company car",
        car_options,
        index=car_options.index(demo.get("company_car", "No")),
    )
    company_benefits = st.text_input(
        "Benefits",
        value=demo.get("company_benefits", "Meal tickets, insurance"),
    )

    st.subheader("Candidate")
    candidate_name = st.text_input("Candidate name", value=demo.get("candidate_name", "Candidate"))
    candidate_salary = st.text_input(
        "Desired salary",
        value=demo.get("candidate_salary", "45000"),
    )
    candidate_smart = st.selectbox(
        "Desired smart work",
        smart_options,
        index=smart_options.index(demo.get("candidate_smart", "Hybrid")),
    )
    candidate_bonus = st.text_input(
        "Desired bonus",
        value=demo.get("candidate_bonus", "Performance bonus"),
    )
    candidate_car = st.selectbox(
        "Desired company car",
        car_options,
        index=car_options.index(demo.get("candidate_car", "No")),
    )
    candidate_benefits = st.text_input(
        "Desired benefits",
        value=demo.get("candidate_benefits", "Meal tickets, training"),
    )

    st.subheader("Topic priorities (1-5)")

    topics = [
        ("salary", "Compensation"),
        ("smart", "Smart work"),
        ("bonus", "Bonus"),
        ("car", "Company car"),
        ("benefits", "Benefits"),
    ]

    for topic_key, topic_label in topics:
        col1, col2 = st.columns(2)

        with col1:
            st.caption(f"{topic_label} - Company priority")
            st.feedback(
                "stars",
                key=f"prio_company_{topic_key}",
                default=demo_priorities.get(topic_key, {}).get("company", 3) - 1,
            )

        with col2:
            st.caption(f"{topic_label} - Candidate priority")
            st.feedback(
                "stars",
                key=f"prio_candidate_{topic_key}",
                default=demo_priorities.get(topic_key, {}).get("candidate", 3) - 1,
            )

    submitted = st.form_submit_button("Save input")

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
    st.success("Input saved. Move to page 02 - Rounds.")
