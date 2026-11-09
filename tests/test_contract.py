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
            [
                "opencodego-haiku5.5",
                "openrouter-haiku5.5",
                "omniroute-haiku",
                "xai-grok-fast",
                "openrouter-direct",
                "omniroute-gemma-free",
                "opencode-mimo-flash",
                "opencode-deepseek-flash",
                "opencode-glm-flash",
                "opencode-free",
                "gemini-2.5-flash",
            ],
        )

    def test_all_endpoints_declare_vision_capability(self):
        for ep in CONFIG["endpoints"]:
            self.assertIsInstance(
                ep.get("supports_vision"),
                bool,
                f"{ep['name']} must explicitly set supports_vision",
            )

    def test_opencode_go_endpoints_use_current_inference_base(self):
        for ep in CONFIG["endpoints"]:
            if ep["name"].startswith("opencode-") and ep.get("model", "").endswith(
                ("flash", "-flash")
            ) and "-free" not in ep["model"] and ep["name"] != "opencode-free":
                self.assertTrue(
                    ep["url"].startswith("https://opencode.ai/inference/go/"),
                    f"{ep['name']} must use the inference/go base URL",
                )

    def test_omniroute_ranks_reach_over_tailscale(self):
        omni = [ep for ep in CONFIG["endpoints"] if ep["name"].startswith("omniroute-")]
        self.assertGreaterEqual(len(omni), 2, "expect haiku + free OmniRoute ranks")
        for ep in omni:
            self.assertIn("100.122.158.123:20128", ep["url"])
        haiku = next(ep for ep in omni if ep["name"] == "omniroute-haiku")
        self.assertEqual(haiku["model"], "no-think/github/claude-haiku-4.5")
        gemma = next(ep for ep in omni if ep["name"] == "omniroute-gemma-free")
        self.assertTrue(gemma["model"].endswith(":free"))
        self.assertFalse(gemma.get("supports_vision", True))

    def test_free_overflow_rank_wire(self):
        free = next(ep for ep in CONFIG["endpoints"] if ep["name"] == "opencode-free")
        self.assertTrue(free.get("no_auth"))
        self.assertIn("opencode.ai/zen/v1", free["url"])
        self.assertIn("-free", free["model"])
        self.assertFalse(free.get("supports_vision", True))
        self.assertEqual(free["headers"].get("x-opencode-client"), "opencode")

    def test_haiku55_double_route(self):
        go = next(ep for ep in CONFIG["endpoints"] if ep["name"] == "opencodego-haiku5.5")
        self.assertEqual(go["url"], "https://opencode.ai/inference/go/openai/v1/chat/completions")
        # OpenCode Go spells it with hyphens; dots return 400 "Model is unavailable".
        self.assertEqual(go["model"], "claude-haiku-5-5")
        self.assertEqual(go["key_env"], ["OPENCODEGOTAGRADER"])
        self.assertTrue(go["supports_vision"])
        orr = next(ep for ep in CONFIG["endpoints"] if ep["name"] == "openrouter-haiku5.5")
        self.assertEqual(orr["url"], "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(orr["model"], "anthropic/claude-haiku-5.5")
        self.assertEqual(orr["key_env"], ["OPENROUTERTAGRADER"])
        self.assertTrue(orr["supports_vision"])

    def test_openrouter_direct_rank_wire(self):
        direct = next(ep for ep in CONFIG["endpoints"] if ep["name"] == "openrouter-direct")
        self.assertEqual(direct["url"], "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(direct["model"], "google/gemma-4-26b-a4b-it:free")
        self.assertEqual(direct["key_env"], ["OPENROUTERTAGRADER"])
        self.assertFalse(direct.get("supports_vision", True))

    def test_auth_fail_cooldown_configured(self):
        self.assertGreaterEqual(int(CONFIG["auth_fail_cooldown_sec"]), 900)
        self.assertIn("auth_fail_cooldown_sec", SOURCE)
        self.assertIn("auth_fail_cooldown_sec", json.dumps(
            json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        ))

    def test_answer_letter_remap_guard_present(self):
        self.assertIn("def remap_answer_letter", SOURCE)
        self.assertIn("remap_answer_letter(", SOURCE)
        self.assertIn("def _parse_options", SOURCE)
        self.assertIn("def _normalize_option_text", SOURCE)

    def test_stable_opencode_session_header(self):
        self.assertIn("ses_\" + os.urandom(32).hex()", SOURCE)
        self.assertIn("x-opencode-client", SOURCE)

    def test_gemini_has_two_rotation_keys(self):
        gemini = next(ep for ep in CONFIG["endpoints"] if ep["name"] == "gemini-2.5-flash")
        self.assertEqual(
            gemini["key_env"],
            ["GEMINI_API_KEY", "GEMINI_FLASH_KEY_2"],
        )

    def test_per_key_cooldown_and_keepalive_protection_present(self):
        self.assertIn("_key_cooldown", SOURCE)
        self.assertIn("chatcmpl-keepalive", SOURCE)
        self.assertIn("self.session.trust_env = False", SOURCE)
        self.assertNotIn("_stream_copilot_sdk", SOURCE)
        self.assertNotIn("_verify_vision_answer", SOURCE)

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
