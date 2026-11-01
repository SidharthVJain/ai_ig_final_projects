"""Streamlit interface for the sequential CrewAI briefing workflow."""

import sys
from pathlib import Path

import httpx
import streamlit as st

FRONTEND_DIR = str(Path(__file__).resolve().parents[1])
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from api_client import generate_briefing, list_research_documents  # noqa: E402

st.title("AI Briefings")
st.caption(
    "Turn GitHub project activity and your research notes into a concise technical briefing "
    "using a sequential Researcher → Writer → Editor crew."
)

with st.expander("How the agent crew works", expanded=False):
    st.markdown(
        """
        1. **Researcher:** examines supplied GitHub repository data, retrieved ChromaDB paper excerpts, and research notes,
           extracts evidence, and can call the custom compatibility and benchmark tools.
        2. **Writer:** turns the findings into a structured, jargon-free developer briefing.
        3. **Editor:** checks clarity and evidence quality, then returns the final Markdown.

        All three agents use the configured Groq model. Repository data is fetched live by
        FastAPI; you can select indexed papers directly or paste additional notes.
        """
    )

indexed_documents = []
try:
    indexed_documents = list_research_documents().get("items", [])
except httpx.HTTPError:
    pass

with st.form("briefing_form"):
    topic = st.text_input(
        "Briefing topic",
        placeholder="e.g. Recent developments in retrieval-augmented generation",
        max_chars=240,
    )
    repository_text = st.text_input(
        "GitHub repository (optional)",
        placeholder="e.g. crewAIInc/crewAI",
        help="Enter one repository in owner/repo format. DevDigest currently supports one repository per briefing.",
        max_chars=100,
    )
    selected_document_ids = st.multiselect(
        "Include indexed research papers (optional)",
        options=[item["document_id"] for item in indexed_documents],
        format_func=lambda value: next((item["filename"] for item in indexed_documents if item["document_id"] == value), value),
        help="The backend retrieves relevant passages from these ChromaDB documents for the Researcher agent.",
    )
    research_notes = st.text_area(
        "Research notes (optional)",
        placeholder="Paste concise findings or excerpts (up to 4,000 characters)...",
        height=150,
        max_chars=4000,
    )
    submitted = st.form_submit_button("Generate AI briefing", type="primary")

if submitted:
    if len(topic.strip()) < 3:
        st.warning("Enter a topic with at least 3 characters.")
    else:
        repository = repository_text.strip()
        repositories = [repository] if repository else []
        if repository and (
            repository.count("/") != 1
            or any(character.isspace() for character in repository)
            or not all(repository.split("/"))
        ):
            st.warning("Enter exactly one GitHub repository in owner/repo format, for example crewAIInc/crewAI.")
        else:
            try:
                with st.spinner("Researcher, Writer, and Editor are working... This may take a minute."):
                    result = generate_briefing(
                        topic=topic.strip(),
                        repositories=repositories,
                        research_notes=research_notes.strip(),
                        document_ids=selected_document_ids,
                    )
                st.session_state["latest_briefing"] = result
            except httpx.HTTPError as exc:
                detail = str(exc)
                if isinstance(exc, httpx.HTTPStatusError):
                    try:
                        detail = exc.response.json().get("detail", detail)
                    except ValueError:
                        pass
                st.error(f"Briefing generation failed: {detail}")

result = st.session_state.get("latest_briefing")
if result:
    st.divider()
    st.subheader(result["topic"])
    st.caption(
        f"Generated {result['generated_at'][:19].replace('T', ' ')} UTC · "
        f"Model: {result['model']} · ID: {result['briefing_id']}"
    )
    st.markdown(result["briefing"])
    with st.expander("Workflow details"):
        st.write("Agents: " + " → ".join(result["agents"]))
        st.write("Available tools: " + ", ".join(result["tools_available"]))
    st.download_button(
        "Download briefing as Markdown",
        data=result["briefing"],
        file_name="devdigest-briefing.md",
        mime="text/markdown",
    )
