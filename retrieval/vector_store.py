import os
from typing import List

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import AzureOpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


def _validate_env() -> None:
    required = (
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
        "AZURE_OPENAI_API_VERSION",
    )
    missing = [name for name in required if not os.getenv(name)]

    if missing:
        raise ValueError(
            "Missing environment variables: " + ", ".join(missing)
        )


def _build_embeddings() -> AzureOpenAIEmbeddings:
    _validate_env()

    return AzureOpenAIEmbeddings(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_deployment=os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    )


def build_vector_store(
    documents: List[Document],
    chunk_size: int = 900,
    chunk_overlap: int = 150,
) -> Chroma:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_documents(documents)

    if not chunks:
        raise ValueError("No chunks were created from the uploaded PDFs.")

    return Chroma.from_documents(
        documents=chunks,
        embedding=_build_embeddings(),
        collection_name="azure_openai_rag",
    )


def retrieve_documents(
    vector_store: Chroma,
    question: str,
    top_k: int = 4,
) -> List[Document]:
    return vector_store.similarity_search(question, k=top_k)
