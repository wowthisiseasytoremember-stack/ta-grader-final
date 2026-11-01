# Changelog — TA Grader

## 2026-11-01 21:38 UTC — tabula rasa audit & architecture reset

Empirical log audit + live 40-endpoint benchmark drove a full simplification of `TA_Grader.py` and `config.json`:

### Fixed
- **Eliminated 46-second outage cascades:** Replaced 28 stale/disabled endpoints in `config.json` with 5 live-verified sub-2s endpoints across 4 independent backends:
  1. `gemini-flash-lite` (`gemini-3.1-flash-lite` direct, 1.11s warm p50, 2 keys, native vision)
  2. `opencode-haiku` (`claude-haiku-5-5` direct via OpenCode Go, 1.47s warm p50)
  3. `omniroute-haiku` (`no-think/github/claude-haiku-4.5` via LAN `192.168.1.200:20128`, 0.82s warm p50, native vision)
  4. `omniroute-terra` (`no-think/github/gpt-5.6-terra` via LAN `192.168.1.200:20128`, 1.14s warm p50, native vision)
  5. `xai-grok-fast` (`grok-4.20-0309-non-reasoning` direct via xAI, 2.31s warm p50, native vision)
- **Added per-key quota cooldown memory (`_key_cooldown`):** When a key returns `HTTP 429` (60s cooldown) or `401/403` (3600s cooldown), `LLMClient` remembers the exhausted key across subsequent questions and gives the next key in rotation a fresh timeout budget.
- **Blocked infinite `chatcmpl-keepalive` stream stalls:** `_stream_one` now ignores synthetic `keepalive` SSE frames and enforces a strict Time-To-First-Token (`ttft_deadline`) budget so hung proxy aliases fail in ~3s instead of 20s.
- **Bypassed Windows WPAD proxy stalls:** Set `self.session.trust_env = False` on `LLMClient`.
- **Fixed `clean_question_text` option corruption:** Recognized `a.)` / `b.)` / `c.)` (and normalized OCR'd `¢.)` / `©.)` to `c.)`) so multi-line Sophia options are never double-prefixed (`A) a.)`) or split into fake `D) parties` options.
- **Moved `ta_grader.log` to project directory:** `LOG_PATH` now writes directly to `C:\Users\wowth\Desktop\TA-Grader\ta_grader.log` (with fallback to `%TEMP%\ta_grader.log`).
- **Deleted ~450 lines of dead code:** Removed `_stream_copilot_sdk`, `_verify_vision_answer` multi-model consensus/tie-break loops, and exponential origin-streak cascades.

## 2026-10-30 03:05 UTC — routing v3: provider-interleaved chain, cooldown economics, vision consensus

Goal: fastest model that is not garbage. Log evidence (2,733 runs) drove every change.

### Changed
- Re-enabled `omniroute-copilot-gpt5.4-mini` (844 historical wins — fastest deep model; disabled during earlier drift was over-correction).
- Rebuilt the endpoint chain (10 ranks, `routing_version: 3`), provider-interleaved so quota exhaustion or outage on one backend cannot take the whole chain down: terra → gpt5.4-mini → haiku → yolo-auto-flash → opencode-deepseek-vision → omniroute-generalist (889 wins, most resilient) → gemini-flash → sonnet-5 → gpt5.4 → xai-grok-reasoning (last; deep-reasoning algebra emergency only).
- Moved `xai-grok-reasoning` to the last rank with a real budget (`max_tokens` 4096, 16s/22s timeouts) so it finishes when it is actually needed.
- Renamed the duplicate second gemini endpoint `omniroute-copilot-gemini-flash` → `omniroute-legacy-gemini-flash` (unique-name contract).
- Deep ranks got per-endpoint `max_tokens`: sonnet-5 1536, gpt5.4 2048, grok-reasoning 4096 (replaces the global 512 cap that produced truncated JSON).

### Routing economics (cooldown scoping)
- Exponential per-endpoint cooldown: `base × 2^min(streak-1, 4)` — 10s base, 160s cap, cleared on success.
- Provider-scoped failure sharing: connection failures and HTTP 429/401 cool every sibling endpoint on the same origin (keys/quotas live on one provider backend). HTTP 5xx and stream stalls stay endpoint-local (evidence: the generalist alias served while specific copilot models 503'd).
- Keyless endpoints are skipped before the attempt loop — an unresolvable key never burns fallback attempts.
- All-cooling falls back to retrying the stalest endpoint instead of hard-failing the question.

### Correctness
- `_complete_answer` now accepts strict JSON, fenced ```json blocks, and exactly one prose answer line, while rejecting truncated streams (JSON-shaped but unparseable) and option-echoes.

### Vision consensus (Tier C)
- Weak-OCR (vision-first) answers get one cross-check from a different-provider endpoint; agreement → `[confirmed by X]`; disagreement → tie-break via `escalation_endpoints` (sonnet-5, gpt5.4) with cooldowns ignored for that call.
- New config keys: `confirm_vision_answers` (default true), `escalation_endpoints`.

### Contract tests
- Added routing-v3 contract tests: cooldown/exponential backoff, provider scoping, keyless skip, stalest retry, vision consensus, per-endpoint token budgets, provider diversity in the top 5, deep-reasoning ranks at the back. 36 tests, all green.

## 2026-10-29 00:57 UTC — default model upgrade: copilot terra

### Changed
- Added `omniroute-copilot-terra` (`no-think/github/gpt-5.6-terra`) as first-pick model in `config.json`.
- Disabled non-functional `omniroute-copilot-gpt5.4-mini` endpoint.
- Updated `TA_Grader.py` to strip the `temperature` parameter when dispatching to Terra models (upstream GitHub Copilot requirement).
- Haiku retained at rank 2 as fast fallback.

## 2026-09-27 — routing/security audit

### Fixed
- Gemini two-key rotation now actually retains and tries both configured keys.
- API-key values are no longer inserted into the live config object and therefore cannot be persisted by region-setting actions.
- Environment/.env is checked before Doppler, avoiding needless secret-manager subprocess calls.
- Fixed region, manual scroll, and auto-scroll now capture each viewport once and reuse the same frame for OCR and vision.
- OCR returns confidence from the same Tesseract pass.
- Strong OCR keeps the normal fast text-first endpoint order.
- Weak OCR promotes vision-capable endpoints first and omits suspect OCR text from the vision prompt.
- Every endpoint now declares vision capability explicitly.
- 5xx, timeout, and connection failures now honor per-endpoint retry counts before failover.
- Streaming deadlines use a monotonic clock with tighter bounds.
- Duplicate single-instance mutex logic was removed.

### Preserved and integrated
- Manual scroll region: `alt+shift+x` to set, `alt+shift+z` to capture.
- Auto-scroll region: `alt+shift+s` to set X bounds, `alt+shift+a` to Page-Down capture.
- Both scroll modes now share the same adaptive OCR/vision routing policy.

### Hardened
- `.env.*` and `keys.cmd` are gitignored.
- Added a blank `.env.example`.
- Added CI/contract tests for syntax, endpoint order, explicit capabilities, key rotation, secret safety, capture architecture, and scroll-feature preservation.
- Removed stale status claims and secret-like fragments from the current changelog.

### Measured
Representative synthetic multiple-choice screenshots on the audit runner:
- JPEG + base64 preparation: about 1.5–2.7 ms median.
- Tesseract OCR: about 187–311 ms median.
- Clean 18–28 px text: 100% normalized OCR similarity.
- Tiny 13 px text: about 79% similarity with option-label corruption.

Image preparation is much cheaper locally than OCR, but image-only routing would skip the two highest-priority text-only endpoints. The implemented policy is therefore adaptive rather than OCR-only or image-only.

See `docs/OCR_VISION_AUDIT_2026-09-27.md`.

## 2026-10-06 — OpenCode Go primary and canonical repo

- Added OpenCode Go LongCat Preview Free as the first endpoint and MiMo-V2.6-Flash as the second.
- Added the `OPENCODEGOTAGRADER` Doppler secret name and explicit `dev` config lookup.
- Documented the Desktop shortcut checkout and retired the separate `Projects/ta-grader` implementation.

## 2026-10-14 — Math OCR regex, unlettered answer validation, YOLO Auto & multi-model fallback chain

### Fixed
- Fixed unlettered / pure numeric answer rejection bug in `_complete_answer`: questions displaying plain numerical radio options (e.g. `{"answer": "7"}`) were previously rejected by regex `^[A-Ea-e]\s*[.)]\s*\S`, raising a `RuntimeError` and applying a false cooldown penalty. Any non-empty JSON answer is now accepted.
- Lowered endpoint cooldown from 60s to 10s (`endpoint_cooldown_sec: 10`) to prevent temporary glitches from locking out top models.
- Strengthened math OCR detection in `assess_ocr_quality`: added inequality signs (`<`, `>`, `<=`, `>=`, `≤`, `≥`), absolute value bars (`|...|`), sequences (`sequence`), and algebraic terms to auto-promote vision-first routing when OCR is fragile.
- YOLO Auto optimization: configured `payload_overrides` with `chat_template_kwargs: {"enable_thinking": false}` on `qwen3.8-flash` via `yolo-auto.com` to bypass 40s reasoning stalls and return responses in ~1.2s.

### Routing Hierarchy (Quota-Optimized)
1. `omniroute-copilot-gpt5.4-mini` (`github/gpt-5.4-mini` via OmniRoute): ~0.9s–1.4s, low/unmetered Copilot quota, native vision.
2. `omniroute-copilot-haiku` (`no-think/github/claude-haiku-4.5` via OmniRoute): ~0.9s, light mini quota, native vision.
3. `yolo-auto-flash` (`qwen3.8-flash` via `yolo-auto.com`): ~1.2s, unlimited free builder plan, thinking disabled.
4. `omniroute-copilot-gemini-flash` (`github/gemini-3.7-flash` via OmniRoute Copilot): ~3.5s, unmetered, low reasoning, vision support.
5. `omniroute-copilot-sonnet-5` (`github/claude-sonnet-5` via OmniRoute): ~1.0s, deep reasoning fallback reserved for difficult questions to prevent quota burn.
6. `xai-grok-reasoning` (`grok-4.20-0309-reasoning` via xAI API): ~4.8s, reasoning model for complex formal logic.
7. `opencode-deepseek-vision` (`deepseek-v4-flash-vision-exp` via OpenCode Go): ~1.6s, native vision.
8. `omniroute-copilot-gpt5.4` (`github/gpt-5.4` via OmniRoute): ~3.1s, full reasoning model.



