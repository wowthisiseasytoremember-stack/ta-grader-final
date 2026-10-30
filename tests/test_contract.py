import ast
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "TA_Grader.py").read_text(encoding="utf-8")
CONFIG_PATH = ROOT / "tests" / "config.template.json"
if not CONFIG_PATH.exists():
    CONFIG_PATH = ROOT / "config.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


class ContractTests(unittest.TestCase):
    def test_python_source_parses(self):
        ast.parse(SOURCE)

    def test_endpoint_order(self):
        self.assertEqual(
            [ep["name"] for ep in CONFIG["endpoints"]],
            ['yolo-auto-flash', 'omniroute-copilot-mini', 'omniroute-antigravity-lite', 'omniroute-copilot-gpt5-mini', 'omniroute-antigravity-flash', 'omniroute-yolo', 'omniroute-ollama-cloud', 'gemini-flash', 'openai-gpt-4o-mini', 'nvidia-llama-3.2-11b-vision', 'nvidia-nemotron-lightning'],
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

    def test_yolo_has_two_rotation_keys(self):
        yolo = next(ep for ep in CONFIG["endpoints"] if ep["name"] == "yolo-auto-flash")
        self.assertEqual(
            yolo["key_env"],
            ["YOLO_AUTO_API_KEY_2", "YOLO_AUTO_API_KEY"],
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

    # ------------------------------------------------------------------
    # Routing v3 contract — extraction-tolerant validation, cooldown
    # economics, keyless skipping, vision consensus
    # ------------------------------------------------------------------

    def test_complete_answer_tolerates_fenced_json_and_rejects_option_echoes(self):
        self.assertIn("fenced", SOURCE)
        self.assertIn("exactly one answer line", SOURCE)
        self.assertIn('s.startswith("{") or s.startswith("[")', SOURCE)
        self.assertIn("truncated stream", SOURCE)

    def test_failure_streaks_drive_exponential_cooldown(self):
        self.assertIn("_fail_streak", SOURCE)
        self.assertIn("_origin_streak", SOURCE)
        self.assertIn("def _mark_failure", SOURCE)
        self.assertIn('base * (2 ** exponent)', SOURCE)

    def test_provider_scoped_failures_cool_shared_origins(self):
        self.assertIn("HTTP 429", SOURCE)
        self.assertIn("connection error", SOURCE)
        self.assertIn("_origin_of", SOURCE)

    def test_keyless_endpoints_never_burn_the_chain(self):
        self.assertIn("skipped (no API key resolved)", SOURCE)

    def test_cooldown_bypasses_and_stalest_retry(self):
        self.assertIn("ignore_cooldown", SOURCE)
        self.assertIn("retrying stalest", SOURCE)

    def test_vision_consensus_and_escalation(self):
        self.assertIn("confirm_vision_answers", SOURCE)
        self.assertIn("escalation_endpoints", SOURCE)
        self.assertIn("def _verify_vision_answer", SOURCE)
        self.assertIn("def _model_letter", SOURCE)

    def test_per_endpoint_token_budgets(self):
        self.assertIn('ep.get("max_tokens") or cfg.get("max_tokens")', SOURCE)
        live = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        eps = {e["name"]: e for e in live["endpoints"]}
        self.assertEqual(eps["xai-grok-reasoning"]["max_tokens"], 4096)
        self.assertEqual(eps["omniroute-copilot-gpt5.4"]["max_tokens"], 2048)
        self.assertEqual(eps["omniroute-copilot-sonnet-5"]["max_tokens"], 1536)

    def test_live_config_routing_v3(self):
        live = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(live.get("routing_version"), 3)
        self.assertTrue(live.get("confirm_vision_answers"))
        enabled_names = [e["name"] for e in live["endpoints"] if e.get("enabled", True)]
        self.assertEqual(len(enabled_names), len(set(enabled_names)))
        # Deep-reasoning ranks sit at the back: knowledge-speed first.
        self.assertLess(
            enabled_names.index("opencode-deepseek-vision"),
            enabled_names.index("xai-grok-reasoning"),
        )
        self.assertLess(
            enabled_names.index("omniroute-generalist"),
            enabled_names.index("omniroute-copilot-gpt5.4"),
        )
        # Provider diversity: an independent origin appears in the top 5.
        def origin(name):
            url = next(e["url"] for e in live["endpoints"] if e["name"] == name)
            return url.split("//", 1)[-1].split("/", 1)[0]
        top_five = {origin(n) for n in enabled_names[:5]}
        self.assertGreaterEqual(len(top_five), 2)


if __name__ == "__main__":
    unittest.main()
