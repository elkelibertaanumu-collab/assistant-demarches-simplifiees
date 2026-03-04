import random
import string
import sys

import requests


def random_email() -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"smoke.{suffix}@example.com"


def main() -> None:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    base_url = base_url.rstrip("/")
    print(f"[SMOKE] Base URL: {base_url}")

    # Health
    r = requests.get(f"{base_url}/api/health", timeout=20)
    r.raise_for_status()
    print("[SMOKE] /api/health OK")

    # Register
    email = random_email()
    password = "StrongPass123"
    register_payload = {"name": "Smoke User", "email": email, "password": password}
    r = requests.post(f"{base_url}/api/auth/register", json=register_payload, timeout=30)
    r.raise_for_status()
    print("[SMOKE] /api/auth/register OK")

    # Login
    r = requests.post(
        f"{base_url}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30
    )
    r.raise_for_status()
    token = r.json().get("token", "")
    if not token:
        raise RuntimeError("Token missing in login response")
    print("[SMOKE] /api/auth/login OK")

    # Ask
    r = requests.post(
        f"{base_url}/api/ask",
        json={"question": "Quels papiers pour une carte d'identite au Togo ?"},
        timeout=45
    )
    r.raise_for_status()
    body = r.json()
    print("[SMOKE] /api/ask OK")
    print(f"[SMOKE] sources={len(body.get('sources', []))} confidence={body.get('confidence_score')}")

    # Me
    r = requests.get(
        f"{base_url}/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20
    )
    r.raise_for_status()
    print("[SMOKE] /api/auth/me OK")

    print("[SMOKE] ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
