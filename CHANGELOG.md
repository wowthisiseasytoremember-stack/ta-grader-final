# Changelog — TA Grader

## 2026-09-27 — routing/security audit

### Fixed
- Fixed Gemini key rotation: all configured keys are retained and tried instead of caching only the first key.
- Removed runtime API-key values from the config object so changing the OCR region cannot persist secrets into `config.json`.
- Added recursive runtime-field stripping before config persistence.
- Replaced two independent screen grabs with one shared capture for OCR and vision.
- Added OCR confidence + option-marker quality checks.
- Added adaptive routing: strong OCR keeps the fast text-first chain; weak OCR promotes vision-capable endpoints first.
- Weak-OCR vision requests omit the suspect OCR transcript instead of biasing the vision model with corrupted text.
- Made vision capability explicit for every configured endpoint.
- Fixed retry behavior so transient 5xx/timeouts/connection failures can retry the same key before rotating/failing over.
- Replaced wall-clock stream deadlines with monotonic timing and reduced the minimum runaway-stream deadline.

### Hardened
- Added `.env.*` and `keys.cmd` to gitignore.
- Added static CI checks for syntax, endpoint order/capabilities, Gemini key rotation configuration, and secret-cache regressions.
- Removed stale endpoint/status documentation and secret-like fragments from the current changelog.

### Measured
Synthetic question-image benchmark on the audit runner:
- JPEG + base64 preparation: about 1.5–2.7 ms median.
- Tesseract OCR: about 187–311 ms median.
- Clean 18–28 px text: 100% normalized OCR similarity in the benchmark.
- Tiny 13 px text exposed a material OCR failure (about 79% similarity, including option-label corruption).

Conclusion: preparing an image is much cheaper locally than OCR, but OCR remains the correct fast path when it is trustworthy because the two highest-priority endpoints are text-only. Vision should take over when OCR quality is suspect.

See `docs/OCR_VISION_AUDIT_2026-09-27.md`.
