"""AI image generation for the deck mixer — multi-provider.

Supports several generative image providers. Pick one with the IMAGE_PROVIDER
setting (e.g. "openai", "gemini", "stability", "together", "fal", "replicate"),
or leave it as "auto" to use the first configured provider in DEFAULT_ORDER.

    Provider     Setting              Model
    --------     -------              -----
    openai       OPENAI_API_KEY       gpt-image-1
    gemini       GEMINI_API_KEY       imagen-4.0
    stability    STABILITY_API_KEY    stable-image core
    together     TOGETHER_API_KEY     FLUX.1-schnell
    fal          FAL_KEY              FLUX schnell
    replicate    REPLICATE_API_TOKEN  black-forest-labs/flux-schnell

Each provider returns image bytes or None. Results cache in-process and every
provider degrades silently so callers can fall back to stock photos.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable

_CACHE: dict[str, bytes | None] = {}

# orientation -> per-provider geometry
_OAI_SIZE   = {"landscape": "1536x1024", "portrait": "1024x1536", "square": "1024x1024"}
_ASPECT     = {"landscape": "16:9", "portrait": "9:16", "square": "1:1"}
_WH         = {"landscape": (1024, 576), "portrait": (576, 1024), "square": (1024, 1024)}
_FAL_SIZE   = {"landscape": "landscape_16_9", "portrait": "portrait_16_9", "square": "square_hd"}


# Last failure reason per provider, for diagnostics (preview_image / test-image).
LAST_ERROR: dict[str, str] = {}


def _http(url: str, *, data: bytes | None = None, headers: dict | None = None,
          timeout: int = 90) -> bytes:
    """POST/GET returning bytes. Raises RuntimeError with the HTTP status and
    response body on failure, so callers can surface a real reason."""
    req = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:400]
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code}: {body or e.reason}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"network error: {e.reason}") from None


def _download(url: str, timeout: int = 30) -> bytes | None:
    try:
        img = _http(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
        return img if len(img) > 5000 else None
    except (urllib.error.URLError, urllib.error.HTTPError):
        return None


# --- individual providers ---------------------------------------------------

# NB: providers no longer swallow errors — exceptions propagate to
# generate_image(), which records them in LAST_ERROR for diagnostics.

def _openai(prompt: str, o: str) -> bytes | None:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    body = json.dumps({"model": "gpt-image-1", "prompt": prompt,
                       "size": _OAI_SIZE[o], "n": 1}).encode()
    raw = _http("https://api.openai.com/v1/images/generations", data=body,
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json"})
    return base64.b64decode(json.loads(raw)["data"][0]["b64_json"])


def _gemini(prompt: str, o: str) -> bytes | None:
    """Google Imagen 4 via the Gemini API. NOTE: Imagen requires a
    billing-enabled key; a free-tier key returns HTTP 403."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        return None
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           "imagen-4.0-generate-001:predict")
    body = json.dumps({
        "instances": [{"prompt": prompt}],
        "parameters": {"sampleCount": 1, "aspectRatio": _ASPECT[o]},
    }).encode()
    raw = _http(url, data=body, headers={"Content-Type": "application/json",
                                         "x-goog-api-key": key})
    preds = json.loads(raw).get("predictions", [])
    if preds and preds[0].get("bytesBase64Encoded"):
        return base64.b64decode(preds[0]["bytesBase64Encoded"])
    raise RuntimeError("no image in Imagen response")


def _gemini_flash(prompt: str, o: str) -> bytes | None:
    """Gemini 2.5 Flash image generation via generateContent — works on the
    FREE tier (no billing). Aspect is requested in the prompt text."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        return None
    aspect_word = {"landscape": "wide 16:9 landscape",
                   "portrait": "tall 9:16 portrait", "square": "square"}[o]
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           "gemini-2.5-flash-image:generateContent")
    body = json.dumps({
        "contents": [{"parts": [{"text": f"Generate a {aspect_word} image. {prompt}"}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }).encode()
    raw = _http(url, data=body, headers={"Content-Type": "application/json",
                                         "x-goog-api-key": key})
    for cand in json.loads(raw).get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])
    raise RuntimeError("no image in Gemini Flash response")


def _stability(prompt: str, o: str) -> bytes | None:
    key = os.environ.get("STABILITY_API_KEY")
    if not key:
        return None
    boundary = "----glazeBoundary7MA4YWxkTrZu0gW"
    parts = []
    for name, value in (("prompt", prompt), ("aspect_ratio", _ASPECT[o]),
                        ("output_format", "jpeg")):
        parts.append(f"--{boundary}\r\n"
                     f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n')
    body = ("".join(parts) + f"--{boundary}--\r\n").encode()
    img = _http("https://api.stability.ai/v2beta/stable-image/generate/core",
                data=body,
                headers={"Authorization": f"Bearer {key}", "Accept": "image/*",
                         "Content-Type": f"multipart/form-data; boundary={boundary}"})
    return img if len(img) > 5000 else None


def _together(prompt: str, o: str) -> bytes | None:
    key = os.environ.get("TOGETHER_API_KEY")
    if not key:
        return None
    w, h = _WH[o]
    body = json.dumps({"model": "black-forest-labs/FLUX.1-schnell-Free",
                       "prompt": prompt, "width": w, "height": h,
                       "n": 1, "response_format": "b64_json"}).encode()
    raw = _http("https://api.together.xyz/v1/images/generations", data=body,
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json"})
    d = json.loads(raw)["data"][0]
    if d.get("b64_json"):
        return base64.b64decode(d["b64_json"])
    return _download(d["url"]) if d.get("url") else None


def _fal(prompt: str, o: str) -> bytes | None:
    key = os.environ.get("FAL_KEY")
    if not key:
        return None
    body = json.dumps({"prompt": prompt, "image_size": _FAL_SIZE[o]}).encode()
    raw = _http("https://fal.run/fal-ai/flux/schnell", data=body,
                headers={"Authorization": f"Key {key}",
                         "Content-Type": "application/json"})
    imgs = json.loads(raw).get("images", [])
    return _download(imgs[0]["url"]) if imgs and imgs[0].get("url") else None


def _replicate(prompt: str, o: str) -> bytes | None:
    key = os.environ.get("REPLICATE_API_TOKEN")
    if not key:
        return None
    body = json.dumps({"input": {"prompt": prompt, "aspect_ratio": _ASPECT[o],
                                 "output_format": "jpg"}}).encode()
    raw = _http(
        "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "Prefer": "wait"})
    out = json.loads(raw).get("output")
    url = out[0] if isinstance(out, list) else out
    return _download(url) if url else None


@dataclass
class Provider:
    name: str
    env_key: str
    fn: Callable[[str, str], "bytes | None"]
    label: str


_PROVIDERS: dict[str, Provider] = {
    "gemini_flash": Provider("gemini_flash", "GEMINI_API_KEY", _gemini_flash, "Google Gemini 2.5 Flash image (free tier)"),
    "openai":    Provider("openai", "OPENAI_API_KEY", _openai, "OpenAI gpt-image-1"),
    "gemini":    Provider("gemini", "GEMINI_API_KEY", _gemini, "Google Imagen 4 (needs billing)"),
    "stability": Provider("stability", "STABILITY_API_KEY", _stability, "Stability core"),
    "together":  Provider("together", "TOGETHER_API_KEY", _together, "Together FLUX.1-schnell"),
    "fal":       Provider("fal", "FAL_KEY", _fal, "fal.ai FLUX schnell"),
    "replicate": Provider("replicate", "REPLICATE_API_TOKEN", _replicate, "Replicate FLUX schnell"),
}

# Free-tier-friendly first: Gemini Flash needs no billing; Imagen does.
DEFAULT_ORDER = ["gemini_flash", "openai", "gemini", "stability",
                 "together", "fal", "replicate"]


def _key_present(p: Provider) -> bool:
    if p.name in ("gemini", "gemini_flash"):
        return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    return bool(os.environ.get(p.env_key))


def configured_providers() -> list[str]:
    """Names of providers that have a key set, in default order."""
    return [n for n in DEFAULT_ORDER if _key_present(_PROVIDERS[n])]


def available() -> bool:
    return bool(configured_providers())


def active_provider() -> str | None:
    """Which provider would be used: the IMAGE_PROVIDER choice, else the first
    configured one. None if nothing is configured."""
    choice = (os.environ.get("IMAGE_PROVIDER") or "auto").lower()
    if choice != "auto":
        return choice if _key_present(_PROVIDERS.get(choice, Provider("", "", None, ""))) else None
    configured = configured_providers()
    return configured[0] if configured else None


def generate_image(prompt: str, orientation: str = "landscape",
                   provider: str | None = None) -> bytes | None:
    """Generate an image, honouring the configured/selected provider.

    provider/IMAGE_PROVIDER pins a specific maker; "auto" (default) tries every
    configured provider in DEFAULT_ORDER until one returns an image.
    """
    if orientation not in _ASPECT:
        orientation = "landscape"
    choice = (provider or os.environ.get("IMAGE_PROVIDER") or "auto").lower()

    if choice != "auto":
        p = _PROVIDERS.get(choice)
        if not p or not _key_present(p):
            return None
        order = [choice]
    else:
        order = configured_providers()

    for name in order:
        ck = f"{name}:{prompt}:{orientation}"
        if ck in _CACHE:
            if _CACHE[ck]:
                return _CACHE[ck]
            continue
        try:
            img = _PROVIDERS[name].fn(prompt, orientation)
        except Exception as e:                     # record the real reason
            LAST_ERROR[name] = str(e)
            img = None
        else:
            LAST_ERROR.pop(name, None)
        _CACHE[ck] = img
        if img:
            return img
    return None


def diagnose(prompt: str = "a simple blue circle on white",
             orientation: str = "landscape") -> str:
    """Try the active provider(s) once and report exactly what happened —
    the saved image size on success, or the real API error on failure."""
    choice = (os.environ.get("IMAGE_PROVIDER") or "auto").lower()
    names = ([choice] if choice != "auto" else configured_providers()) or []
    if not names:
        return ("No image-generation provider configured. Set a key "
                "(e.g. GEMINI_API_KEY) and IMAGE_PROVIDER, then retry.")
    lines = [f"IMAGE_PROVIDER={choice}; trying: {', '.join(names)}"]
    for name in names:
        p = _PROVIDERS.get(name)
        if not p:
            lines.append(f"  {name}: unknown provider"); continue
        if not _key_present(p):
            lines.append(f"  {name}: no key set"); continue
        try:
            img = p.fn(prompt, orientation if orientation in _ASPECT else "landscape")
            lines.append(f"  {name}: ✓ {len(img):,} bytes" if img
                         else f"  {name}: ✗ returned no image")
        except Exception as e:
            lines.append(f"  {name}: ✗ {e}")
    return "\n".join(lines)
