#!/usr/bin/env python3
"""Render verified spots as Markdown for the chat, grouped by area, with photos.

Reads verified.json (output of verify_places.py). For every verified spot it checks the
`images` candidates in order, keeps the first one that loads as an image, and rewrites it
to a GitHub image proxy URL so chat apps that only trust a few image hosts show it. It
prints one section per area (in the order of place.areas), a card per spot, then the
numbered source list. Warnings go to stderr. Uses only the Python standard library.

The spots shown are the same ones build_mymaps_csv.py writes to the CSV files.

Usage:
    python3 scripts/render_spots.py output/<slug>/verified.json
    python3 scripts/render_spots.py output/<slug>/verified.json -o spots.md --no-check-images
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_mymaps_csv import collect_sources, select_spots  # noqa: E402

USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
)
IMAGE_REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "image/webp,image/png,image/jpeg,image/*;q=0.8",
    "Referer": "https://example.com/",
    "Sec-Fetch-Dest": "image",
    "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Site": "cross-site",
}
EMBEDDABLE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_BYTES = 1_500_000
GITHUB_MARKDOWN_API = "https://api.github.com/markdown"

DEFAULT_LABELS = {
    "other_areas": "Other areas",
    "address": "Address",
    "local_terms": "Local terms",
    "item_sources": "Sources",
    "google_maps": "Google Maps",
    "website": "Website",
    "sources_used": "Sources used",
    "rejected_sources": "Rejected sources",
}


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def md_url(url: str) -> str:
    return url.replace(" ", "%20").replace("(", "%28").replace(")", "%29")


def sniff_image(head: bytes) -> bool:
    return (
        head.startswith(b"\xff\xd8\xff")
        or head.startswith(b"\x89PNG\r\n\x1a\n")
        or head.startswith((b"GIF87a", b"GIF89a"))
        or (head[:4] == b"RIFF" and head[8:12] == b"WEBP")
    )


def check_image(url: str, timeout: float) -> tuple[str, str, str]:
    """Return (result, final_url, reason). result is "ok", "bad" or "unreachable".

    The request imitates a chat app embedding the image from another site, so images
    that only load on their own site (hotlink protection, Cross-Origin-Resource-Policy)
    are rejected. The final URL after redirects is returned, because some chat apps do
    not follow redirects for embedded images.
    """
    if not url.startswith("https://"):
        return "bad", url, "not https (many chat apps block http images)"
    request = urllib.request.Request(md_url(url), headers=IMAGE_REQUEST_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
            corp = response.headers.get("Cross-Origin-Resource-Policy", "").strip().lower()
            length = response.headers.get("Content-Length", "")
            if not final_url.startswith("https://"):
                return "bad", final_url, "redirects to http"
            if content_type not in EMBEDDABLE_TYPES:
                return "bad", final_url, f"content type {content_type or 'missing'}"
            if corp in ("same-origin", "same-site"):
                return "bad", final_url, f"Cross-Origin-Resource-Policy: {corp}"
            if length.isdigit() and int(length) > MAX_IMAGE_BYTES:
                return "bad", final_url, f"too large ({int(length) // 1024} KB); use a smaller thumbnail"
            if not sniff_image(response.read(16)):
                return "bad", final_url, "body is not an image"
            return "ok", final_url, ""
    except urllib.error.HTTPError as error:
        return "bad", url, f"HTTP {error.code}"
    except ValueError as error:
        return "bad", url, str(error)
    except (urllib.error.URLError, TimeoutError, OSError):
        return "unreachable", url, "could not be reached"


def github_proxy_url(url: str, timeout: float) -> str | None:
    """Return GitHub's camo proxy URL for an image, or None if GitHub can't be reached.

    Some chat apps, often on mobile and web, only load images from an allowlist of
    hosts, and camo.githubusercontent.com is commonly on it. GitHub's Markdown API
    rewrites image URLs to signed camo URLs without uploading anything.
    """
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "my-maps-spots"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps({"text": f"![]({md_url(url)})", "mode": "gfm"}).encode()
    request = urllib.request.Request(GITHUB_MARKDOWN_API, data=body, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            html = response.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        warn(f"GitHub Markdown API failed ({error}); photos may not show in apps that only trust a few image hosts")
        return None
    match = re.search(r'<img src="(https://camo\.githubusercontent\.com/[^"]+)"', html)
    return match.group(1) if match else None


def spot_key(spot: dict) -> str:
    return str(spot.get("id") or spot.get("name") or spot.get("local_name") or "")


def choose_images(spots: list[dict], check: bool, proxy: bool, timeout: float) -> dict[str, str | None]:
    chosen: dict[str, str | None] = {}
    if not check:
        for spot in spots:
            images = spot.get("images") or []
            chosen[spot_key(spot)] = images[0] if images else None
        return chosen

    def first_working(spot: dict) -> tuple[str | None, list[str]]:
        results = []
        for url in spot.get("images") or []:
            result, final_url, reason = check_image(url, timeout)
            results.append(result)
            if result != "ok":
                warn(f"{spot_key(spot)}: image rejected ({reason}): {url}")
                continue
            if not proxy:
                return final_url, results
            camo_url = github_proxy_url(final_url, timeout)
            if camo_url is None:
                return final_url, results
            camo_result, _, camo_reason = check_image(camo_url, timeout)
            if camo_result == "ok":
                return camo_url, results
            warn(f"{spot_key(spot)}: GitHub's image proxy can't load it ({camo_reason}): {url}")
        return None, results

    all_results: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for spot, (url, results) in zip(spots, pool.map(first_working, spots)):
            chosen[spot_key(spot)] = url
            all_results += results
    if all_results and all(r == "unreachable" for r in all_results):
        warn(
            "no image could be reached; this environment may have no network access. "
            "Check the image URLs with your own browsing tool, keep only working ones, "
            "and rerun with --no-check-images."
        )
    return chosen


def terms_text(terms: list) -> str:
    parts = []
    for t in terms or []:
        if isinstance(t, str):
            parts.append(t)
            continue
        term, meaning = (t.get("term") or "").strip(), (t.get("meaning") or "").strip()
        if not term:
            continue
        text = f"*{term}* = {meaning}" if meaning else f"*{term}*"
        if t.get("pronunciation"):
            text += f" ({t['pronunciation']})"
        parts.append(text)
    return "; ".join(parts)


def area_title(area: dict) -> str:
    name = area.get("name") or area.get("local_name") or area.get("id") or ""
    local = area.get("local_name") or ""
    if local and local.casefold() != name.casefold():
        return f"{name} ({local})"
    return name


def group_by_area(spots: list[dict], areas: list[dict], labels: dict) -> list[tuple[str, str, list[dict]]]:
    """Return [(title, summary, spots)] in place.areas order, then the leftovers."""
    lookup: dict[str, int] = {}
    for i, area in enumerate(areas):
        for key in (area.get("id"), area.get("name"), area.get("local_name")):
            if key:
                lookup.setdefault(str(key).casefold(), i)

    buckets: list[list[dict]] = [[] for _ in areas]
    other: list[dict] = []
    for spot in spots:
        ref = str(spot.get("area") or "").strip().casefold()
        if ref in lookup:
            buckets[lookup[ref]].append(spot)
        else:
            warn(f"{spot_key(spot)}: " + (f"unknown area '{spot['area']}'" if ref else "no area set") + "; shown under other areas")
            other.append(spot)

    groups = []
    for area, bucket in zip(areas, buckets):
        if bucket:
            groups.append((area_title(area), area.get("summary") or "", bucket))
    if other:
        groups.append((labels["other_areas"], "", other))
    # Most-recommended spots first inside each area; sorted() is stable.
    return [(t, s, sorted(b, key=lambda sp: -len(sp.get("sources") or []))) for t, s, b in groups]


def render_card(spot: dict, image: str | None, source_numbers: dict[str, int], labels: dict) -> list[str]:
    name = spot.get("name") or spot.get("local_name") or ""
    out = [f"### {name}", ""]
    if image:
        out += [f"![{name}]({md_url(image)})", ""]

    meta = []
    if spot.get("category"):
        meta.append(f"*{spot['category']}*")
    if spot.get("google_maps_url"):
        meta.append(f"[{labels['google_maps']}]({md_url(spot['google_maps_url'])})")
    if spot.get("website"):
        meta.append(f"[{labels['website']}]({md_url(spot['website'])})")
    if meta:
        out += [" · ".join(meta), ""]

    description = (spot.get("description") or "").strip()
    if description:
        out += [description, ""]

    details = []
    if spot.get("address"):
        details.append(f"- **{labels['address']}:** {spot['address']}")
    terms = terms_text(spot.get("local_terms"))
    if terms:
        details.append(f"- **{labels['local_terms']}:** {terms}")
    links = []
    for url in sorted(spot.get("sources") or [], key=lambda u: source_numbers.get(u, len(source_numbers) + 1)):
        number = source_numbers.get(url)
        links.append(f"[{number}]({md_url(url)})" if number else md_url(url))
    if links:
        details.append(f"- **{labels['item_sources']}:** " + " ".join(links))
    if details:
        out += details + [""]
    return out


def source_line(source: dict) -> str:
    title = source.get("title") or source.get("url", "")
    link = f"[{title}]({md_url(source['url'])})" if source.get("url") else title
    meta = ", ".join(str(x) for x in [source.get("author"), source.get("date"), source.get("language"), source.get("kind")] if x)
    return link + (f" ({meta})" if meta else "")


def render(data: dict, check_images: bool, proxy_images: bool, timeout: float) -> str:
    place = data.get("place") or {}
    labels = {**DEFAULT_LABELS, **(data.get("labels") or {})}
    all_spots = data.get("spots") or []
    if all_spots and not any("verification" in s for s in all_spots):
        raise SystemExit("error: no verification data; run verify_places.py first")

    spots, _excluded = select_spots(all_spots)
    spots_by_id = {(s.get("id") or s.get("name")): s for s in all_spots}
    sources = collect_sources(data, spots_by_id)
    used = [s for s in sources if s.get("status", "used") == "used"]
    rejected = [s for s in sources if s.get("status") == "rejected"]
    source_numbers = {s["url"]: i for i, s in enumerate(used, 1) if s.get("url")}

    images = choose_images(spots, check_images, proxy_images, timeout)
    for spot in spots:
        if not images.get(spot_key(spot)):
            warn(f"{spot_key(spot)}: no working image; add candidates from other sites and rerun")

    out: list[str] = []
    for title, summary, group in group_by_area(spots, place.get("areas") or [], labels):
        out += [f"## {title}", ""]
        if summary:
            out += [f"*{summary}*", ""]
        for spot in group:
            out += render_card(spot, images.get(spot_key(spot)), source_numbers, labels)

    out += [f"## {labels['sources_used']}", ""]
    out += [f"{i}. {source_line(s)}" for i, s in enumerate(used, 1)] or ["- -"]
    out.append("")
    if rejected:
        out += [f"## {labels['rejected_sources']}", ""]
        out += [f"- {source_line(s)}: {s.get('reason') or '-'}" for s in rejected]
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("verified", type=Path, help="path to verified.json")
    parser.add_argument("-o", "--output", type=Path, help="write Markdown here instead of stdout")
    parser.add_argument("--no-check-images", action="store_true", help="use the first image candidate unchecked")
    parser.add_argument(
        "--no-proxy",
        action="store_true",
        help="output original image URLs instead of GitHub proxy URLs (photos may then not show in apps that only trust a few image hosts)",
    )
    parser.add_argument("--timeout", type=float, default=8.0, help="seconds per image request (default 8)")
    args = parser.parse_args()

    data = json.loads(args.verified.read_text(encoding="utf-8"))
    markdown = render(data, not args.no_check_images, not args.no_proxy, args.timeout)
    if args.output:
        args.output.write_text(markdown, encoding="utf-8")
    else:
        sys.stdout.write(markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
