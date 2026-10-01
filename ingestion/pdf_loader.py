from pathlib import Path
from typing import List

import fitz
from langchain_core.documents import Document


def load_pdf_documents(path: Path) -> List[Document]:
    """Extract one LangChain Document per non-empty PDF page."""
    documents: List[Document] = []

    with fitz.open(path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            text = page.get_text("text").strip()

            if not text:
                continue

            documents.append(
                Document(
                    page_content=text,
                    metadata={
                        "source": path.name,
                        "page": page_number,
                    },
                )
            )

    return documents
