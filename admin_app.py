import streamlit as st

from core.negotiation import collect_round_errors, run_single_round
from core.report import build_report
from core.storage import load_state, reset_workflow, rewind_phase, save_round_result
from core.topic_tree import get_sorted_main_topics
from core.validation import (
    validate_report_inputs,
    validate_review_readiness,
    validate_state_for_round,
)
from core.workflow import PHASE_LABELS
from ui_helpers import get_session_id

st.set_page_config(page_title="Admin", layout="wide")
st.title("Admin / Negotiation Runner")

session_id = get_session_id(st, "admin")
state = load_state(session_id)
workflow = state["workflow"]
current_phase = workflow["current_phase"]
status = workflow["status"]
results = state.get("results", {})

st.subheader("Negotiation subject")
st.info(state.get("job_description", "No job description yet."))

with st.expander("Topic framework", expanded=True):
    topic_tree = state.get("topic_tree", {})
    for main_topic in get_sorted_main_topics(topic_tree):
        if main_topic.get("is_other") and not main_topic.get("subtopics"):
            continue

        st.markdown(
            f"### {main_topic.get('title', 'Untitled main topic')}"
        )
        if main_topic.get("description"):
            st.caption(main_topic["description"])
        st.caption(
            "Main priorities "
            f"| company: {main_topic.get('priorities', {}).get('company') or '-'} / 5 "
            f"| candidate: {main_topic.get('priorities', {}).get('candidate') or '-'} / 5"
        )

        for subtopic in main_topic.get("subtopics", []):
            company_position = subtopic.get("positions", {}).get("company", {})
            candidate_position = subtopic.get("positions", {}).get("candidate", {})
            with st.container(border=True):
                st.markdown(f"**{subtopic.get('title', 'Untitled subtopic')}**")
                if subtopic.get("description"):
                    st.caption(subtopic["description"])
                st.caption(
                    f"Created by {subtopic.get('created_by', '-')} in {subtopic.get('phase_created', '-')}"
                )
                st.write(
                    "Company: "
                    f"{company_position.get('value') or '-'} "
                    f"| priority {company_position.get('priority') or '-'} / 5 "
                    f"| deal breaker {'yes' if company_position.get('deal_breaker') else 'no'}"
                )
                if company_position.get("notes"):
                    st.caption(f"Company notes: {company_position['notes']}")
                st.write(
                    "Candidate: "
                    f"{candidate_position.get('value') or '-'} "
                    f"| priority {candidate_position.get('priority') or '-'} / 5 "
                    f"| deal breaker {'yes' if candidate_position.get('deal_breaker') else 'no'}"
                )
                if candidate_position.get("notes"):
                    st.caption(f"Candidate notes: {candidate_position['notes']}")

with st.expander("Raw session data", expanded=False):
    st.json(state, expanded=False)

setup_errors = validate_state_for_round(state, current_phase)
if setup_errors:
    st.warning("The session is not ready for the current round.")
    for error in setup_errors:
        st.write(f"- {error}")
    st.stop()

st.markdown(f"### Current phase: **{PHASE_LABELS.get(current_phase, current_phase)}**")
st.caption(f"Status: {status}")

col1, col2 = st.columns(2)

with col1:
    if status == "editing":
        if st.button(f"Run {PHASE_LABELS.get(current_phase, current_phase)}"):
            with st.spinner("Round running..."):
                result = run_single_round(state, current_phase)
                save_round_result(current_phase, result, session_id=session_id)
            st.rerun()

with col2:
    if st.button("Reset workflow"):
        reset_workflow(session_id=session_id)
        st.rerun()
    if current_phase != "ALIGNMENT":
        if st.button("Go back one round (test mode)"):
            try:
                rewind_phase(session_id=session_id)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.rerun()

if status == "review":
    st.success("Round completed. Humans can update the data before the next round.")

    current_result = load_state(session_id)["results"].get(current_phase)
    review_errors = validate_review_readiness(load_state(session_id), current_phase, current_result)
    if current_result:
        with st.expander(
            f"{PHASE_LABELS.get(current_phase, current_phase)} - current result",
            expanded=True,
        ):
            st.markdown(current_result["summary"])
            round_errors = collect_round_errors(current_result)
            if round_errors:
                st.error("The round contains LLM failures.")
                for error in round_errors:
                    st.write(f"- {error}")

    if current_phase != "CLOSING":
        can_advance = not review_errors
        for error in review_errors:
            st.error(error)

        if can_advance and st.button("Open next round"):
            try:
                from core.storage import advance_phase

                advance_phase(session_id=session_id)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.rerun()
    else:
        st.info("Closing completed. The final report is ready for download.")

if results:
    st.markdown("## Completed rounds")
    for phase in ["ALIGNMENT", "NEGOTIATION", "CLOSING"]:
        if phase not in results:
            continue

        with st.expander(PHASE_LABELS[phase], expanded=False):
            st.markdown(results[phase]["summary"])

    report_errors = validate_report_inputs(load_state(session_id), results)
    if report_errors:
        st.warning("The report is not available yet.")
        for error in report_errors:
            st.write(f"- {error}")
    else:
        report = build_report(load_state(session_id), results)
        st.download_button(
            "Download report",
            report,
            f"{session_id}_negotiation_report.md",
            "text/markdown",
        )
