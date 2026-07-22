#!/usr/bin/env python3
"""Validate a Google Merchant RSS product feed using the Python standard library."""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse


GOOGLE_NS = "http://base.google.com/ns/1.0"
G = f"{{{GOOGLE_NS}}}"
REQUIRED_ITEM_FIELDS = (
    "id",
    "title",
    "description",
    "link",
    "image_link",
    "availability",
    "condition",
    "price",
)
VALID_AVAILABILITY = {"in_stock", "out_of_stock", "preorder", "backorder"}
VALID_CONDITION = {"new", "refurbished", "used"}
PRICE_RE = re.compile(r"^(\d+(?:\.\d+)?) ([A-Z]{3})$")


def _text(element: ET.Element | None) -> str:
    return "" if element is None or element.text is None else element.text.strip()


def _valid_web_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_feed(path: Path, *, allow_empty: bool = False) -> tuple[int, list[str]]:
    errors: list[str] = []

    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        return 0, [f"cannot parse {path}: {exc}"]

    if root.tag != "rss":
        errors.append("root element must be <rss>")
    if root.get("version") != "2.0":
        errors.append("<rss> version must be 2.0")

    channel = root.find("channel")
    if channel is None:
        return 0, errors + ["feed must contain one <channel>"]

    for field in ("title", "link", "description"):
        if not _text(channel.find(field)):
            errors.append(f"channel <{field}> must not be empty")

    channel_link = _text(channel.find("link"))
    if channel_link and not _valid_web_url(channel_link):
        errors.append("channel <link> must be an HTTP(S) URL")

    items = channel.findall("item")
    if not items and not allow_empty:
        errors.append("feed must contain at least one <item>")

    seen_ids: set[str] = set()
    for number, item in enumerate(items, start=1):
        prefix = f"item {number}"
        values = {name: _text(item.find(f"{G}{name}")) for name in REQUIRED_ITEM_FIELDS}

        for name, value in values.items():
            if not value:
                errors.append(f"{prefix}: <g:{name}> must not be empty")

        product_id = values["id"]
        if len(product_id) > 50:
            errors.append(f"{prefix}: <g:id> exceeds 50 characters")
        if product_id in seen_ids:
            errors.append(f"{prefix}: duplicate <g:id> {product_id!r}")
        seen_ids.add(product_id)

        if len(values["title"]) > 150:
            errors.append(f"{prefix}: <g:title> exceeds 150 characters")
        if len(values["description"]) > 5000:
            errors.append(f"{prefix}: <g:description> exceeds 5000 characters")

        for name in ("link", "image_link"):
            if values[name] and not _valid_web_url(values[name]):
                errors.append(f"{prefix}: <g:{name}> must be an HTTP(S) URL")

        if values["availability"] and values["availability"] not in VALID_AVAILABILITY:
            errors.append(
                f"{prefix}: unsupported availability {values['availability']!r}"
            )
        if values["condition"] and values["condition"] not in VALID_CONDITION:
            errors.append(f"{prefix}: unsupported condition {values['condition']!r}")

        for name in ("price", "sale_price"):
            value = _text(item.find(f"{G}{name}"))
            if not value and name == "sale_price":
                continue
            match = PRICE_RE.fullmatch(value)
            if not match:
                errors.append(f"{prefix}: <g:{name}> must be a number and ISO currency")
                continue
            try:
                if Decimal(match.group(1)) <= 0:
                    errors.append(f"{prefix}: <g:{name}> must be greater than zero")
            except InvalidOperation:
                errors.append(f"{prefix}: <g:{name}> contains an invalid number")

    return len(items), errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("feed", type=Path, help="path to the RSS XML feed")
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="allow the initial seed feed to contain no product items",
    )
    args = parser.parse_args(argv)

    item_count, errors = validate_feed(args.feed, allow_empty=args.allow_empty)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"Valid Google Merchant RSS feed: {item_count} item(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
