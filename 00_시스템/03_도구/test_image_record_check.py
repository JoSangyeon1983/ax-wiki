"""Check exact article coverage when images are managed by separate records."""
import tempfile
import unittest
from pathlib import Path

from image_record_check import validate_article_targets


class ArticleImageCoverageTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.managed = self.root / "overview.png"
        self.other = self.root / "flow.png"
        self.managed.write_bytes(b"fixture")
        self.other.write_bytes(b"fixture")

    def test_original_exact_match(self):
        validate_article_targets(self.root, [self.managed], {self.managed}, [])

    def test_explicit_separate_image(self):
        validate_article_targets(self.root, [self.managed], {self.managed, self.other}, ["flow.png"])

    def test_unlisted_extra_image_rejected(self):
        with self.assertRaisesRegex(ValueError, "do not match"):
            validate_article_targets(self.root, [self.managed], {self.managed, self.other}, [])

    def test_missing_article_reference_rejected(self):
        with self.assertRaisesRegex(ValueError, "do not match"):
            validate_article_targets(self.root, [self.managed], {self.managed}, ["flow.png"])

    def test_missing_file_rejected(self):
        with self.assertRaisesRegex(ValueError, "Invalid other"):
            validate_article_targets(self.root, [self.managed], {self.managed, self.root / "missing.png"}, ["missing.png"])

    def test_duplicate_and_overlap_rejected(self):
        for values in (["flow.png", "flow.png"], ["overview.png"]):
            with self.subTest(values=values), self.assertRaisesRegex(ValueError, "overlapping"):
                validate_article_targets(self.root, [self.managed], {self.managed, self.other}, values)

    def test_outside_path_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside wiki"):
            validate_article_targets(self.root, [self.managed], {self.managed}, ["../outside.png"])

    def test_archive_path_rejected(self):
        archive = self.root / "99_보관소" / "old.png"
        archive.parent.mkdir()
        archive.write_bytes(b"fixture")
        with self.assertRaisesRegex(ValueError, "Invalid other"):
            validate_article_targets(self.root, [self.managed], {self.managed, archive}, ["99_보관소/old.png"])


if __name__ == "__main__":
    unittest.main()
