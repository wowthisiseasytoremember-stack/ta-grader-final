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
1. OpenCode Go `mimo-v2.6-flash` — fast text-first primary
2. OpenCode Go `longcat-2.5-preview-free` — free text-first fallback
3. `yolo-auto-flash` and remaining configured endpoints — later fallbacks

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
