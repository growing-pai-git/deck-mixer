"""Image fetching for the deck mixer.

Primary source: Pexels API (free, professional stock photos, no generation cost).
Requires: PEXELS_API_KEY environment variable.
Secondary source: Unsplash API. Requires: UNSPLASH_ACCESS_KEY.
With neither key set, no photo is fetched and the deck shows image placeholders.

Pexels free API: https://www.pexels.com/api/
  - 200 req/hour, 20,000 req/month
  - No attribution required in presentations (check TOS for your use case)
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


_CACHE: dict[str, bytes | None] = {}


def fetch_pexels(query: str, orientation: str = "landscape") -> bytes | None:
    """
    Fetch a stock photo from Pexels matching `query`.

    Returns JPEG bytes or None if unavailable.
    Results are cached in-process to avoid redundant API calls within one deck.
    """
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        return None

    cache_key = f"{query}:{orientation}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    try:
        q = urllib.parse.quote(query)
        search_url = (
            f"https://api.pexels.com/v1/search"
            f"?query={q}&per_page=3&orientation={orientation}&size=medium"
        )
        req = urllib.request.Request(search_url, headers={"Authorization": api_key})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read())

        photos = data.get("photos", [])
        if not photos:
            _CACHE[cache_key] = None
            return None

        # Pick the second result when available to avoid the most generic stock shot
        photo = photos[min(1, len(photos) - 1)]
        img_url = photo["src"]["large"]  # ~1900px wide

        with urllib.request.urlopen(img_url, timeout=10) as resp:
            img_bytes = resp.read()

        _CACHE[cache_key] = img_bytes
        return img_bytes

    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, KeyError):
        _CACHE[cache_key] = None
        return None



def fetch_unsplash(query: str, orientation: str = "landscape") -> bytes | None:
    """Fetch a photo from Unsplash. Requires UNSPLASH_ACCESS_KEY."""
    api_key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not api_key:
        return None
    cache_key = f"unsplash:{query}:{orientation}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]
    try:
        q = urllib.parse.quote(query)
        url = (f"https://api.unsplash.com/search/photos"
               f"?query={q}&per_page=3&orientation={orientation}"
               f"&client_id={api_key}")
        req = urllib.request.Request(url, headers={"Accept-Version": "v1"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read())
        results = data.get("results", [])
        if not results:
            _CACHE[cache_key] = None
            return None
        img_url = results[0]["urls"]["regular"]
        with urllib.request.urlopen(img_url, timeout=10) as resp:
            img = resp.read()
        _CACHE[cache_key] = img
        return img
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, KeyError):
        _CACHE[cache_key] = None
        return None



# Provider chain. Both need a key: without one the deck gets image
# placeholders instead of a random stock photo nobody chose.
_PROVIDERS = [
    (fetch_pexels, "PEXELS_API_KEY"),
    (fetch_unsplash, "UNSPLASH_ACCESS_KEY"),
]


def configured() -> list[str]:
    """Names of the stock-photo sources that have a key set."""
    return [fn.__name__.removeprefix("fetch_").title()
            for fn, env in _PROVIDERS if os.environ.get(env)]


def fetch_image(query: str, orientation: str = "landscape") -> bytes | None:
    """Resolve a photo through the keyed providers (Pexels → Unsplash); the
    first that returns usable bytes wins. None when no key is set."""
    for provider, env in _PROVIDERS:
        if not os.environ.get(env):
            continue
        img = provider(query, orientation)
        if img:
            return img
    return None
