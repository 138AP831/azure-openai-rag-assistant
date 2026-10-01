import hashlib
import os
from pathlib import Path
from typing import List

import streamlit as st
from dotenv import load_dotenv
from langchain_core.documents import Document

from ingestion.pdf_loader import load_pdf_documents
from retrieval.vector_store import build_vector_store, retrieve_documents
from llm.azure_openai import build_chat_model
from llm.prompts import build_grounded_prompt
from utils.cache import ResponseCache

load_dotenv()

st.set_page_config(
    page_title="Azure OpenAI RAG Assistant",
    page_icon="📄",
    layout="wide",
)

CACHE = ResponseCache(max_items=100)


def config_value(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def collection_fingerprint(documents: List[Document]) -> str:
    parts = []
    for doc in documents:
        parts.append(
            f"{doc.metadata.get('source')}|{doc.metadata.get('page')}|"
            f"{doc.page_content[:500]}"
        )
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


st.title("📄 Azure OpenAI RAG Document Assistant")
st.caption("PDF → chunking → embeddings → ChromaDB → Azure OpenAI → grounded answer")

with st.sidebar:
    st.header("RAG configuration")

    chunk_size = st.number_input(
        "Chunk size",
        min_value=300,
        max_value=2000,
        value=int(config_value("CHUNK_SIZE", "900")),
        step=50,
    )
    chunk_overlap = st.number_input(
        "Chunk overlap",
        min_value=0,
        max_value=500,
        value=int(config_value("CHUNK_OVERLAP", "150")),
        step=10,
    )
    top_k = st.number_input(
        "Retrieved chunks",
        min_value=1,
        max_value=10,
        value=int(config_value("TOP_K", "4")),
        step=1,
    )

    if st.button("Clear current session", use_container_width=True):
        for key in ("vector_store", "documents", "doc_fingerprint"):
            st.session_state.pop(key, None)
        CACHE.clear()
        st.rerun()

uploaded_files = st.file_uploader(
    "Upload PDF documents",
    type=["pdf"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("Upload one or more PDFs to start.")
    st.stop()

temp_dir = Path(".uploaded")
temp_dir.mkdir(exist_ok=True)

documents: List[Document] = []

with st.spinner("Reading PDFs..."):
    for uploaded in uploaded_files:
        safe_name = Path(uploaded.name).name
        temp_path = temp_dir / safe_name
        temp_path.write_bytes(uploaded.getvalue())
        documents.extend(load_pdf_documents(temp_path))

if not documents:
    st.warning("No extractable text was found in the uploaded PDFs.")
    st.stop()

fingerprint = collection_fingerprint(documents)

if st.session_state.get("doc_fingerprint") != fingerprint:
    try:
        with st.spinner("Creating embeddings and indexing the knowledge base..."):
            st.session_state.vector_store = build_vector_store(
                documents,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            st.session_state.documents = documents
            st.session_state.doc_fingerprint = fingerprint
            CACHE.clear()
    except Exception as exc:
        st.error(
            "Indexing failed. Verify Azure OpenAI endpoint, API key, and embedding deployment."
        )
        st.exception(exc)
        st.stop()

st.success(
    f"Indexed {len(documents)} extracted PDF pages from {len(uploaded_files)} file(s)."
)

question = st.text_input(
    "Ask a question about your documents",
    placeholder="e.g. What were the main revenue drivers?",
)

if not question.strip():
    st.caption("Enter a question and click Ask.")
    st.stop()

if st.button("Ask", type="primary"):
    normalized_question = " ".join(question.lower().split())
    cache_key = f"{fingerprint}:{normalized_question}"

    cached = CACHE.get(cache_key)

    if cached is not None:
        answer, sources = cached
        st.info("Served from the in-memory cache.")
    else:
        try:
            with st.spinner("Retrieving relevant context..."):
                retrieved = retrieve_documents(
                    st.session_state.vector_store,
                    question,
                    top_k=top_k,
                )

            if not retrieved:
                st.warning("No relevant chunks were found.")
                st.stop()

            context_parts = []
            sources = []

            for idx, doc in enumerate(retrieved, start=1):
                source = str(doc.metadata.get("source", "unknown"))
                page = str(doc.metadata.get("page", "?"))
                context_parts.append(
                    f"[Source {idx}] {source}, page {page}\n{doc.page_content}"
                )
                sources.append(
                    {
                        "source": source,
                        "page": page,
                        "chunk": doc.page_content,
                    }
                )

            context = "\n\n".join(context_parts)

            with st.spinner("Generating grounded answer..."):
                llm = build_chat_model()
                prompt = build_grounded_prompt(
                    context=context,
                    question=question,
                )
                message = llm.invoke(prompt)

            answer = getattr(message, "content", str(message))
            CACHE.set(cache_key, (answer, sources))

        except Exception as exc:
            st.error(
                "Generation failed. Verify Azure OpenAI settings, deployments, and API version."
            )
            st.exception(exc)
            st.stop()

    st.subheader("Answer")
    st.write(answer)

    st.subheader("Sources")
    for idx, source in enumerate(sources, start=1):
        with st.expander(
            f"Source {idx}: {source['source']} — page {source['page']}"
        ):
            st.write(source["chunk"])
