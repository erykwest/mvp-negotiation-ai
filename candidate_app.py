import streamlit as st

from core.storage import (
    add_subtopic,
    delete_subtopic,
    load_party_state,
    save_candidate,
    update_main_topic_priority,
    update_subtopic,
)
from core.topic_tree import get_sorted_main_topics
from core.workflow import PHASE_LABELS, is_round_open, is_round_review, workflow_state_label
from ui_helpers import get_session_id


def priority_default(priority: int | None) -> int | None:
    return priority - 1 if priority in {1, 2, 3, 4, 5} else None


def priority_from_feedback(value: int | None, fallback: int | None = None) -> int | None:
    if value is None:
        return fallback
    return value + 1


def can_add_subtopics(workflow: dict) -> bool:
    return is_round_open(workflow) and workflow.get("current_phase") == "NEGOTIATION"


def can_edit_candidate_subtopic_structure(workflow: dict, subtopic: dict) -> bool:
    if not is_round_open(workflow):
        return False
    if subtopic.get("locked"):
        return False
    if workflow.get("current_phase") != "NEGOTIATION":
        return False
    return subtopic.get("created_by") == "candidate" and subtopic.get("phase_created") == "NEGOTIATION"


def can_edit_candidate_subtopic_position(workflow: dict, subtopic: dict) -> bool:
    if not is_round_open(workflow):
        return False
    current_phase = workflow.get("current_phase")
    if current_phase == "NEGOTIATION":
        if subtopic.get("phase_created") == "NEGOTIATION" and subtopic.get("created_by") != "candidate":
            return False
    return True


st.set_page_config(page_title="Candidate", layout="wide")
st.title("Candidate Interface")

session_id = get_session_id(st, "candidate")
state = load_party_state("candidate", session_id)
workflow = state.get("workflow", {})

st.caption(
    f"Session: `{session_id}` | Phase: {PHASE_LABELS.get(workflow.get('current_phase', 'ALIGNMENT'))} "
    f"| State: {workflow_state_label(workflow.get('status'))}"
)

if is_round_review(workflow):
    st.info("A round is complete. You can update candidate inputs before the next round.")
else:
    st.caption("Your priorities, deal breakers, and notes stay private until they are turned into shared round outputs.")

with st.form("candidate_metadata_form"):
    st.text_area(
        "Job description",
        value=state.get("job_description", ""),
        height=180,
        disabled=True,
    )
    candidate_name = st.text_input(
        "Candidate name",
        value=state.get("candidate", {}).get("name", "Marco Rinaldi"),
    )
    save_metadata = st.form_submit_button("Save candidate metadata")

if save_metadata:
    save_candidate(
        {"candidate": {"name": candidate_name}},
        session_id=session_id,
    )
    st.success("Candidate metadata saved.")
    st.rerun()

st.divider()
st.subheader("Topic framework")

main_topics = get_sorted_main_topics(state.get("topic_tree", {}))
non_other_topics = [topic for topic in main_topics if not topic.get("is_other")]
if not non_other_topics:
    st.info("Waiting for company to define the initial topic structure.")

for main_topic in main_topics:
    with st.expander(main_topic.get("title", "Untitled main topic"), expanded=main_topic.get("is_other", False)):
        if main_topic.get("description"):
            st.caption(main_topic["description"])

        with st.form(f"candidate_main_topic_{main_topic['id']}"):
            candidate_priority_input = st.feedback(
                "stars",
                key=f"candidate_main_priority_{session_id}_{main_topic['id']}",
                default=priority_default(main_topic.get("priorities", {}).get("candidate")),
            )
            save_main_topic = st.form_submit_button("Save candidate main topic priority")

        if save_main_topic:
            update_main_topic_priority(
                main_topic["id"],
                "candidate",
                priority_from_feedback(candidate_priority_input, main_topic.get("priorities", {}).get("candidate")),
                session_id=session_id,
            )
            st.success("Candidate main topic priority saved.")
            st.rerun()

        if can_add_subtopics(workflow):
            with st.form(f"candidate_add_subtopic_{main_topic['id']}"):
                st.markdown("#### Add subtopic")
                new_subtopic_title = st.text_input("Subtopic title")
                new_subtopic_description = st.text_area("Subtopic description", height=80)
                new_subtopic_value = st.text_area("Candidate position", height=100)
                new_subtopic_priority_input = st.feedback(
                    "stars",
                    key=f"candidate_add_subtopic_priority_{session_id}_{main_topic['id']}",
                )
                new_subtopic_deal_breaker = st.checkbox("Deal breaker")
                new_subtopic_notes = st.text_area("Candidate notes", height=80)
                add_subtopic_button = st.form_submit_button("Add subtopic")

            if add_subtopic_button:
                if new_subtopic_title.strip() and new_subtopic_value.strip():
                    add_subtopic(
                        main_topic["id"],
                        "candidate",
                        new_subtopic_title,
                        new_subtopic_description,
                        new_subtopic_value,
                        priority_from_feedback(new_subtopic_priority_input),
                        new_subtopic_deal_breaker,
                        new_subtopic_notes,
                        session_id=session_id,
                    )
                    st.success("Subtopic added.")
                    st.rerun()
                else:
                    st.error("Subtopic title and candidate position are required.")

        if not main_topic.get("subtopics"):
            st.caption("No subtopics yet.")

        for subtopic in main_topic.get("subtopics", []):
            candidate_position = subtopic.get("positions", {}).get("candidate", {})
            structure_editable = can_edit_candidate_subtopic_structure(workflow, subtopic)
            position_editable = can_edit_candidate_subtopic_position(workflow, subtopic)

            with st.expander(subtopic.get("title", "Untitled subtopic"), expanded=False):
                if not position_editable:
                    st.info("This subtopic was added by company in round 2. You can complete it in round 3.")
                with st.form(f"candidate_subtopic_{subtopic['id']}"):
                    edited_subtopic_title = st.text_input(
                        "Title",
                        value=subtopic.get("title", ""),
                        disabled=not structure_editable,
                    )
                    edited_subtopic_description = st.text_area(
                        "Description",
                        value=subtopic.get("description", ""),
                        disabled=not structure_editable,
                        height=80,
                    )
                    st.caption("Counterparty inputs remain private. Shared outputs are generated by the round workflow.")

                    candidate_value = st.text_area(
                        "Candidate position",
                        value=candidate_position.get("value", ""),
                        height=100,
                        disabled=not position_editable,
                    )
                    candidate_priority_input = st.feedback(
                        "stars",
                        key=f"candidate_subtopic_priority_{session_id}_{subtopic['id']}",
                        default=priority_default(candidate_position.get("priority")),
                        disabled=not position_editable,
                    )
                    candidate_deal_breaker = st.checkbox(
                        "Deal breaker",
                        value=candidate_position.get("deal_breaker", False),
                        key=f"candidate_subtopic_deal_breaker_{session_id}_{subtopic['id']}",
                        disabled=not position_editable,
                    )
                    candidate_notes = st.text_area(
                        "Candidate notes",
                        value=candidate_position.get("notes", ""),
                        height=80,
                        disabled=not position_editable,
                    )

                    col1, col2 = st.columns(2)
                    with col1:
                        save_subtopic = st.form_submit_button("Save subtopic", disabled=not position_editable)
                    with col2:
                        confirm_delete_subtopic = st.checkbox(
                            "Confirm delete subtopic",
                            key=f"confirm_delete_subtopic_candidate_{session_id}_{subtopic['id']}",
                            disabled=not structure_editable,
                        )
                        delete_subtopic_button = st.form_submit_button(
                            "Delete subtopic",
                            disabled=not structure_editable,
                        )

                if save_subtopic:
                    update_subtopic(
                        subtopic["id"],
                        "candidate",
                        candidate_value,
                        priority_from_feedback(candidate_priority_input, candidate_position.get("priority")),
                        candidate_deal_breaker,
                        candidate_notes,
                        title=edited_subtopic_title if structure_editable else None,
                        description=edited_subtopic_description if structure_editable else None,
                        session_id=session_id,
                    )
                    st.success("Subtopic saved.")
                    st.rerun()

                if delete_subtopic_button:
                    if confirm_delete_subtopic:
                        delete_subtopic(subtopic["id"], "candidate", session_id=session_id)
                        st.success("Subtopic deleted.")
                        st.rerun()
                    else:
                        st.error("Confirm deletion before removing the subtopic.")
