# OCR vs vision audit — 2026-09-27

## Decision

Use **adaptive routing**, not OCR-only and not image-only.

- **Good OCR:** preserve endpoint priority so the two fast text-only Yolo endpoints get first attempt.
- **Weak OCR:** promote vision-capable endpoints ahead of text-only endpoints.
- Capture every viewport once and reuse the exact frame for OCR and vision.
- Apply the same policy to fixed, manual-scroll, and automatic-scroll captures.
- When OCR is weak, omit the suspect OCR transcript from the vision request.
- Clipboard input remains text-first because it is already exact machine-readable text.

## Benchmark

Representative synthetic multiple-choice screenshots were used to compare local image preparation with Tesseract OCR. The audit runner used Tesseract 5.5.0.

| Case | JPEG + base64 median | OCR median | OCR similarity |
|---|---:|---:|---:|
| clear 28 px | 2.7 ms | 311.1 ms | 100% |
| small 18 px | 2.4 ms | 303.6 ms | 100% |
| blurred 22 px | 2.4 ms | 270.6 ms | 100% |
| tiny 13 px | 1.6 ms | 187.0 ms | 79.3% |
| low contrast | 1.6 ms | 211.2 ms | 100% |
| 50% down/up-scale | 1.6 ms | 217.0 ms | 99.5% |
| blur + JPEG artifacts | 1.7 ms | 216.9 ms | 99.5% |
| tiny + downscale + JPEG | 1.5 ms | 196.2 ms | 98.0% |

Median local preprocessing ratio across these samples was roughly **127x more time for OCR than JPEG/base64 preparation**.

## Interpretation

Preparing an image is effectively free compared with OCR. That does **not** prove image-only is faster end-to-end: multimodal upload and model inference latency are provider-dependent.

The endpoint chain matters:

1. `yolo-auto-flash` — text-only
2. `yolo-auto-small` — text-only
3. `gemini-flash` — vision
4. `openai-gpt-4o-mini` — vision
5. NVIDIA vision fallbacks
6. text/local fallbacks

Skipping OCR entirely would skip the intended fast path. Clean OCR was also perfect in the representative benchmark. But tiny text produced a concrete failure where option labels were corrupted, which is dangerous for multiple-choice grading.

Therefore the implementation:
- accepts the ~0.2–0.3 s OCR cost when OCR looks trustworthy;
- promotes vision when OCR confidence or option structure looks suspicious;
- keeps text-only endpoints available as later fallback.

## Capture-path improvements

### Fixed region
One screen grab is reused for OCR and image encoding.

### Manual scroll
Each ENTER capture stores one PIL frame, runs OCR on that same frame, and later stitches those same frames for vision.

### Auto-scroll
Each Page-Down viewport stores one PIL frame, runs OCR on that same frame, uses that frame for repeated-frame detection, and stitches the same frames for vision. No second screen grab is needed.

## Security and reliability fixes

- Gemini retains both configured keys for actual 429/auth rotation.
- Secrets are cached only in process memory.
- Region persistence recursively strips runtime-only config fields.
- Environment/.env is checked before Doppler.
- Transient 5xx/timeouts/connection failures honor configured retries.
- Stream timing uses a monotonic clock.
- Duplicate single-instance mutex code was removed.
- CI protects the endpoint, secret, and capture contracts.

## Remaining measurement gap

The audit runtime did not have the user's provider API secrets, so it could not make controlled live calls against Yolo, Gemini, OpenAI, and NVIDIA to compare full end-to-end provider latency and answer accuracy on the same corpus.

The code now logs selected strategy and endpoint, so that provider-level benchmark can be run locally without another architecture change.
