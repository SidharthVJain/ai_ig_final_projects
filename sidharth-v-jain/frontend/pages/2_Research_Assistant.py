"""Streamlit interface for PDF ingestion and grounded research Q&A."""

import sys
from pathlib import Path

import httpx
import streamlit as st

FRONTEND_DIR = str(Path(__file__).resolve().parents[1])
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from api_client import (  # noqa: E402
    ask_research_question,
    list_research_documents,
    upload_research_document,
)

st.title("Research Assistant")
st.caption(
    "Upload text-based research papers or technical PDFs, then ask questions grounded "
    "in their contents. Answers include document and page references."
)


def show_api_error(exc: httpx.HTTPError) -> None:
    detail = str(exc)
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            detail = exc.response.json().get("detail", detail)
        except (ValueError, AttributeError):
            pass
    st.error(f"Research API error: {detail}")


with st.expander("How this works", expanded=False):
    st.markdown(
        """
        1. Upload a PDF. The backend extracts selectable text with PyMuPDF.
        2. Text is split into overlapping chunks while retaining page numbers.
        3. `sentence-transformers` generates embeddings and ChromaDB stores them locally.
        4. Your question retrieves the most relevant chunks; Groq drafts an answer using
           only those excerpts and cites the matching source labels.

        **Current limitation:** scanned/image-only PDFs need OCR and are not supported yet.
        """
    )

st.subheader("1. Add research documents")
uploaded_file = st.file_uploader(
    "Choose a PDF",
    type=["pdf"],
    help="Maximum size is configured by the backend (15 MB by default).",
)
if st.button(
    "Upload and index PDF",
    type="primary",
    disabled=uploaded_file is None,
    use_container_width=False,
):
    try:
        with st.spinner("Extracting text, creating embeddings, and saving to ChromaDB..."):
            result = upload_research_document(uploaded_file.name, uploaded_file.getvalue())
        st.success(result.get("message", "Document indexed successfully."))
        st.session_state.pop("research_documents", None)
        st.session_state.pop("research_answer", None)
    except httpx.HTTPError as exc:
        show_api_error(exc)

st.divider()
st.subheader("2. Your indexed library")
refresh_col, info_col = st.columns([1, 4])
with refresh_col:
    refresh_documents = st.button("Refresh library")
if refresh_documents or "research_documents" not in st.session_state:
    try:
        st.session_state["research_documents"] = list_research_documents().get("items", [])
        st.session_state.pop("research_library_error", None)
    except httpx.HTTPError as exc:
        st.session_state["research_library_error"] = str(exc)

library_error = st.session_state.get("research_library_error")
if library_error:
    st.warning(
        "Could not load the document library. Check that FastAPI is running and that "
        "the RAG dependencies have been installed. " + library_error
    )

documents = st.session_state.get("research_documents", [])
with info_col:
    st.caption(f"{len(documents)} document(s) indexed")

if documents:
    for document in documents:
        with st.container(border=True):
            st.markdown(f"**{document['filename']}**")
            meta_cols = st.columns(4)
            meta_cols[0].caption(f"{document['page_count']} text pages")
            meta_cols[1].caption(f"{document['chunk_count']} chunks")
            meta_cols[2].caption(f"ID: {document['document_id'][:8]}…")
            uploaded_at = document.get("uploaded_at", "")
            meta_cols[3].caption(uploaded_at[:10] if uploaded_at else "Upload date unavailable")
else:
    st.info("No research documents indexed yet. Upload a PDF to start building your library.")

st.divider()
st.subheader("3. Ask your documents")
if documents:
    document_labels = {
        item["document_id"]: item["filename"] for item in documents
    }
    selected_document_ids = st.multiselect(
        "Search scope",
        options=list(document_labels),
        default=list(document_labels),
        format_func=lambda value: document_labels[value],
        help="Select one or more documents. Leave all selected to search the full library.",
    )
    with st.form("research_question_form"):
        question = st.text_area(
            "Your question",
            placeholder="e.g. What problem does this paper address, and what are its main contributions?",
            height=100,
            max_chars=2000,
        )
        top_k = st.slider("Number of passages to retrieve", min_value=3, max_value=8, value=5)
        submitted = st.form_submit_button("Ask research assistant", type="primary")

    if submitted:
        if len(question.strip()) < 3:
            st.warning("Please enter a question with at least 3 characters.")
        elif not selected_document_ids:
            st.warning("Select at least one document to search.")
        else:
            try:
                with st.spinner("Retrieving relevant passages and generating a grounded answer..."):
                    answer = ask_research_question(
                        question=question.strip(),
                        document_ids=selected_document_ids,
                        top_k=top_k,
                    )
                st.session_state["research_answer"] = answer
            except httpx.HTTPError as exc:
                st.session_state.pop("research_answer", None)
                show_api_error(exc)
else:
    st.caption("Upload at least one document to enable question answering.")

answer = st.session_state.get("research_answer")
if answer:
    st.divider()
    st.subheader("Answer")
    st.markdown(answer["answer"])
    st.caption(
        f"Retrieved {answer['retrieved_count']} passages · Model: {answer['model']}"
    )
    st.markdown("#### Sources")
    for source in answer.get("sources", []):
        with st.expander(
            f"[{source['citation_id']}] {source['filename']} · Page {source['page_number']}"
        ):
            st.write(source["excerpt"])
