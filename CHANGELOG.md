# Changelog — TA Grader

## 2026-09-27 — routing/security audit

### Fixed
- Fixed Gemini key rotation: all configured keys are retained and tried instead of silently caching only the first key.
- Removed runtime API-key values from the config object so changing either fixed or scroll regions cannot persist secrets into `config.json`.
- Added recursive runtime-field stripping before config persistence.
- Changed fixed capture from two independent screen grabs to one shared frame for OCR and vision.
- Changed each scroll segment to one shared frame for OCR and the stitched vision image.
- Added OCR confidence + option-marker quality checks.
- Added adaptive routing: strong OCR keeps the fast text-first chain; weak OCR promotes vision-capable endpoints first.
- Weak-OCR vision requests omit the suspect OCR transcript.
- Made vision capability explicit for every configured endpoint.
- Fixed transient retry behavior for 5xx/timeouts/connection failures.
- Replaced wall-clock stream deadlines with monotonic timing and shortened runaway-stream bounds.
- Removed duplicate single-instance mutex logic.
- Changed secret lookup to environment/.env first and Doppler fallback.

### Preserved
- Dedicated scroll-region support from the concurrent 2026-09-27 master updates.
- `alt+shift+x` set-scroll-region workflow.
- `alt+shift+z` multi-segment scroll capture workflow.

### Hardened
- Added `.env.*` and `keys.cmd` to gitignore.
- Added a safe `.env.example`.
- Added static CI checks for syntax, endpoint order/capabilities, Gemini key rotation, secret-cache regressions, and scroll-feature preservation.
- Removed stale status claims and secret-like fragments from the current changelog.

### Measured
Synthetic multiple-choice screenshots on the audit runner:
- JPEG + base64: about 1.5–2.7 ms median.
- Tesseract OCR: about 187–311 ms median.
- Clean 18–28 px text: 100% normalized OCR similarity.
- Tiny 13 px text: about 79% similarity with option-label corruption.

Conclusion: image preparation is much cheaper locally than OCR, but OCR remains the correct fast path when trustworthy because the two highest-priority endpoints are text-only. Vision should take over when OCR quality is suspect.

See `docs/OCR_VISION_AUDIT_2026-09-27.md`.
