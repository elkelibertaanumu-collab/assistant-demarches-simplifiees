from collections import deque
import re
import time

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
        return AuthResponse(token=token, user=AuthUser(**safe_user))
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
        return AuthResponse(token=token, user=AuthUser(**user))
    except ValueError:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")


@router.get("/auth/me", response_model=AuthMeResponse)
def auth_me(authorization: str | None = Header(default=None)) -> AuthMeResponse:
    token = extract_bearer_token(authorization)
    user = auth_service.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session invalide.")
    return AuthMeResponse(user=AuthUser(**user))


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
