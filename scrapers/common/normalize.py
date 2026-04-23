"""Small text-normalization helpers shared across scrapers."""

from __future__ import annotations

import re
import unicodedata

_HONORIFIC_RE = re.compile(r"^\s*(Hon\.|Honorable|Judge)\s+", re.IGNORECASE)
_SUFFIX_RE = re.compile(r",?\s*(Jr\.|Sr\.|II|III|IV)\s*$", re.IGNORECASE)
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def clean_whitespace(text: str) -> str:
    """Collapse any run of whitespace to a single space and strip the ends."""
    if text is None:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def slugify(name: str) -> str:
    """Lowercase, ASCII-only, hyphen-separated slug."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return _SLUG_RE.sub("-", ascii_name.lower()).strip("-")


def parse_judge_name(raw: str) -> dict[str, str]:
    """Split a display-cased judge name into {name, honorific, suffix}.

    The CASD index lists judges like "Hon. Anthony J. Battaglia" and
    "Hon. Lupe  Rodriguez, Jr.". We want the base name separate from the
    honorific (for the card's `honorific` field) and the suffix (to keep
    the slug clean).
    """
    text = clean_whitespace(raw)
    honorific = ""
    m = _HONORIFIC_RE.match(text)
    if m:
        honorific = m.group(1).rstrip(".")
        if not honorific.endswith("."):
            honorific += "."
        text = text[m.end():]

    suffix = ""
    m = _SUFFIX_RE.search(text)
    if m:
        suffix = m.group(1)
        text = _SUFFIX_RE.sub("", text).rstrip(",").strip()

    return {
        "name": clean_whitespace(text),
        "honorific": honorific or "Hon.",
        "suffix": suffix,
    }


def lastname_slug(full_name: str) -> str:
    """Return the lowercase, punctuation-free last-name slug CASD uses for
    its per-judge directories at /judges/{slug}/docs/.
    """
    parsed = parse_judge_name(full_name)
    parts = parsed["name"].split()
    if not parts:
        return ""
    return slugify(parts[-1])
