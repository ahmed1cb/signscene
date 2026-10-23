import os

import requests

API_BASE = (
    os.environ.get("SIGNSCENE_API_BASE")
    or os.environ.get("SIGNSCENE_BACKEND_URL")
    or "http://127.0.0.1:8080"
)


def process_sentence(sentence: str, timeout: int = 3):
    if not sentence:
        return None
    try:
        resp = requests.post(
            f"{API_BASE}/scene/process",
            json={"sentence": sentence},
            timeout=timeout,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        print(data)
        if not data.get("success"):
            return None
        return {
            "prompt": data.get("prompt", ""),
            "negative_prompt": data.get("negative_prompt", ""),
            "defaults": data.get("defaults") or {},
        }
    except Exception:
        return None
