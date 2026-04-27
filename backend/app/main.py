from pathlib import Path
import json

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.document_parser import extract_text
from app.services.text_processor import clean_text, chunk_text
from app.services.vector_store import VectorStoreService
from app.utils.file_utils import generate_unique_filename, sanitize_filename
from app.services.llm_service import LLMService

app = FastAPI(title="Chat with Your Docs API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {".txt", ".pdf", ".doc", ".docx"}

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class QueryRequest(BaseModel):
    query: str


def format_sse(data: dict) -> str:
    """
    Server-Sent Events (SSE) formatında veri döndürür.
    """
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/")
def root():
    return {"message": "API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    file_extension = Path(file.filename).suffix.lower()

    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.filename}",
        )

    safe_name = sanitize_filename(file.filename)
    unique_name = generate_unique_filename(safe_name)
    file_path = UPLOAD_DIR / unique_name

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    try:
        extracted_text = extract_text(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    cleaned_text = clean_text(extracted_text)
    chunks = chunk_text(cleaned_text)

    document_id = unique_name.rsplit(".", 1)[0]

    try:
        vector_store = VectorStoreService()
        vector_store.add_chunks(
            document_id=document_id,
            chunks=chunks,
            filename=unique_name,
            content_type=file.content_type,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Vector store error: {str(e)}",
        )

    return {
        "message": "File uploaded successfully and indexed",
        "file": {
            "filename": unique_name,
            "content_type": file.content_type,
            "saved_to": str(file_path),
        },
        "text_length": len(cleaned_text),
        "chunk_count": len(chunks),
        "preview_chunks": chunks[:2],
        "document_id": document_id,
    }


@app.post("/query")
def query_documents(request: QueryRequest):
    try:
        vector_store = VectorStoreService()
        matches = vector_store.query(request.query)

        return {
            "query": request.query,
            "match_count": len(matches),
            "matches": matches,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask")
def ask_documents(request: QueryRequest):
    try:
        vector_store = VectorStoreService()
        matches = vector_store.query(request.query)

        llm_service = LLMService()
        answer = llm_service.generate_answer(request.query, matches)

        return {
            "question": request.query,
            "answer": answer,
            "source_count": len(matches),
            "sources": [
                {
                    "document_id": match["document_id"],
                    "filename": match["filename"],
                    "chunk_index": match["chunk_index"],
                    "distance": match["distance"],
                }
                for match in matches
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask/stream")
def ask_documents_stream(request: QueryRequest):
    query = request.query.strip()

    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        vector_store = VectorStoreService()
        matches = vector_store.query(query)

        llm_service = LLMService()

        sources = [
            {
                "document_id": match["document_id"],
                "filename": match["filename"],
                "chunk_index": match["chunk_index"],
                "distance": match["distance"],
            }
            for match in matches
        ]

        def event_generator():
            try:
                # İlk olarak kaynakları gönder
                yield format_sse({
                    "type": "sources",
                    "content": sources,
                })

                # Eğer llm_service içinde gerçek streaming metodu varsa onu kullan
                if hasattr(llm_service, "generate_answer_stream"):
                    for chunk in llm_service.generate_answer_stream(query, matches):
                        if chunk:
                            yield format_sse({
                                "type": "token",
                                "content": chunk,
                            })
                else:
                    # Fallback: mevcut non-stream cevabı tek parça olarak gönder
                    answer = llm_service.generate_answer(query, matches)
                    yield format_sse({
                        "type": "token",
                        "content": answer,
                    })

                yield format_sse({"type": "done"})

            except Exception as e:
                yield format_sse({
                    "type": "error",
                    "content": str(e),
                })

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))