import re
from typing import List


def clean_text(text: str) -> str:
    # fazla boşlukları temizle
    text = re.sub(r"\s+", " ", text)

    # gereksiz karakterleri kırp
    text = text.strip()

    return text


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100
) -> List[str]:

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        chunk = text[start:end]
        chunks.append(chunk)

        start += chunk_size - overlap

    return chunks