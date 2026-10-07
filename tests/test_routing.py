import unittest
import json
import os
import ast
import pathlib
import typing
import re
import uuid
import time
from types import SimpleNamespace

requests = SimpleNamespace(Session=lambda: None, exceptions=SimpleNamespace(Timeout=TimeoutError, ConnectionError=ConnectionError))
from unittest.mock import patch

# ─── AST Extraction ───────────────────────────────────────────────────────────

source_path = pathlib.Path(__file__).resolve().parents[1] / "TA_Grader.py"
source = source_path.read_text(encoding="utf-8")
tree = ast.parse(source)

class_node = None
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef) and node.name == "LLMClient":
        class_node = node
        break

assert class_node is not None, "LLMClient not found in TA_Grader.py"

namespace = {
    "endpoint_api_keys": lambda cfg, ep: ["test"],
    "endpoint_supports_vision": lambda ep: ep.get("supports_vision", False),
    "requests": requests,
    "json": json,
    "time": time,
    "os": os,
    "re": re,
    "uuid": uuid,
    "Any": typing.Any,
    "Callable": typing.Callable,
    "Optional": typing.Optional,
    "log": lambda _: None,
}

class_code = ast.get_source_segment(source, class_node)
exec(class_code, namespace)
LLMClient = namespace["LLMClient"]

# ─── Fakes ────────────────────────────────────────────────────────────────────


class FakeResponse:
    def __init__(self, status_code=200, chunks=None):
        self.status_code = status_code
        self._chunks = chunks or []
        self.closed = False

    def iter_lines(self, chunk_size=1):
        for chunk in self._chunks:
            yield b"data: " + json.dumps(
                {"choices": [{"delta": {"content": chunk}}]}
            ).encode()
        yield b"data: [DONE]"

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, responses=None):
        self._responses = list(responses or [])
        self._calls = []

    def post(self, url, **kwargs):
        self._calls.append({"url": url, "json": kwargs.get("json")})
        if self._responses:
            return self._responses.pop(0)
        raise Exception("No more fake responses")


# ─── Helpers ──────────────────────────────────────────────────────────────────


def make_ep(
    name="ep1",
    url="http://test/v1",
    model="m1",
    supports_vision=False,
    enabled=True,
):
    ep = {
        "name": name,
        "url": url,
        "model": model,
        "supports_vision": supports_vision,
        "supports_response_format": False,
        "timeout_sec": 2,
        "total_timeout_sec": 4,
        "max_retries": 0,
    }
    if not enabled:
        ep["enabled"] = False
    return ep


def make_cfg(endpoints=None):
    return {
        "system_prompt": "JSON",
        "endpoints": endpoints or [make_ep()],
        "max_tokens": 512,
    }


# ─── Tests ────────────────────────────────────────────────────────────────────


class TestCompleteAnswer(unittest.TestCase):
    def setUp(self):
        self.client = LLMClient()
        self.client.session = FakeSession()

    def test_partial_returns_false(self):
        self.assertFalse(self.client._complete_answer('{"answer":"B'))

    def test_full_returns_true(self):
        self.assertTrue(self.client._complete_answer('{"answer":"B) Four"}'))


class TestTextOnly(unittest.TestCase):
    def test_text_only_drops_image_and_vision_priority(self):
        client = LLMClient()
        client.session = FakeSession([FakeResponse(chunks=['{"answer":"C) Seven"}'])])
        cfg = make_cfg([make_ep("text"), make_ep("vision", supports_vision=True)])
        cfg["vision_enabled"] = False
        raw, name = client.stream("OCR question", cfg, lambda *_: None,
                                  image_b64="image", prefer_vision=True)
        self.assertEqual(name, "text")
        payload = client.session._calls[0]["json"]
        self.assertIsInstance(payload["messages"][1]["content"], str)
        self.assertIn("OCR question", payload["messages"][1]["content"])


class TestStreamCompletion(unittest.TestCase):
    def setUp(self):
        self.client = LLMClient()

    def test_split_chunks_completes_and_closes(self):
        resp = FakeResponse(
            chunks=['{"answer":"B', ") Four", '"}']
        )
        self.client.session = FakeSession([resp])
        cfg = make_cfg([make_ep("ep1"), make_ep("ep2")])
        raw, name = self.client.stream(
            "hello", cfg, lambda content, name: None
        )
        self.assertEqual(raw, '{"answer":"B) Four"}')
        self.assertTrue(resp.closed)


class TestFallback(unittest.TestCase):
    def setUp(self):
        self.client = LLMClient()

    def test_bad_then_good_falls_back(self):
        bad = FakeResponse(chunks=['{"answer":"B'])
        good = FakeResponse(chunks=['{"answer":"B) Four"}'])
        self.client.session = FakeSession([bad, good])
        cfg = make_cfg([make_ep("ep1"), make_ep("ep2")])
        raw, name = self.client.stream(
            "hello", cfg, lambda content, name: None
        )
        self.assertEqual(raw, '{"answer":"B) Four"}')
        self.assertTrue(bad.closed)
        self.assertTrue(good.closed)


class TestCooldown(unittest.TestCase):
    def setUp(self):
        self.client = LLMClient()

    def test_503_cools_ep1(self):
        resp1 = FakeResponse(status_code=503)
        resp2 = FakeResponse(chunks=['{"answer":"B) Four"}'])
        self.client.session = FakeSession([resp1, resp2])
        eps = [
            make_ep(name="ep1", url="http://ep1/v1"),
            make_ep(name="ep2", url="http://ep2/v1"),
        ]
        cfg = make_cfg(endpoints=eps)

        # First call: ep1 gets 503, ep2 succeeds
        raw, name = self.client.stream(
            "hello", cfg, lambda content, name: None
        )
        self.assertEqual(raw, '{"answer":"B) Four"}')
        self.assertEqual(name, "ep2")

        # Second call: ep1 should be skipped (cooled)
        resp3 = FakeResponse(chunks=['{"answer":"A) One"}'])
        self.client.session._responses = [resp3]
        raw2, name2 = self.client.stream(
            "hello", cfg, lambda content, name: None
        )
        self.assertEqual(raw2, '{"answer":"A) One"}')
        self.assertEqual(name2, "ep2")

        # Total requests: 2 from first call + 1 from second = 3
        self.assertEqual(len(self.client.session._calls), 3)


class TestDisabledEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = LLMClient()

    def test_disabled_endpoint_skipped(self):
        resp = FakeResponse(chunks=['{"answer":"B) Four"}'])
        self.client.session = FakeSession([resp])
        eps = [
            make_ep(name="ep1", url="http://ep1/v1", enabled=False),
            make_ep(name="ep2", url="http://ep2/v1"),
        ]
        cfg = make_cfg(endpoints=eps)
        raw, name = self.client.stream(
            "hello", cfg, lambda content, name: None
        )
        self.assertEqual(name, "ep2")
        # Only one call should have been made (to ep2)
        self.assertEqual(len(self.client.session._calls), 1)
        self.assertEqual(self.client.session._calls[0]["url"], "http://ep2/v1")


class TestPreferVision(unittest.TestCase):
    def setUp(self):
        self.client = LLMClient()

    def test_prefer_vision_promotes_vision_endpoint(self):
        resp = FakeResponse(chunks=['{"answer":"B) Four"}'])
        self.client.session = FakeSession([resp])
        eps = [
            make_ep(name="ep1", url="http://ep1/v1", supports_vision=False),
            make_ep(name="ep2", url="http://ep2/v1", supports_vision=True),
        ]
        cfg = make_cfg(endpoints=eps)
        raw, name = self.client.stream(
            "BAD OCR",
            cfg,
            lambda content, name: None,
            image_b64="abc",
            prefer_vision=True,
        )
        self.assertEqual(name, "ep2")
        # Verify payload: image_url present, text excludes BAD OCR
        call_json = self.client.session._calls[0]["json"]
        messages = call_json["messages"]
        # Find the user message content
        user_msg = [
            m for m in messages if m.get("role") == "user"
        ][0]
        content = user_msg["content"]
        # content should be a list with image_url
        if isinstance(content, list):
            has_image_url = any(
                part.get("type") == "image_url" for part in content
            )
            text_parts = [
                part.get("text", "")
                for part in content
                if part.get("type") == "text"
            ]
        else:
            has_image_url = False
            text_parts = [content]
        self.assertTrue(has_image_url)
        combined_text = " ".join(text_parts)
        self.assertNotIn("BAD OCR", combined_text)


class TestEnvironmentOverride(unittest.TestCase):
    def setUp(self):
        self.client = LLMClient()

    def test_url_env_override(self):
        resp = FakeResponse(chunks=['{"answer":"B) Four"}'])
        self.client.session = FakeSession([resp])
        ep = make_ep(name="test_chat", url="http://original/v1")
        ep["url_env"] = "TEST_CHAT_URL"
        cfg = make_cfg(endpoints=[ep])
        with patch.dict(os.environ, {"TEST_CHAT_URL": "http://override"}):
            raw, name = self.client.stream(
                "hello", cfg, lambda content, name: None
            )
        self.assertEqual(self.client.session._calls[0]["url"], "http://override")


if __name__ == "__main__":
    unittest.main()
