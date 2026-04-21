from pathlib import Path

import chromadb

from app.core.config import settings
from app.services.embedding_service import EmbeddingService

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CHROMA_DB_DIR = BASE_DIR / "data" / "chroma_db"


class VectorStoreService:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        self.collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME
        )
        self.embedding_service = EmbeddingService()

    def add_chunks(
        self,
        document_id: str,
        chunks: list[str],
        filename: str,
        content_type: str,
    ) -> None:
        ids = []
        documents = []
        metadatas = []
        embeddings = []

        for i, chunk in enumerate(chunks):
            ids.append(f"{document_id}_chunk_{i}")
            documents.append(chunk)
            metadatas.append(
                {
                    "document_id": document_id,
                    "filename": filename,
                    "content_type": content_type,
                    "chunk_index": i,
                }
            )
            embeddings.append(self.embedding_service.embed_text(chunk))

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def query(self, query_text: str, n_results: int = 3):
        query_embedding = self.embedding_service.embed_text(query_text)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        matches = []

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, metadata, distance in zip(documents, metadatas, distances):
             matches.append(
                {
                    "document_id": metadata.get("document_id"),
                    "filename": metadata.get("filename"),
                    "chunk_index": metadata.get("chunk_index"),
                    "content_type": metadata.get("content_type"),
                    "distance": distance,
                    "content": doc,
                }
            )

        return matches