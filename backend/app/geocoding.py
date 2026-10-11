"""Optional Photon lookup with caching and a single-process rate budget."""

import json, time, threading, os
from urllib.request import Request, urlopen
from urllib.parse import urlencode, urlparse
from urllib.error import URLError, HTTPError
from fastapi import HTTPException
from app.geo import india_extent

_cache = {}
_lock = threading.Lock()
_last = 0.0


def geocode(query):
    global _last
    if os.getenv("GEOCODING_ENABLED", "true").lower() != "true":
        raise HTTPException(
            503, "Place lookup disabled; use saved locations, text or map selection"
        )
    url = os.getenv("GEOCODING_URL", "https://photon.komoot.io/api/")
    if urlparse(url).scheme not in {"https", "http"}:
        raise HTTPException(503, "Geocoding provider configuration invalid")
    key = query.strip().casefold()
    now = time.monotonic()
    with _lock:
        cached = _cache.get(key)
        if cached and now - cached[0] < 86400:
            return cached[1]
        if now - _last < 1.1:
            raise HTTPException(429, "Place lookup is busy; wait a moment and search again")
        _last = now
    request = Request(
        url + "?" + urlencode({"q": query, "limit": 8, "bbox": "68,6,98,38"}),
        headers={
            "User-Agent": os.getenv("GEOCODING_USER_AGENT", "DisasterMS/2.0 local-college-demo"),
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=8) as response:
            raw = response.read(1000001)
            if len(raw) > 1000000:
                raise ValueError("Oversized provider response")
            data = json.loads(raw)
        items = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            coords = feature.get("geometry", {}).get("coordinates", [])
            if len(coords) < 2 or not india_extent(coords[1], coords[0]):
                continue
            if str(props.get("countrycode", "")).upper() != "IN":
                continue
            items.append(
                {
                    "label": ", ".join(
                        dict.fromkeys(
                            str(props[k])
                            for k in ["name", "street", "city", "district", "state", "country"]
                            if props.get(k)
                        )
                    ),
                    "latitude": coords[1],
                    "longitude": coords[0],
                    "city": props.get("city") or props.get("name", ""),
                    "district": props.get("district", ""),
                    "state": props.get("state", ""),
                    "source": "Photon / OpenStreetMap (place match, not incident verification)",
                }
            )
        result = {"items": items, "attribution": "Photon / © OpenStreetMap contributors"}
        with _lock:
            if len(_cache) >= 500:
                _cache.pop(next(iter(_cache)))
            _cache[key] = (time.monotonic(), result)
        return result
    except HTTPError as exc:
        raise HTTPException(
            429 if exc.code == 429 else 503,
            "Place provider unavailable or rate limited; use text/map selection",
        ) from None
    except (URLError, TimeoutError, ValueError, KeyError, TypeError):
        raise HTTPException(
            503, "Place lookup failed; use saved locations, text or a selected map point"
        ) from None
