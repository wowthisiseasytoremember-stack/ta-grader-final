---
schema: agents-md/v1
project: ta-grader-final
initiative: career
family: education-tooling
what: >-
  Floating Windows answer-key overlay: captures a fixed region, manual scroll region,
  auto-scroll region, or clipboard, then answers through a provider-interleaved
  fast/fallback LLM chain (routing v3) and floats the parsed answer on screen.
goal: >-
  Answer every question with the fastest model that is not garbage. Knowledge-speed
  models first, deep reasoning last (algebra is rare); provider diversity so one
  quota outage cannot take the chain down.
status: active
stack: [python, tkinter, requests, tesseract-ocr, sse-streaming]
entrypoints:
  - TA_Grader.py
  - config.json
  - Run_TA_Grader.bat
updated: '2026-10-30 03:27 UTC'
---

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

## Endpoint priority (routing v3 — provider-interleaved, knowledge-speed first)
1. `omniroute-copilot-terra` (`no-think/github/gpt-5.6-terra`) — ~1.4s, Copilot Terra model, native vision, chemistry/math accuracy
2. `omniroute-copilot-gpt5.4-mini` (`github/gpt-5.4-mini`) — ~0.9–1.4s, 844 historical wins, native vision (re-enabled)
3. `omniroute-copilot-haiku` (`no-think/github/claude-haiku-4.5`) — ~0.9s, light mini quota fallback, native vision
4. `yolo-auto-flash` (`qwen3.8-flash` via `yolo-auto.com`) — ~1.2s, thinking disabled, free builder tier, independent provider
5. `opencode-deepseek-vision` (`deepseek-v4-flash-vision-exp` via OpenCode Go) — ~1.6s, native vision, independent provider
6. `omniroute-generalist` (`generalist` via OmniRoute) — 889 historical wins, most resilient Copilot alias
7. `omniroute-copilot-gemini-flash` (`github/gemini-3.7-flash`) — ~3.5s, unmetered, vision support
8. `omniroute-copilot-sonnet-5` (`github/claude-sonnet-5`) — deep reasoning fallback, `max_tokens` 1536
9. `omniroute-copilot-gpt5.4` (`github/gpt-5.4`) — full reasoning fallback, `max_tokens` 2048
10. `xai-grok-reasoning` (`grok-4.20-0309-reasoning`) — deep-reasoning emergency (algebra) rank, `max_tokens` 4096, 16s/22s timeouts

## Routing v3 — cooldown economics and provider scoping
- Goal: fastest model that is not garbage — knowledge-speed first, deep reasoning last (algebra is rare).
- Provider diversity is intentional: quota exhaustion or outage typically kills every model on one provider at once, so ranks alternate across provider backends (OmniRoute/Copilot, yolo-auto, OpenCode Go, xAI).
- Exponential per-endpoint cooldown: `base × 2^min(streak-1, 4)` (10s base, 160s cap), cleared on success.
- Connection failures, HTTP 429/401, and connect-timeouts cool **every sibling endpoint on the same origin** (provider-scoped: keys/quotas live on one backend). HTTP 5xx and stream stalls stay endpoint-local (model-pool scoped).
- Keyless endpoints (no resolvable API key) are skipped before the attempt loop so they never burn fallback attempts.
- If every eligible endpoint is cooling, the stalest endpoint is retried instead of hard-failing.
- Per-endpoint `max_tokens` overrides the global budget so deep ranks finish instead of emitting truncated JSON.
- Weak-OCR (vision-first) answers get a cross-check from one different-provider endpoint: agreement → `[confirmed by X]`; disagreement → tie-break via `escalation_endpoints` (sonnet-5, gpt5.4) with cooldowns ignored for that call.
- `_complete_answer` accepts strict JSON, fenced ```json blocks, and exactly one prose answer line; rejects truncated streams and option-echoes.

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
