# AGENTS.md — TA Grader

## What this is
Floating Windows answer-key overlay. It captures a fixed region, manual multi-segment scroll region, automatic Page-Down scroll region, or clipboard text; routes the question through a fast/fallback LLM chain; and displays the parsed answer in a floating overlay.

## Capture and routing policy
The current default is text-only (`vision_enabled=false`). Every capture mode still uses the same frame for OCR, but the LLM client removes image payloads and vision priority. The prior adaptive vision implementation is retained for explicit opt-in; current fast endpoints declare text-only capability.

## Endpoint priority
1. `omniroute-copilot-mini` — `github/gpt-4o-mini`
2. `yolo-auto-flash` — `qwen3.8-27b`
3. `omniroute-copilot-gemini-flash` — `github/gemini-3.7-flash`
4. `omniroute-antigravity-lite` — `antigravity/gemini-3.1-flash-lite`
5. `omniroute-antigravity-flash` — `antigravity/gemini-3.5-flash-lite`

Legacy endpoints remain disabled. Each active endpoint uses zero retries, a 4-second read timeout and a 6-second shared attempt budget; failures cool down for 60 seconds. Complete JSON is required before accepting an answer. HTTP read timeout behavior means the budget is not a strict wall-clock cap. No Claude or Opus models are configured.

OmniRoute URL may be overridden with `OMNIROUTE_CHAT_URL`. SurfaceBook uses Tailscale because the former LAN address was unreachable. Read README.md and docs/SURFACEBOOK_RECOVERY_2026-10-02.md before updating a live Windows copy. Preserve machine config and credentials.

## Hotkeys
- `menu` / `apps` — fixed region
- `alt+q` — redefine fixed region
- `alt+shift+x` — set manual scroll region
- `alt+shift+z` — manual scroll capture (ENTER each segment, ESC to finish)
- `alt+shift+s` — set auto-scroll X bounds
- `alt+shift+a` — automatic Page-Down capture
- `alt+c` — clipboard
- `alt+v` — clear overlays
- `alt+x` — re-show last answer

## Secret handling
- Read environment/.env first; use Doppler only as fallback.
- Cache secret values only in process memory, never inside `config.json`.
- Strip runtime-only fields before any region configuration is persisted.
- `.env`, `.env.*`, and `keys.cmd` are gitignored.
- Never put API values in launcher files, config, docs, issues, commits, or logs.

Expected names:
`YOLO_AUTO_API_KEY_2`, `YOLO_AUTO_API_KEY`, `YOLO_API_KEY`, `GEMINI_API_KEY`, `GEMINI_FLASH_KEY_2`,
`OPENAI_API_KEY`, `NVIDIA_API_KEY`, `OMNIROUTE_API_KEY`.

## Validation
- `tests/test_hotkeys.py` verifies Menu is bound once and queued OCR duplicates are debounced.
- `tests/test_routing.py` verifies complete responses, fallback, cooldown, URL overrides, and image removal in text-only mode.
- `tests/test_contract.py` protects endpoint order, vision declarations, multi-key rotation, secret handling, all scroll modes, adaptive routing, and the single-instance gate.
- `docs/OCR_VISION_AUDIT_2026-09-27.md` records benchmark evidence and rationale.

## Dependencies
```
pip install keyboard requests pillow pytesseract
```

Tesseract default:
`C:\\Program Files\\Tesseract-OCR\\tesseract.exe`.
