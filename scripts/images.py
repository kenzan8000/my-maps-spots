"""Check that a spot photo can be embedded, and resolve it to a direct image URL.

Shared by render_spots.py (chat photos) and build_mymaps_csv.py (My Maps pin popups).
Uses only the Python standard library.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

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


def canonical_wikimedia_url(url: str) -> str | None:
    """upload.wikimedia.org path for a Commons thumbnail, without tracking query.

    Special:FilePath redirects to thumb.wikimedia.org with utm parameters. The same
    file is also at upload.wikimedia.org, which is the address that stays valid.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.netloc not in ("thumb.wikimedia.org", "upload.wikimedia.org"):
        return None
    if not parsed.path.startswith("/wikipedia/"):
        return None
    canonical = urllib.parse.urlunparse(("https", "upload.wikimedia.org", parsed.path, "", "", ""))
    return None if canonical == url else canonical


def resolve_direct_image(urls: list, timeout: float, check: bool) -> tuple[str | None, list[tuple[str, str, str]]]:
    """Return (direct_url, failures) for a My Maps pin popup.

    My Maps fetches the popup photo itself, so this stays on the image file URL and
    does not rewrite it through the GitHub proxy used for chat. failures are
    (url, result, reason). With check=False, the first https URL is used as given.
    """
    if not check:
        for url in urls:
            if isinstance(url, str) and url.startswith("https://"):
                return url, []
        if urls:
            return None, [(str(urls[0]), "bad", "not https (many chat apps block http images)")]
        return None, []

    failures: list[tuple[str, str, str]] = []
    for url in urls:
        result, final_url, reason = check_image(str(url), timeout)
        if result != "ok":
            failures.append((str(url), result, reason))
            continue
        canonical = canonical_wikimedia_url(final_url)
        if canonical:
            again, again_url, _reason = check_image(canonical, timeout)
            if again == "ok":
                return again_url, failures
        return final_url, failures
    return None, failures
