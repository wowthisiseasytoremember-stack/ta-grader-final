# Changelog — TA Grader

## 2026-11-10 00:29 UTC — v5.4: audit fixes — disk-vision leak, DEFAULT_CONFIG refresh, docs
- Independent tabula-rasa audit (fresh-eyes subagent, read-only) verdict: core healthy — perfect file parity, 38 tests green both machines, no key material in the repo — with one real bug + doc rot.
- **M1 fixed (the bug):** `alt+i` session toggle could leak to disk — region saves (`_do_reselect`, `_do_set_scroll`, `_do_set_auto_scroll`) serialized `self.cfg` including the toggled `vision_enabled`, so a restart could boot vision-ON. All three now route through `_save_disk_config()`, which overwrites `vision_enabled` with `self._disk_vision` captured from disk at boot. Hotkey remains session-only by construction.
- **M2 fixed:** `DEFAULT_CONFIG` carried a stale 5-rank ghost chain (retired `gemini-3.1-flash-lite`, LAN `192.168.1.200` OmniRoute URL, duplicate hotkeys) — regenerated as a field-for-field mirror of the live 11-rank `config.json` (env names only, `auth_fail_cooldown_sec` included, `system_prompt` refs `PERSONA`). `PERSONA` itself was stale (old general-ed prompt) — aligned verbatim to the live config prompt. A parity check now fails on any drift (endpoints, budgets, scaled keys).
- **M4 fixed:** README routing-v3 rot (10 dead ranks, wrong repo/secret-names) rewritten to the live 11-rank list + Doppler `prd`.
- **Referer fixed:** `HTTP-Referer` pointed at a non-existent repo (`justinryan/ta-grader`) → `wowthisiseasytoremember-stack/ta-grader-final`.
- **M6 fixed:** changelog stamps reconciled to commit times (v5 00:45, v5.1 08:22, v5.2 08:43, hotfix 10:21, v5.3 23:38 UTC; v5.3 was nested under a stale header).
- Contract suite 22 tests (adds `_save_disk_config` exists / no direct `CONFIG_PATH.write_text(json.dumps(config_for_disk(self.cfg)))` in source / boot-time capture / DEFAULT_CONFIG-vs-live-chain / PERSONA-equals-live-prompt); all four suites green locally + on ichabod.
- **Same hour, user call:** `gemini-2.5-flash` (rank 11) disabled — `"enabled": false` in config/template/DEFAULT_CONFIG. It 404s every call (Google openai-compat drift), so it only burned 3.8s whenever the chain reached it. Entry kept for an easy re-enable after a model-path probe.

## 2026-11-09 23:38 UTC — v5.3: vision killed to opt-in
- User call after the 02:17:32 all-rank vision timeout: **vision-first is now opt-in and OFF by default**. `hotkey alt+i` toggles `vision_enabled` in-memory for the session (green/amber overlay announces state; never persists — every boot starts text-first).
- Defaults flipped in `DEFAULT_CONFIG` and all four read sites `.get("vision_enabled", False)`; the LLM strip-guard also uses the False fallback. Weak-OCR questions now answer text-first even when OCR is garbage (user accepts the quality tradeoff).
- Routing harness `make_cfg` sets `vision_enabled: True` so the vision-promotion tests still test the promotion path, not the off path.
- Contract suite 19 tests; all four suites green locally; config/template carry `vision_enabled: false` + `hotkey_vision: alt+i`.

## 2026-11-09 10:21 UTC — v5.2 hotfix: vision budgets widened for image payloads

The 02:17:32 vision-first question failed on every rank — the 2.2–2.6s TTFT budgets were tuned from text probes and don't fit image-payload latency.

- Vision ranks widened: Go/OpenRouter haiku 3.2/4.0, omniroute-haiku 2.8/3.6, grok 2.8/3.4, Go flashes 3.0/3.8 etc. Text-only ranks (gemma pair, opencode-free) keep tight budgets.
- Re-verified from the app's own vantage after the bump: Go haiku vision stream 200 @ ~1.08s; OpenRouter haiku vision stream 200 @ ~1.34s (image rendered on this machine, payload shape identical to the app's).
- Separate: `gemini-2.5-flash` now 404s (URL/model drift on Google's openai-compat path) — last rank, cosmetic until probed.
- Contract suite 18 tests; all four suites green locally.

## 2026-11-09 08:43 UTC — v5.2: haiku-5.5 double route (Go → OpenRouter) on top

User directive: haiku-5.5 first, attempted via OpenCode Go then via OpenRouter.

- **Miss vs catalog naming:** OpenCode Go's model list shows `claude-haiku-5-5` (hyphens). The dotted `claude-haiku-5.5` returns 400 "Model is unavailable" — archived here so nobody re-trips on it.
- **New rank 1 `opencodego-haiku5.5`:** `claude-haiku-5-5` via Go `inference/go`, key `OPENCODEGOTAGRADER` (Birkinbagh). Probed 3× — HTTP 200 at 920–968ms total, content `**A) 4**`, finish stop. Vision true; `supports_response_format` false (json_object compat unknown on the Claude-via-Go bridge).
- **New rank 2 `openrouter-haiku5.5`:** `anthropic/claude-haiku-5.5` via OpenRouter (user's own key `OPENROUTERTAGRADER`), HTTP 200 on probe. Same timeouts (2.6s TTFT / 3.2s wall).
- **Go catalog note:** 30 models behind `OPENCODEGOTAGRADER` incl. `claude-haiku-5-5`, `gemini-4-argon`, `grok-4.7`, `kimi-k3`, `qwen3.8`, `minimax-m3.1-flash` — spare options for later experiments, not wired now.
- `omniroute-haiku` (free Copilot 4.5) drops to rank 3 — free insurance under the 5.5 pair; OmniRoute github/claude-haiku-5.5 still 502 (token refresh pending).
- Contract suite 18 tests; all four suites green locally.

## 2026-11-09 08:22 UTC — v5.1: keys vaulted + openrouter-direct rank wired

- Stored `TAGRADER` (NVIDIA NIM key) and `OPENROUTERTAGRADER` (OpenRouter key, user's own account) in Doppler `ichabod/prd` + untracked `Desktop\TA-Grader\.env`; never in tracked files. Transit-verified byte-for-byte after the PS→ssh stdin corruption was routed via scp'd base64 + remote decode.
- Live probe with the OpenRouter key: HTTP 200 @ 1.5s, correct answer — **new rank 3 `openrouter-direct`** (`google/gemma-4-26b-a4b-it:free`, direct, no OmniRoute hop, user's own quota). `omniroute-gemma-free` demoted one slot as same-model backup (shared OmniRoute account). OpenRouter-direct measured 200 in 1.5s; NVIDIA NIM key stored but not yet wired (needs a model probe — see TODO).
- **OpenCode Go ranks revived the same hour**: Birkinbagh account key (`oc_sk_…`, 51 chars) vaulted as `OPENCODEGO_BIRKINBAGH` and swapped into `OPENCODEGOTAGRADER` (Doppler + `.env`; prior DEAD value existed only in `.env` — the name was never in Doppler). Go probe HTTP 200, `mimo-v2.6-flash` answered correctly. Old dead value backed up under `OPENCODEGOTAGRADER_PREV` (base64-encoded; the old key pre-swap was not retrievable because the name simply did not exist in Doppler).
- Contract suite now 17 tests; all four suites green locally + on ichabod, committed and pushed.

## 2026-11-09 00:45 UTC — cascade v5: haiku-first, verified-cheap ranks, Go demoted

Log audit showed the chain degraded to a single live endpoint (xai-grok 64/71) while mimo/deepseek/glm 403'd every call, gemini went 0/30, and the OmniRoute container sat dead for two days. The OmniRoute container was restarted on ichabod, and a full-model census (1972 models) + live probe matrix picked the final chain.

### Final 8-rank chain (all but Go ranks live-verified this session)
1. `omniroute-haiku` — `no-think/github/claude-haiku-4.5` via OmniRoute Tailscale `100.122.158.123:20128`; **fast and smart (~1.4s warm), near-zero Copilot premium burn** (user-directed rank 1). NOTE: an earlier audit note claiming the github router "retired" haiku-4.5 is WRONG — live probes (3×) returned 200 with correct answers, and it served a real answer through the old rank at 16:31:30.
2. `xai-grok-fast` — xAI direct, ~0.85s, proven workhorse (64/71 in the current log).
3. `omniroute-gemma-free` — `openrouter/google/gemma-4-26b-a4b-it:free` via OmniRoute; 200 @ ~1.1s, $0, answered the probe correctly; text-only (`supports_vision:false`).
4–6. `opencode-mimo-flash` / `opencode-deepseek-flash` / `opencode-glm-flash` — OpenCode Go `inference/go` base with stable per-run `ses_<64-hex>` `x-opencode-session` + `x-opencode-client` headers. Dormant until a fresh Console key lands (all stored keys expired server-side); they self-revive on the next question after the key lands — no restart needed.
7. `opencode-free` — anonymous bearer-less overflow (`zen/v1`, `no_auth:true`, UA `opencode/2.2.5`); per-IP capped (429 `FreeUsageLimitError` when the free pool is dry); <1s when free quota is live.
8. `gemini-2.5-flash` — demoted last (0/30 across the entire current log: high-demand 503s + timeouts); 3.2s/3.8s budgets, 2 rotation keys.

### Probe matrix findings (2026-11-08, OmniRoute — do not re-trust these blindly)
- **agy/antigravity ranks are dead as endpoints**: `antigravity/gemini-3.1-flash-lite` and `gpt-oss-120b-medium` return 200 whose *content* is a deprecation notice ("This version of Antigravity is no longer…"). Both 2 agy accounts effectively unusable for grading.
- `aug/haiku4.5`, `aug/gpt5.4-mini` → 502 server_error.
- `oc/*` (opencode router): free models 429 rate-limit (~4.5s to answer-rate-limit — expensive), paid models (`gpt-5.4-mini`, `qwen3.8-flash`, `minimax-m3`) 402 billing_error.
- `github/kimi-k3` → 400 invalid_request; `github/gemini-3.8-flash` → HTTP 200 with EMPTY content (trap; would have parked uselessly).
- `github/mai-code-1.1-flash` → 200 @ ~2.5s, answered correctly — viable but slower spare if gemma-free ever dies.
- `no-think/github/claude-haiku-5.5` still 502 empty-upstream (4.5–11.5s to fail — stale Copilot OAuth suspected; refresh pending).

### Behavior fixes in this release
- **HTTP 401/403 now parks the whole endpoint** for `auth_fail_cooldown_sec` (1800s, config-driven) instead of cycling every 60s; 429s keep 60s key rotation.
- **Stalest-retry is key-aware:** when everything is cooling, endpoints whose keys are live are preferred over endpoints parked with dead credentials.
- **`remap_answer_letter()` guard:** verifies the returned letter against the OCR'd option text and re-maps when the model puts the right text under the wrong letter (Q8-class mismatch). Conservative: unmatched shapes pass through unchanged.
- `tests/config.template.json` mirrors the live 8-rank chain; contract suite (16 tests) + routing/regressions/hotkeys all green locally and on ichabod.

### Known pending
- **OpenCode Go credentials expired server-side** (`api_key_expired`; fleet-wide incl. every key in Doppler `ichabod/prd`). Create a fresh key in OpenCode Console → Account → API keys (browser login; can't be minted from CLI) → Doppler `OPENCODEGOTAGRADER` + `Desktop\TA-Grader\.env`.
- **OmniRoute Copilot token refresh** for haiku-5.5/sonnet-5.5 (502 empty upstream).
- Restart the app to load the new chain.

## 2026-11-06 19:27 UTC — opencode-mimo-flash default primary endpoint

Promoted OpenCode Go's MiMo Flash (`mimo-v2.6-flash`) to the default (Rank 1) endpoint and interleaved fallbacks to eliminate provider lock:

### Changed
- **Default model to `opencode-mimo-flash`:** Configured `mimo-v2.6-flash` via OpenCode Go (`OPENCODEGOTAGRADER`) as rank 1 with native vision, native `json_object` format support, 2.2s/2.8s timeouts, and ~1.94s warm p50.
- **Interleaved fallback chain:**
  1. `opencode-mimo-flash` (`mimo-v2.6-flash` via OpenCode Go, 1.94s, native vision)
  2. `gemini-2.5-flash` (`gemini-2.5-flash` direct via Google AI Studio, 1.25s, 2 rotating keys, native vision)
  3. `opencode-deepseek-flash` (`deepseek-v4.1-flash` via OpenCode Go with `thinking: disabled`, 1.06s, native vision)
  4. `xai-grok-fast` (`grok-4.20-0309-non-reasoning` direct via xAI, 0.85s, native vision)
  5. `opencode-glm-flash` (`glm-5.3-flash` via OpenCode Go, 1.20s, native vision)
  6. `omniroute-haiku` (`claude-haiku-4.5` via LAN Copilot, 1.00s, native vision)

## 2026-11-04 00:31 UTC — zero-quota-murder flash/lite waterfall & timeout cascade fix

Log audit revealed a 7.2s timeout cascade caused by adjacent OmniRoute endpoints at ranks 1 & 2 sharing Copilot upstream stalls, while OpenCode `beam-free` was tripping TTFT keepalive guards with hidden reasoning tokens. Replaced with an interleaved, zero-quota-burn sub-1.3s flash waterfall:

### Changed
- **Interleaved waterfall:** Ranks now alternate across independent backends to eliminate shared-fate latency stalls:
  1. `omniroute-haiku` (`claude-haiku-4.5` via LAN Copilot, 1.00s, native vision)
  2. `opencode-deepseek-flash` (`deepseek-v4.1-flash` via OpenCode Go with `thinking: disabled`, 1.06s, native vision)
  3. `opencode-glm-flash` (`glm-5.3-flash` via OpenCode Go, 1.20s, $0 allowance burn, native vision)
  4. `gemini-2.5-flash` (`gemini-2.5-flash` direct via Google AI Studio, 1.25s, 2 rotating keys, native vision)
  5. `xai-grok-fast` (`grok-4.20-0309-non-reasoning` direct via xAI, 0.85s, native vision safety net)
- **Disabled reasoning on DeepSeek Flash:** Added `payload_overrides: {"thinking": {"type": "disabled"}}` to suppress hidden thinking tokens and deliver pure sub-1.1s direct JSON without burning Go plan allowance.
- **Extended endpoint cooldown:** Increased `endpoint_cooldown_sec` from 15s to 60s in `config.json` so failing/stalled endpoints stay cooled across multiple questions.
- **Removed `opencode-beam`:** Eliminated broken reasoning model that was tripping the TTFT streaming stall guard.

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



