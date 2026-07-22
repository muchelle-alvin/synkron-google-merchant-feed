from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.validate_feed import validate_feed


VALID_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:g="http://base.google.com/ns/1.0" version="2.0">
  <channel>
    <title>Synkron Shop Google Product Feed</title>
    <link>https://shop.example.com/</link>
    <description>Synkron test feed</description>
    <item>
      <g:id>SKU-1</g:id>
      <g:title>Sensor &amp; cable</g:title>
      <g:description>A test product.</g:description>
      <g:link>https://shop.example.com/products/sensor/1</g:link>
      <g:image_link>https://shop.example.com/product-images/2</g:image_link>
      <g:availability>in_stock</g:availability>
      <g:condition>new</g:condition>
      <g:price>1200 KES</g:price>
    </item>
  </channel>
</rss>
"""


class FeedValidationTests(unittest.TestCase):
    def validate(self, content: str, *, allow_empty: bool = False) -> tuple[int, list[str]]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "feed.xml"
            path.write_text(content, encoding="utf-8")
            return validate_feed(path, allow_empty=allow_empty)

    def test_accepts_valid_feed(self) -> None:
        count, errors = self.validate(VALID_FEED)
        self.assertEqual(count, 1)
        self.assertEqual(errors, [])

    def test_rejects_duplicate_ids_and_invalid_values(self) -> None:
        second_item = VALID_FEED.split("    <item>", 1)[1].split("    </item>", 1)[0]
        invalid = VALID_FEED.replace(
            "    </item>",
            "    </item>\n    <item>" + second_item + "    </item>",
        ).replace("<g:availability>in_stock</g:availability>", "<g:availability>available</g:availability>")

        count, errors = self.validate(invalid)
        self.assertEqual(count, 2)
        self.assertTrue(any("duplicate <g:id>" in error for error in errors))
        self.assertTrue(any("unsupported availability" in error for error in errors))

    def test_empty_feed_requires_explicit_opt_in(self) -> None:
        empty = VALID_FEED.split("    <item>", 1)[0] + "  </channel>\n</rss>\n"
        _, errors = self.validate(empty)
        self.assertIn("feed must contain at least one <item>", errors)

        count, errors = self.validate(empty, allow_empty=True)
        self.assertEqual(count, 0)
        self.assertEqual(errors, [])

    def test_rejects_malformed_xml(self) -> None:
        count, errors = self.validate("<rss>")
        self.assertEqual(count, 0)
        self.assertTrue(errors[0].startswith("cannot parse"))


if __name__ == "__main__":
    unittest.main()
