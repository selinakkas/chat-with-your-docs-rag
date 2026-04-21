from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.services.document_parser import extract_text
from app.utils.file_utils import generate_unique_filename, sanitize_filename
from app.services.text_processor import clean_text, chunk_text

app = FastAPI(title="Chat with Your Docs API")

ALLOWED_EXTENSIONS = {".txt", ".pdf", ".doc", ".docx"}

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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

    return {
        "message": "File uploaded successfully",
        "file": {
            "filename": unique_name,
            "content_type": file.content_type,
            "saved_to": str(file_path),
        },
        "text_length": len(cleaned_text),
        "chunk_count": len(chunks),
        "preview_chunks": chunks[:2],
    }

    