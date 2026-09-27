import ast
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "TA_Grader.py").read_text(encoding="utf-8")
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


class ContractTests(unittest.TestCase):
    def test_python_source_parses(self):
        ast.parse(SOURCE)

    def test_endpoint_order(self):
        self.assertEqual(
            [ep["name"] for ep in CONFIG["endpoints"]],
            [
                "yolo-auto-flash",
                "yolo-auto-small",
                "gemini-flash",
                "openai-gpt-4o-mini",
                "nvidia-llama-3.2-11b-vision",
                "nvidia-phi-3-vision",
                "nvidia-nemotron-lightning",
                "omniroute-gemini-fast",
            ],
        )

    def test_all_endpoints_declare_vision_capability(self):
        for ep in CONFIG["endpoints"]:
            self.assertIsInstance(
                ep.get("supports_vision"),
                bool,
                f"{ep['name']} must explicitly set supports_vision",
            )

    def test_gemini_has_two_rotation_keys(self):
        gemini = next(ep for ep in CONFIG["endpoints"] if ep["name"] == "gemini-flash")
        self.assertEqual(
            gemini["key_env"],
            ["GEMINI_API_KEY", "GEMINI_FLASH_KEY_2"],
        )

    def test_runtime_secret_values_are_not_cached_in_config(self):
        self.assertNotIn("_verified_key", SOURCE)
        self.assertNotIn("_verified_keys", SOURCE)
        self.assertIn("_SECRET_CACHE", SOURCE)
        self.assertIn("config_for_disk", SOURCE)
        self.assertEqual(SOURCE.count("config_for_disk(self.cfg)"), 3)

    def test_adaptive_capture_core(self):
        self.assertIn("capture_region_image", SOURCE)
        self.assertIn("ocr_image", SOURCE)
        self.assertIn("assess_ocr_quality", SOURCE)
        self.assertIn("prefer_vision", SOURCE)
        self.assertIn("endpoint_supports_vision", SOURCE)
        self.assertNotIn("capture_region_base64", SOURCE)
        self.assertNotIn("def ocr_region", SOURCE)

    def test_manual_scroll_preserved_and_adaptive(self):
        self.assertEqual(CONFIG["hotkey_scroll"], "alt+shift+z")
        self.assertEqual(CONFIG["hotkey_set_scroll"], "alt+shift+x")
        self.assertIn("scroll_region", CONFIG)
        self.assertIn("def capture_scroll_region", SOURCE)
        self.assertIn("Scroll OCR quality", SOURCE)

    def test_auto_scroll_preserved_and_adaptive(self):
        self.assertEqual(CONFIG["hotkey_auto_scroll"], "alt+shift+a")
        self.assertEqual(CONFIG["hotkey_set_auto_scroll"], "alt+shift+s")
        self.assertIn("auto_scroll_region", CONFIG)
        self.assertIn("def _do_auto_scroll", SOURCE)
        self.assertIn("Auto-scroll:", SOURCE)
        self.assertIn("combined_confidence", SOURCE)
        self.assertIn("stitch_images", SOURCE)

    def test_single_instance_gate_is_not_duplicated(self):
        self.assertEqual(SOURCE.count("def ensure_single_instance"), 1)
        self.assertNotIn("def enforce_single_instance", SOURCE)


if __name__ == "__main__":
    unittest.main()
