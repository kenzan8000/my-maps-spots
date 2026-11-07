#!/usr/bin/env python3
"""Verify spot locations, Google Maps links and websites for a My Maps export.

Reads spots.json (see SKILL.md), writes verified.json with coordinates and a
verification status per spot. Uses only the Python standard library.

Modes:
  google  Google Places API (New) Text Search. Needs GOOGLE_MAPS_API_KEY.
          One Places request confirms the key before any spot is looked up.
  osm     OpenStreetMap Nominatim, cross-checked with Wikidata or the address.
          Never produces Google Maps links.
  auto    google if a key is available, otherwise osm (default).

--check-key
    Print whether GOOGLE_MAPS_API_KEY is set and exit, without calling Google.
    Exit status 0 means a key was found, 1 means it was not. The key itself is
    never printed. spots.json is not required with this flag.
"""

from __future__ import annotations

import argparse
import difflib
import json
import math
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
WIKIDATA_ENTITY_URL = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACES_FIELDS = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.viewport",
        "places.websiteUri",
        "places.googleMapsUri",
    ]
)

NAME_MATCH_THRESHOLD = 0.6
# Google and Wikidata often pin large places (islands, parks) at different points.
GOOGLE_WIKIDATA_MAX_M = 1000

_last_request: dict[str, float] = {}
_MIN_INTERVAL = {"nominatim.openstreetmap.org": 1.1, "www.wikidata.org": 0.2}


class FatalError(Exception):
    pass


def user_agent() -> str:
    contact = os.environ.get("MY_MAPS_SPOTS_CONTACT", "").strip()
    ua = "my-maps-spots/1.0 (travel map skill; python-urllib)"
    return f"{ua} {contact}" if contact else ua


def http_json(url: str, *, data: dict | None = None, headers: dict | None = None) -> object:
    host = urllib.parse.urlparse(url).netloc
    wait = _MIN_INTERVAL.get(host, 0) - (time.monotonic() - _last_request.get(host, 0))
    if wait > 0:
        time.sleep(wait)

    body = json.dumps(data).encode() if data is not None else None
    req_headers = {"User-Agent": user_agent(), "Accept": "application/json"}
    if body is not None:
        req_headers["Content-Type"] = "application/json"
    req_headers.update(headers or {})

    for attempt in range(3):
        req = urllib.request.Request(url, data=body, headers=req_headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                _last_request[host] = time.monotonic()
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            _last_request[host] = time.monotonic()
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue
            detail = e.read().decode("utf-8", "replace")[:500]
            raise FatalError(f"HTTP {e.code} from {host}: {detail}") from e
        except urllib.error.URLError as e:
            if attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue
            raise FatalError(f"Network error contacting {host}: {e.reason}") from e
    raise FatalError(f"Giving up on {host}")


ENV_NAMES = ("GOOGLE_MAPS_API_KEY", "MY_MAPS_SPOTS_CONTACT")


def load_env_files(env_file: Path | None) -> tuple[str, list[str]]:
    """Fill unset variables from .env files; real environment variables win.

    Looks at --env-file, then the skill folder's .env, then a .env next to this script.
    Only the variables in ENV_NAMES are read. Returns (key_source, checked): where
    GOOGLE_MAPS_API_KEY came from ("environment variable", a .env path, or "") and a
    description of each place that was checked. Never includes the key itself.
    """
    key_source = "environment variable" if os.environ.get("GOOGLE_MAPS_API_KEY", "").strip() else ""
    checked = [f"environment variable GOOGLE_MAPS_API_KEY: {'set' if key_source else 'not set'}"]
    seen: set[Path] = set()
    for path in [env_file, SKILL_DIR / ".env", Path(__file__).resolve().parent / ".env"]:
        if path is None:
            continue
        path = path.expanduser().resolve()
        if path in seen:
            continue
        seen.add(path)
        if not path.is_file():
            checked.append(f"{path}: not found")
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except OSError as error:
            checked.append(f"{path}: found but cannot be read ({error})")
            continue
        found = set()
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[len("export ") :]
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            name, value = name.strip(), value.strip().strip("'\"")
            if name in ENV_NAMES and value:
                found.add(name)
                if not os.environ.get(name):
                    os.environ[name] = value
                    if name == "GOOGLE_MAPS_API_KEY":
                        key_source = str(path)
        checked.append(
            f"{path}: found, GOOGLE_MAPS_API_KEY {'is set' if 'GOOGLE_MAPS_API_KEY' in found else 'is missing or empty'}"
        )
    return key_source, checked


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^\w]+", " ", text).strip()


def name_variants(spot: dict) -> list[str]:
    variants = []
    for raw in [spot.get("local_name", ""), spot.get("name", "")]:
        if not raw:
            continue
        variants.append(raw)
        outside = re.sub(r"\(.*?\)", "", raw).strip()
        if outside:
            variants.append(outside)
        for inside in re.findall(r"\((.*?)\)", raw):
            variants.extend(p.strip() for p in inside.split("/") if p.strip())
    seen, out = set(), []
    for v in variants:
        n = normalize(v)
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def name_score(spot: dict, candidate: str) -> float:
    cand = normalize(candidate or "")
    if not cand:
        return 0.0
    best = 0.0
    for v in name_variants(spot):
        if v == cand or (len(v) >= 4 and v in cand) or (len(cand) >= 4 and cand in v):
            return 1.0
        best = max(best, difflib.SequenceMatcher(None, v, cand).ratio())
    return round(best, 2)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def expand_bbox(bbox: list[float], margin_km: float) -> list[float]:
    south, west, north, east = bbox
    dlat = margin_km / 111.0
    mid = math.radians((south + north) / 2)
    dlon = margin_km / (111.0 * max(math.cos(mid), 0.01))
    return [south - dlat, west - dlon, north + dlat, east + dlon]


def in_bbox(lat: float, lon: float, bbox: list[float]) -> bool:
    south, west, north, east = bbox
    return south <= lat <= north and west <= lon <= east


def resolve_place_bbox(place: dict) -> list[float]:
    if place.get("bbox"):
        bbox = [float(x) for x in place["bbox"]]
        if len(bbox) != 4:
            raise FatalError("place.bbox must be [south, west, north, east]")
        return bbox
    query = place.get("query") or place.get("name")
    if not query:
        raise FatalError("spots.json needs place.query (for example 'Helsinki, Finland')")
    params = urllib.parse.urlencode({"q": query, "format": "jsonv2", "limit": 1})
    results = http_json(f"{NOMINATIM_URL}?{params}")
    if not results:
        raise FatalError(f"Could not find the place '{query}'. Set place.bbox manually.")
    s, n, w, e = (float(x) for x in results[0]["boundingbox"])
    return [s, w, n, e]


_wikidata_cache: dict[str, dict] = {}


def wikidata_entity(qid: str) -> dict:
    qid = qid.strip().upper()
    if not re.fullmatch(r"Q\d+", qid):
        return {}
    if qid not in _wikidata_cache:
        _wikidata_cache[qid] = _fetch_wikidata_entity(qid)
    return _wikidata_cache[qid]


def _fetch_wikidata_entity(qid: str) -> dict:
    data = http_json(WIKIDATA_ENTITY_URL.format(qid=qid))
    entity = data.get("entities", {}).get(qid, {})
    claims = entity.get("claims", {})
    out: dict = {"qid": qid}
    for claim in claims.get("P18", []):
        if claim.get("rank") == "deprecated":
            continue
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, str) and value:
            out["image"] = value
            break
    for claim in claims.get("P625", []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if value:
            out["lat"], out["lon"] = value["latitude"], value["longitude"]
            break
    for claim in claims.get("P856", []):
        if claim.get("rank") == "deprecated":
            continue
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if value:
            out["website"] = value
            break
    return out


def nominatim_search(query: str, bbox: list[float], language: str) -> list[dict]:
    south, west, north, east = bbox
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": 5,
        "extratags": 1,
        "addressdetails": 0,
        "viewbox": f"{west},{north},{east},{south}",
        "bounded": 1,
    }
    if language:
        params["accept-language"] = language
    return http_json(f"{NOMINATIM_URL}?{urllib.parse.urlencode(params)}") or []


def places_request(body: dict, key: str, field_mask: str) -> object:
    headers = {"X-Goog-Api-Key": key, "X-Goog-FieldMask": field_mask}
    try:
        return http_json(PLACES_SEARCH_URL, data=body, headers=headers)
    except FatalError as e:
        msg = str(e)
        if "HTTP 400" in msg or "HTTP 401" in msg or "HTTP 403" in msg:
            raise FatalError(
                "Google Places API rejected the request. Check that the key is valid "
                "and that 'Places API (New)' is enabled for its project.\n" + msg
            ) from e
        raise


def probe_places_key(key: str) -> None:
    """One small Text Search so a rejected key fails before any spot is looked up."""
    places_request({"textQuery": "cafe", "pageSize": 1}, key, "places.id")


def places_search(query: str, bbox: list[float], language: str, key: str) -> list[dict]:
    south, west, north, east = bbox
    body = {
        "textQuery": query,
        "pageSize": 5,
        "locationBias": {
            "rectangle": {
                "low": {"latitude": south, "longitude": west},
                "high": {"latitude": north, "longitude": east},
            }
        },
    }
    if language:
        body["languageCode"] = language
    data = places_request(body, key, PLACES_FIELDS)
    return data.get("places", []) if isinstance(data, dict) else []


def google_maps_url(name: str, place_id: str) -> str:
    query = urllib.parse.quote(name)
    pid = urllib.parse.quote(place_id)
    return f"https://www.google.com/maps/search/?api=1&query={query}&query_place_id={pid}"


def pick_website(spot: dict, *candidates: tuple[str, str]) -> tuple[str, str]:
    if spot.get("website") and spot.get("website_confirmed_official"):
        return spot["website"], "agent (confirmed official)"
    for url, source in candidates:
        if url:
            return url, source
    return "", ""


def add_wikidata_image(spot: dict) -> None:
    """Append the spot's Wikidata image (P18, hosted on Wikimedia Commons) to spot["images"].

    It goes last, as a fallback behind the photos the agent found. render_spots.py checks
    that the file really loads before using it.
    """
    if not spot.get("wikidata"):
        return
    try:
        filename = wikidata_entity(spot["wikidata"]).get("image")
    except FatalError:
        return
    if not filename:
        return
    url = "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(filename.replace(" ", "_")) + "?width=480"
    images = spot.setdefault("images", [])
    if url not in images:
        images.append(url)


def verify_google(spot: dict, bbox: list[float], language: str, key: str) -> dict:
    v = {"mode": "google", "notes": []}
    query = spot.get("search_query") or spot.get("local_name") or spot.get("name")
    results = places_search(query, bbox, language, key)
    scored = []
    for r in results:
        loc = r.get("location") or {}
        if "latitude" not in loc:
            continue
        name = (r.get("displayName") or {}).get("text", "")
        scored.append((name_score(spot, name), in_bbox(loc["latitude"], loc["longitude"], bbox), r))
    scored.sort(key=lambda t: (t[1], t[0]), reverse=True)

    if not scored:
        v["status"] = "not_found"
        v["notes"].append(f"Google Places returned nothing for '{query}'")
        return v

    score, inside, best = scored[0]
    name = (best.get("displayName") or {}).get("text", "")
    loc = best["location"]
    v.update(
        matched_name=name,
        matched_address=best.get("formattedAddress", ""),
        name_score=score,
        lat=loc["latitude"],
        lon=loc["longitude"],
    )

    if not inside:
        v["status"] = "unconfirmed"
        v["notes"].append("Google's best match is outside the place area")
        return v
    if score < NAME_MATCH_THRESHOLD:
        v["status"] = "unconfirmed"
        v["notes"].append(f"Google's best match '{name}' does not look like this spot")
        return v

    wd = wikidata_entity(spot["wikidata"]) if spot.get("wikidata") else {}
    if "lat" in wd:
        dist = round(haversine_m(loc["latitude"], loc["longitude"], wd["lat"], wd["lon"]))
        v["cross_check"] = {"source": f"wikidata {wd['qid']}", "distance_m": dist}
        if dist > GOOGLE_WIKIDATA_MAX_M:
            v["status"] = "unconfirmed"
            v["notes"].append(
                f"Google and Wikidata disagree by {dist} m; check the Wikidata ID or search query"
            )
            return v

    v["status"] = "verified"
    v["google_maps_url"] = google_maps_url(name, best["id"])
    v["website"], v["website_source"] = pick_website(
        spot,
        (best.get("websiteUri", ""), "google places"),
        (wd.get("website", ""), f"wikidata {wd.get('qid', '')}"),
    )
    return v


def verify_osm(spot: dict, bbox: list[float], language: str, tolerance_m: float) -> dict:
    v = {"mode": "osm", "notes": []}
    queries = []
    for q in [spot.get("search_query"), spot.get("local_name"), spot.get("name")]:
        if q and q not in queries:
            queries.append(q)

    candidates = []
    for q in queries:
        results = nominatim_search(q, bbox, language)
        candidates = [(name_score(spot, r.get("name") or r.get("display_name", "")), r) for r in results]
        candidates = [c for c in candidates if c[0] >= NAME_MATCH_THRESHOLD]
        if candidates:
            break

    if not candidates:
        v["status"] = "not_found"
        v["notes"].append("OpenStreetMap has no matching place inside the area")
        return v

    wanted_qid = (spot.get("wikidata") or "").upper()

    def rank(c):
        score, r = c
        same_qid = bool(wanted_qid) and (r.get("extratags") or {}).get("wikidata", "").upper() == wanted_qid
        return (same_qid, score, float(r.get("importance") or 0))

    candidates.sort(key=rank, reverse=True)
    score, best = candidates[0]
    lat, lon = float(best["lat"]), float(best["lon"])
    tags = best.get("extratags") or {}
    v.update(
        matched_name=best.get("name") or "",
        matched_address=best.get("display_name", ""),
        name_score=score,
        lat=lat,
        lon=lon,
    )

    s, n, w, e = (float(x) for x in best.get("boundingbox", [lat, lat, lon, lon]))
    outline = expand_bbox([s, w, n, e], tolerance_m / 1000)

    qid = wanted_qid or tags.get("wikidata", "").upper()
    if wanted_qid and tags.get("wikidata") and tags["wikidata"].upper() != wanted_qid:
        v["notes"].append(f"OSM links to {tags['wikidata']}, spots.json says {wanted_qid}")
    wd = wikidata_entity(qid) if qid else {}

    confirmed = False
    if "lat" in wd:
        dist = round(haversine_m(lat, lon, wd["lat"], wd["lon"]))
        v["cross_check"] = {"source": f"wikidata {wd['qid']}", "distance_m": dist}
        if dist <= tolerance_m or in_bbox(wd["lat"], wd["lon"], outline):
            confirmed = True
        else:
            v["notes"].append(f"OpenStreetMap and Wikidata disagree by {dist} m")

    if not confirmed and spot.get("address"):
        results = nominatim_search(spot["address"], bbox, language)
        if results:
            alat, alon = float(results[0]["lat"]), float(results[0]["lon"])
            dist = round(haversine_m(lat, lon, alat, alon))
            v["cross_check"] = {"source": "address", "distance_m": dist}
            if dist <= tolerance_m or in_bbox(alat, alon, outline):
                confirmed = True
            else:
                v["notes"].append(f"Address geocodes {dist} m away from the OpenStreetMap place")
        else:
            v["notes"].append("Address could not be geocoded")

    if not confirmed:
        v["status"] = "unconfirmed"
        if "cross_check" not in v:
            v["notes"].append("No second source to confirm the location; add a wikidata ID or address")
        return v

    v["status"] = "verified"
    v["google_maps_url"] = ""
    v["website"], v["website_source"] = pick_website(
        spot,
        (wd.get("website", ""), f"wikidata {wd.get('qid', '')}"),
        (tags.get("website") or tags.get("contact:website") or "", "openstreetmap"),
    )
    return v


def report_key_check(key_source: str, checked: list[str]) -> int:
    """Print where the key lookup looked. Never includes the key. Returns 0 if found, else 1."""
    if key_source:
        print(f"Google Maps API key: found in {key_source}.", file=sys.stderr)
        code = 0
    else:
        print("Google Maps API key: not found.", file=sys.stderr)
        code = 1
    print("Checked:", file=sys.stderr)
    for line in checked:
        print(f"  - {line}", file=sys.stderr)
    return code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spots", nargs="?", type=Path, help="path to spots.json")
    parser.add_argument("-o", "--output", type=Path, help="output path (default: verified.json next to input)")
    parser.add_argument("--mode", choices=["auto", "google", "osm"], default="auto")
    parser.add_argument(
        "--check-key",
        action="store_true",
        help="print whether GOOGLE_MAPS_API_KEY is set, then exit (no Google request)",
    )
    parser.add_argument("--env-file", type=Path, help="extra .env file to read GOOGLE_MAPS_API_KEY from")
    parser.add_argument("--tolerance-m", type=float, default=150, help="max distance between two sources (default 150)")
    parser.add_argument(
        "--margin-km",
        type=float,
        default=15,
        help="how far outside the place's boundary a spot may be, for day trips (default 15)",
    )
    args = parser.parse_args()

    key_source, checked = load_env_files(args.env_file)
    if args.check_key:
        return report_key_check(key_source, checked)
    if args.spots is None:
        parser.error("spots.json is required unless --check-key is set")

    data = json.loads(args.spots.read_text(encoding="utf-8"))
    place = data.get("place", {})
    spots = data.get("spots", [])
    language = place.get("user_language", "")

    key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    mode = args.mode
    if mode == "auto":
        mode = "google" if key else "osm"
    if mode == "google" and not key:
        print("error: --mode google needs GOOGLE_MAPS_API_KEY. Checked:", file=sys.stderr)
        for line in checked:
            print(f"  - {line}", file=sys.stderr)
        return 2
    if mode == "google":
        print(f"Google mode: using the Google Maps API key from {key_source}.", file=sys.stderr)
    elif args.mode == "osm":
        print(
            "Open data mode (forced with --mode osm): coordinates are checked with "
            "OpenStreetMap and Wikidata, and Google Maps links are left empty.",
            file=sys.stderr,
        )
    else:
        print(
            "Open data mode (no Google Maps API key found): coordinates are checked with "
            "OpenStreetMap and Wikidata, and Google Maps links are left empty. Checked:",
            file=sys.stderr,
        )
        for line in checked:
            print(f"  - {line}", file=sys.stderr)
        print(
            "  If you expected Google mode, pass --env-file <path to the .env> or set "
            "GOOGLE_MAPS_API_KEY, then rerun.",
            file=sys.stderr,
        )

    try:
        if mode == "google":
            probe_places_key(key)
            print("Places API accepted the key.", file=sys.stderr)
        place_bbox = resolve_place_bbox(place)
        search_bbox = expand_bbox(place_bbox, args.margin_km)
        for i, spot in enumerate(spots, 1):
            label = spot.get("name") or spot.get("id") or f"spot {i}"
            if mode == "google":
                v = verify_google(spot, search_bbox, language, key)
            else:
                v = verify_osm(spot, search_bbox, language, args.tolerance_m)
            for field in ["lat", "lon"]:
                if field in v:
                    spot[field] = round(float(v.pop(field)), 6)
            spot["google_maps_url"] = v.pop("google_maps_url", "")
            spot["website"] = v.pop("website", "") if v["status"] == "verified" else spot.get("website", "")
            spot["website_source"] = v.pop("website_source", "")
            spot["verification"] = v
            if v["status"] == "verified":
                add_wikidata_image(spot)
            notes = f" ({'; '.join(v['notes'])})" if v["notes"] else ""
            print(f"[{i}/{len(spots)}] {v['status']:<11} {label}{notes}", file=sys.stderr)
    except FatalError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    place["bbox"] = [round(x, 6) for x in place_bbox]
    data["verification"] = {
        "mode": mode,
        "google_key_source": key_source if mode == "google" else "",
        "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tolerance_m": args.tolerance_m,
        "margin_km": args.margin_km,
    }
    out = args.output or args.spots.with_name("verified.json")
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    counts: dict[str, int] = {}
    for spot in spots:
        status = spot["verification"]["status"]
        counts[status] = counts.get(status, 0) + 1
    summary = ", ".join(f"{n} {s}" for s, n in sorted(counts.items()))
    print(f"Wrote {out} ({summary}), mode: {mode}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
