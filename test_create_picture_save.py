import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import createPicture


class PictureSaveTests(unittest.TestCase):
    def make_catalog(self, root: Path):
        with patch.object(createPicture, "load_space_v_words", return_value=["alpha", "beta"]), \
                patch.object(createPicture, "load_qmdict_words", return_value=[]):
            catalog = createPicture.PictureCatalog(root / "out", root / "common")
        catalog.output.mkdir(parents=True)
        return catalog

    def test_direct_download_is_detected_without_preview(self):
        with tempfile.TemporaryDirectory() as raw:
            catalog = self.make_catalog(Path(raw))
            (catalog.output / "alpha.jpg").write_bytes(b"downloaded")
            result = catalog.save_or_advance("alpha", b"", "clipboard.png")
            self.assertTrue(result["detected_existing"])
            self.assertEqual(result["word"], "beta")
            self.assertEqual((catalog.output / "alpha.jpg").read_bytes(), b"downloaded")

    def test_existing_file_wins_over_stale_preview(self):
        with tempfile.TemporaryDirectory() as raw:
            catalog = self.make_catalog(Path(raw))
            (catalog.output / "alpha.jpg").write_bytes(b"downloaded")
            result = catalog.save_or_advance("alpha", b"stale-preview", "clipboard.png")
            self.assertTrue(result["detected_existing"])
            self.assertFalse((catalog.output / "alpha.png").exists())

    def test_missing_image_skips_and_save_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as raw:
            catalog = self.make_catalog(Path(raw))
            skipped = catalog.save_or_advance("alpha", b"", "clipboard.png")
            self.assertTrue(skipped["skipped"])
            self.assertEqual(skipped["word"], "beta")

            catalog.set_word("alpha")
            payload = b"\x89PNG\r\n\x1a\n\x00raw"
            saved = catalog.save_or_advance("alpha", payload, "clipboard.png")
            self.assertEqual((catalog.output / "alpha.png").read_bytes(), payload)
            self.assertEqual(saved["word"], "beta")

    def test_skip_refreshes_queue_before_selecting_next_word(self):
        with tempfile.TemporaryDirectory() as raw:
            catalog = self.make_catalog(Path(raw))
            (catalog.output / "beta.png").write_bytes(b"downloaded")
            skipped = catalog.save_or_advance("alpha", b"", "clipboard.png")
            self.assertTrue(skipped["skipped"])
            self.assertEqual(skipped["word"], "")

    def test_manual_missing_word_advances_to_first_queue_word(self):
        with tempfile.TemporaryDirectory() as raw:
            catalog = self.make_catalog(Path(raw))
            skipped = catalog.save_or_advance("manual", b"", "clipboard.png")
            self.assertTrue(skipped["skipped"])
            self.assertEqual(skipped["word"], "alpha")

    def test_parallel_saves_are_idempotent(self):
        with tempfile.TemporaryDirectory() as raw:
            catalog = self.make_catalog(Path(raw))
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda _: catalog.save_or_advance("alpha", b"complete", "clipboard.png"), range(8)))
            self.assertEqual(sum("saved" in result for result in results), 1)
            self.assertEqual(sum(bool(result.get("detected_existing")) for result in results), 7)
            self.assertEqual((catalog.output / "alpha.png").read_bytes(), b"complete")

    def test_filename_stem_matches_server_vocab_key_contract(self):
        self.assertEqual(createPicture.filename_for_word("Ice Cream"), "ice cream")
        self.assertEqual(createPicture.filename_for_word("Don't"), "don't")
        self.assertEqual(createPicture.filename_for_word("well-known"), "well-known")
        self.assertNotEqual(createPicture.word_key("don't"), createPicture.word_key("dont"))
        self.assertNotEqual(createPicture.word_key("ice-cream"), createPicture.word_key("ice cream"))
        self.assertNotIn(".avif", createPicture.IMAGE_EXTENSIONS)

    def test_prompt_button_copies_exact_current_word_prompt(self):
        html = createPicture.HTML_FILE.read_text(encoding="utf-8")
        self.assertIn("thiết kế ảnh minh họa cho từ vựng ${String(word || '').trim()}", html)
        self.assertIn("navigator.clipboard.writeText(text)", html)
        self.assertIn("document.execCommand('copy')", html)
        self.assertIn('role="status" aria-live="polite"', html)
        self.assertIn("result.detected_existing", html)


if __name__ == "__main__":
    unittest.main()
