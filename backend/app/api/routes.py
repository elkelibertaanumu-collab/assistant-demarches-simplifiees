from collections import deque
import json
import os
from pathlib import Path
import re
import subprocess
import time
from urllib.parse import urlparse

from fastapi import APIRouter, Header, HTTPException, Request

from app.models.schemas import (
    AskRequest,
    AskResponse,
    AuthLoginRequest,
    AuthLogoutResponse,
    AuthMeResponse,
    AuthRegisterRequest,
    AuthResponse,
    AuthUser,
    AdminActionResponse,
    AdminSourcesResponse,
    AdminSourcesUpdateRequest,
    ChecklistRequest,
    ChecklistResponse,
    FormAssistRequest,
    FormAssistResponse,
    FormCatalogResponse,
    FormGenerateRequest,
    FormGenerateResponse,
    HistoryItem,
    HistoryResponse
)
from app.services.auth_service import AuthService
from app.services.form_service import FormService
from app.services.history_store import load_history, save_history
from app.services.rag_service import RagService

router = APIRouter()
rag_service = RagService()
form_service = FormService()
auth_service = AuthService()
loaded_history = load_history()
history_store: deque[HistoryItem] = deque(loaded_history, maxlen=20)
history_counter = max((item.id for item in loaded_history), default=0)
auth_rate_state: dict[str, list[float]] = {}
AUTH_WINDOW_SECONDS = 10 * 60
AUTH_MAX_ATTEMPTS = 8
PROJECT_ROOT = Path(__file__).resolve().parents[3]
WEB_SOURCES_FILE = PROJECT_ROOT / "backend" / "data" / "raw" / "web_sources.json"
BACKEND_DIR = PROJECT_ROOT / "backend"
ADMIN_EMAILS = {e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()}
if not ADMIN_EMAILS:
    ADMIN_EMAILS = {"admin@demarches.tg"}


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        return ""
    value = authorization.strip()
    if not value.lower().startswith("bearer "):
        return ""
    return value[7:].strip()


def password_is_strong(password: str) -> bool:
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    return True


def check_auth_rate_limit(key: str) -> None:
    now = time.time()
    attempts = auth_rate_state.get(key, [])
    attempts = [t for t in attempts if now - t <= AUTH_WINDOW_SECONDS]
    if len(attempts) >= AUTH_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Trop de tentatives. Reessaie plus tard.")
    attempts.append(now)
    auth_rate_state[key] = attempts


def is_admin_email(email: str) -> bool:
    return email.strip().lower() in ADMIN_EMAILS


def with_role(user: dict) -> dict:
    role = "admin" if is_admin_email(str(user.get("email", ""))) else "user"
    return {
        "id": str(user.get("id", "")),
        "name": str(user.get("name", "")),
        "email": str(user.get("email", "")),
        "role": role
    }


def require_admin_user(authorization: str | None) -> dict:
    token = extract_bearer_token(authorization)
    user = auth_service.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session invalide.")
    user_with_role = with_role(user)
    if user_with_role["role"] != "admin":
        raise HTTPException(status_code=403, detail="Acces admin requis.")
    return user_with_role


@router.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@router.post("/auth/register", response_model=AuthResponse)
def auth_register(payload: AuthRegisterRequest, request: Request) -> AuthResponse:
    requester = request.client.host if request.client else "unknown"
    check_auth_rate_limit(f"register:{requester}:{payload.email.strip().lower()}")
    if not password_is_strong(payload.password):
        raise HTTPException(
            status_code=400,
            detail="Mot de passe faible: min 8 caracteres avec majuscule, minuscule et chiffre."
        )
    try:
        user = auth_service.register(
            name=payload.name,
            email=payload.email,
            password=payload.password
        )
        token, safe_user = auth_service.login(payload.email, payload.password)
        return AuthResponse(token=token, user=AuthUser(**with_role(safe_user)))
    except ValueError as exc:
        if str(exc) == "EMAIL_ALREADY_EXISTS":
            raise HTTPException(status_code=409, detail="Cet email est deja utilise.")
        raise HTTPException(status_code=400, detail="Inscription impossible.")


@router.post("/auth/login", response_model=AuthResponse)
def auth_login(payload: AuthLoginRequest, request: Request) -> AuthResponse:
    requester = request.client.host if request.client else "unknown"
    check_auth_rate_limit(f"login:{requester}:{payload.email.strip().lower()}")
    try:
        token, user = auth_service.login(payload.email, payload.password)
        return AuthResponse(token=token, user=AuthUser(**with_role(user)))
    except ValueError:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")


@router.get("/auth/me", response_model=AuthMeResponse)
def auth_me(authorization: str | None = Header(default=None)) -> AuthMeResponse:
    token = extract_bearer_token(authorization)
    user = auth_service.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session invalide.")
    return AuthMeResponse(user=AuthUser(**with_role(user)))


@router.post("/auth/logout", response_model=AuthLogoutResponse)
def auth_logout(authorization: str | None = Header(default=None)) -> AuthLogoutResponse:
    token = extract_bearer_token(authorization)
    if token:
        auth_service.logout(token)
    return AuthLogoutResponse(ok=True)


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest) -> AskResponse:
    global history_counter
    response = rag_service.answer(payload.question)
    history_counter += 1
    history_store.appendleft(
        HistoryItem(
            id=history_counter,
            question=payload.question,
            summary=response.summary,
            confidence_score=response.confidence_score,
            generated_at=response.generated_at
        )
    )
    save_history(list(history_store))
    return response


@router.post("/checklist", response_model=ChecklistResponse)
def generate_checklist(payload: ChecklistRequest) -> ChecklistResponse:
    items = [
        f"Lire la procedure officielle: {payload.procedure}",
        "Verifier les pieces obligatoires",
        "Preparer le budget des frais",
        "Deposer la demande et conserver le recu"
    ]
    return ChecklistResponse(procedure=payload.procedure, items=items)


@router.get("/history", response_model=HistoryResponse)
def history() -> HistoryResponse:
    return HistoryResponse(items=list(history_store))


@router.get("/form/catalog", response_model=FormCatalogResponse)
def form_catalog() -> FormCatalogResponse:
    return FormCatalogResponse(items=form_service.list_templates())


@router.post("/form/assist", response_model=FormAssistResponse)
def form_assist(payload: FormAssistRequest) -> FormAssistResponse:
    return form_service.assist_field(
        form_id=payload.form_id,
        field_key=payload.field_key,
        current_values=payload.current_values
    )


@router.post("/form/generate", response_model=FormGenerateResponse)
def form_generate(payload: FormGenerateRequest) -> FormGenerateResponse:
    return form_service.generate_preview(form_id=payload.form_id, values=payload.values)


@router.get("/admin/sources", response_model=AdminSourcesResponse)
def admin_sources(authorization: str | None = Header(default=None)) -> AdminSourcesResponse:
    require_admin_user(authorization)
    if not WEB_SOURCES_FILE.exists():
        return AdminSourcesResponse(items=[])
    try:
        payload = json.loads(WEB_SOURCES_FILE.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            payload = []
    except Exception:
        payload = []
    return AdminSourcesResponse(items=payload)


@router.put("/admin/sources", response_model=AdminActionResponse)
def admin_update_sources(
    request: AdminSourcesUpdateRequest,
    authorization: str | None = Header(default=None)
) -> AdminActionResponse:
    require_admin_user(authorization)
    normalized_items: list[dict] = []
    for item in request.items:
        parsed = urlparse(item.url)
        if parsed.scheme.lower() != "https" or not parsed.netloc.lower().endswith(".gouv.tg"):
            raise HTTPException(status_code=400, detail=f"URL non autorisee: {item.url}")
        if item.type not in {"html", "pdf"}:
            raise HTTPException(status_code=400, detail=f"Type invalide: {item.type}")
        normalized_items.append(item.model_dump())

    WEB_SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    WEB_SOURCES_FILE.write_text(
        json.dumps(normalized_items, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return AdminActionResponse(ok=True, message=f"{len(normalized_items)} source(s) sauvegardee(s).")


@router.post("/admin/reindex", response_model=AdminActionResponse)
def admin_reindex(authorization: str | None = Header(default=None)) -> AdminActionResponse:
    require_admin_user(authorization)
    ingest = subprocess.run(
        ["python", "-m", "scripts.ingest_sources"],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
        timeout=240
    )
    if ingest.returncode != 0:
        raise HTTPException(status_code=500, detail=(ingest.stderr or ingest.stdout or "Echec ingestion").strip())

    build = subprocess.run(
        ["python", "-m", "scripts.build_index"],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
        timeout=240
    )
    if build.returncode != 0:
        raise HTTPException(status_code=500, detail=(build.stderr or build.stdout or "Echec indexation").strip())

    msg = "Reindexation terminee."
    tail = "\n".join((ingest.stdout + "\n" + build.stdout).strip().splitlines()[-4:])
    if tail:
        msg = f"{msg} {tail}"
    return AdminActionResponse(ok=True, message=msg)
