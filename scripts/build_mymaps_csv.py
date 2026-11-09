#!/usr/bin/env python3
"""Build Google My Maps import files from verified.json (output of verify_places.py).

Writes into --out-dir:
  <slug>-all.csv           every verified spot, one layer, text fields only
  <slug>-<category>.csv    one file per category, one layer each
  <slug>-all.kml           the same spots, with a photo in each pin popup
  <slug>-<category>.kml    one file per category, photos included
  sources.md, sources.csv  every source read, used or rejected
  excluded.csv             spots left out, with the reason

A CSV import cannot show a photo in the popup. The KML puts the image URL in
ExtendedData under the name gx_media_links, which is where My Maps stores a
pin's popup photo. Import the KML to get the photo.

Uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import io
import json
import math
import re
import sys
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from images import resolve_direct_image, warn  # noqa: E402

COLUMNS = [
    "Name",
    "Local name",
    "Category",
    "Area",
    "Description",
    "Latitude",
    "Longitude",
    "Google Maps URL",
    "Website",
    "Sources",
]
MAX_ROWS = 2000
MAX_BYTES = 5 * 1024 * 1024 - 64 * 1024
MAX_LAYERS = 10
DUPLICATE_DISTANCE_M = 30
# Popup fields other than the writeup. The writeup goes in <description>.
# Latitude and Longitude are the placemark point, not extra fields.
# gx_media_links is added separately and is what makes the photo show.
KML_FIELDS = ["Local name", "Category", "Area", "Google Maps URL", "Website", "Sources"]
KML_NS = "http://www.opengis.net/kml/2.2"
ET.register_namespace("", KML_NS)


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^\w]+", "-", text, flags=re.UNICODE).strip("-") or "spots"


def normalize_name(text: str) -> str:
    return re.sub(r"\W+", " ", unicodedata.normalize("NFKC", text.casefold())).strip()


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def valid_coords(spot: dict) -> bool:
    try:
        lat, lon = float(spot["lat"]), float(spot["lon"])
    except (KeyError, TypeError, ValueError):
        return False
    return -90 <= lat <= 90 and -180 <= lon <= 180 and not (lat == 0 and lon == 0)


def local_terms_text(terms: list) -> str:
    parts = []
    for t in terms or []:
        if isinstance(t, str):
            parts.append(t)
            continue
        term, meaning = t.get("term", "").strip(), t.get("meaning", "").strip()
        if not term:
            continue
        text = f"{term} = {meaning}" if meaning else term
        if t.get("pronunciation"):
            text += f" ({t['pronunciation']})"
        parts.append(text)
    return "; ".join(parts)


def area_name_map(place: dict) -> dict[str, str]:
    """Map area id (and name) to the display name, from place.areas."""
    names: dict[str, str] = {}
    for area in place.get("areas") or []:
        display = area.get("name") or area.get("local_name") or area.get("id") or ""
        for key in (area.get("id"), area.get("name"), area.get("local_name")):
            if key:
                names[str(key).casefold()] = display
    return names


def spot_row(spot: dict, area_names: dict[str, str] | None = None) -> dict:
    area = str(spot.get("area") or "").strip()
    area = (area_names or {}).get(area.casefold(), area)
    description = (spot.get("description") or "").strip()
    terms = local_terms_text(spot.get("local_terms"))
    if terms:
        description = f"{description}\n\nLocal terms: {terms}" if description else f"Local terms: {terms}"
    return {
        "Name": spot.get("name") or spot.get("local_name") or "",
        "Local name": spot.get("local_name", ""),
        "Category": spot.get("category") or "Other",
        "Area": area,
        "Description": description,
        "Latitude": f"{float(spot['lat']):.6f}",
        "Longitude": f"{float(spot['lon']):.6f}",
        "Google Maps URL": spot.get("google_maps_url", ""),
        "Website": spot.get("website", ""),
        "Sources": " ".join(spot.get("sources") or []),
    }


def csv_bytes(rows: list[dict], columns: list[str]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def chunk_rows(rows: list[dict]) -> list[list[dict]]:
    header = len(csv_bytes([], COLUMNS))
    chunks, current, size = [], [], header
    for row in rows:
        row_size = len(csv_bytes([row], COLUMNS)) - header
        if current and (len(current) >= MAX_ROWS or size + row_size > MAX_BYTES):
            chunks.append(current)
            current, size = [], header
        current.append(row)
        size += row_size
    if current:
        chunks.append(current)
    return chunks


def spot_key(spot: dict) -> str:
    return str(spot.get("id") or spot.get("name") or spot.get("local_name") or "")


def choose_map_images(spots: list[dict], check: bool, timeout: float) -> dict[str, str | None]:
    """First photo My Maps can fetch for each spot, at the URL after redirects."""

    def one(spot: dict) -> tuple[str | None, list[tuple[str, str, str]]]:
        return resolve_direct_image(list(spot.get("images") or []), timeout, check)

    chosen: dict[str, str | None] = {}
    results: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        resolved = list(pool.map(one, spots))
    for spot, (url, failures) in zip(spots, resolved):
        key = spot_key(spot)
        chosen[key] = url
        for failed_url, result, reason in failures:
            results.append(result)
            warn(f"{key}: image rejected ({reason}): {failed_url}")
        if url is None:
            warn(f"{key}: no working image; add candidates from other sites and rerun")
    if results and all(result == "unreachable" for result in results) and not any(chosen.values()):
        warn(
            "no image could be reached; this environment may have no network access. "
            "Check the image URLs with your own browsing tool, keep only working ones, "
            "and rerun with --no-check-images."
        )
    return chosen


def _kml_tag(name: str) -> str:
    return f"{{{KML_NS}}}{name}"


def html_escape(text: str) -> str:
    """Escape <, > and quotes. Leave & as &.

    The balloon is stored in CDATA, so &amp; would be the letters amp, not an
    ampersand. My Maps does not turn those letters back into &, and the link
    will not open.
    """
    return text.replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def cdata_wrap(text: str) -> str:
    """Literal text inside XML."""
    parts = text.split("]]>")
    return "<![CDATA[" + "]]]]><![CDATA[>".join(parts) + "]]>"


def kml_maps_url(url: str) -> str:
    """Google Maps link for a My Maps pin. It must not contain &.

    On import, My Maps rewrites & to the letters amp inside the pin field, so
    ?api=1&query=...&query_place_id=... does not open. A single place-id
    parameter has no &.
    """
    if not url:
        return url
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    place_id = (query.get("query_place_id") or [""])[0]
    if place_id:
        return "https://www.google.com/maps/place/?q=place_id:" + urllib.parse.quote(place_id, safe="-_")
    if "&" not in url:
        return url
    return url.split("&", 1)[0]


def kml_image_url(url: str) -> str:
    """Photo address for a My Maps pin. Drop the query string so it has no &.

    Wikimedia thumb URLs still identify the file without ?utm_source=...&...
    """
    if not url or "&" not in url:
        return url
    parsed = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse(parsed._replace(query="", fragment=""))


def popup_html(description: str, image: str | None) -> str:
    """Balloon HTML in the shape a My Maps photo export uses.

    A pin with a photo and a note exports as an <img> (height 200, width auto),
    a blank line, then the note with newlines turned into <br>.
    """
    parts = []
    if image:
        parts.append(f'<img src="{html_escape(image)}" height="200" width="auto" />')
    text = description.strip()
    if text:
        parts.append("<br>".join(html_escape(line) for line in text.split("\n")))
    return "<br><br>".join(parts)


def kml_bytes(title: str, entries: list[tuple[dict, str | None]]) -> bytes:
    """KML document. Point coordinates are longitude,latitude, as KML requires.

    The popup photo is stored the way My Maps stores one: the image URL in
    ExtendedData named gx_media_links, and the same URL as an <img> in the
    description. A CSV column cannot do this. Import this file, not the CSV,
    to get the photo.
    """
    document = ET.Element(_kml_tag("kml"))
    doc = ET.SubElement(document, _kml_tag("Document"))
    ET.SubElement(doc, _kml_tag("name")).text = title
    balloons: list[tuple[str, str]] = []
    # ElementTree writes & as &amp;. My Maps then shows that in the link and it
    # will not open, so URL fields are filled in as CDATA after serialization.
    literals: list[tuple[str, str]] = []

    def literal(text: str) -> str:
        token = f"__KMLVAL_{len(literals)}__"
        literals.append((token, text))
        return token

    for i, (row, image) in enumerate(entries):
        placemark = ET.SubElement(doc, _kml_tag("Placemark"))
        ET.SubElement(placemark, _kml_tag("name")).text = row.get("Name") or ""
        photo = kml_image_url(image) if image else None
        html = popup_html(row.get("Description") or "", photo)
        if html:
            token = f"__BALLOON_{i}__"
            ET.SubElement(placemark, _kml_tag("description")).text = token
            balloons.append((token, html))
        extra = ET.SubElement(placemark, _kml_tag("ExtendedData"))
        if photo:
            media = ET.SubElement(extra, _kml_tag("Data"), {"name": "gx_media_links"})
            ET.SubElement(media, _kml_tag("value")).text = literal(photo)
        for field in KML_FIELDS:
            value = (row.get(field) or "").strip()
            if field == "Google Maps URL":
                value = kml_maps_url(value)
            if not value:
                continue
            data = ET.SubElement(extra, _kml_tag("Data"), {"name": field})
            ET.SubElement(data, _kml_tag("value")).text = literal(value)
        point = ET.SubElement(placemark, _kml_tag("Point"))
        # KML order is longitude, latitude. The CSV columns are the other way round.
        ET.SubElement(point, _kml_tag("coordinates")).text = f"{row['Longitude']},{row['Latitude']},0"
    ET.indent(document, space="  ")
    body = ET.tostring(document, encoding="unicode", xml_declaration=False)
    for token, html in balloons:
        body, count = re.subn(
            rf"<description>\s*{re.escape(token)}\s*</description>",
            f"<description>{cdata_wrap(html)}</description>",
            body,
            count=1,
        )
        if count != 1:
            raise RuntimeError(f"could not place the popup HTML for {token}")
    for token, text in literals:
        body, count = re.subn(
            rf"<value>\s*{re.escape(token)}\s*</value>",
            f"<value>{cdata_wrap(text)}</value>",
            body,
            count=1,
        )
        if count != 1:
            raise RuntimeError(f"could not place the field value for {token}")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n' + body + "\n").encode("utf-8")


def chunk_entries(title: str, entries: list[tuple[dict, str | None]]) -> list[list[tuple[dict, str | None]]]:
    chunks: list[list[tuple[dict, str | None]]] = []
    current: list[tuple[dict, str | None]] = []
    for entry in entries:
        trial = current + [entry]
        oversize = current and (len(trial) > MAX_ROWS or len(kml_bytes(title, trial)) > MAX_BYTES)
        if oversize:
            chunks.append(current)
            current = [entry]
        else:
            current = trial
    if current:
        chunks.append(current)
    return chunks


def write_kml_layer(out_dir: Path, stem: str, title: str, entries: list[tuple[dict, str | None]]) -> list[Path]:
    chunks = chunk_entries(title, entries)
    paths = []
    for i, chunk in enumerate(chunks, 1):
        name = f"{stem}.kml" if len(chunks) == 1 else f"{stem}-part{i}.kml"
        path = out_dir / name
        path.write_bytes(kml_bytes(title if len(chunks) == 1 else f"{title} ({i})", chunk))
        paths.append(path)
    return paths


def write_layer(out_dir: Path, stem: str, rows: list[dict]) -> list[Path]:
    chunks = chunk_rows(rows)
    paths = []
    for i, chunk in enumerate(chunks, 1):
        name = f"{stem}.csv" if len(chunks) == 1 else f"{stem}-part{i}.csv"
        path = out_dir / name
        path.write_bytes(csv_bytes(chunk, COLUMNS))
        paths.append(path)
    return paths


def dedupe(spots: list[dict]) -> tuple[list[dict], list[tuple[dict, str]]]:
    kept: list[dict] = []
    dropped: list[tuple[dict, str]] = []
    for spot in spots:
        match = None
        for k in kept:
            same_name = normalize_name(k.get("local_name") or k["name"]) == normalize_name(
                spot.get("local_name") or spot["name"]
            )
            close = haversine_m(float(k["lat"]), float(k["lon"]), float(spot["lat"]), float(spot["lon"])) <= DUPLICATE_DISTANCE_M
            if same_name or close:
                match = k
                break
        if match is None:
            kept.append(spot)
            continue
        for url in spot.get("sources") or []:
            if url not in match.setdefault("sources", []):
                match["sources"].append(url)
        dropped.append((spot, f"duplicate of {match['name']}"))
    return kept, dropped


def collect_sources(data: dict, spots_by_id: dict[str, dict]) -> list[dict]:
    sources = [dict(s) for s in data.get("sources") or []]
    by_url = {s.get("url"): s for s in sources if s.get("url")}
    for spot in data.get("spots") or []:
        for url in spot.get("sources") or []:
            if url not in by_url:
                entry = {"url": url, "status": "used", "reason": "referenced by a spot but missing from the sources list"}
                sources.append(entry)
                by_url[url] = entry
            entry = by_url[url]
            ids = entry.setdefault("spots", [])
            sid = spot.get("id") or spot.get("name")
            if sid not in ids:
                ids.append(sid)
    for s in sources:
        s["spot_names"] = [spots_by_id[i]["name"] if i in spots_by_id else str(i) for i in s.get("spots") or []]
    return sources


def select_spots(all_spots: list[dict]) -> tuple[list[dict], list[tuple[dict, str]]]:
    """Split spots into (included, excluded with reason). Shared with render_spots.py."""
    excluded: list[tuple[dict, str]] = []
    candidates = []
    for spot in all_spots:
        v = spot.get("verification") or {}
        if v.get("status") != "verified":
            reason = "; ".join(v.get("notes") or []) or v.get("status", "not verified")
            excluded.append((spot, f"{v.get('status', 'unverified')}: {reason}"))
        elif not valid_coords(spot):
            excluded.append((spot, "invalid coordinates"))
        elif not spot.get("sources"):
            excluded.append((spot, "no first-hand source listed"))
        else:
            candidates.append(spot)

    included, duplicates = dedupe(candidates)
    return included, excluded + duplicates


def write_sources(out_dir: Path, place_name: str, sources: list[dict], spots: list[dict]) -> None:
    columns = ["Status", "Title", "Author", "Date", "Language", "Kind", "URL", "Reason", "Spots"]
    rows = [
        {
            "Status": s.get("status", ""),
            "Title": s.get("title", ""),
            "Author": s.get("author", ""),
            "Date": s.get("date", ""),
            "Language": s.get("language", ""),
            "Kind": s.get("kind", ""),
            "URL": s.get("url", ""),
            "Reason": s.get("reason", ""),
            "Spots": "; ".join(s["spot_names"]),
        }
        for s in sources
    ]
    (out_dir / "sources.csv").write_bytes(csv_bytes(rows, columns))

    def line(s: dict) -> str:
        title = s.get("title") or s.get("url", "")
        link = f"[{title}]({s['url']})" if s.get("url") else title
        meta = ", ".join(x for x in [s.get("author"), s.get("date"), s.get("language"), s.get("kind")] if x)
        return f"- {link}" + (f" ({meta})" if meta else "")

    used = [s for s in sources if s.get("status", "used") == "used"]
    rejected = [s for s in sources if s.get("status") == "rejected"]
    md = [f"# Sources for {place_name}", ""]
    md += ["## Used", ""]
    for s in used:
        md.append(line(s))
        if s.get("reason"):
            md.append(f"  - Why: {s['reason']}")
        if s["spot_names"]:
            md.append(f"  - Spots: {', '.join(s['spot_names'])}")
    if not used:
        md.append("- None")
    md += ["", "## Rejected", ""]
    for s in rejected:
        md.append(line(s))
        md.append(f"  - Why: {s.get('reason') or 'not given'}")
    if not rejected:
        md.append("- None")
    md += ["", "## Spots and their sources", ""]
    for spot in spots:
        md.append(f"- **{spot['name']}**")
        for url in spot.get("sources") or []:
            md.append(f"  - {url}")
    (out_dir / "sources.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("verified", type=Path, help="path to verified.json")
    parser.add_argument("--out-dir", type=Path, help="output folder (default: next to verified.json)")
    parser.add_argument(
        "--no-check-images",
        action="store_true",
        help="use the first https image URL without checking it (My Maps still needs a direct image file)",
    )
    parser.add_argument("--timeout", type=float, default=8.0, help="seconds per image request (default 8)")
    args = parser.parse_args()

    data = json.loads(args.verified.read_text(encoding="utf-8"))
    place = data.get("place", {})
    slug = slugify(place.get("slug") or place.get("query") or "spots")
    out_dir = args.out_dir or args.verified.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    all_spots = data.get("spots") or []
    if all_spots and not any("verification" in s for s in all_spots):
        print("error: no verification data; run verify_places.py first", file=sys.stderr)
        return 1

    included, excluded = select_spots(all_spots)

    for pattern in (f"{slug}-*.csv", f"{slug}-*.kml"):
        for old in out_dir.glob(pattern):
            old.unlink()

    area_names = area_name_map(place)
    images = choose_map_images(included, not args.no_check_images, args.timeout)
    entries = [(spot_row(s, area_names), images.get(spot_key(s))) for s in included]
    rows = [row for row, _image in entries]
    place_title = place.get("query") or slug
    written = write_layer(out_dir, f"{slug}-all", rows)
    written += write_kml_layer(out_dir, f"{slug}-all", place_title, entries)

    categories: dict[str, list[tuple[dict, str | None]]] = {}
    for entry in entries:
        categories.setdefault(entry[0]["Category"], []).append(entry)
    for category, cat_entries in categories.items():
        stem = f"{slug}-{slugify(category)}"
        written += write_layer(out_dir, stem, [row for row, _image in cat_entries])
        written += write_kml_layer(out_dir, stem, category, cat_entries)

    excluded_columns = ["Name", "Local name", "Category", "Reason", "Matched name", "Sources"]
    excluded_rows = [
        {
            "Name": s.get("name", ""),
            "Local name": s.get("local_name", ""),
            "Category": s.get("category", ""),
            "Reason": reason,
            "Matched name": (s.get("verification") or {}).get("matched_name", ""),
            "Sources": " ".join(s.get("sources") or []),
        }
        for s, reason in excluded
    ]
    (out_dir / "excluded.csv").write_bytes(csv_bytes(excluded_rows, excluded_columns))

    spots_by_id = {(s.get("id") or s.get("name")): s for s in all_spots}
    sources = collect_sources(data, spots_by_id)
    write_sources(out_dir, place.get("query") or slug, sources, included)

    with_photo = sum(1 for _row, image in entries if image)
    print(
        f"{len(included)} spots included, {len(excluded)} excluded, {with_photo} with a popup photo",
        file=sys.stderr,
    )
    if len(categories) > MAX_LAYERS:
        print(
            f"warning: {len(categories)} categories but My Maps allows {MAX_LAYERS} layers per map; "
            "merge some categories or import the combined file",
            file=sys.stderr,
        )
    for path in written + [out_dir / "sources.md", out_dir / "sources.csv", out_dir / "excluded.csv"]:
        print(f"  {path}", file=sys.stderr)
    for spot, reason in excluded:
        print(f"  excluded: {spot.get('name')} ({reason})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
