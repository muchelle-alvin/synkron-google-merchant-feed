import io
import unittest

from scripts.analyze_catalog_export import analyze_catalog


class AnalyzeCatalogExportTests(unittest.TestCase):
    def test_counts_products_variants_and_required_active_batches(self) -> None:
        export = io.StringIO(
            "Product ID,Variant ID,Status,Show In Store\n"
            "p1,v1,Active,YES\n"
            "p1,v2,Active,YES\n"
            "p2,v3,Inactive,YES\n"
            "p3,v4,Active,NO\n"
        )

        summary = analyze_catalog(export, batch_size=2)

        self.assertEqual(summary["csv_rows"], 4)
        self.assertEqual(summary["unique_products"], 3)
        self.assertEqual(summary["published_products"], 2)
        self.assertEqual(summary["active_products"], 2)
        self.assertEqual(summary["merchant_eligible_products"], 1)
        self.assertEqual(summary["merchant_eligible_variants"], 2)
        self.assertEqual(summary["commerce_batches_required"], 1)

    def test_rejects_non_positive_batch_size(self) -> None:
        with self.assertRaisesRegex(ValueError, "batch_size must be positive"):
            analyze_catalog(io.StringIO("Product ID\n"), batch_size=0)


if __name__ == "__main__":
    unittest.main()
