# OCR vs vision audit — 2026-09-27

## Decision

Use **adaptive routing**, not OCR-only and not image-only.

- **Good OCR:** keep the normal endpoint order so the two fastest text-only endpoints stay first.
- **Weak OCR:** promote vision-capable endpoints ahead of text-only endpoints.
- Capture each frame once and reuse the exact same frame for OCR and vision.
- Apply the same policy to fixed-region and multi-segment scroll captures.
- When OCR is weak, do not include the suspect OCR transcript in the vision prompt.
- Clipboard input remains text-first because it is already machine-readable.

## What was measured

Representative synthetic multiple-choice screenshots were used to measure:
1. JPEG encoding + base64 preparation.
2. Tesseract OCR latency.
3. Normalized OCR similarity against known ground-truth text.

Audit runner: Tesseract 5.5.0.

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

Image preparation itself is effectively free compared with OCR. That does **not** prove image-only is faster end-to-end, because multimodal upload/inference latency is provider-dependent.

The endpoint chain matters:
1. `yolo-auto-flash` — text-only
2. `yolo-auto-small` — text-only
3. `gemini-flash` — vision
4. `openai-gpt-4o-mini` — vision
5. NVIDIA vision fallbacks
6. text/local fallbacks

Skipping OCR entirely would skip the two highest-priority fast endpoints. Clean OCR was also perfect in the representative benchmark. But tiny text produced a concrete failure where option labels were corrupted, which is dangerous for multiple-choice grading.

Therefore:
- pay the ~0.2–0.3 s OCR cost when OCR quality is trustworthy;
- promote vision when OCR confidence/option structure suggests corruption;
- keep text-only endpoints later as fallback if vision providers are unavailable.

## Scroll capture

The concurrent scroll-capture feature is preserved. Each scroll segment now:
- grabs the screen once;
- reuses that frame for OCR and the stitched vision image;
- contributes OCR confidence to the combined capture;
- uses the same adaptive text-first/vision-first decision as the fixed region.

## Security and reliability fixes

- Gemini retains both configured keys for actual rotation.
- Secrets are cached only in process memory.
- Config persistence strips runtime-only keys recursively.
- Environment/.env is checked before Doppler.
- Transient 5xx/timeouts/connection failures retry correctly.
- Stream timing uses a monotonic clock.
- Duplicate single-instance mutex code was removed.
- CI locks the routing/security/scroll-preservation contract.

## Remaining measurement gap

This cloud audit runner did not have the user's provider API secrets, so it could not make controlled live calls against Yolo, Gemini, OpenAI, and NVIDIA to compare full end-to-end answer latency/cost on the same question corpus.

The code now logs strategy selection and endpoint use, so the next local validation can measure real provider latency without changing architecture again.
