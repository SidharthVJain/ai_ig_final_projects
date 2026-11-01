"""DevDigest Streamlit entry point."""

import httpx
import streamlit as st

# Streamlit executes this file as the application script, so api_client is
# imported from the same frontend directory rather than as a package path.
from api_client import get_backend_url, get_health

st.set_page_config(
    page_title="DevDigest",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("DevDigest")
st.caption("Your open-source and AI research intelligence workspace")

with st.sidebar:
    st.header("DevDigest")
    st.caption("Explore repositories, research papers, and AI-generated briefs.")
    st.divider()
    st.page_link("app.py", label="Overview", icon="🏠")
    st.page_link("pages/1_Repository_Explorer.py", label="Repository Explorer", icon="🔎")
    st.page_link("pages/2_Research_Assistant.py", label="Research Assistant", icon="📄")
    st.page_link("pages/3_AI_Briefings.py", label="AI Briefings", icon="🧠")
    st.divider()
    st.caption("Development build · v0.4.0")

st.subheader("Project workspace")
st.write(
    "DevDigest brings GitHub project activity and technical research papers into one place. "
    "Explore repositories, index your research PDFs, and ask source-grounded questions. "
    "Generate technical briefings with a Researcher, Writer, and Editor agent crew."
)

left, right = st.columns([2, 1], gap="large")
with left:
    st.markdown("#### Build roadmap")
    st.markdown(
        """
        1. **Foundation:** Streamlit ↔ FastAPI connection
        2. **Open-source intelligence:** GitHub repositories, releases, and commits
        3. **Research assistant:** PDF ingestion, embeddings, and ChromaDB retrieval
        4. **AI briefings:** Researcher, Writer, and Editor agents using Groq + CrewAI
        5. **Release:** testing, guardrails, and cloud deployment
        """
    )
with right:
    st.markdown("#### Backend connection")
    st.code(get_backend_url(), language="text")
    if st.button("Check backend connection", type="primary", use_container_width=True):
        try:
            st.session_state["backend_health"] = get_health()
            st.session_state.pop("backend_error", None)
        except httpx.HTTPError as exc:
            st.session_state.pop("backend_health", None)
            st.session_state["backend_error"] = str(exc)
    health = st.session_state.get("backend_health")
    error = st.session_state.get("backend_error")
    if health:
        st.success("Backend connected")
        st.caption(f"Service: {health['service']}")
        st.caption(f"Version: {health['version']}")
        st.caption(f"Environment: {health['environment']}")
    elif error:
        st.error("Could not connect to the backend")
        st.caption("Start FastAPI and check BACKEND_URL in .env.")
    else:
        st.info("Click the button to test the FastAPI connection.")

st.divider()
st.info("Open **Research Assistant** to upload papers and ask source-grounded questions.")
