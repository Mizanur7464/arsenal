"""2captcha.com — image captcha for Queue-it (set TWOCAPTCHA_API_KEY in .env)."""

import base64
import os
import time
import urllib.parse
import urllib.request

from .logger_setup import sub, sub_ok, sub_warn

IN_URL = "https://2captcha.com/in.php"
RES_URL = "https://2captcha.com/res.php"


def api_key() -> str:
    return (
        os.getenv("TWOCAPTCHA_API_KEY")
        or os.getenv("CAPTCHA_API_KEY")
        or os.getenv("TWO_CAPTCHA_API_KEY")
        or ""
    ).strip()


def configured() -> bool:
    return bool(api_key())


def _http_get(url: str, params: dict) -> str:
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{url}?{qs}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace").strip()


def solve_image_base64(image_b64: str, *, timeout_sec: int = 120) -> str | None:
    """Send image captcha to 2captcha; return text solution or None."""
    key = api_key()
    if not key:
        sub_warn("TWOCAPTCHA_API_KEY missing in .env")
        return None

    sub("Sending captcha to 2captcha...")
    try:
        payload = urllib.parse.urlencode(
            {"key": key, "method": "base64", "body": image_b64, "json": 0}
        ).encode("utf-8")
        req = urllib.request.Request(IN_URL, data=payload, method="POST")
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = resp.read().decode("utf-8", errors="replace").strip()
        resp = body
    except Exception as e:
        sub_warn(f"2captcha upload failed: {e}")
        return None

    if not resp.startswith("OK|"):
        sub_warn(f"2captcha upload error: {resp[:120]}")
        return None

    task_id = resp.split("|", 1)[1]
    sub(f"2captcha task {task_id} — waiting for solution...")
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        time.sleep(5)
        try:
            check = _http_get(
                RES_URL,
                {"key": key, "action": "get", "id": task_id, "json": 0},
            )
        except Exception as e:
            sub_warn(f"2captcha poll error: {e}")
            continue
        if check.startswith("OK|"):
            solution = check.split("|", 1)[1].strip()
            sub_ok(f"2captcha solved: {solution[:12]}...")
            return solution
        if check == "CAPCHA_NOT_READY":
            continue
        sub_warn(f"2captcha result: {check[:120]}")
        return None

    sub_warn("2captcha timeout waiting for solution")
    return None
