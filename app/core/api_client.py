"""Auth API client. Talks to the Node.js backend using requests."""
from typing import List
import requests

from core import session

class AuthError(Exception):
    pass

BASE_URL = "http://127.0.0.1:8080"


def _post(path: str, payload: dict, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.post(f"{BASE_URL}{path}", json=payload, headers=headers, timeout=5)
        if resp.status_code >= 400:
            try:
                data = resp.json()
                raise AuthError(data.get("error") or resp.reason)
            except Exception:
                raise AuthError(resp.reason)
        return resp.json()
    except requests.RequestException as e:
        raise AuthError(str(e))


def _get(path: str, token: str) -> dict:
    try:
        resp = requests.get(f"{BASE_URL}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=5)
        if resp.status_code >= 400:
            try:
                data = resp.json()
                raise AuthError(data.get("error") or resp.reason)
            except Exception:
                raise AuthError(resp.reason)
        return resp.json()
    except requests.RequestException as e:
        raise AuthError(str(e))


def register(full_name: str, com_id: str, password: str, preferred: List[str]) -> dict:
    data = _post("/auth/register", {
        "full_name": full_name,
        "com_id": com_id,
        "password": password,
        "preferred": preferred,
    })
    return data.get("user", data)


def login(com_id: str, password: str) -> dict:
    data = _post("/auth/login", {
        "com_id": com_id,
        "password": password,
    })
    token = data.get("token")
    user = data.get("user", {})
    if token:
        session.save(token, user)
    return user


def me(token: str) -> dict:
    data = _get("/auth/me", token)
    return data.get("user", {})
