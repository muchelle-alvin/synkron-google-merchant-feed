from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BATCH_SOURCE = (ROOT / "deluge/generate_synkron_google_feed_batch.dg").read_text()
PUBLISH_SOURCE = (ROOT / "deluge/publish_synkron_google_feed.dg").read_text()


class DelugeContractTests(unittest.TestCase):
    def test_sources_have_balanced_blocks(self) -> None:
        for source in (BATCH_SOURCE, PUBLISH_SOURCE):
            self.assertEqual(source.count("{"), source.count("}"))
            self.assertEqual(source.count("["), source.count("]"))

    def test_batch_uses_documented_page_parameter_and_validates_response(self) -> None:
        self.assertIn('commerce_parameters.put("page",requested_page);', BATCH_SOURCE)
        self.assertNotIn('commerce_parameters.put("page_start_from"', BATCH_SOURCE)
        self.assertIn("returned_page != requested_page", BATCH_SOURCE)
        self.assertIn("batch_size = 200;", BATCH_SOURCE)

    def test_publisher_guards_batch_identity_and_global_offer_ids(self) -> None:
        self.assertIn("batch_run_id != run_id", PUBLISH_SOURCE)
        self.assertIn("seen_page_markers.containKey(page_marker)", PUBLISH_SOURCE)
        self.assertIn("seen_offer_ids.containKey(staged_offer_id)", PUBLISH_SOURCE)
        self.assertIn("last_has_more_page == true", PUBLISH_SOURCE)

    def test_connections_are_referenced_by_link_name(self) -> None:
        self.assertIn('connection : "synkron_commerce_product_feed"', BATCH_SOURCE)
        self.assertIn('connection : "synkron_github_merchant_feed"', BATCH_SOURCE)
        self.assertIn('connection : "synkron_github_merchant_feed"', PUBLISH_SOURCE)


if __name__ == "__main__":
    unittest.main()
