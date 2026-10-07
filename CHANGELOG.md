# Changelog — TA Grader

## 2026-10-02 — fast text-only routing and SurfaceBook recovery

- Prefer Copilot GPT-4o mini, then YOLO Qwen, Copilot Gemini Flash, and Antigravity Flash/Lite.
- Disable vision by default; screenshot inputs still use OCR. Preserve adaptive vision for opt-in.
- Disable quota-exhausted Ollama Cloud and failed legacy credentials in the shipped chain.
- Use Tailscale for the SurfaceBook router URL; support an environment override.
- Require complete JSON, close HTTP responses, reduce retries, and cool down failed endpoints.
- Bind Menu once on release and debounce duplicate queued OCR captures for 1.5 seconds.
- Preserve SurfaceBook config/credentials with backups and restart the GUI in its interactive session.
- 21 local and Windows tests passed; five real captures used Copilot mini in roughly one second each.
- Add current setup, recovery, and consolidation documentation.

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
