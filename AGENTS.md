# AGENTS.md — TA Grader

## What this is
Floating answer-key overlay for Windows. OCRs screen regions or clipboard text, sends to LLM, displays answer in a floating overlay. Hotkey-driven.

## Hotkeys
- `menu` (or `apps`) — OCR region (run question) — single bottom-row key, collision-free, no Alt/ChatGPT conflicts
- `alt+q` — Redefine OCR region (drag-select)
- `alt+c` — Send clipboard
- `alt+v` — Clear overlays
- `alt+x` — Re-show last answer

## Architecture
- `TA_Grader.py` — single-file app (Tk UI + LLM client + OCR)
- `config.json` — endpoints, hotkeys, UI settings
- `Run_TA_Grader.bat` — launcher with API keys (run as Admin)

## Endpoint chain (tried in order)
1. `gemini-flash` (`gemini-2.5-flash` direct) — primary (ultra fast & stable)
2. `omniroute-generalist` (`generalist` via `http://192.168.1.200:20128/v1/chat/completions`) — secondary
3. `omniroute-free2` (`FREE2` via `http://192.168.1.200:20128/v1/chat/completions`) — tertiary

## API keys
Stored in `keys.cmd` / `.env` / `Run_TA_Grader.bat` (inline for elevated Admin processes).
Source of truth: Doppler on ichabod (`doppler secrets get <KEY> -p ichabod`).

## Live Status (Audited 2026-09-04 02:24 UTC)
- OmniRoute: Active & Healthy (HTTP 200 via ichabod proxy)
- Mistral: Active (HTTP 200 / rotating backup)
- Gemini: Active & Healthy (HTTP 200)
- DeepSeek: Active & Healthy (HTTP 200)

## Dependencies
```
pip install keyboard requests pillow pytesseract
```
Tesseract OCR must be installed at `C:\Program Files\Tesseract-OCR\tesseract.exe`.
