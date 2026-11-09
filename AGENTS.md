---
schema: agents-md/v1
project: ta-grader-final
initiative: career
family: education-tooling
what: >-
  Floating Windows answer-key overlay: captures a fixed region, manual scroll region,
  auto-scroll region, or clipboard, then answers through an 8-rank sub-2-second
  multi-provider LLM chain with per-key quota cooldown memory and an answer-letter
  remap guard.
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
updated: '2026-11-09 08:20 UTC'
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

## Endpoint priority (Verified 8-Rank Chain, 2026-11-09)
1. `omniroute-haiku` (`no-think/github/claude-haiku-4.5` via OmniRoute Tailscale `100.122.158.123:20128`) — **rank 1 by user call: fast (~1.4s warm) + smart, near-zero Copilot burn**. Earlier "github router retired haiku-4.5" note was wrong — verified 200 three times 2026-11-09.
2. `xai-grok-fast` (`grok-4.20-0309-non-reasoning` via xAI Direct) — ~0.85s warm p50, proven workhorse (64/71 in the 2026-11-08 session).
3. `openrouter-direct` (`google/gemma-4-26b-a4b-it:free` via `openrouter.ai/api/v1`, key `OPENROUTERTAGRADER` — user's own account, no middle hop) — 200 @ ~1.5s from the app machine, $0, correct answer on probe 2026-11-09 08:20 UTC; text-only.
4. `omniroute-gemma-free` (same model via OmniRoute's shared OpenRouter accounts) — same-model insurance for the direct rank (and vice versa).
5. `opencode-mimo-flash` (`mimo-v2.6-flash` via OpenCode Go `inference/go`) — ~1.94s warm p50, native vision, native `json_object`. **LIVE again as of 2026-11-09 08:20 UTC: the Birkinbagh account key (`oc_sk_…`, vaulted as `OPENCODEGO_BIRKINBAGH`) probed HTTP 200 with a correct answer; it now fills `OPENCODEGOTAGRADER` in Doppler + `.env` (the old dead key never existed in Doppler — stale `.env` was the only source).**
6. `opencode-deepseek-flash` (`deepseek-v4.1-flash` via OpenCode Go, `thinking: disabled`) — ~1.06s warm p50. Same live key.
7. `opencode-glm-flash` (`glm-5.3-flash` via OpenCode Go) — ~1.20s warm p50. Same live key.
8. `opencode-free` (overflow; `deepseek-v4.1-flash-free` via `opencode.ai/zen/v1`) — bearer-less (`no_auth: true`), UA `opencode/2.2.5` + `x-opencode-client: opencode`; per-IP capped (429 `FreeUsageLimitError` when dry).
9. `gemini-2.5-flash` (Google AI Studio Direct) — demoted last: 0/30 across the 2026-11-08 log (high-demand 503s + timeouts); 3.2s/3.8s budgets; 2 rotation keys.

### Storable-but-unwired
- `TAGRADER` (NVIDIA NIM) in Doppler + `.env` — no rank yet; probe `integrate.api.nvidia.com` for a sub-2s grader model before wiring.

### Dead ends (probe-verified 2026-11-09 — don't wire these back without a re-probe)
- agy/antigravity ranks return 200 whose body is a deprecation notice — both agy accounts unusable for grading.
- `aug/*` → 502; `github/kimi-k3` → 400; `github/gemini-3.8-flash` → 200 with EMPTY content (trap); `oc/*` free → 429, `oc/*` paid → 402 billing.
- `no-think/github/claude-haiku-5.5` still 502 empty upstream (stale Copilot OAuth suspected; refresh pending).

## Quota & Cooldown Mechanics
- **Per-Key Quota Cooldown (`_key_cooldown`):** When a key returns `HTTP 429`, that specific key is cooled for `60s` and the next key is tried immediately with a fresh timeout budget. Bearer-less ranks feed sentinel `NO_AUTH_KEY` so the same bookkeeping applies.
- **Per-Endpoint Cooldown (`_cooldown`):** all keys failed → endpoint cools `15s`; `HTTP 429` → `60s`; **`HTTP 401/403` → `auth_fail_cooldown_sec` (1800s)** so dead credentials stop taxing every question.
- **Key-aware stalest retry:** when every endpoint is cooling, ranks whose keys are live are preferred over ranks parked with dead credentials.
- **OpenCode routing contract (2026-11):** requests to `opencode.ai` carry a stable per-run `ses_<64-hex>` `x-opencode-session` and `x-opencode-client: opencode`.
- **Answer-letter remap guard (`remap_answer_letter`):** before display, the returned "letter) text" is checked against the OCR'd option list; text-anchored re-mapping fixes OCR-debris letter/text mismatches. Conservative — unmatched shapes pass through unchanged and get logged.
- **OmniRoute ranks:** router `omniroute-ichabod` container on ichabod must be up (`docker start omniroute-ichabod`; port 20128).
- **Keepalive & TTFT Enforcement:** Synthetic `chatcmpl-keepalive` SSE frames are ignored, and streams must emit a real content token within `timeout_sec` (2.0s–3.2s).
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
