import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "backend" / "data" / "raw"
SOURCES_FILE = RAW_DIR / "web_sources.json"
OUTPUT_FILE = RAW_DIR / "sources.jsonl"
ALLOWED_HOST_SUFFIX = ".gouv.tg"


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def extract_html_text(url: str, timeout: int = 25) -> str:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def extract_pdf_text(url: str, timeout: int = 45) -> str:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    temp_pdf = RAW_DIR / "_tmp_ingest.pdf"
    temp_pdf.write_bytes(response.content)
    try:
        reader = PdfReader(str(temp_pdf))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = " ".join(pages)
        return re.sub(r"\s+", " ", text).strip()
    finally:
        if temp_pdf.exists():
            temp_pdf.unlink()


def extract_text(url: str, source_type: str) -> str:
    if source_type == "pdf" or url.lower().endswith(".pdf"):
        return extract_pdf_text(url)
    return extract_html_text(url)


def infer_title(url: str) -> str:
    host = urlparse(url).netloc.replace("www.", "")
    return f"Source officielle: {host}"


def is_official_secure_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        return False
    host = parsed.netloc.lower()
    return host.endswith(ALLOWED_HOST_SUFFIX)


def load_source_list() -> list[dict]:
    if not SOURCES_FILE.exists():
        raise FileNotFoundError(
            f"Missing source list file: {SOURCES_FILE}. "
            "Create it from backend/data/raw/web_sources.example.json."
        )
    return json.loads(SOURCES_FILE.read_text(encoding="utf-8"))


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    source_list = load_source_list()
    today = date.today().isoformat()
    output_lines: list[str] = []

    for idx, item in enumerate(source_list):
        url = str(item.get("url", "")).strip()
        if not url:
            continue
        if not is_official_secure_url(url):
            print(f"[INGEST] SKIPPED (non officiel/non https): {url}")
            continue
        category = str(item.get("category", "general")).strip() or "general"
        source_type = str(item.get("type", "html")).strip() or "html"
        title = str(item.get("title", "")).strip() or infer_title(url)
        updated_at = str(item.get("updated_at", "")).strip() or today
        source_id = str(item.get("id", "")).strip() or f"{slugify(category)}-{idx+1:03d}"

        try:
            text = extract_text(url=url, source_type=source_type)
            if len(text) < 80:
                print(f"[INGEST] Skipped short content: {url}")
                continue
            payload = {
                "id": source_id,
                "title": title,
                "url": url,
                "updated_at": updated_at,
                "category": category,
                "country": "Togo",
                "text": text
            }
            output_lines.append(json.dumps(payload, ensure_ascii=False))
            print(f"[INGEST] OK: {title} ({category})")
        except Exception as exc:
            print(f"[INGEST] FAILED: {url} -> {exc}")

    OUTPUT_FILE.write_text("\n".join(output_lines), encoding="utf-8")
    print(f"[INGEST] Wrote {len(output_lines)} sources to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
