import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

import bcrypt
try:
    import psycopg  # type: ignore
except Exception:
    psycopg = None

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "backend" / "data" / "processed"
USERS_FILE = DATA_DIR / "auth_users.json"
SESSIONS_FILE = DATA_DIR / "auth_sessions.json"


class AuthService:
    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", "").strip()
        self.use_postgres = bool(self.database_url)
        if self.use_postgres and psycopg is None:
            raise RuntimeError("DATABASE_URL is set but psycopg is not installed.")
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.users = self._load_json(USERS_FILE, default=[]) if not self.use_postgres else []
        self.sessions = self._load_json(SESSIONS_FILE, default={}) if not self.use_postgres else {}
        if self.use_postgres:
            self._ensure_postgres_tables()

    def _connect(self):
        if not self.database_url or psycopg is None:
            raise RuntimeError("Postgres not configured.")
        return psycopg.connect(self.database_url)

    def _ensure_postgres_tables(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS auth_users (
                      id TEXT PRIMARY KEY,
                      name TEXT NOT NULL,
                      email TEXT NOT NULL UNIQUE,
                      password_hash TEXT NOT NULL,
                      created_at TIMESTAMPTZ NOT NULL
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS auth_sessions (
                      token TEXT PRIMARY KEY,
                      user_id TEXT NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
                      created_at TIMESTAMPTZ NOT NULL
                    );
                    """
                )
            conn.commit()

    def _load_json(self, path: Path, default):
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default

    def _save_users(self) -> None:
        USERS_FILE.write_text(json.dumps(self.users, ensure_ascii=False, indent=2), encoding="utf-8")

    def _save_sessions(self) -> None:
        SESSIONS_FILE.write_text(json.dumps(self.sessions, ensure_ascii=False, indent=2), encoding="utf-8")

    def register(self, name: str, email: str, password: str) -> dict:
        normalized_email = email.strip().lower()
        if self.use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM auth_users WHERE email = %s LIMIT 1", (normalized_email,))
                    if cur.fetchone():
                        raise ValueError("EMAIL_ALREADY_EXISTS")
                    user_id = secrets.token_hex(8)
                    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                    created_at = datetime.now(timezone.utc).isoformat()
                    cur.execute(
                        """
                        INSERT INTO auth_users (id, name, email, password_hash, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (user_id, name.strip(), normalized_email, password_hash, created_at)
                    )
                conn.commit()
            return {"id": user_id, "name": name.strip(), "email": normalized_email}

        if any(u["email"] == normalized_email for u in self.users):
            raise ValueError("EMAIL_ALREADY_EXISTS")
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        user = {
            "id": secrets.token_hex(8),
            "name": name.strip(),
            "email": normalized_email,
            "password_hash": password_hash,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.users.append(user)
        self._save_users()
        return {"id": user["id"], "name": user["name"], "email": user["email"]}

    def login(self, email: str, password: str) -> tuple[str, dict]:
        normalized_email = email.strip().lower()
        if self.use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, name, email, password_hash FROM auth_users WHERE email = %s LIMIT 1",
                        (normalized_email,)
                    )
                    row = cur.fetchone()
                    if not row:
                        raise ValueError("INVALID_CREDENTIALS")
                    user_id, user_name, user_email, password_hash = row
                    ok = bcrypt.checkpw(password.encode("utf-8"), str(password_hash).encode("utf-8"))
                    if not ok:
                        raise ValueError("INVALID_CREDENTIALS")
                    token = secrets.token_urlsafe(32)
                    cur.execute(
                        """
                        INSERT INTO auth_sessions (token, user_id, created_at)
                        VALUES (%s, %s, %s)
                        """,
                        (token, user_id, datetime.now(timezone.utc).isoformat())
                    )
                conn.commit()
            safe_user = {"id": user_id, "name": user_name, "email": user_email}
            return token, safe_user

        user = next((u for u in self.users if u["email"] == normalized_email), None)
        if not user:
            raise ValueError("INVALID_CREDENTIALS")
        ok = bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8"))
        if not ok:
            raise ValueError("INVALID_CREDENTIALS")
        token = secrets.token_urlsafe(32)
        self.sessions[token] = {
            "user_id": user["id"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self._save_sessions()
        safe_user = {"id": user["id"], "name": user["name"], "email": user["email"]}
        return token, safe_user

    def get_user_by_token(self, token: str) -> dict | None:
        if not token:
            return None
        if self.use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT u.id, u.name, u.email
                        FROM auth_sessions s
                        JOIN auth_users u ON u.id = s.user_id
                        WHERE s.token = %s
                        LIMIT 1
                        """,
                        (token,)
                    )
                    row = cur.fetchone()
                    if not row:
                        return None
                    return {"id": row[0], "name": row[1], "email": row[2]}

        session = self.sessions.get(token)
        if not session:
            return None
        user = next((u for u in self.users if u["id"] == session["user_id"]), None)
        if not user:
            return None
        return {"id": user["id"], "name": user["name"], "email": user["email"]}

    def logout(self, token: str) -> None:
        if self.use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM auth_sessions WHERE token = %s", (token,))
                conn.commit()
            return
        if token in self.sessions:
            self.sessions.pop(token, None)
            self._save_sessions()
