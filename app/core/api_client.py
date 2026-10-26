"""Auth API client. Talks to the Node.js backend using requests."""
import requests

from core import session
from core.config import HTTP_BASE as BASE_URL


class AuthError(Exception):
    pass


def _error_message(resp) -> str:
    try:
        data = resp.json()
    except ValueError:
        return resp.reason
    if isinstance(data, dict):
        return data.get("error") or resp.reason
    return resp.reason


def _post(path: str, payload: dict, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.post(f"{BASE_URL}{path}", json=payload, headers=headers, timeout=5)
        if resp.status_code >= 400:
            raise AuthError(_error_message(resp))
        return resp.json()
    except requests.RequestException as e:
        raise AuthError(str(e))


def _get(path: str, token: str) -> dict:
    try:
        resp = requests.get(f"{BASE_URL}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=5)
        if resp.status_code >= 400:
            raise AuthError(_error_message(resp))
        return resp.json()
    except requests.RequestException as e:
        raise AuthError(str(e))


def register(full_name: str, com_id: str, password: str) -> dict:
    data = _post("/auth/register", {
        "full_name": full_name,
        "com_id": com_id,
        "password": password,
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
