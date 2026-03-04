import re


def normalize_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned


def chunk_text(text: str, max_chars: int = 1000, overlap: int = 150) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    size = max(200, max_chars)
    step = max(50, size - overlap)

    while start < len(text):
        end = min(len(text), start + size)
        chunks.append(text[start:end])
        start += step

    return chunks
