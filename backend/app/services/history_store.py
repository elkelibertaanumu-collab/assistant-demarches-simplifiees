import json
import os
from pathlib import Path

from app.models.schemas import HistoryItem
try:
    import psycopg  # type: ignore
except Exception:
    psycopg = None

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "backend" / "data" / "processed"
HISTORY_FILE = DATA_DIR / "history.json"
MAX_ITEMS = 20
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
USE_POSTGRES = bool(DATABASE_URL and psycopg is not None)


def _connect():
    if not DATABASE_URL or psycopg is None:
        raise RuntimeError("Postgres not configured.")
    return psycopg.connect(DATABASE_URL)


def _ensure_history_table() -> None:
    if not USE_POSTGRES:
        return
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS app_history (
                  id BIGINT PRIMARY KEY,
                  question TEXT NOT NULL,
                  summary TEXT NOT NULL,
                  confidence_score DOUBLE PRECISION NOT NULL,
                  generated_at TIMESTAMPTZ NOT NULL
                );
                """
            )
        conn.commit()


def load_history() -> list[HistoryItem]:
    if USE_POSTGRES:
        _ensure_history_table()
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, question, summary, confidence_score, generated_at
                    FROM app_history
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (MAX_ITEMS,)
                )
                rows = cur.fetchall()
        items: list[HistoryItem] = []
        for row in rows:
            items.append(
                HistoryItem(
                    id=int(row[0]),
                    question=str(row[1]),
                    summary=str(row[2]),
                    confidence_score=float(row[3]),
                    generated_at=str(row[4])
                )
            )
        return items

    if not HISTORY_FILE.exists():
        return []
    try:
        payload = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            return []
        items: list[HistoryItem] = []
        for row in payload:
            try:
                items.append(HistoryItem(**row))
            except Exception:
                continue
        return items[:MAX_ITEMS]
    except Exception:
        return []


def save_history(items: list[HistoryItem]) -> None:
    if USE_POSTGRES:
        _ensure_history_table()
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM app_history")
                for item in items[:MAX_ITEMS]:
                    cur.execute(
                        """
                        INSERT INTO app_history (id, question, summary, confidence_score, generated_at)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            int(item.id),
                            item.question,
                            item.summary,
                            float(item.confidence_score),
                            item.generated_at
                        )
                    )
            conn.commit()
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    serializable = [item.model_dump() for item in items[:MAX_ITEMS]]
    HISTORY_FILE.write_text(
        json.dumps(serializable, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
