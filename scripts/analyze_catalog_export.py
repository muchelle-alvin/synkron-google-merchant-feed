#!/usr/bin/env python3
"""Summarize a Zoho Commerce item export for feed batch planning."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from math import ceil
from pathlib import Path
from typing import TextIO


def _is_yes(value: str | None) -> bool:
    return (value or "").strip().casefold() in {"true", "yes", "1"}


def analyze_catalog(stream: TextIO, batch_size: int = 200) -> dict[str, object]:
    """Return record, visibility, eligibility, and API batch counts."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")

    rows = 0
    statuses: Counter[str] = Counter()
    product_ids: set[str] = set()
    variant_ids: set[str] = set()
    active_product_ids: set[str] = set()
    visible_product_ids: set[str] = set()
    eligible_product_ids: set[str] = set()
    eligible_variant_ids: set[str] = set()

    for row in csv.DictReader(stream):
        rows += 1
        product_id = (row.get("Product ID") or "").strip()
        variant_id = (row.get("Variant ID") or "").strip()
        status = (row.get("Status") or "").strip().casefold()
        visible = _is_yes(row.get("Show In Store"))

        statuses[status or "(blank)"] += 1
        if product_id:
            product_ids.add(product_id)
        if variant_id:
            variant_ids.add(variant_id)
        if product_id and status == "active":
            active_product_ids.add(product_id)
        if product_id and visible:
            visible_product_ids.add(product_id)
        if product_id and status == "active" and visible:
            eligible_product_ids.add(product_id)
            if variant_id:
                eligible_variant_ids.add(variant_id)

    active_products = len(active_product_ids)
    return {
        "csv_rows": rows,
        "unique_products": len(product_ids),
        "unique_variants": len(variant_ids),
        "status_rows": dict(sorted(statuses.items())),
        "published_products": len(visible_product_ids),
        "active_products": active_products,
        "merchant_eligible_products": len(eligible_product_ids),
        "merchant_eligible_variants": len(eligible_variant_ids),
        "commerce_batch_size": batch_size,
        "commerce_batches_required": ceil(active_products / batch_size),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--batch-size", type=int, default=200)
    args = parser.parse_args()

    with args.csv_path.open(encoding="utf-8-sig", newline="") as stream:
        summary = analyze_catalog(stream, args.batch_size)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
