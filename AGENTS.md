# AGENTS.md — TA Grader

## What this is
Floating Windows answer-key overlay. It captures a fixed region, manual multi-segment scroll region, automatic Page-Down scroll region, or clipboard text; routes the question through a fast/fallback LLM chain; and displays the parsed answer in a floating overlay.

## Capture and routing policy
All screen capture modes use the same adaptive policy:

1. Capture each viewport once.
2. Reuse that exact frame for Tesseract OCR and vision input.
3. OCR returns text plus mean word confidence from one `image_to_data` pass.
4. Strong OCR preserves normal endpoint priority, keeping the fast text-only Yolo endpoints first.
5. Weak OCR promotes vision-capable endpoints first.
6. Weak-OCR vision requests omit the suspect OCR transcript so it cannot bias the visual read.
7. Text-only endpoints remain fallbacks if vision providers fail.

Clipboard input remains text-first because it is already machine-readable.

## Endpoint priority
1. `omniroute-copilot-sonnet-5` (`github/claude-sonnet-5`) — ~1.0s, high accuracy across logic, math, & vision
2. `yolo-auto-flash` (`qwen3.8-flash` via `yolo-auto.com`) — ~1.2s, thinking disabled, free builder tier
3. `omniroute-copilot-gemini-flash` (`github/gemini-3.7-flash` via OmniRoute Copilot) — ~3.5s, unmetered, low reasoning, vision support
4. `xai-grok-reasoning` (`grok-4.20-0309-reasoning`) — ~4.8s, reasoning enabled for complex logic
5. `opencode-deepseek-vision` (`deepseek-v4-flash-vision-exp` via OpenCode Go) — ~1.6s, native vision
6. `omniroute-copilot-gpt5.4` (`github/gpt-5.4`) — ~3.1s full reasoning fallback

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
`YOLO_AUTO_API_KEY`, `YOLO_API_KEY`, `GEMINI_API_KEY`, `GEMINI_FLASH_KEY_2`,
`OPENAI_API_KEY`, `NVIDIA_API_KEY`, `OMNIROUTE_API_KEY`, `OPENCODEGOTAGRADER`.

OpenCode Go uses Doppler project `ichabod`, config `dev`. The Desktop shortcut copy also
loads its gitignored `.env` at startup; after changing that file, restart TA Grader.

## Validation
- `tests/test_contract.py` protects endpoint order, vision declarations, multi-key rotation, secret handling, all scroll modes, adaptive routing, and the single-instance gate.
- `docs/OCR_VISION_AUDIT_2026-09-27.md` records benchmark evidence and rationale.

## Dependencies
```
pip install keyboard requests pillow pytesseract
```

Tesseract default:
`C:\\Program Files\\Tesseract-OCR\\tesseract.exe`.
