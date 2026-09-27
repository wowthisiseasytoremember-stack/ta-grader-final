# AGENTS.md — TA Grader

## What this is
Floating Windows answer-key overlay. It captures a fixed screen region, a multi-segment scroll region, or clipboard text; routes the question through a fast/fallback LLM chain; and displays the parsed answer in a floating overlay.

## Routing policy
Screen captures use **adaptive text-first / vision-first routing**:

- Capture each screen frame once.
- Reuse that exact frame for Tesseract OCR and vision input.
- OCR returns text plus confidence from one `image_to_data` pass.
- If OCR quality is acceptable, preserve the configured endpoint order so fast text-only Yolo endpoints get first attempt.
- If OCR quality is weak, promote vision-capable endpoints first.
- Weak-OCR vision requests omit the suspect OCR transcript so it cannot bias the visual read.
- Text-only endpoints remain later fallbacks if vision providers fail.
- Clipboard requests remain text-first because clipboard text is already machine-readable.

The same policy applies to fixed-region and stitched scroll captures.

## Endpoint priority
1. `yolo-auto-flash` — qwen3.8-flash, text-only
2. `yolo-auto-small` — yolo-small, text-only
3. `gemini-flash` — gemini-2.5-flash, vision-capable, two-key rotation
4. `openai-gpt-4o-mini` — vision-capable
5. `nvidia-llama-3.2-11b-vision` — vision-capable
6. `nvidia-phi-3-vision` — vision-capable
7. `nvidia-nemotron-lightning` — text-only
8. `omniroute-gemini-fast` — local text-only fallback

## Hotkeys
- `menu` / `apps` — run fixed OCR region
- `alt+q` — redefine fixed OCR region
- `alt+shift+x` — set dedicated scroll region
- `alt+shift+z` — capture scroll segments (ENTER each segment, ESC to finish)
- `alt+c` — send clipboard
- `alt+v` — clear overlays
- `alt+x` — re-show last answer

## Architecture
- `TA_Grader.py` — Tk UI, fixed/scroll capture, OCR quality scoring, routing, LLM client
- `config.json` — endpoint order/capabilities, OCR thresholds, regions, hotkeys, UI settings
- `Run_TA_Grader.bat` — elevated Windows launcher
- `tests/test_contract.py` — static routing/security/scroll-preservation contract tests
- `docs/OCR_VISION_AUDIT_2026-09-27.md` — benchmark and routing rationale

## Secret handling
- Secrets come from environment/.env first, Doppler only as fallback.
- Runtime secret values are cached only in process memory, never inside the config object.
- Persisted config is recursively stripped of runtime-only fields.
- `.env`, `.env.*`, and `keys.cmd` are gitignored.
- Do not put API values in the launcher, config, docs, issues, commits, or logs.

Expected environment names:
`YOLO_AUTO_API_KEY`, `YOLO_API_KEY`, `GEMINI_API_KEY`, `GEMINI_FLASH_KEY_2`,
`OPENAI_API_KEY`, `NVIDIA_API_KEY`, `OMNIROUTE_API_KEY`.

## Dependencies
```
pip install keyboard requests pillow pytesseract
```

Tesseract OCR must be installed. Configured Windows default:
`C:\\Program Files\\Tesseract-OCR\\tesseract.exe`.
