"""Parsing of the vSphere tag string collected by the VCF Operations vCenter adapter.

The vCenter adapter stores all tags of an object in one property (``summary|tag``,
shown as "Summary | vSphere Tag") using the format::

    [<Category1-Tag1>, <Category2-Tag2>, <Category1-Tag3>]

This module turns that string into a ``{category: [tag, ...]}`` mapping. It has no
dependency on the SDK so it can be unit tested on its own.
"""
import re
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple

SPLIT_FIRST = "first"
SPLIT_LAST = "last"

# Values the vCenter adapter (or an empty property) may report when nothing is tagged
_EMPTY_VALUES = {"", "[]", "none", "[none]", "null"}

_ITEM_SEPARATOR = re.compile(r">\s*,\s*<")


def split_items(raw: Optional[str]) -> List[str]:
    """Split the raw tag string into ``Category-Tag`` items."""
    if raw is None:
        return []
    value = raw.strip()
    if value.lower() in _EMPTY_VALUES:
        return []
    if value.startswith("["):
        value = value[1:]
    if value.endswith("]"):
        value = value[:-1]
    value = value.strip()
    if value.startswith("<"):
        value = value[1:]
    if value.endswith(">"):
        value = value[:-1]
    if not value:
        return []
    return [item.strip() for item in _ITEM_SEPARATOR.split(value) if item.strip()]


def split_item(
    item: str,
    known_categories: Iterable[str] = (),
    split_mode: str = SPLIT_FIRST,
) -> Tuple[str, str]:
    """Split one ``Category-Tag`` item into ``(category, tag)``.

    Category and tag names may both contain ``-``, so the split is ambiguous. If the
    item starts with one of ``known_categories`` followed by ``-``, the longest such
    category wins. Otherwise the item is split at the first (default) or last ``-``.
    An item without any ``-`` is returned as ``("", item)``.
    """
    matches = [c for c in known_categories if c and item.startswith(c + "-")]
    if matches:
        category = max(matches, key=len)
        return category, item[len(category) + 1 :]
    if "-" not in item:
        return "", item
    if split_mode == SPLIT_LAST:
        category, _, tag = item.rpartition("-")
    else:
        category, _, tag = item.partition("-")
    return category.strip(), tag.strip()


def parse_tags(
    raw: Optional[str],
    known_categories: Iterable[str] = (),
    split_mode: str = SPLIT_FIRST,
) -> Dict[str, List[str]]:
    """Parse the raw tag string into ``{category: [tags]}`` (tags sorted, unique)."""
    known = list(known_categories)
    result: Dict[str, List[str]] = {}
    for item in split_items(raw):
        category, tag = split_item(item, known, split_mode)
        tags = result.setdefault(category, [])
        if tag not in tags:
            tags.append(tag)
    for tags in result.values():
        tags.sort(key=str.lower)
    return result


def sanitize_key_segment(name: str) -> str:
    """Make a category name safe to use as one segment of a VCF Operations stat key.

    ``|`` separates key segments and ``:`` marks instanced keys, so both are replaced.
    """
    cleaned = name.replace("|", "/").replace(":", "_").strip()
    return cleaned or "Uncategorized"


def parse_list_parameter(value: Optional[str]) -> List[str]:
    """Parse a comma-separated configuration value into a list of non-empty items."""
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]
