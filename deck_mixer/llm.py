"""Structured-JSON LLM call — the 'art director' brain for Glaze.

Multi-provider, mirroring imagegen.py's design so the two "which AI does the
work" choices are configured the same way. Pick one with LLM_PROVIDER
(e.g. "gemini", "claude", "openai"), or leave it "auto" to try every
configured provider in DEFAULT_ORDER until one succeeds.

    Provider   Setting              Model
    --------   -------              -----
    gemini     GEMINI_API_KEY       gemini-flash-latest
    claude     ANTHROPIC_API_KEY    claude-sonnet-4-6
    openai     OPENAI_API_KEY       gpt-4o-mini

Adding a provider: write one function `(system, user, schema) -> dict | None`
that raises on failure (don't swallow errors — the caller records them for
diagnostics), then register it in _PROVIDERS. Nothing else needs to change;
every call site in planner.py / glaze/proof.py / glaze/style.py goes through
call_json() and is provider-agnostic.

Every provider is handed the SAME JSON-Schema `schema` (the kind already
written as a Claude tool `input_schema` — plain lowercase-typed JSON Schema),
so one schema per call site works across all providers.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable

# Last failure reason per provider, for diagnostics.
LAST_ERROR: dict[str, str] = {}


def _http(url: str, *, data: bytes, headers: dict, timeout: int = 60) -> bytes:
    """POST returning bytes. Raises RuntimeError with the HTTP status and
    response body on failure, so callers can surface a real reason."""
    req = urllib.request.Request(url, data=data, headers=headers)
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


# --- individual providers ---------------------------------------------------
# Each returns a dict matching `schema`, or None if its key isn't set.
# Exceptions propagate to call_json(), which records them in LAST_ERROR.

def _gemini(system: str, user: str, schema: dict, model: str = "gemini-flash-latest") -> dict | None:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = json.dumps({
        "contents": [{"parts": [{"text": user}]}],
        "systemInstruction": {"parts": [{"text": system}]},
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema},
    }).encode()
    raw = _http(url, data=body, headers={"Content-Type": "application/json",
                                         "X-goog-api-key": key})
    data = json.loads(raw)
    parts = data["candidates"][0]["content"]["parts"]
    text = next(p["text"] for p in parts if "text" in p)
    return json.loads(text)


def _claude(system: str, user: str, schema: dict, model: str = "claude-sonnet-4-6") -> dict | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    import anthropic
    client = anthropic.Anthropic(api_key=key)
    tool = {"name": "response", "description": "Structured response.", "input_schema": schema}
    msg = client.messages.create(
        model=model, max_tokens=4000, system=system, tools=[tool],
        tool_choice={"type": "tool", "name": "response"},
        messages=[{"role": "user", "content": user}],
    )
    for block in msg.content:
        if block.type == "tool_use" and block.name == "response":
            return block.input
    raise RuntimeError("no tool_use block in Claude response")


def _openai(system: str, user: str, schema: dict, model: str = "gpt-4o-mini") -> dict | None:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    sys_msg = system + "\n\nRespond with ONLY a JSON object matching this schema:\n" + json.dumps(schema)
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": sys_msg},
                     {"role": "user", "content": user}],
        "response_format": {"type": "json_object"},
    }).encode()
    raw = _http("https://api.openai.com/v1/chat/completions", data=body,
               headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    content = json.loads(raw)["choices"][0]["message"]["content"]
    return json.loads(content)


@dataclass
class Provider:
    name: str
    env_key: str
    fn: Callable[[str, str, dict], "dict | None"]
    label: str


_PROVIDERS: dict[str, Provider] = {
    "gemini": Provider("gemini", "GEMINI_API_KEY", _gemini, "Google Gemini (gemini-flash-latest)"),
    "claude": Provider("claude", "ANTHROPIC_API_KEY", _claude, "Anthropic Claude (claude-sonnet-4-6)"),
    "openai": Provider("openai", "OPENAI_API_KEY", _openai, "OpenAI (gpt-4o-mini)"),
}

DEFAULT_ORDER = ["gemini", "claude", "openai"]


def _key_present(p: Provider) -> bool:
    if p.name == "gemini":
        return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    return bool(os.environ.get(p.env_key))


def configured_providers() -> list[str]:
    """Names of providers that have a key set, in default order."""
    return [n for n in DEFAULT_ORDER if _key_present(_PROVIDERS[n])]


def available() -> bool:
    return bool(configured_providers())


def active_provider() -> str | None:
    """Which provider would be used: the LLM_PROVIDER choice, else the first
    configured one. None if nothing is configured."""
    choice = (os.environ.get("LLM_PROVIDER") or "auto").lower()
    if choice != "auto":
        return choice if _key_present(_PROVIDERS.get(choice, Provider("", "", None, ""))) else None
    configured = configured_providers()
    return configured[0] if configured else None


def call_json(system: str, user: str, schema: dict, provider: str | None = None) -> dict | None:
    """Ask whichever LLM is configured for a JSON object matching `schema`.

    provider/LLM_PROVIDER pins a specific one; "auto" (default) tries every
    configured provider in DEFAULT_ORDER until one returns a result.
    """
    choice = (provider or os.environ.get("LLM_PROVIDER") or "auto").lower()
    order = [choice] if choice != "auto" else configured_providers()

    for name in order:
        p = _PROVIDERS.get(name)
        if not p or not _key_present(p):
            continue
        try:
            result = p.fn(system, user, schema)
        except Exception as e:                     # record the real reason
            LAST_ERROR[name] = str(e)
            result = None
        else:
            LAST_ERROR.pop(name, None)
        if result:
            return result
    return None


def diagnose() -> str:
    """Try the active provider(s) once with a trivial schema and report
    exactly what happened — success or the real API error."""
    choice = (os.environ.get("LLM_PROVIDER") or "auto").lower()
    names = [choice] if choice != "auto" else configured_providers()
    if not names:
        return ("No LLM provider configured. Set a key (e.g. GEMINI_API_KEY, "
                "ANTHROPIC_API_KEY, or OPENAI_API_KEY) and retry.")
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}
    lines = [f"LLM_PROVIDER={choice}; trying: {', '.join(names)}"]
    for name in names:
        p = _PROVIDERS.get(name)
        if not p:
            lines.append(f"  {name}: unknown provider"); continue
        if not _key_present(p):
            lines.append(f"  {name}: no key set"); continue
        try:
            result = p.fn("Reply with exactly {\"ok\": true}.", "ping", schema)
            lines.append(f"  {name}: ✓ {result}" if result else f"  {name}: ✗ returned nothing")
        except Exception as e:
            lines.append(f"  {name}: ✗ {e}")
    return "\n".join(lines)
