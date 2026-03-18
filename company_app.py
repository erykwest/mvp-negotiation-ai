import streamlit as st

from core.storage import (
    add_main_topic,
    add_subtopic,
    delete_main_topic,
    delete_subtopic,
    load_party_state,
    save_company,
    update_main_topic,
    update_main_topic_priority,
    update_subtopic,
)
from core.topic_tree import OTHER_MAIN_TOPIC_ID, get_sorted_main_topics, has_locked_template_structure
from core.workflow import PHASE_LABELS, is_round_open, is_round_review, workflow_state_label
from ui_helpers import get_session_id


def priority_default(priority: int | None) -> int | None:
    return priority - 1 if priority in {1, 2, 3, 4, 5} else None


def priority_from_feedback(value: int | None, fallback: int | None = None) -> int | None:
    if value is None:
        return fallback
    return value + 1


def can_manage_main_topics(workflow: dict) -> bool:
    return workflow.get("current_phase") == "ALIGNMENT" and is_round_open(workflow)


def can_add_subtopics(workflow: dict) -> bool:
    return is_round_open(workflow) and workflow.get("current_phase") in {"ALIGNMENT", "NEGOTIATION"}


def can_edit_company_subtopic_structure(workflow: dict, subtopic: dict) -> bool:
    if not is_round_open(workflow):
        return False
    if subtopic.get("locked"):
        return False
    if subtopic.get("created_by") != "company":
        return False
    if workflow.get("current_phase") == "ALIGNMENT":
        return subtopic.get("phase_created") == "ALIGNMENT"
    if workflow.get("current_phase") == "NEGOTIATION":
        return subtopic.get("phase_created") == "NEGOTIATION"
    return False


def can_edit_company_subtopic_position(workflow: dict, subtopic: dict) -> bool:
    if not is_round_open(workflow):
        return False
    current_phase = workflow.get("current_phase")
    if current_phase == "NEGOTIATION":
        if subtopic.get("phase_created") == "NEGOTIATION" and subtopic.get("created_by") != "company":
            return False
    return True


st.set_page_config(page_title="Company", layout="wide")
st.title("Company Interface")

session_id = get_session_id(st, "company")
state = load_party_state("company", session_id)
workflow = state.get("workflow", {})

st.caption(
    f"Session: `{session_id}` | Phase: {PHASE_LABELS.get(workflow.get('current_phase', 'ALIGNMENT'))} "
    f"| State: {workflow_state_label(workflow.get('status'))}"
)

if is_round_review(workflow):
    st.info("A round is complete. You can update company inputs before the next round.")
else:
    st.caption("Your priorities, deal breakers, and notes stay private until they are turned into shared round outputs.")

with st.form("company_metadata_form"):
    job_description = st.text_area(
        "Job description",
        value=state.get("job_description", ""),
        height=180,
    )
    company_name = st.text_input(
        "Company name",
        value=state.get("company", {}).get("name", "TechNova Engineering"),
    )
    save_metadata = st.form_submit_button("Save company metadata")

if save_metadata:
    save_company(
        {
            "job_description": job_description,
            "company": {"name": company_name},
        },
        session_id=session_id,
    )
    st.success("Company metadata saved.")
    st.rerun()

st.divider()
st.subheader("Topic framework")
st.caption("Company owns the initial setup. New main topics are only allowed during setup. New subtopics can be added again in round 2.")

template_locked_structure = has_locked_template_structure(state.get("topic_tree", {}))

if can_manage_main_topics(workflow) and not template_locked_structure:
    with st.form("add_main_topic_form"):
        new_main_title = st.text_input("New main topic")
        new_main_description = st.text_area("Description", height=80)
        add_main = st.form_submit_button("Add main topic")
    if add_main:
        if new_main_title.strip():
            add_main_topic(new_main_title, new_main_description, session_id=session_id)
            st.success("Main topic added.")
            st.rerun()
        else:
            st.error("Main topic title is required.")
elif template_locked_structure:
    st.caption("Main topics come from the recruiting template and are locked. You can still set priorities and add subtopics inside the predefined sections.")
else:
    st.caption("Main topic structure is locked after setup. You can still edit company priorities and positions.")

for main_topic in get_sorted_main_topics(state.get("topic_tree", {})):
    main_label = main_topic.get("title", "Untitled main topic")
    with st.expander(main_label, expanded=main_topic.get("is_other", False)):
        if main_topic.get("description"):
            st.caption(main_topic["description"])

        with st.form(f"company_main_topic_{main_topic['id']}"):
            structure_editable = (
                can_manage_main_topics(workflow)
                and not main_topic.get("is_other")
                and not main_topic.get("locked")
            )

            edited_title = st.text_input(
                "Title",
                value=main_topic.get("title", ""),
                disabled=not structure_editable,
            )
            edited_description = st.text_area(
                "Description",
                value=main_topic.get("description", ""),
                disabled=not structure_editable,
                height=80,
            )
            edited_order = st.number_input(
                "Order",
                value=int(main_topic.get("order", 0)),
                step=1,
                disabled=not structure_editable,
            )
            company_priority_input = st.feedback(
                "stars",
                key=f"company_main_priority_{session_id}_{main_topic['id']}",
                default=priority_default(main_topic.get("priorities", {}).get("company")),
            )

            col1, col2 = st.columns(2)
            with col1:
                save_main_topic = st.form_submit_button("Save main topic")
            with col2:
                confirm_delete_main = st.checkbox(
                    "Confirm delete main topic",
                    key=f"confirm_delete_main_{session_id}_{main_topic['id']}",
                    disabled=not structure_editable,
                )
                delete_main_topic_button = st.form_submit_button(
                    "Delete main topic",
                    disabled=not structure_editable,
                )

        if save_main_topic:
            resolved_priority = priority_from_feedback(
                company_priority_input,
                main_topic.get("priorities", {}).get("company"),
            )
            update_main_topic_priority(
                main_topic["id"],
                "company",
                resolved_priority,
                session_id=session_id,
            )
            if structure_editable:
                update_main_topic(
                    main_topic["id"],
                    edited_title,
                    edited_description,
                    int(edited_order),
                    session_id=session_id,
                )
            st.success("Main topic saved.")
            st.rerun()

        if delete_main_topic_button:
            if confirm_delete_main:
                delete_main_topic(main_topic["id"], session_id=session_id)
                st.success("Main topic deleted.")
                st.rerun()
            else:
                st.error("Confirm deletion before removing the main topic.")

        if can_add_subtopics(workflow):
            with st.form(f"add_subtopic_{main_topic['id']}"):
                st.markdown("#### Add subtopic")
                new_subtopic_title = st.text_input("Subtopic title")
                new_subtopic_description = st.text_area("Subtopic description", height=80)
                new_subtopic_value = st.text_area("Company position", height=100)
                new_subtopic_priority_input = st.feedback(
                    "stars",
                    key=f"company_add_subtopic_priority_{session_id}_{main_topic['id']}",
                )
                new_subtopic_deal_breaker = st.checkbox("Deal breaker")
                new_subtopic_notes = st.text_area("Company notes", height=80)
                add_subtopic_button = st.form_submit_button("Add subtopic")

            if add_subtopic_button:
                if new_subtopic_title.strip() and new_subtopic_value.strip():
                    add_subtopic(
                        main_topic["id"],
                        "company",
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
                    st.error("Subtopic title and company position are required.")

        if not main_topic.get("subtopics"):
            st.caption("No subtopics yet.")

        for subtopic in main_topic.get("subtopics", []):
            company_position = subtopic.get("positions", {}).get("company", {})
            structure_editable = can_edit_company_subtopic_structure(workflow, subtopic)
            position_editable = can_edit_company_subtopic_position(workflow, subtopic)

            with st.expander(subtopic.get("title", "Untitled subtopic"), expanded=False):
                if not position_editable:
                    st.info("This subtopic was added by candidate in round 2. You can complete it in round 3.")
                with st.form(f"company_subtopic_{subtopic['id']}"):
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

                    company_value = st.text_area(
                        "Company position",
                        value=company_position.get("value", ""),
                        height=100,
                        disabled=not position_editable,
                    )
                    company_priority_input = st.feedback(
                        "stars",
                        key=f"company_subtopic_priority_{session_id}_{subtopic['id']}",
                        default=priority_default(company_position.get("priority")),
                        disabled=not position_editable,
                    )
                    company_deal_breaker = st.checkbox(
                        "Deal breaker",
                        value=company_position.get("deal_breaker", False),
                        key=f"company_subtopic_deal_breaker_{session_id}_{subtopic['id']}",
                        disabled=not position_editable,
                    )
                    company_notes = st.text_area(
                        "Company notes",
                        value=company_position.get("notes", ""),
                        height=80,
                        disabled=not position_editable,
                    )
                    st.caption("Counterparty inputs remain private. Shared outputs are generated by the round workflow.")

                    col1, col2 = st.columns(2)
                    with col1:
                        save_subtopic = st.form_submit_button("Save subtopic", disabled=not position_editable)
                    with col2:
                        confirm_delete_subtopic = st.checkbox(
                            "Confirm delete subtopic",
                            key=f"confirm_delete_subtopic_company_{session_id}_{subtopic['id']}",
                            disabled=not structure_editable,
                        )
                        delete_subtopic_button = st.form_submit_button(
                            "Delete subtopic",
                            disabled=not structure_editable,
                        )

                if save_subtopic:
                    update_subtopic(
                        subtopic["id"],
                        "company",
                        company_value,
                        priority_from_feedback(company_priority_input, company_position.get("priority")),
                        company_deal_breaker,
                        company_notes,
                        title=edited_subtopic_title if structure_editable else None,
                        description=edited_subtopic_description if structure_editable else None,
                        session_id=session_id,
                    )
                    st.success("Subtopic saved.")
                    st.rerun()

                if delete_subtopic_button:
                    if confirm_delete_subtopic:
                        delete_subtopic(subtopic["id"], "company", session_id=session_id)
                        st.success("Subtopic deleted.")
                        st.rerun()
                    else:
                        st.error("Confirm deletion before removing the subtopic.")
