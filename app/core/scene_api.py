import requests

from core.config import HTTP_BASE as API_BASE


class SceneAPIError(Exception):
    pass


def generate_scene(sentence: str, token: str, timeout: int = 60) -> dict:
    if not sentence:
        raise SceneAPIError("sentence is required")
    if not token:
        raise SceneAPIError("authentication is required")

    try:
        resp = requests.post(
            f"{API_BASE}/scene/generate",
            json={"sentence": sentence},
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise SceneAPIError(str(exc)) from exc

    try:
        data = resp.json()
    except ValueError:
        data = {}

    if resp.status_code >= 400 or not data.get("success"):
        raise SceneAPIError(
            data.get("error") or resp.reason or "scene generation failed"
        )

    scene = data.get("scene")
    if not isinstance(scene, str) or not scene.startswith("data:image/"):
        raise SceneAPIError("backend returned an invalid scene")

    return data
