from pathlib import Path
from typing import List

from pypdf import PdfReader
from docx import Document


def parse_txt(file_path: Path) -> str:
    # farklı encodingleri dene
    encodings = ["utf-8", "utf-16", "latin-1"]

    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                content = f.read()
                if content.strip():  # boş değilse
                    print(f"[TXT PARSED with {enc}]")
                    return content
        except Exception as e:
            continue

    # son çare: binary okuyup decode etmeye çalış
    with open(file_path, "rb") as f:
        raw = f.read()
        try:
            content = raw.decode("utf-8", errors="ignore")
            print("[TXT FALLBACK utf-8 ignore]")
            return content
        except:
            return ""

def parse_pdf(file_path: Path) -> str:
    reader = PdfReader(file_path)
    text = []

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text.append(page_text)

    return "\n".join(text)


def parse_docx(file_path: Path) -> str:
    doc = Document(file_path)
    text = []

    for para in doc.paragraphs:
        text.append(para.text)

    return "\n".join(text)


def extract_text(file_path: Path) -> str:
    extension = file_path.suffix.lower()

    if extension == ".txt":
        return parse_txt(file_path)
    elif extension == ".pdf":
        return parse_pdf(file_path)
    elif extension == ".docx":
        return parse_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {extension}")