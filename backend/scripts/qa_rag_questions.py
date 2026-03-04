import sys
from pathlib import Path

from fastapi.testclient import TestClient


QUESTIONS = [
    "Quels papiers pour une carte d'identite au Togo ?",
    "Comment demander un casier judiciaire ?",
    "Comment creer une micro-entreprise ?",
    "Quels documents pour immatriculer une activite ?",
    "Comment faire une declaration fiscale ?",
    "Quelles etapes pour une plainte ?",
    "Quels documents pour un passeport ?",
    "Comment obtenir un releve de notes officiel ?",
    "Quelles erreurs eviter dans un dossier administratif ?",
    "Comment verifier les frais et delais avant depot ?",
]


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "backend"))
    from app.main import app  # imported after sys.path update

    client = TestClient(app)
    ok = 0
    for idx, q in enumerate(QUESTIONS, 1):
        r = client.post("/api/ask", json={"question": q})
        if r.status_code != 200:
            print(f"[QA] {idx}. FAIL status={r.status_code} q={q}")
            continue
        body = r.json()
        sources = body.get("sources", [])
        steps = body.get("steps", [])
        docs = body.get("required_documents", [])
        if not sources or not steps or not docs:
            print(f"[QA] {idx}. FAIL incomplete payload q={q}")
            continue
        ok += 1
        print(f"[QA] {idx}. OK sources={len(sources)} conf={body.get('confidence_score')}")

    print(f"[QA] Passed {ok}/{len(QUESTIONS)}")
    if ok < len(QUESTIONS):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
