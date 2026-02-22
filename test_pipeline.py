import unittest
from pathlib import Path

from pipeline import ItemExtractionPipeline


_TR_FILE = Path(__file__).parent / "docs_sample" / "doc_sample.txt"
SAMPLE_DOCUMENT = _TR_FILE.read_text(encoding="utf-8")


class TestItemExtractionPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = ItemExtractionPipeline()

    def test_01_process_document_returns_result(self):
        """Pipeline executes and returns a result dict."""
        result = self.pipeline.process_document(SAMPLE_DOCUMENT, document_id=1)
        self.assertIsInstance(result, dict)

    def test_02_items_are_extracted(self):
        """At least one item is extracted from the sample document."""
        result = self.pipeline.process_document(SAMPLE_DOCUMENT, document_id=2)
        items_raw = result.get("items_raw", [])
        self.assertGreater(len(items_raw), 0, "No items were extracted from the document.")
        print(f"\n[OK] {len(items_raw)} items extracted (raw)")
        for i, item in enumerate(items_raw, 1):
            print(f"  [{i}] {item[:120]}...")

    def test_03_items_are_processed(self):
        """All extracted items go through the full classification pipeline."""
        result = self.pipeline.process_document(SAMPLE_DOCUMENT, document_id=3)
        items_processed = result.get("items_processed", [])
        self.assertGreater(len(items_processed), 0, "No items were processed.")
        print(f"\n[OK] {len(items_processed)} items fully processed")

    def test_04_processed_items_have_required_fields(self):
        """Each processed item contains all required fields."""
        result = self.pipeline.process_document(SAMPLE_DOCUMENT, document_id=4)
        items_processed = result.get("items_processed", [])
        required = ["id", "document_id", "name", "type", "description", "metadata"]

        for item in items_processed:
            for field in required:
                self.assertIn(field, item, f"Field '{field}' missing from item: {item.get('id')}")

    def test_05_items_have_valid_type(self):
        """Each processed item has a valid type (product or service)."""
        result = self.pipeline.process_document(SAMPLE_DOCUMENT, document_id=5)
        items_processed = result.get("items_processed", [])

        for item in items_processed:
            self.assertIn(
                item.get("type"),
                ("product", "service"),
                f"Invalid type '{item.get('type')}' for item {item.get('id')}",
            )
            print(f"  [{item['id']}] type={item['type']}, name={item.get('name', '')[:60]}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
