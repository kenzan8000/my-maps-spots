"""Pin icon for a Google My Maps KML import.

My Maps reads the icon from the style id `icon-<id>-<RRGGBB>`. The color in that
id is the same for every pin, My Maps' ordinary blue, because the id needs one
for the icon to show. Icon 1899 is the normal pin.
"""

from __future__ import annotations

import re
import unicodedata

# The normal My Maps pin.
DEFAULT_ICON_ID = 1899
BLANK_ICON_HREF = "https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png"
# One color for every pin. My Maps' usual icon blue. The style id requires it.
PIN_COLOR = "0288D1"

# (key, My Maps icon id, words that mean this spot). Specific keys come first.
# Ids are ones My Maps already uses in its own style ids, or icon images at
# mt.googleapis.com/vt/icon/name=icons/onion/<id>-<name>_4x.png.
ICONS: tuple[tuple[str, int, tuple[str, ...]], ...] = (
    ("pizza", 1651, ("pizza", "pizzeria")),
    ("fast_food", 1567, ("fast food", "burger", "kebab")),
    ("cafe", 1534, ("cafe", "coffee", "kahvila", "espresso")),
    ("bar", 1518, ("bar", "pub", "brewery", "nightlife")),
    ("drinks", 1517, ("cocktail", "wine bar")),
    ("restaurant", 1577, ("restaurant", "dining", "bistro", "ristorante", "ravintola", "food")),
    ("grocery", 1578, ("grocery", "supermarket", "market hall")),
    ("shopping", 1685, ("shopping", "shop", "store", "mall")),
    ("hotel", 1602, ("hotel", "hostel", "lodging")),
    ("museum", 1636, ("museum", "gallery", "museo")),
    ("church", 1670, ("church", "chapel", "cathedral", "kirkko", "kirche", "basilica")),
    ("monument", 1599, ("monument", "memorial", "statue")),
    ("historic", 1598, ("castle", "fortress", "palace", "ruins")),
    ("viewpoint", 1729, ("viewpoint", "lookout", "observation")),
    ("beach", 1521, ("beach",)),
    ("waterfall", 1892, ("waterfall",)),
    ("hiking", 1596, ("hike", "hiking", "trail")),
    ("park", 1886, ("park", "garden", "nature", "forest")),
    ("camping", 1765, ("camping", "campsite")),
    ("ferry", 1569, ("ferry",)),
    ("tram", 1718, ("tram",)),
    ("train", 1716, ("train", "railway")),
    ("bus", 1532, ("bus",)),
    ("airport", 1504, ("airport",)),
    ("cinema", 1635, ("cinema", "movie")),
    ("theater", 1709, ("theater", "theatre", "opera")),
    ("music", 1637, ("music", "concert", "jazz")),
    ("playground", 1652, ("playground",)),
    ("pool", 1701, ("swimming", "pool")),
    ("university", 1726, ("university", "campus")),
    ("civic", 1548, ("city hall", "town hall", "parliament")),
    ("amusement", 1568, ("amusement",)),
    ("info", 1608, ("tourist information",)),
)

_BY_KEY = {key: (icon_id, key) for key, icon_id, _words in ICONS}


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[\s-]+", " ", text).strip()


def _has_word(blob: str, word: str) -> bool:
    # Categories are often plural: Museums, Parks, Churches.
    return re.search(rf"(?<!\w){re.escape(word)}(?:es|s)?(?!\w)", blob) is not None


def choose_icon(spot: dict) -> tuple[int, str]:
    """Return (icon id, key). Unknown or missing types use the normal pin."""
    explicit = fold(str(spot.get("icon") or "")).replace(" ", "_")
    if explicit:
        return _BY_KEY.get(explicit, (DEFAULT_ICON_ID, "pin"))
    name = fold(f"{spot.get('name') or ''} {spot.get('local_name') or ''}")
    category = fold(str(spot.get("category") or ""))
    for blob in (name, category):
        for key, icon_id, words in ICONS:
            if any(_has_word(blob, fold(word)) for word in words):
                return icon_id, key
    return DEFAULT_ICON_ID, "pin"


def pin_style(spot: dict) -> dict:
    icon_id, icon_key = choose_icon(spot)
    return {"icon_id": icon_id, "icon_key": icon_key, "color": PIN_COLOR}


def style_id(icon_id: int, color: str = PIN_COLOR) -> str:
    return f"icon-{icon_id}-{color}"


def kml_color(rrggbb: str) -> str:
    """KML IconStyle color is aabbggrr."""
    rr, gg, bb = rrggbb[0:2], rrggbb[2:4], rrggbb[4:6]
    return f"ff{bb}{gg}{rr}".lower()
