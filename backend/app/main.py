from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel
from app.services.document_parser import extract_text
from app.services.text_processor import clean_text, chunk_text
from app.services.vector_store import VectorStoreService
from app.utils.file_utils import generate_unique_filename, sanitize_filename
from app.services.llm_service import LLMService
from fastapi.middleware.cors import CORSMiddleware

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

    # filename işlemleri
    safe_name = sanitize_filename(file.filename)
    unique_name = generate_unique_filename(safe_name)
    file_path = UPLOAD_DIR / unique_name

    # dosyayı kaydet
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # text extraction
    try:
        extracted_text = extract_text(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # cleaning + chunking
    cleaned_text = clean_text(extracted_text)
    chunks = chunk_text(cleaned_text)

    document_id = unique_name.rsplit(".", 1)[0]

    # vector store indexing
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