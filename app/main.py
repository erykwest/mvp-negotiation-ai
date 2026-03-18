import streamlit as st

st.set_page_config(page_title="Negotiation MVP - Legacy Prototype", layout="wide")
st.title("Negotiation MVP - Legacy Prototype")
st.warning(
    "This multi-page app is kept only as a legacy prototype. "
    "The canonical workflow now lives in company_app.py, candidate_app.py, and admin_app.py."
)
st.write("Use the sidebar pages only if you need to inspect the older single-session prototype flow.")
