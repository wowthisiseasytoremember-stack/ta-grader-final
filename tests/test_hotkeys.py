import ast, unittest, types, queue
from pathlib import Path

SRC = str(Path(__file__).resolve().parents[1] / "TA_Grader.py")

def _extract(name):
    tree = ast.parse(Path(SRC).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return compile(ast.Module(body=[node], type_ignores=[]), SRC, "exec")
    raise NameError(name)

class TestHotkeys(unittest.TestCase):
    def setUp(self):
        self.clock = [0.0]
        self.time_ns = types.SimpleNamespace(monotonic=lambda: self.clock[0])
        self.release = lambda *a, **k: None
        self.log = lambda *a, **k: None

    def _make_pump_ns(self, q):
        ns = {"queue": queue, "time": self.time_ns,
              "release_modifier_keys": self.release, "log": self.log,
              "_pump": None}
        code = _extract("_pump")
        exec(code, ns)
        ns["self"] = types.SimpleNamespace(_events=q, root=types.SimpleNamespace(after=lambda *a: None),
                                           _pump=ns["_pump"], _do_ocr=lambda *a: ns.setdefault("_ocr_count", 0) or ns.__setitem__("_ocr_count", ns.get("_ocr_count", 0) + 1))
        ns["self"]._do_ocr = lambda: ns.__setitem__("_ocr_count", ns.get("_ocr_count", 0) + 1)
        return ns

    def test_pump_dispatch(self):
        q = queue.Queue()
        q.put("ocr")
        q.put("ocr")
        ns = self._make_pump_ns(q)
        self.clock[0] = 0.0
        ns["_pump"](ns["self"])
        self.assertEqual(ns.get("_ocr_count", 0), 1)
        self.clock[0] = 1.0
        q.put("ocr")
        ns["_pump"](ns["self"])
        self.assertEqual(ns.get("_ocr_count", 0), 1)
        self.clock[0] = 3.0
        q.put("ocr")
        ns["_pump"](ns["self"])
        self.assertEqual(ns.get("_ocr_count", 0), 2)

    def test_install_hotkeys(self):
        code = _extract("_install_hotkeys")
        added = []
        kb = types.SimpleNamespace(add_hotkey=lambda *a, **k: added.append((a, k)))
        ns = {"keyboard": kb, "messagebox": None, "log": self.log}
        exec(code, ns)
        cfg = {"hotkey_ocr": "menu", "hotkey_clip": "alt+c", "hotkey_clear": "alt+v"}
        ns["_install_hotkeys"](types.SimpleNamespace(cfg=cfg, _events=queue.Queue()))
        args = [a[0] for a, k in added]
        self.assertIn("menu", args)
        self.assertIn("alt+c", args)
        self.assertIn("alt+v", args)
        self.assertEqual(len(args), 3)
        menu = [kw for a, kw in added if a[0] == "menu"]
        self.assertTrue(menu[0]["trigger_on_release"])

if __name__ == "__main__":
    unittest.main()

