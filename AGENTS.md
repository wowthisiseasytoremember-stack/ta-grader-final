---
schema: agents-md/v1
project: ta-grader-final
initiative: career
family: education-tooling
what: >-
  Floating Windows answer-key overlay: captures a fixed region, manual scroll region,
  auto-scroll region, or clipboard, then answers through a 5-rank sub-2-second
  multi-provider LLM chain with per-key quota cooldown memory.
goal: >-
  Answer every multiple-choice question in ~1 second using verified direct cloud and
  LAN endpoints with zero fragile middlemen, instant per-key quota rotation, and
  deterministic failover.
status: active
stack: [python, tkinter, requests, tesseract-ocr, sse-streaming]
entrypoints:
  - TA_Grader.py
  - config.json
  - Run_TA_Grader.bat
updated: '2026-11-01 21:38 UTC'
---

# AGENTS.md — TA Grader

## What this is
Floating Windows answer-key overlay. It captures a fixed region, manual multi-segment scroll region, automatic Page-Down scroll region, or clipboard text; routes the question through a 5-rank verified LLM chain; and displays the parsed answer in a floating overlay.

## Capture and routing policy
All screen capture modes use the same adaptive policy:

1. Capture each viewport once.
2. Reuse that exact frame for Tesseract OCR and vision input.
3. OCR returns text plus mean word confidence from one `image_to_data` pass.
4. Strong OCR (`>= 65.0` confidence and `>= 3` option markers) sends clean text to the primary chain.
5. Weak OCR promotes vision-capable endpoints first and omits the suspect OCR transcript so it cannot bias the visual read.

## Endpoint priority (Tabula Rasa Reset — 5 Verified Sub-2s Endpoints)
1. `gemini-flash-lite` (`gemini-3.1-flash-lite` via Google AI Studio Direct) — ~1.11s warm p50, 2 rotation keys (`GEMINI_API_KEY`, `GEMINI_FLASH_KEY_2`), native vision, native `json_object` response format, zero proxy dependency.
2. `opencode-haiku` (`claude-haiku-5-5` via OpenCode Go Direct) — ~1.47s warm p50, independent cloud provider (`OPENCODEGOTAGRADER`).
3. `omniroute-haiku` (`no-think/github/claude-haiku-4.5` via OmniRoute LAN `192.168.1.200:20128`) — ~0.82s warm p50, native vision.
4. `omniroute-terra` (`no-think/github/gpt-5.6-terra` via OmniRoute LAN `192.168.1.200:20128`) — ~1.14s warm p50, native vision, strong math/chemistry accuracy.
5. `xai-grok-fast` (`grok-4.20-0309-non-reasoning` via xAI Direct) — ~2.31s warm p50, independent cloud provider (`XAI_API_KEY`), native vision.

## Quota & Cooldown Mechanics
- **Per-Key Quota Cooldown (`_key_cooldown`):** When a key returns `HTTP 429`, that specific key is cooled for `60s` (`3600s` on `HTTP 401/403`) and the next key is tried immediately with a fresh timeout budget. Subsequent hotkey presses skip the cooling key automatically.
- **Per-Endpoint Cooldown (`_cooldown`):** If all keys on an endpoint fail, the endpoint cools for `15s` (`60s` on 429/401/403) and the next rank answers immediately.
- **Keepalive & TTFT Enforcement:** Synthetic `chatcmpl-keepalive` SSE frames are ignored, and streams must emit a real content token within `timeout_sec` (3.0s–4.5s).
- **Windows Proxy Bypass:** `session.trust_env = False` prevents Windows WPAD proxy discovery stalls.
- **Logs:** Written directly to `C:\Users\wowth\Desktop\TA-Grader\ta_grader.log` (with fallback to `%TEMP%\ta_grader.log`).

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
- Read environment/.env first; use Doppler (`ichabod` / `prd`) only as fallback.
- Cache secret values only in process memory, never inside `config.json`.
- Strip runtime-only fields before any region configuration is persisted.
- `.env`, `.env.*`, and `keys.cmd` are gitignored.
- Never put API values in launcher files, config, docs, issues, commits, or logs.

## Validation
- `tests/test_contract.py` protects endpoint order, vision declarations, multi-key rotation, per-key cooldowns, keepalive rejection, secret handling, all scroll modes, and the single-instance gate.
