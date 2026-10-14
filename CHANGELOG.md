# Changelog — TA Grader

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

### Routing Hierarchy
1. `omniroute-copilot-gemini-flash` (`github/gemini-3.7-flash` via OmniRoute Copilot): ~1.0s, unmetered, low reasoning, vision support.
2. `yolo-auto-flash` (`qwen3.8-flash` via `yolo-auto.com`): ~1.2s, unlimited free builder plan, thinking disabled.
3. `omniroute-copilot-sonnet-5` (`github/claude-sonnet-5` via OmniRoute): ~1.0s, high accuracy across critical thinking, logic & math.
4. `xai-grok-reasoning` (`grok-4.20-0309-reasoning` via xAI API): ~4.8s, reasoning model for complex formal logic.
5. `opencode-deepseek-vision` (`deepseek-v4-flash-vision-exp` via OpenCode Go): ~1.6s, native vision.
6. `omniroute-copilot-gpt5.4` (`github/gpt-5.4` via OmniRoute): ~3.1s, full reasoning model.



