# Azure OpenAI RAG Document Assistant

A small, interview-ready Retrieval-Augmented Generation (RAG) application built with Python, Streamlit, LangChain, ChromaDB, Azure OpenAI, and PyMuPDF.

## Features
- Upload one or more PDFs
- Page-aware PDF text extraction
- Recursive chunking with configurable size/overlap
- Azure OpenAI embeddings
- Local ChromaDB vector store
- Top-k semantic retrieval
- Grounded Azure OpenAI answers
- Source filename + page citations
- In-memory LRU response cache for repeated questions

## Architecture

PDF Upload
   |
   v
PyMuPDF page extraction
   |
   v
RecursiveCharacterTextSplitter
   |
   v
Azure OpenAI Embeddings
   |
   v
ChromaDB
   |
Question --> Similarity Search (top-k)
                     |
                     v
              Retrieved chunks
                     |
                     v
               Azure OpenAI
                     |
                     v
            Grounded answer + sources

## Tech stack
- Python 3.10+
- Streamlit
- LangChain
- Azure OpenAI
- ChromaDB
- PyMuPDF
- python-dotenv

## Project structure

azure-openai-rag-assistant/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── ingestion/
│   ├── __init__.py
│   └── pdf_loader.py
├── retrieval/
│   ├── __init__.py
│   └── vector_store.py
├── llm/
│   ├── __init__.py
│   ├── azure_openai.py
│   └── prompts.py
└── utils/
    ├── __init__.py
    └── cache.py

## Azure OpenAI setup

Create an Azure OpenAI resource and deploy:
- a chat model deployment
- an embeddings model deployment

Copy `.env.example` to `.env` and fill in your values.

Example:

AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE.openai.azure.com/
AZURE_OPENAI_API_KEY=YOUR_KEY
AZURE_OPENAI_CHAT_DEPLOYMENT=YOUR_CHAT_DEPLOYMENT
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=YOUR_EMBEDDING_DEPLOYMENT
AZURE_OPENAI_API_VERSION=2024-10-21

CHUNK_SIZE=900
CHUNK_OVERLAP=150
TOP_K=4

Never commit a real `.env` file or API key.

## Run locally

python -m venv .venv

Windows:
.venv\Scripts\activate

macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py

## RAG implementation

### Ingestion
Each PDF page is extracted separately and stored as a LangChain Document with filename and page metadata.

### Chunking
RecursiveCharacterTextSplitter creates overlapping chunks. Chunk size and overlap can be changed from the sidebar.

### Embeddings + vector store
Chunks are embedded with Azure OpenAI and indexed in a local ChromaDB collection.

### Retrieval
The user's question is embedded and a similarity search returns the most relevant chunks.

### Grounded generation
A strict prompt tells Azure OpenAI to use only retrieved context and explicitly say when the answer is not present.

### Caching
The app keeps a small process-local LRU cache keyed by the document collection fingerprint and normalized question. This avoids repeated generation calls for identical questions during the current app process.

## Interview talking points
- Why RAG instead of fine-tuning?
- Why use a vector database?
- How embeddings capture semantic similarity
- Why recursive chunking and overlap?
- How top-k affects recall and context size
- How to reduce latency and token usage
- How to replace process-local cache with Redis
- How to scale from local ChromaDB to a shared production vector database
- How to add authentication, rate limiting, monitoring, and audit logs
- How to evaluate retrieval quality separately from generation quality

## Production improvements
For production, add a managed/shared vector store, distributed caching, persistent document metadata, authentication/authorization, observability, rate limiting, background ingestion jobs, and automated evaluation.
