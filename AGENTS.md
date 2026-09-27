# AGENTS.md — TA Grader

## What this is
Floating Windows answer-key overlay. It captures a selected screen region or clipboard text, routes the question through a fast/fallback LLM chain, and displays the parsed answer in a floating overlay.

## Current routing policy
Screen-region requests use **adaptive text-first / vision-first routing**:

- Capture the screen region once.
- Run one Tesseract pass that returns OCR text plus confidence.
- If OCR quality is acceptable, preserve the configured endpoint order so the fast text-only Yolo endpoints get first attempt.
- If OCR quality is weak, try vision-capable endpoints first and do not reinforce the vision model with the suspect OCR transcript.
- If preferred endpoints fail, the remainder of the endpoint chain is still available as fallback.
- Clipboard requests remain text-first because clipboard text is already exact.

Configured endpoint priority:
1. `yolo-auto-flash` — qwen3.8-flash, text-only
2. `yolo-auto-small` — yolo-small, text-only
3. `gemini-flash` — gemini-2.5-flash, vision-capable, two-key rotation
4. `openai-gpt-4o-mini` — vision-capable
5. `nvidia-llama-3.2-11b-vision` — vision-capable
6. `nvidia-phi-3-vision` — vision-capable
7. `nvidia-nemotron-lightning` — text-only
8. `omniroute-gemini-fast` — local text-only fallback

## Hotkeys
- `menu` / `apps` — run the fixed OCR region
- `alt+q` — redefine OCR region
- `alt+c` — send clipboard
- `alt+v` — clear overlays
- `alt+x` — re-show last answer

## Architecture
- `TA_Grader.py` — Tk UI, capture/OCR, endpoint routing, LLM client
- `config.json` — endpoint order/capabilities, OCR thresholds, hotkeys, UI settings
- `Run_TA_Grader.bat` — elevated Windows launcher
- `tests/test_contract.py` — static routing/security contract tests
- `docs/OCR_VISION_AUDIT_2026-09-27.md` — benchmark and routing rationale

## Secret handling
- Secrets must come from Doppler or environment variables.
- Runtime secret values are cached only in process memory, never inside the config object.
- Persisted config is recursively stripped of runtime-only fields.
- `.env`, `.env.*`, and `keys.cmd` are gitignored.
- Do not put API values in `Run_TA_Grader.bat`, config, docs, issues, commits, or logs.

Expected environment names:
`YOLO_AUTO_API_KEY`, `YOLO_API_KEY`, `GEMINI_API_KEY`, `GEMINI_FLASH_KEY_2`,
`OPENAI_API_KEY`, `NVIDIA_API_KEY`, `OMNIROUTE_API_KEY`.

## Dependencies
```
pip install keyboard requests pillow pytesseract
```

Tesseract OCR must be installed. The configured Windows default is:
`C:\\Program Files\\Tesseract-OCR\\tesseract.exe`.
