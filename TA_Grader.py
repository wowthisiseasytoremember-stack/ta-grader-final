"""
TA Grader — Floating Answer-Key Overlay (Windows)

Hotkeys (configurable via config.json):
  ctrl+shift+z   OCR region (drag-select)
  win+shift+c    Send clipboard
  win+shift+v    Clear overlays
  win+shift+x    Re-show last answer

Design:
  - All UI on Tk main thread; LLM/OCR on background threads via queue.Queue.
  - Persistent HTTP session + streaming display updates (~500 ms TTFT).
  - JSON-only model contract; streaming-safe extraction with regex fallback.
  - Endpoint-agnostic: any OpenAI-compatible chat completions URL.
  - Auto-migrates old primary/fallback config format to flat endpoints list.

Dependencies:
  pip install keyboard requests pillow pytesseract
"""

from __future__ import annotations

import json
import uuid
import os
import re
import sys
import io
import base64
import time
import queue
import threading
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Optional

# Load .env file manually
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.strip().split("=", 1)
            os.environ[k.strip().lstrip("\ufeff")] = v.strip().strip("\"'")

import requests
import keyboard
import pytesseract
from PIL import Image, ImageGrab
import tkinter as tk
from tkinter import messagebox


# ---------------------------------------------------------------------------
# Paths / Logging
# ---------------------------------------------------------------------------

APP_NAME = "TA Grader"
HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "config.json"
LOG_PATH = Path(tempfile.gettempdir()) / "ta_grader.log"


def log(msg: str) -> None:
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# DPI Awareness (Windows)
# ---------------------------------------------------------------------------

def enable_dpi_awareness() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor v2
    except Exception:
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # per-monitor v1
        except Exception:
            pass


def release_modifier_keys() -> None:
    """Explicitly release Alt, Ctrl, Shift, and Win virtual keys in Windows to prevent stuck modifier state."""
    if os.name != "nt":
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32
        # VK_MENU (Alt)=0x12, VK_CONTROL (Ctrl)=0x11, VK_SHIFT=0x10, VK_LWIN=0x5B, VK_RWIN=0x5C, VK_APPS=0x5D
        # Left/Right variants: VK_LSHIFT=0xA0, VK_RSHIFT=0xA1, VK_LCONTROL=0xA2, VK_RCONTROL=0xA3, VK_LMENU=0xA4, VK_RMENU=0xA5
        # KEYEVENTF_KEYUP = 0x0002
        for vk in (0x12, 0x11, 0x10, 0x5B, 0x5C, 0x5D, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5):
            user32.keybd_event(vk, 0, 2, 0)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Default config / PERSONA
# ---------------------------------------------------------------------------

PERSONA = """You are an answer-key assistant for general-education multiple-choice questions: US/world history, English literature, basic math, general science, introductory social science, and similar survey subjects.

Read all options carefully before deciding. Compare the options against each other to identify the most accurate and contextually correct one, correcting any minor OCR spelling errors mentally.

You MUST start your response with the '{' character immediately. Output ONLY valid JSON in this exact format (do not write any conversational intro, prose, explanation, or markdown backticks):

{"answer": "<letter>) <answer text>"}

Where <letter> is one of A, B, C, D, E and <answer text> is the complete text of the correct option. The JSON must be the entire response."""

DEFAULT_CONFIG: dict[str, Any] = {
    "fixed_ocr_region": None,
    "scroll_region": None,
    "auto_scroll_region": None,
    "hotkey_ocr": "ctrl+shift+z",
    "hotkey_reselect": "ctrl+alt+z",
    "hotkey_scroll": "alt+shift+z",
    "hotkey_set_scroll": "alt+shift+x",
    "hotkey_auto_scroll": "alt+shift+a",
    "hotkey_set_auto_scroll": "alt+shift+s",
    "hotkey_clip": "win+shift+c",
    "hotkey_clear": "win+shift+v",
    "hotkey_reshow": "win+shift+x",
    "overlay_timeout_sec": 60,
    "overlay_font_size": 18,
    "max_overlay_width_px": 620,
    "max_overlay_height_px": 280,
    "tesseract_path": r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    "tesseract_psm": 6,
    "ocr_min_confidence": 75.0,
    "ocr_min_option_markers": 3,
    "doppler_project": "ichabod",
    "doppler_config": "dev",
    "system_prompt": PERSONA,
    "max_tokens": 1000,
    "temperature": 0.2,
    "endpoints": [
        {
            "name": "opencode-go-longcat-free",
            "url": "https://opencode.ai/zen/go/v1/chat/completions",
            "model": "longcat-2.5-preview-free",
            "key_env": ["OPENCODEGOTAGRADER"],
            "timeout_sec": 30,
            "max_retries": 0,
            "supports_response_format": False,
            "supports_vision": False,
        },
        {
            "name": "opencode-go-mimo-v2.6-flash",
            "url": "https://opencode.ai/zen/go/v1/chat/completions",
            "model": "mimo-v2.6-flash",
            "key_env": ["OPENCODEGOTAGRADER"],
            "timeout_sec": 30,
            "max_retries": 0,
            "supports_response_format": False,
            "supports_vision": False,
        },
        {
            "name": "yolo-auto-flash",
            "url": "https://yolo-auto.com/v1/chat/completions",
            "model": "qwen3.8-flash",
            "key_env": ["YOLO_AUTO_API_KEY", "YOLO_API_KEY"],
            "timeout_sec": 10,
            "max_retries": 1,
            "supports_response_format": False,
            "supports_vision": False,
        },
        {
            "name": "yolo-auto-small",
            "url": "https://yolo-auto.com/v1/chat/completions",
            "model": "yolo-small",
            "key_env": ["YOLO_AUTO_API_KEY", "YOLO_API_KEY"],
            "timeout_sec": 10,
            "max_retries": 1,
            "supports_response_format": False,
            "supports_vision": False,
        },
        {
            "name": "gemini-flash",
            "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            "model": "gemini-2.5-flash",
            "key_env": ["GEMINI_API_KEY", "GEMINI_FLASH_KEY_2"],
            "timeout_sec": 15,
            "max_retries": 1,
            "supports_response_format": True,
            "supports_vision": True,
        },
        {
            "name": "openai-gpt-4o-mini",
            "url": "https://api.openai.com/v1/chat/completions",
            "model": "gpt-4o-mini",
            "key_env": ["OPENAI_API_KEY"],
            "timeout_sec": 15,
            "max_retries": 1,
            "supports_response_format": True,
            "supports_vision": True,
        },
        {
            "name": "nvidia-llama-3.2-11b-vision",
            "url": "https://integrate.api.nvidia.com/v1/chat/completions",
            "model": "meta/llama-3.2-11b-vision-instruct",
            "key_env": ["NVIDIA_API_KEY"],
            "timeout_sec": 15,
            "max_retries": 1,
            "supports_response_format": True,
            "supports_vision": True,
        },
        {
            "name": "nvidia-phi-3-vision",
            "url": "https://integrate.api.nvidia.com/v1/chat/completions",
            "model": "microsoft/phi-3-vision-128k-instruct",
            "key_env": ["NVIDIA_API_KEY"],
            "timeout_sec": 15,
            "max_retries": 1,
            "supports_response_format": True,
            "supports_vision": True,
        },
        {
            "name": "nvidia-nemotron-lightning",
            "url": "https://integrate.api.nvidia.com/v1/chat/completions",
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
            "key_env": ["NVIDIA_API_KEY"],
            "timeout_sec": 15,
            "max_retries": 1,
            "supports_response_format": True,
            "supports_vision": False,
        },
        {
            "name": "omniroute-gemini-fast",
            "url": "http://192.168.1.200:20128/v1/chat/completions",
            "model": "gemini-2.5-flash",
            "key_env": ["OMNIROUTE_API_KEY"],
            "timeout_sec": 15,
            "max_retries": 0,
            "supports_response_format": False,
            "supports_vision": False,
        },
    ],
}


# ---------------------------------------------------------------------------
# Config loading + auto-migration from old primary/fallback format
# ---------------------------------------------------------------------------

def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        log(f"Created config template at {CONFIG_PATH}")

    cfg: dict[str, Any] = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    # Auto-migrate old primary/fallback format → flat endpoints list.
    # Must inspect the raw file (cfg), not the merged view: DEFAULT_CONFIG
    # always contains "endpoints", so checking merged would never migrate.
    if "endpoints" not in cfg and ("primary" in cfg or "fallback" in cfg):
        slots: list[dict] = []
        p = cfg.pop("primary", None)
        if p:
            slots.extend(p if isinstance(p, list) else [p])
        f = cfg.pop("fallback", None)
        if f:
            slots.extend(f if isinstance(f, list) else [f])
        cfg["endpoints"] = slots
        CONFIG_PATH.write_text(
            json.dumps({**DEFAULT_CONFIG, **cfg}, indent=2), encoding="utf-8"
        )
        log("Config migrated: primary/fallback → flat endpoints list")

    merged: dict[str, Any] = {**DEFAULT_CONFIG, **cfg}

    # OCR path setup with auto-detection fallback
    tpath = merged.get("tesseract_path", "")
    if tpath and os.path.exists(tpath):
        pytesseract.pytesseract.tesseract_cmd = tpath
    else:
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        found = shutil.which("tesseract")
        if not found:
            for cp in common_paths:
                if os.path.exists(cp):
                    found = cp
                    break
        if found:
            pytesseract.pytesseract.tesseract_cmd = found
            log(f"Auto-detected tesseract at {found!r}")
        else:
            log(f"tesseract not found at {tpath!r} or standard paths; OCR hotkey will fail")

    return merged


# ---------------------------------------------------------------------------
# Keyring — Doppler first, env var fallback
# ---------------------------------------------------------------------------

def doppler_get(project: str, key_name: str, config: str = "") -> Optional[str]:
    """Try to fetch a secret from Doppler. Returns None on any failure."""
    if not project:
        return None
    try:
        r = subprocess.run(
            ["doppler", "secrets", "get", "--plain", key_name, "-p", project]
            + (["-c", config] if config else []),
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            v = (r.stdout or "").strip()
            return v if v else None
        log(f"doppler non-zero for {key_name}: {r.stderr.strip()[:200]}")
    except FileNotFoundError:
        log("doppler CLI not on PATH; falling back to env var")
    except subprocess.TimeoutExpired:
        log(f"doppler call for {key_name} timed out")
    except Exception as e:
        log(f"doppler error for {key_name}: {e}")
    return None


_SECRET_CACHE: dict[str, Optional[str]] = {}


def get_api_key(cfg: dict[str, Any], key_name: str) -> Optional[str]:
    """Fetch and cache a secret without ever storing it inside cfg."""
    if key_name in _SECRET_CACHE:
        return _SECRET_CACHE[key_name]

    env_v = os.environ.get(key_name, "")
    value = env_v.strip() if env_v and env_v.strip() else None
    if not value:
        project = (cfg.get("doppler_project") or "").strip()
        config = (cfg.get("doppler_config") or "").strip()
        value = doppler_get(project, key_name, config)

    _SECRET_CACHE[key_name] = value
    return value


def endpoint_api_keys(cfg: dict[str, Any], ep: dict[str, Any]) -> list[str]:
    """Return all configured, available, de-duplicated keys for an endpoint."""
    key_envs = ep.get("key_env") or []
    if isinstance(key_envs, str):
        key_envs = [key_envs]

    keys: list[str] = []
    seen: set[str] = set()
    for key_name in key_envs:
        value = get_api_key(cfg, key_name)
        if value and value not in seen:
            keys.append(value)
            seen.add(value)
    return keys


def verify_all_keys(cfg: dict[str, Any]) -> None:
    """Fail fast if no endpoint has a key, without mutating config with secrets."""
    endpoints = cfg.get("endpoints", [])
    working = 0
    errors: list[str] = []
    for ep in endpoints:
        keys = endpoint_api_keys(cfg, ep)
        if keys:
            working += 1
            log(
                f"key OK for '{ep.get('name', '?')}' "
                f"({len(keys)} available; names={ep.get('key_env')})"
            )
        else:
            errors.append(f"  '{ep.get('name', '?')}': no key (tried {ep.get('key_env')})")
    if working == 0:
        raise RuntimeError("No endpoints have working API keys:\n" + "\n".join(errors))


def endpoint_supports_vision(ep: dict[str, Any]) -> bool:
    explicit = ep.get("supports_vision")
    if explicit is not None:
        return bool(explicit)
    url = str(ep.get("url", "")).lower()
    model = str(ep.get("model", "")).lower()
    return (
        "generativelanguage.googleapis.com" in url
        or "gpt-4o" in model
        or "claude" in model
    )


def config_for_disk(cfg: dict[str, Any]) -> dict[str, Any]:
    """Strip runtime-only fields recursively before persisting config."""
    def clean(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                k: clean(v)
                for k, v in value.items()
                if not str(k).startswith("_")
            }
        if isinstance(value, list):
            return [clean(v) for v in value]
        return value

    return clean(cfg)


# ---------------------------------------------------------------------------
# Answer extraction — streaming-safe; JSON-first, regex fallback
# ---------------------------------------------------------------------------

_ANSWER_RE = re.compile(
    r"\b([A-Ea-e])[)\.]\s*([^\n]+?)(?=\n|$|[A-Ea-e][)\.]\s|\Z)",
    re.IGNORECASE,
)


def extract_answer(text: str) -> Optional[str]:
    """Unified extractor that works on streaming partial output and reasoning traces.

    Priority:
      1. Complete or embedded JSON object  → parse and return 'answer' value
      2. Streaming partial JSON             → scan for "answer":"... char-by-char
      3. Regex fallback                     → find last or first <letter>) <text> pattern
    """
    if not text:
        return None

    s = text.strip()

    # 1. Search for any complete JSON object embedded in the text
    # (handles markdown fences, preambles, and conversational intros)
    for m_json in re.finditer(r'\{[^{}]*?"answer"[^{}]*?\}', s, re.DOTALL | re.IGNORECASE):
        candidate = m_json.group(0).strip()
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if str(k).lower() == "answer":
                        vv = str(v).strip()
                        if vv:
                            return vv
        except Exception:
            pass

    # If the text itself was fenced or has a code block, inspect it
    if "```" in s:
        fenced_matches = re.findall(r'```(?:json)?\s*([\s\S]*?)\s*```', s, re.IGNORECASE)
        for block in fenced_matches:
            b = block.strip()
            if b.startswith("{") and b.endswith("}"):
                try:
                    obj = json.loads(b)
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            if str(k).lower() == "answer":
                                vv = str(v).strip()
                                if vv:
                                    return vv
                except Exception:
                    pass

    # 2. Streaming partial — locate "answer":"... and decode char-by-char
    m = re.search(r'["\']answer["\']\s*:\s*(["\'])', text, re.IGNORECASE)
    if m:
        quote = m.group(1)
        i = m.end()
        chars: list[str] = []
        esc = False
        while i < len(text):
            c = text[i]
            if esc:
                if c == "n":
                    chars.append("\n")
                elif c == "\\":
                    chars.append("\\")
                elif c == "r":
                    chars.append("\r")
                elif c == "t":
                    chars.append("\t")
                else:
                    chars.append(c)
                esc = False
            elif c == "\\":
                esc = True
            elif c == quote:
                break
            else:
                chars.append(c)
            i += 1
        val = "".join(chars).strip()
        if val:
            return val

    # 3. Regex fallback (non-JSON endpoint output or reasoning trace)
    # Search for all pattern matches, favoring the last one if model reasoned first
    matches = list(_ANSWER_RE.finditer(text))
    if matches:
        last_m = matches[-1]
        ans = last_m.group(2).strip().rstrip('"} ,')
        return f"{last_m.group(1).upper()}) {ans}"

    return None


def clean_question_text(text: str) -> str:
    """Pre-clean OCR and clipboard question text without corrupting line structure.

    Operations:
      1. Strip Windows carriage returns (\r).
      2. Fix hyphenated word breaks across lines (e.g., 'con-\nstitution' -> 'constitution').
      3. Collapse excessive empty lines while preserving discrete option lines.
      4. Trim leading/trailing whitespace per line.
    """
    if not text:
        return text

    t = text.replace("\r", "").strip()
    # Join hyphenated words split across line breaks
    t = re.sub(r"(\w+)-\n+(\w+)", r"\1\2", t)
    # Normalize excessive blank lines (max 2 consecutive newlines)
    t = re.sub(r"\n{3,}", "\n\n", t)
    # Clean whitespace per line without collapsing lines into one another
    lines = [re.sub(r"[ \t]+", " ", line.strip()) for line in t.splitlines()]
    return "\n".join([line for line in lines if line])


# ---------------------------------------------------------------------------
# OCR / capture — one screen grab shared by text and vision paths
# ---------------------------------------------------------------------------

def capture_region_image(x: int, y: int, w: int, h: int) -> Image.Image:
    """Capture a region once so OCR and vision inspect the same frame."""
    return ImageGrab.grab(bbox=(x, y, x + w, y + h)).convert("RGB")


def image_to_base64(img: Image.Image) -> str:
    """Encode a captured frame for a vision-capable endpoint."""
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=False)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def ocr_image(img: Image.Image, psm: int = 6) -> tuple[str, float]:
    """OCR one image and return reconstructed text plus mean word confidence."""
    def run(psm_value: int) -> tuple[str, float]:
        data = pytesseract.image_to_data(
            img.convert("L"),
            config=f"--psm {psm_value}",
            output_type=pytesseract.Output.DICT,
        )
        lines: list[str] = []
        words: list[str] = []
        confidences: list[float] = []
        current_line: Optional[tuple[int, int, int]] = None

        for i, raw_word in enumerate(data.get("text", [])):
            word = str(raw_word).strip()
            if not word:
                continue
            key = (
                int(data["block_num"][i]),
                int(data["par_num"][i]),
                int(data["line_num"][i]),
            )
            if current_line is not None and key != current_line and words:
                lines.append(" ".join(words))
                words = []
            current_line = key
            words.append(word)
            try:
                conf = float(data["conf"][i])
                if conf >= 0:
                    confidences.append(conf)
            except (TypeError, ValueError):
                pass

        if words:
            lines.append(" ".join(words))
        text = "\n".join(lines).replace("\r", "").strip()
        confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return text, confidence

    text, confidence = run(psm)
    if not text and psm == 6:
        text, confidence = run(3)
        if text:
            log(f"OCR: psm6 empty; psm3 returned {len(text)} chars")
    return text, confidence


def assess_ocr_quality(
    text: str,
    confidence: float,
    cfg: dict[str, Any],
) -> tuple[bool, str]:
    """Decide whether OCR is trustworthy enough for text-only fast endpoints."""
    if not text.strip():
        return False, "empty OCR"

    min_conf = float(cfg.get("ocr_min_confidence", 75.0))
    if confidence < min_conf:
        return False, f"confidence {confidence:.1f} < {min_conf:.1f}"

    markers = {
        m.group(1).upper()
        for m in re.finditer(r"(?m)^\s*([A-Ea-e])[\)\.:]\s+", text)
    }
    min_markers = int(cfg.get("ocr_min_option_markers", 3))
    if len(text.splitlines()) >= 4 and len(markers) < min_markers:
        return False, f"only {len(markers)} option markers found"

    return True, f"confidence {confidence:.1f}, markers={len(markers)}"


def stitch_images(images: list[Image.Image]) -> Image.Image:
    """Stack captured viewports vertically without re-decoding JPEGs."""
    total_h = sum(img.height for img in images)
    max_w = max(img.width for img in images)
    combined = Image.new("RGB", (max_w, total_h), "white")
    y_offset = 0
    for img in images:
        combined.paste(img, (0, y_offset))
        y_offset += img.height
    return combined


def capture_scroll_region(
    x: int,
    y: int,
    w: int,
    h: int,
    scroll_pause: float = 0.5,
) -> tuple[Optional[str], Optional[str], float]:
    """Capture manual scroll segments using one grab per segment."""
    print("Scroll Capture Mode: Press ENTER to capture each segment, ESC to finish and process")
    segments: list[Image.Image] = []
    ocr_segments: list[str] = []
    confidences: list[float] = []

    try:
        while True:
            event = keyboard.read_event(suppress=True)
            if event.event_type != keyboard.KEY_DOWN:
                continue
            if event.name == "enter":
                img = capture_region_image(x, y, w, h)
                segments.append(img)
                txt, confidence = ocr_image(img)
                if txt.strip():
                    ocr_segments.append(txt.strip())
                if confidence > 0:
                    confidences.append(confidence)
                print(
                    f"  Captured segment {len(segments)} "
                    f"({len(txt)} chars, OCR confidence {confidence:.1f})"
                )
                time.sleep(scroll_pause)
            elif event.name == "esc":
                print("  Finished scroll capture")
                break
    except Exception as e:
        log(f"Scroll capture error: {e}")
        return None, None, 0.0

    if not segments:
        return None, None, 0.0

    try:
        combined = stitch_images(segments)
        combined_b64 = image_to_base64(combined)
        combined_ocr = clean_question_text("\n\n".join(ocr_segments))
        combined_confidence = (
            sum(confidences) / len(confidences) if confidences else 0.0
        )
        log(
            f"Scroll capture: {len(segments)} segments, "
            f"{combined.width}x{combined.height}px, "
            f"{len(combined_ocr)} chars OCR, confidence={combined_confidence:.1f}"
        )
        return combined_b64, combined_ocr, combined_confidence
    except Exception as e:
        log(f"Failed to stitch scroll capture: {e}")
        first_text = ocr_segments[0] if ocr_segments else ""
        first_conf = confidences[0] if confidences else 0.0
        return image_to_base64(segments[0]), first_text, first_conf


# ---------------------------------------------------------------------------
# LLMClient — persistent session, streaming endpoint chain, key rotation
# ---------------------------------------------------------------------------

class LLMClient:
    """OpenAI-compatible chat completions client.
    Streams deltas, rotates keys on 429/auth errors, chains endpoints on failure."""

    def __init__(self) -> None:
        self.session = requests.Session()

    def stream(
        self,
        text: str,
        cfg: dict[str, Any],
        on_chunk: Callable[[str, str], None],
        image_b64: Optional[str] = None,
        on_status: Optional[Callable[[str], None]] = None,
        prefer_vision: bool = False,
    ) -> tuple[str, str]:
        """Try configured order, promoting vision endpoints only when OCR is weak."""
        last_err: Any = "no endpoints configured"
        endpoints = list(cfg.get("endpoints", []))
        if prefer_vision and image_b64:
            endpoints = (
                [ep for ep in endpoints if endpoint_supports_vision(ep)]
                + [ep for ep in endpoints if not endpoint_supports_vision(ep)]
            )
        for ep in endpoints:
            name = ep.get("name", ep.get("url", "?"))
            if on_status:
                try:
                    on_status(name)
                except Exception:
                    pass
            try:
                result = self._stream_one(
                    text, cfg, ep, on_chunk,
                    image_b64=image_b64,
                    prefer_vision=prefer_vision,
                )
                log(f"LLM: '{name}' returned {len(result)} chars")
                if not extract_answer(result):
                    raise RuntimeError(f"Model returned invalid/incomplete response: {result!r}")
                
                # Endpoint promotion disabled to ensure fast primary models stay first

                return result, name
            except Exception as e:
                log(f"LLM: '{name}' failed: {e}")
                last_err = e
        raise RuntimeError(f"All endpoints failed. Last error: {last_err}")

    def _stream_one(
        self,
        text: str,
        cfg: dict[str, Any],
        ep: dict[str, Any],
        on_chunk: Callable[[str, str], None],
        image_b64: Optional[str] = None,
        prefer_vision: bool = False,
    ) -> str:
        url = ep["url"]
        model = ep["model"]
        name = ep.get("name", url)
        max_retries = ep.get("max_retries", 1)
        is_deepseek = "deepseek" in model.lower() and "api.deepseek.com" in url.lower()

        api_keys = endpoint_api_keys(cfg, ep)
        if not api_keys:
            raise RuntimeError(f"no API keys available for '{name}'")

        supports_vision = endpoint_supports_vision(ep)
        prompt_text = "" if (prefer_vision and image_b64 and supports_vision) else text
        user_prompt_instruction = (
            (prompt_text + "\n\n" if prompt_text else "") +
            "Solve the multiple-choice question shown. Remember: Output ONLY the JSON object. "
            "Do not include any introduction or markdown. Start directly with '{'."
        )

        if image_b64 and supports_vision:
            user_content: Any = [
                {"type": "text", "text": user_prompt_instruction},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            ]
        else:
            user_content = user_prompt_instruction

        token_limit = max(int(cfg.get("max_tokens", 1000)), 2048)

        # Build payload (shared across all key attempts for this endpoint)
        payload: dict[str, Any] = {
            "model": model,
            "stream": True,
            "temperature": cfg.get("temperature", 0.2),
            "max_tokens": token_limit,
            "messages": [
                {"role": "system", "content": cfg["system_prompt"]},
                {
                    "role": "user",
                    "content": user_content,
                },
            ],
        }
        if ep.get("supports_response_format", True):
            payload["response_format"] = {"type": "json_object"}
        # DeepSeek reasoner-specific parameters
        if is_deepseek and "reasoner" in model.lower():
            payload["max_tokens"] = max(token_limit, 4096)
            payload.pop("response_format", None)
            payload.pop("temperature", None)

        # Base headers (auth filled in per-key below)
        base_headers: dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "TA-Grader/1.0",
        }
        if "openrouter.ai" in url.lower():
            base_headers["HTTP-Referer"] = "https://github.com/justinryan/ta-grader"
            base_headers["X-Title"] = "TA Grader"
        if "opencode.ai" in url.lower():
            # OpenCode Go routes and caches sessions using this documented header.
            base_headers["x-opencode-session"] = str(uuid.uuid4())
        if ep.get("headers"):
            base_headers.update(ep["headers"])

        last_err = "unknown"
        for api_key in api_keys:
            headers = {**base_headers, "Authorization": f"Bearer {api_key}"}

            for attempt in range(max_retries + 1):
                try:
                    # 3 s connect timeout; endpoint-specific read timeout for TTFT
                    timeout_sec = ep.get("timeout_sec", 15)
                    r = self.session.post(
                        url, json=payload, headers=headers,
                        stream=True, timeout=(3.0, float(timeout_sec)),
                    )
                    if r.status_code < 400:
                        # Track content and reasoning separately.
                        # Reasoning (DeepSeek thinking trace) is never shown to the user
                        # or returned as the final result — it would corrupt extraction.
                        accumulated_content = ""
                        seen_content = False
                        total_deadline = time.monotonic() + max(float(timeout_sec) * 2, 20.0)
                        idle_timeout = max(float(timeout_sec), 15.0)
                        last_activity = time.monotonic()
                        for raw_line in r.iter_lines():
                            now = time.monotonic()
                            if now > total_deadline:
                                log(f"LLM: '{name}' exceeded total stream deadline, failing over")
                                raise TimeoutError(f"Stream exceeded total deadline")
                            if now - last_activity > idle_timeout:
                                log(f"LLM: '{name}' stalled for {idle_timeout}s without data, failing over")
                                raise TimeoutError(f"Stream stalled without data")
                            if not raw_line:
                                continue
                            last_activity = now
                            line = raw_line.decode("utf-8", errors="replace")
                            if not line.startswith("data: "):
                                continue
                            data = line[6:].strip()
                            if data == "[DONE]":
                                break
                            try:
                                obj = json.loads(data)
                                if "error" in obj:
                                    raise RuntimeError(f"mid-stream error: {obj['error']}")
                                choices = obj.get("choices") or []
                                if not choices:
                                    continue
                                delta = choices[0].get("delta") or {}
                                content = delta.get("content") or ""
                                # reasoning_content (DeepSeek) is intentionally ignored:
                                # it leaks raw thinking tokens ({8228, <think>…) that
                                # break extract_answer and confuse the user.
                                if content:
                                    accumulated_content = (
                                        content if not seen_content
                                        else accumulated_content + content
                                    )
                                    seen_content = True
                                    on_chunk(accumulated_content, name)
                            except (json.JSONDecodeError, IndexError, TypeError):
                                pass
                        if accumulated_content:
                            return accumulated_content
                        last_err = "empty response from model"
                    elif r.status_code in (401, 403, 429):
                        last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                        log(f"LLM: '{name}' HTTP {r.status_code}, rotating key")
                        break  # try next key; no point retrying same key
                    elif r.status_code >= 500:
                        last_err = f"server error {r.status_code}"
                        log(f"LLM: '{name}' server error {r.status_code}")
                        if attempt < max_retries:
                            time.sleep(2 ** attempt)
                            continue
                        break
                    else:
                        last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                        break
                except requests.exceptions.Timeout:
                    last_err = f"timeout (TTFT/chunk delay exceeded {timeout_sec} s)"
                    log(f"LLM: '{name}' timed out")
                    if attempt < max_retries:
                        time.sleep(2 ** attempt)
                        continue
                    break
                except requests.exceptions.ConnectionError as e:
                    last_err = f"connection error: {str(e)[:120]}"
                    log(f"LLM: '{name}' connection error")
                    if attempt < max_retries:
                        time.sleep(2 ** attempt)
                        continue
                    break

        raise RuntimeError(f"all keys failed for '{name}': {last_err}")


# ---------------------------------------------------------------------------
# RegionSelector — fullscreen drag-to-select overlay
# ---------------------------------------------------------------------------

class RegionSelector:
    """Creates a fullscreen dim overlay for drag-select region picking.
    Must be used from the Tk main thread only."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root

    def select(self) -> Optional[tuple[int, int, int, int]]:
        """Block (via wait_window) until user selects a region or presses Escape.
        Returns (x, y, w, h) in screen coordinates, or None if cancelled/too small."""
        result: dict[str, Any] = {"box": None}

        sel = tk.Toplevel(self.root)
        sel.attributes("-fullscreen", True, "-alpha", 0.3, "-topmost", True)
        sel.overrideredirect(True)
        sel.configure(bg="grey")
        # NOTE: sel.title() intentionally omitted — overrideredirect windows have no title bar

        canvas = tk.Canvas(sel, cursor="cross", highlightthickness=0, bg="grey")
        canvas.pack(fill=tk.BOTH, expand=True)
        sw = sel.winfo_screenwidth()
        sh = sel.winfo_screenheight()

        # Track dark-band and outline canvas item IDs so we can redraw cleanly
        band_ids: list[int] = []
        outline_id: list[Optional[int]] = [None]
        cur = {"x1": 0, "y1": 0}

        def redraw(x1: int, y1: int, x2: int, y2: int) -> None:
            # Move existing items via coords() rather than delete+recreate —
            # avoids per-drag-frame canvas churn and reduces flicker.
            if outline_id[0] is None:
                band_ids.extend([
                    canvas.create_rectangle(0, 0, sw, y1, fill="black", outline=""),
                    canvas.create_rectangle(0, y2, sw, sh, fill="black", outline=""),
                    canvas.create_rectangle(0, y1, x1, y2, fill="black", outline=""),
                    canvas.create_rectangle(x2, y1, sw, y2, fill="black", outline=""),
                ])
                outline_id[0] = canvas.create_rectangle(x1, y1, x2, y2, outline="#00ff00", width=3)
            else:
                canvas.coords(band_ids[0], 0, 0, sw, y1)
                canvas.coords(band_ids[1], 0, y2, sw, sh)
                canvas.coords(band_ids[2], 0, y1, x1, y2)
                canvas.coords(band_ids[3], x2, y1, sw, y2)
                canvas.coords(outline_id[0], x1, y1, x2, y2)

        def on_press(_e: tk.Event) -> None:
            cur["x1"] = sel.winfo_pointerx()
            cur["y1"] = sel.winfo_pointery()
            redraw(cur["x1"], cur["y1"], cur["x1"], cur["y1"])

        def on_drag(_e: tk.Event) -> None:
            x1, x2 = sorted((cur["x1"], sel.winfo_pointerx()))
            y1, y2 = sorted((cur["y1"], sel.winfo_pointery()))
            redraw(x1, y1, x2, y2)

        def on_release(_e: tk.Event) -> None:
            px, py = sel.winfo_pointerx(), sel.winfo_pointery()
            x1, x2 = sorted((cur["x1"], px))
            y1, y2 = sorted((cur["y1"], py))
            sel.destroy()
            w, h = x2 - x1, y2 - y1
            result["box"] = (x1, y1, w, h) if w >= 10 and h >= 10 else None

        def on_escape(_e: tk.Event) -> None:
            sel.destroy()
            result["box"] = None

        canvas.bind("<Button-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        sel.bind("<Escape>", on_escape)
        sel.focus_force()
        sel.wait_window()
        release_modifier_keys()
        return result["box"]


# ---------------------------------------------------------------------------
# OverlayManager — floating answer panels
# ---------------------------------------------------------------------------

class OverlayManager:
    """Manages all floating answer overlays.
    All public methods must be called from the Tk main thread,
    except record_last() which is thread-safe (plain list mutation)."""

    _LAST_ANSWERS_MAX = 5

    def __init__(self, root: tk.Tk, cfg: dict[str, Any]) -> None:
        self.root = root
        self.cfg = cfg
        self._overlays: list[tk.Toplevel] = []
        self._last_answers: list[tuple[str, int, int, str]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show(
        self,
        text: str,
        anchor_x: int,
        anchor_y: int,
        title: str = "TA Grader",
        fg: str = "#e0e0e0",
        bg: str = "#1e1e1e",
    ) -> tk.Toplevel:
        """Create and return a new floating overlay. Main thread only."""
        max_w = int(self.cfg.get("max_overlay_width_px", 620))
        max_h = int(self.cfg.get("max_overlay_height_px", 280))
        font_size = int(self.cfg.get("overlay_font_size", 18))

        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.attributes("-topmost", True)
        overlay.title(title)

        frame = tk.Frame(overlay, bg=bg, bd=1, relief="solid")
        frame.pack()

        inner = tk.Frame(frame, bg=bg)
        inner.pack(fill="both", expand=True, padx=2, pady=2)

        tw = tk.Text(
            inner, wrap="word", bg=bg, fg=fg,
            font=("Segoe UI", font_size, "bold"),
            bd=0, highlightthickness=0,
            padx=10, pady=8,
            height=3, width=30,
            cursor="arrow", takefocus=0,
        )
        sb = tk.Scrollbar(
            inner, orient="vertical", command=tw.yview,
            bg=bg, troughcolor=bg, activebackground="#888888",
            width=14, bd=1, relief="ridge",
        )
        tw.configure(yscrollcommand=sb.set)
        tw.tag_configure("answer", font=("Segoe UI", font_size, "bold"))

        # Read-only: allow select/copy/navigate; block edits
        def _block_edits(e: tk.Event) -> Optional[str]:
            ctrl = (e.state & 0x0004) != 0
            if ctrl and e.keysym.lower() in ("c", "a"):
                return None
            if e.keysym in ("Up", "Down", "Left", "Right", "Prior", "Next", "Home", "End"):
                return None
            return "break"

        tw.bind("<KeyPress>", _block_edits)
        tw.bind("<<Paste>>", lambda e: "break")
        tw.bind("<<Cut>>", lambda e: "break")
        tw.bind("<<Clear>>", lambda e: "break")
        tw.bind("<Button-2>", lambda e: "break")  # disable middle-click paste

        tw.insert("1.0", text, "answer")
        tw.pack(side="left", fill="both", expand=True)

        overlay.update_idletasks()
        w = min(tw.winfo_reqwidth() + 4, max_w)
        h = min(tw.winfo_reqheight() + 4, max_h)
        # Only show scrollbar when content actually overflows
        if tw.winfo_reqheight() > max_h:
            sb.pack(side="right", fill="y")

        x, y = self._place(anchor_x, anchor_y, w, h)
        overlay.geometry(f"{w}x{h}+{x}+{y}")

        overlay.bind("<FocusOut>", lambda _e: self._destroy(overlay))
        timeout_ms = int(self.cfg.get("overlay_timeout_sec", 60)) * 1000
        overlay._timeout_id = overlay.after(timeout_ms, lambda: self._destroy(overlay))  # type: ignore[attr-defined]

        # Attach internals for in-place updates
        overlay._tw = tw          # type: ignore[attr-defined]
        overlay._max_w = max_w    # type: ignore[attr-defined]
        overlay._max_h = max_h    # type: ignore[attr-defined]
        overlay._sb = sb          # type: ignore[attr-defined]
        overlay._anchor = (anchor_x, anchor_y)  # type: ignore[attr-defined]

        self._overlays.append(overlay)
        return overlay

    def update(self, overlay: tk.Toplevel, new_text: str) -> None:
        """Update overlay text in-place (no destroy/recreate). Main thread only."""
        try:
            if not overlay.winfo_exists():
                return
            tw: tk.Text = overlay._tw  # type: ignore[attr-defined]
            tw.delete("1.0", "end")
            tw.insert("1.0", new_text, "answer")
            tw.yview_moveto(0)

            overlay.update_idletasks()
            w = min(tw.winfo_reqwidth() + 4, overlay._max_w)  # type: ignore[attr-defined]
            h = min(tw.winfo_reqheight() + 4, overlay._max_h)  # type: ignore[attr-defined]

            # Show/hide scrollbar depending on whether content now overflows
            sb = overlay._sb  # type: ignore[attr-defined]
            if tw.winfo_reqheight() > overlay._max_h:  # type: ignore[attr-defined]
                sb.pack(side="right", fill="y")
            else:
                sb.pack_forget()

            ax, ay = overlay._anchor  # type: ignore[attr-defined]
            x, y = self._place(ax, ay, w, h)
            overlay.geometry(f"{w}x{h}+{x}+{y}")

            # Reset the auto-dismiss timer so it counts from when the answer arrived,
            # not from when "Thinking…" was first shown.
            try:
                overlay.after_cancel(overlay._timeout_id)  # type: ignore[attr-defined]
            except Exception:
                pass
            timeout_ms = int(self.cfg.get("overlay_timeout_sec", 60)) * 1000
            overlay._timeout_id = overlay.after(timeout_ms, lambda: self._destroy(overlay))  # type: ignore[attr-defined]
        except tk.TclError:
            pass

    def clear_all(self) -> None:
        """Destroy all active overlays. Main thread only."""
        for o in list(self._overlays):
            self._destroy(o)

    def record_last(self, answer: str, ax: int, ay: int, endpoint: str) -> None:
        """Record a completed answer for re-show. Thread-safe (plain list mutation)."""
        self._last_answers.insert(0, (answer, ax, ay, endpoint))
        del self._last_answers[self._LAST_ANSWERS_MAX:]

    def reshow_last(self) -> None:
        """Re-show the most recent answer. Main thread only."""
        if not self._last_answers:
            ax, ay = self.root.winfo_pointerx(), self.root.winfo_pointery()
            self.show("(no recent answers)", ax, ay, fg="#ffd080")
            return
        answer, ax, ay, ep = self._last_answers[0]
        self.show(answer, ax, ay, title=f"re-shown ({ep})")
        log(f"re-shown answer ({len(answer)} chars) from '{ep}'")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _destroy(self, overlay: tk.Toplevel) -> None:
        try:
            if overlay in self._overlays:
                self._overlays.remove(overlay)
            if overlay.winfo_exists():
                overlay.destroy()
        except Exception:
            pass

    def _place(self, ax: int, ay: int, w: int, h: int) -> tuple[int, int]:
        """Position overlay above-right of anchor with screen clamping."""
        x = ax + 16
        y = ay - h - 16         # prefer above the anchor
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        if y < 0:
            y = ay + 16          # fall below if not enough room above
        if x + w > sw:
            x = max(0, sw - w)
        if y + h > sh:
            y = max(0, sh - h)
        if y < 0:
            y = 0
        return x, y


# ---------------------------------------------------------------------------
# StatusWindow — small always-on-top indicator
# ---------------------------------------------------------------------------

class StatusWindow:
    """Small always-on-top window showing hotkey reference and connection dot."""

    _BG = "#1e1e1e"
    _FG = "#e0e0e0"
    _ACCENT = "#a0c0ff"

    def __init__(self, root: tk.Tk, cfg: dict[str, Any]) -> None:
        self.win = tk.Toplevel(root)
        self.win.title(APP_NAME)
        self.win.attributes("-topmost", True)
        self.win.resizable(False, False)
        self.win.geometry("300x150+100+100")
        self.win.configure(bg=self._BG)

        tk.Label(
            self.win, text=f"{APP_NAME}  ●  running",
            font=("Segoe UI", 10, "bold"),
            bg=self._BG, fg=self._FG,
        ).pack(pady=(10, 2))

        lines = [
            f"  {cfg['hotkey_ocr']}  OCR (fixed region)",
            f"  {cfg.get('hotkey_reselect', 'ctrl+alt+z')}  Redefine region",
            f"  {cfg['hotkey_clip']}  Send clipboard",
            f"  {cfg['hotkey_clear']}  Clear overlays",
        ]
        if cfg.get("hotkey_reshow"):
            lines.append(f"  {cfg['hotkey_reshow']}  Re-show last")

        tk.Label(
            self.win, text="\n".join(lines),
            font=("Segoe UI", 9), justify=tk.LEFT,
            bg=self._BG, fg=self._ACCENT,
        ).pack()

        dot_canvas = tk.Canvas(
            self.win, width=20, height=14,
            highlightthickness=0, bg=self._BG,
        )
        dot_canvas.pack(pady=(4, 0))
        self._dot_canvas = dot_canvas
        self._dot_id = dot_canvas.create_oval(4, 2, 16, 14, fill="grey", outline="")

        self.win.bind("<Escape>", lambda _e: sys.exit(0))

    def set_dot(self, color: str) -> None:
        """Update the status indicator color. Main thread only."""
        if not self._dot_id or not self.win.winfo_exists():
            return
        try:
            self._dot_canvas.itemconfig(self._dot_id, fill=color)
            self.win.update_idletasks()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# App — orchestrates everything
# ---------------------------------------------------------------------------

def ensure_single_instance() -> Any:
    """Ensure only one instance of TA Grader runs at a time on Windows."""
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        mutex = kernel32.CreateMutexW(None, False, "Global\\TAGraderSingleInstanceMutex")
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            log("Another instance of TA Grader is already running. Exiting.")
            sys.exit(0)
        return mutex
    return None


class App:
    """Top-level application class. Creates all components and drives the main loop."""

    def __init__(self) -> None:
        enable_dpi_awareness()

        # Tk root must exist before any messagebox/Toplevel
        self.root = tk.Tk()
        self.root.withdraw()

        self._warn_admin()

        self.cfg = load_config()
        try:
            verify_all_keys(self.cfg)
        except RuntimeError as e:
            log(f"API key error: {e}")
            messagebox.showerror("API Key Not Found", str(e))
            sys.exit(1)

        self.fixed_region: Optional[tuple[int, int, int, int]] = (
            tuple(self.cfg["fixed_ocr_region"]) if self.cfg.get("fixed_ocr_region") else None
        )
        self.scroll_region: Optional[tuple[int, int, int, int]] = (
            tuple(self.cfg["scroll_region"]) if self.cfg.get("scroll_region") else None
        )
        self.auto_scroll_region: Optional[tuple[int, int, int, int]] = (
            tuple(self.cfg["auto_scroll_region"]) if self.cfg.get("auto_scroll_region") else None
        )

        self.llm = LLMClient()
        self.selector = RegionSelector(self.root)
        self.overlays = OverlayManager(self.root, self.cfg)
        self.status = StatusWindow(self.root, self.cfg)

        self._events: queue.Queue[str] = queue.Queue()
        self._install_hotkeys()
        self.root.after(100, self._pump)

    # ------------------------------------------------------------------
    # Startup helpers
    # ------------------------------------------------------------------

    def _warn_admin(self) -> None:
        if os.name != "nt":
            return
        try:
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                ok = messagebox.askyesno(
                    APP_NAME,
                    f"{APP_NAME} is not running as Administrator.\n\n"
                    "Global hotkeys may fail to capture keystrokes from other applications.\n"
                    "It is recommended to run as Administrator.\n\n"
                    "Run anyway?",
                )
                if not ok:
                    sys.exit(0)
        except Exception as e:
            log(f"admin check failed: {e}")

    def _install_hotkeys(self) -> None:
        cfg = self.cfg
        try:
            hotkey_str = cfg["hotkey_ocr"]
            # Register primary hotkey
            # If menu key is used, suppress=True prevents Windows from popping up the right-click context menu
            is_menu_key = hotkey_str.strip().lower() in ("menu", "apps", "application")
            suppress_key = True if is_menu_key else False

            try:
                keyboard.add_hotkey(hotkey_str, lambda: self._events.put("ocr"), suppress=suppress_key)
            except Exception as e:
                log(f"Failed to bind {hotkey_str}: {e}")

            # Also register apps/menu aliases so all Windows keyboard drivers catch it
            if is_menu_key:
                for alt_m in ("apps", "menu"):
                    if alt_m != hotkey_str.lower():
                        try:
                            keyboard.add_hotkey(alt_m, lambda: self._events.put("ocr"), suppress=True)
                            log(f"Registered complementary menu hotkey: {alt_m}")
                        except Exception:
                            pass

            # If user configured > or ., also bind the alternate (alt+. and alt+shift+. / alt+>)
            if ">" in hotkey_str or "period" in hotkey_str or "." in hotkey_str:
                for alt_k in ("alt+.", "alt+>", "alt+shift+."):
                    if alt_k != hotkey_str:
                        try:
                            keyboard.add_hotkey(alt_k, lambda: self._events.put("ocr"), suppress=False)
                            log(f"Registered complementary hotkey: {alt_k}")
                        except Exception:
                            pass

            if cfg.get("hotkey_reselect"):
                keyboard.add_hotkey(cfg["hotkey_reselect"], lambda: self._events.put("reselect"), suppress=False)
            if cfg.get("hotkey_scroll"):
                keyboard.add_hotkey(cfg["hotkey_scroll"], lambda: self._events.put("scroll"), suppress=False)
            if cfg.get("hotkey_set_scroll"):
                keyboard.add_hotkey(cfg["hotkey_set_scroll"], lambda: self._events.put("set_scroll"), suppress=False)
            if cfg.get("hotkey_auto_scroll"):
                keyboard.add_hotkey(cfg["hotkey_auto_scroll"], lambda: self._events.put("auto_scroll"), suppress=False)
            if cfg.get("hotkey_set_auto_scroll"):
                keyboard.add_hotkey(cfg["hotkey_set_auto_scroll"], lambda: self._events.put("set_auto_scroll"), suppress=False)
            keyboard.add_hotkey(cfg["hotkey_clip"], lambda: self._events.put("clip"), suppress=False)
            keyboard.add_hotkey(cfg["hotkey_clear"], lambda: self._events.put("clear"), suppress=False)
            if cfg.get("hotkey_reshow"):
                keyboard.add_hotkey(cfg["hotkey_reshow"], lambda: self._events.put("reshow"), suppress=False)
            log(
                f"hotkeys: {cfg['hotkey_ocr']}, {cfg.get('hotkey_reselect', '(none)')}, "
                f"{cfg['hotkey_clip']}, {cfg['hotkey_clear']}, {cfg.get('hotkey_reshow', '(none)')}, "
                f"{cfg.get('hotkey_scroll', '(none)')}, {cfg.get('hotkey_set_scroll', '(none)')}, "
                f"{cfg.get('hotkey_auto_scroll', '(none)')}, {cfg.get('hotkey_set_auto_scroll', '(none)')}"
            )
        except Exception as e:
            log(f"hotkey registration failed: {e}")
            messagebox.showerror(
                "Hotkey Error",
                f"Failed to register hotkeys:\n{e}\n\nRun as Administrator.",
            )
            sys.exit(1)

    # ------------------------------------------------------------------
    # Event pump — 100 ms tick on main thread
    # ------------------------------------------------------------------

    def _pump(self) -> None:
        try:
            while True:
                ev = self._events.get_nowait()
                release_modifier_keys()
                if ev == "ocr":
                    self._do_ocr()
                elif ev == "reselect":
                    self._do_reselect()
                elif ev == "clip":
                    self._do_clip()
                elif ev == "scroll":
                    self._do_scroll()
                elif ev == "set_scroll":
                    self._do_set_scroll()
                elif ev == "auto_scroll":
                    self._do_auto_scroll()
                elif ev == "set_auto_scroll":
                    self._do_set_auto_scroll()
                elif ev == "clear":
                    self.overlays.clear_all()
                elif ev == "reshow":
                    self.overlays.reshow_last()
                release_modifier_keys()
        except queue.Empty:
            pass
        self.root.after(100, self._pump)

    # ------------------------------------------------------------------
    # Hotkey handlers (main thread)
    # ------------------------------------------------------------------

    def _do_ocr(self) -> None:
        if not self.fixed_region:
            self._do_reselect()
            return
        x, y, w, h = self.fixed_region
        self._process_region(x, y, w, h)

    def _do_reselect(self) -> None:
        self.overlays.clear_all()
        box = self.selector.select()
        if not box:
            return
        self.fixed_region = box
        try:
            self.cfg["fixed_ocr_region"] = list(box)
            CONFIG_PATH.write_text(
                json.dumps(config_for_disk(self.cfg), indent=2),
                encoding="utf-8",
            )
            log(f"Saved fixed OCR region {box} to config.json")
        except Exception as e:
            log(f"Failed to save fixed OCR region to config.json: {e}")

        x, y, w, h = box
        self._process_region(x, y, w, h)

    def _do_set_scroll(self) -> None:
        """Define a dedicated manual-scroll region for tall questions."""
        self.overlays.clear_all()
        box = self.selector.select()
        if not box:
            return
        self.scroll_region = box
        try:
            self.cfg["scroll_region"] = list(box)
            CONFIG_PATH.write_text(
                json.dumps(config_for_disk(self.cfg), indent=2),
                encoding="utf-8",
            )
            log(f"Saved scroll region {box} to config.json")
            self.overlays.show(
                f"Scroll region set: {box}\n\n"
                f"Press {self.cfg.get('hotkey_scroll', 'alt+shift+z')} to capture.",
                box[0] + box[2],
                box[1],
                fg="#80ff80",
            )
        except Exception as e:
            log(f"Failed to save scroll region to config.json: {e}")

    def _do_scroll(self) -> None:
        """Manual scroll capture: ENTER each segment, ESC to finish."""
        region = self.scroll_region or self.fixed_region
        if not region:
            self._do_reselect()
            return

        x, y, w, h = region
        self.overlays.clear_all()
        anchor_x, anchor_y = x + w, y
        placeholder = self.overlays.show(
            "Scroll Capture: Press ENTER to capture each segment, ESC to finish",
            anchor_x,
            anchor_y,
            fg="#ffd080",
        )
        self.status.set_dot("#ffaa00")

        def worker() -> None:
            combined_b64, combined_text, combined_confidence = capture_scroll_region(
                x, y, w, h
            )
            if not combined_b64:
                self.root.after(
                    0,
                    lambda: self.overlays.update(placeholder, "Scroll capture cancelled"),
                )
                self.root.after(0, lambda: self.status.set_dot("#c04040"))
                return

            combined_text = clean_question_text(combined_text or "")
            ocr_usable, ocr_reason = assess_ocr_quality(
                combined_text,
                combined_confidence,
                self.cfg,
            )
            prefer_vision = not ocr_usable
            log(
                f"Scroll OCR quality: usable={ocr_usable} ({ocr_reason}); "
                f"strategy={'vision-first' if prefer_vision else 'text-first'}"
            )

            self.root.after(0, lambda: self.overlays.update(placeholder, "Thinking…"))
            self.root.after(0, lambda: self.status.set_dot("#808080"))
            threading.Thread(
                target=self._run_llm,
                args=(
                    combined_text,
                    placeholder,
                    anchor_x,
                    anchor_y,
                    combined_b64,
                    prefer_vision,
                ),
                daemon=True,
            ).start()

        threading.Thread(target=worker, daemon=True).start()

    def _do_set_auto_scroll(self) -> None:
        """Define X-axis bounds for automatic full-height scroll capture."""
        self.overlays.clear_all()
        box = self.selector.select()
        if not box:
            return

        x, _y, w, _h = box
        region = (x, 0, w, self.root.winfo_screenheight())
        self.auto_scroll_region = region
        try:
            self.cfg["auto_scroll_region"] = list(region)
            CONFIG_PATH.write_text(
                json.dumps(config_for_disk(self.cfg), indent=2),
                encoding="utf-8",
            )
            log(f"Saved auto-scroll X bounds: left={x}, right={x+w}")
            self.overlays.show(
                f"Auto-scroll X bounds set: left={x}, right={x+w}\n\n"
                f"Press {self.cfg.get('hotkey_auto_scroll', 'alt+shift+a')} "
                "to auto-capture full height.",
                x + w,
                50,
                fg="#80ff80",
            )
        except Exception as e:
            log(f"Failed to save auto-scroll region to config.json: {e}")

    def _do_auto_scroll(self) -> None:
        """Auto-scroll with Page Down until repeated frames indicate the bottom."""
        if not self.auto_scroll_region:
            self._do_set_auto_scroll()
            return

        x, _y, w, _h = self.auto_scroll_region
        screen_h = self.root.winfo_screenheight()
        self.overlays.clear_all()
        anchor_x, anchor_y = x + w, 50

        placeholder = self.overlays.show(
            "Auto-Scroll Capture: Press ESC to cancel...",
            anchor_x,
            anchor_y,
            fg="#ffaa00",
        )
        self.status.set_dot("#ffaa00")

        def worker() -> None:
            import hashlib

            segments: list[Image.Image] = []
            ocr_segments: list[str] = []
            confidences: list[float] = []
            last_img_hash: Optional[bytes] = None
            no_change_count = 0
            max_no_change = 3
            max_segments = 50

            try:
                for _ in range(max_segments):
                    if keyboard.is_pressed("esc"):
                        log("Auto-scroll cancelled by user")
                        break

                    img = capture_region_image(x, 0, w, screen_h)
                    segments.append(img)

                    txt, confidence = ocr_image(
                        img,
                        int(self.cfg.get("tesseract_psm", 6)),
                    )
                    if txt.strip():
                        ocr_segments.append(txt.strip())
                    if confidence > 0:
                        confidences.append(confidence)

                    log(
                        f"Auto-scroll: captured segment {len(segments)} "
                        f"({len(txt)} chars, OCR confidence={confidence:.1f})"
                    )

                    # MD5 is only a cheap frame-equality fingerprint here, not security.
                    img_hash = hashlib.md5(img.tobytes()).digest()
                    if img_hash == last_img_hash:
                        no_change_count += 1
                        if no_change_count >= max_no_change:
                            log(
                                "Auto-scroll: reached bottom "
                                f"(no change for {max_no_change} captures)"
                            )
                            break
                    else:
                        no_change_count = 0
                    last_img_hash = img_hash

                    keyboard.send("page down")
                    time.sleep(0.6)

                if not segments:
                    self.root.after(
                        0,
                        lambda: self.overlays.update(
                            placeholder, "Auto-scroll capture cancelled"
                        ),
                    )
                    self.root.after(0, lambda: self.status.set_dot("#c04040"))
                    return

                combined = stitch_images(segments)
                combined_b64 = image_to_base64(combined)
                combined_ocr = clean_question_text("\n\n".join(ocr_segments))
                combined_confidence = (
                    sum(confidences) / len(confidences) if confidences else 0.0
                )

                ocr_usable, ocr_reason = assess_ocr_quality(
                    combined_ocr,
                    combined_confidence,
                    self.cfg,
                )
                prefer_vision = not ocr_usable
                log(
                    f"Auto-scroll: {len(segments)} segments, "
                    f"{combined.width}x{combined.height}px, "
                    f"{len(combined_ocr)} chars OCR, "
                    f"confidence={combined_confidence:.1f}; "
                    f"quality={ocr_reason}; "
                    f"strategy={'vision-first' if prefer_vision else 'text-first'}"
                )

                self.root.after(
                    0, lambda: self.overlays.update(placeholder, "Thinking…")
                )
                self.root.after(0, lambda: self.status.set_dot("#808080"))
                threading.Thread(
                    target=self._run_llm,
                    args=(
                        combined_ocr,
                        placeholder,
                        anchor_x,
                        anchor_y,
                        combined_b64,
                        prefer_vision,
                    ),
                    daemon=True,
                ).start()

            except Exception as e:
                log(f"Auto-scroll error: {e}")
                self.root.after(
                    0,
                    lambda: self.overlays.update(
                        placeholder, f"Auto-scroll failed: {e}"
                    ),
                )
                self.root.after(0, lambda: self.status.set_dot("#c04040"))

        threading.Thread(target=worker, daemon=True).start()

    def _process_region(self, x: int, y: int, w: int, h: int) -> None:
        cfg = self.cfg
        self.overlays.clear_all()
        anchor_x, anchor_y = x + w, y

        captured: Optional[Image.Image] = None
        image_b64: Optional[str] = None
        try:
            captured = capture_region_image(x, y, w, h)
            image_b64 = image_to_base64(captured)
        except Exception as e:
            log(f"Image capture warning: {e}")

        text = ""
        ocr_confidence = 0.0
        if captured is not None:
            try:
                text, ocr_confidence = ocr_image(
                    captured,
                    int(cfg.get("tesseract_psm", 6)),
                )
                text = clean_question_text(text)
            except Exception as e:
                log(f"OCR warning: {e}")

        ocr_usable, ocr_reason = assess_ocr_quality(text, ocr_confidence, cfg)
        prefer_vision = bool(image_b64) and not ocr_usable
        log(
            f"OCR quality: usable={ocr_usable} ({ocr_reason}); "
            f"strategy={'vision-first' if prefer_vision else 'text-first'}"
        )

        if not text.strip() and not image_b64:
            self.overlays.show(
                f"No content found in region.\n\n"
                f"Press {cfg.get('hotkey_reselect', 'alt+q')} to redefine region.",
                anchor_x,
                anchor_y,
                fg="#ffd080",
            )
            return

        placeholder = self.overlays.show(
            "Thinking…",
            anchor_x,
            anchor_y,
            fg="#a0c0ff",
        )
        self.status.set_dot("#808080")
        threading.Thread(
            target=self._run_llm,
            args=(
                text,
                placeholder,
                anchor_x,
                anchor_y,
                image_b64,
                prefer_vision,
            ),
            daemon=True,
        ).start()

    def _do_clip(self) -> None:
        self.overlays.clear_all()  # dismiss any previous answer before starting a new query
        anchor_x, anchor_y = self.root.winfo_pointerx(), self.root.winfo_pointery()

        try:
            text = self.root.clipboard_get()
            text = clean_question_text(text)
        except tk.TclError:
            text = ""

        if not text.strip():
            self.overlays.show("Clipboard is empty.", anchor_x, anchor_y, fg="#ffd080")
            return

        placeholder = self.overlays.show("Thinking…", anchor_x, anchor_y, fg="#a0c0ff")
        self.status.set_dot("#808080")
        threading.Thread(
            target=self._run_llm,
            args=(text, placeholder, anchor_x, anchor_y, None),
            daemon=True,
        ).start()

    # ------------------------------------------------------------------
    # Shared LLM worker — runs on a background thread
    # ------------------------------------------------------------------

    def _run_llm(
        self,
        text: str,
        placeholder: tk.Toplevel,
        anchor_x: int,
        anchor_y: int,
        image_b64: Optional[str] = None,
        prefer_vision: bool = False,
    ) -> None:
        """Background thread. Uses root.after() for all Tk operations."""
        def on_chunk(accumulated: str, _ep: str) -> None:
            answer = extract_answer(accumulated)
            if answer:
                self.root.after(0, lambda a=answer: self.overlays.update(placeholder, a))

        def on_status(ep_name: str) -> None:
            self.root.after(0, lambda: self.overlays.update(placeholder, f"Thinking… [{ep_name}]"))

        try:
            final_raw, endpoint_used = self.llm.stream(
                text,
                self.cfg,
                on_chunk,
                image_b64=image_b64,
                on_status=on_status,
                prefer_vision=prefer_vision,
            )
            final_answer = extract_answer(final_raw)
            if not final_answer:
                # Log the full raw response so we can diagnose extraction failures
                log(f"extract_answer failed. endpoint={endpoint_used!r} raw={final_raw!r}")
                final_answer = "⚠ No answer found.\n\nTry selecting a larger region or re-copying the text."
            log(
                f"Input question ({len(text)} chars, image={'yes' if image_b64 else 'no'}, "
                f"strategy={'vision-first' if prefer_vision else 'text-first'}):\n"
                f"{text}\n--> Answer from '{endpoint_used}': {final_answer}"
            )
            self.overlays.record_last(final_answer, anchor_x, anchor_y, endpoint_used)
            self.root.after(0, lambda a=final_answer: self.overlays.update(placeholder, a))
            self.root.after(0, lambda: self.status.set_dot("#40c040"))
        except Exception as e:
            log(f"LLM error: {e}")
            self.root.after(
                0, lambda: self.overlays.update(placeholder, f"Service unavailable — {e}")
            )
            self.root.after(0, lambda: self.status.set_dot("#c04040"))

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    _mutex = ensure_single_instance()
    log(f"=== {APP_NAME} started ===")
    App().run()
