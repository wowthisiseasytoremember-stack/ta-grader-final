# TA Grader Final

Canonical: https://github.com/wowthisiseasytoremember-stack/ta-grader-final

Windows live: `C:\Users\wowth\Desktop\TA-Grader`  
Linux: `/home/ichabod/Projects/ta-grader-final`

## Configuration

Text-only mode: `vision_enabled=false`. Screenshot OCR preserves the same frame with fixed-region scroll and autoscroll. Backend via Tailscale: `http://100.122.158.123:20128/v1/chat/completions`. The old LAN address `192.168.1.200` was unreachable from SurfaceBook. Override with env `OMNIROUTE_CHAT_URL`. Dashboard/login on Tailscale.

## Hotkeys

| Key | Action |
|---|---|
| `menu` / `apps` | Capture the fixed region |
| `alt+q` | Redefine the fixed region |
| `alt+c` | Send clipboard text |
| `alt+v` | Clear overlays |
| `alt+x` | Re-show the last answer |
| `alt+shift+x` | Set the manual scroll region |
| `alt+shift+z` | Capture manual scroll segments |
| `alt+shift+s` | Set automatic scroll bounds |
| `alt+shift+a` | Capture with automatic scrolling |

Scroll captures run when their hotkeys are pressed. Menu/app aliases previously double-bound; fixed to single binding on release, debounce 1.5 s.

## Models (Fast Order)

| Model | Synth (s) |
|---|---|
| `github/gpt-4o-mini` | 0.70 |
| YOLO `qwen3.8-27b` | 2.28 |
| `github/gemini-3.7-flash` | 1.53 |
| `antigravity/gemini-3.1-flash-lite` | 1.41 |
| `antigravity/gemini-3.5-flash-lite` | 1.66 |

Each: 4 s read, 6 s budget, 0 retries, 60 s cooldown. Real app: 5 consecutive copilot-mini ~1 s, no duplicate. OllamaCloud monthly quota exhausted/disabled; OpenAI and NVIDIA 401/disabled; other legacy endpoints off.

## Tests

- 21 tests passed locally and on Windows (Python 3.14 on SurfaceBook).
- CI: 3.13 dependency-free tests.

## Usage

```bash
pip install keyboard requests pillow pytesseract
# Tesseract at Windows Program Files
Run_TA_Grader.bat          # elevated launcher
```

Each question tries models in this order and stops at the first valid complete JSON answer. Failed endpoints cool down for 60 seconds. No Opus or other Claude model is configured. Timings are observations, not guarantees; HTTP read timeouts are not strict total wall-clock caps.

Copy `.env.example` to `.env` and add credentials locally. Set `OMNIROUTE_CHAT_URL` for your router address. Preserve each machine’s existing `config.json` and `.env` during updates. Run `python -m unittest discover -s tests -v` and `python -m py_compile TA_Grader.py` to validate changes. See [SurfaceBook recovery](docs/SURFACEBOOK_RECOVERY_2026-10-02.md) and [repository consolidation](docs/REPOSITORY_CONSOLIDATION.md).
