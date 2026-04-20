import re
import uuid
from pathlib import Path


def sanitize_filename(filename: str) -> str:
    # sadece harf, sayı, nokta ve alt çizgi bırak
    filename = filename.lower()
    filename = re.sub(r"[^a-z0-9_.-]", "_", filename)
    return filename


def generate_unique_filename(filename: str) -> str:
    ext = Path(filename).suffix
    name = Path(filename).stem

    unique_id = uuid.uuid4().hex[:8]

    return f"{name}_{unique_id}{ext}"