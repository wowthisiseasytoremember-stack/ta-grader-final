# OCR vs vision audit — 2026-09-27

## Decision

Use **adaptive routing**, not OCR-only and not image-only.

- **Good OCR:** keep the normal endpoint order so the two fastest text-only endpoints stay first.
- **Weak OCR:** promote vision-capable endpoints ahead of text-only endpoints.
- Capture the screen **once** and reuse the exact same frame for both OCR and vision.
- When OCR is judged weak, do not include the suspect OCR transcript in the vision prompt.
- Clipboard input remains text-first because it is already machine-readable text.

This is the smallest design that preserves the fast path while fixing the main accuracy failure mode.

## What was measured

A local benchmark generated representative multiple-choice screenshots, then measured:

1. JPEG encoding + base64 preparation for an image request.
2. Tesseract OCR latency.
3. Normalized OCR similarity against the known ground-truth question text.

The runner used Tesseract 5.5.0.

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

## What the benchmark means

Image preparation itself is essentially free compared with OCR. That does **not** mean image-only routing is faster end-to-end, because multimodal API inference and upload costs are downstream and provider-dependent.

The current endpoint chain matters:

1. `yolo-auto-flash` — text-only
2. `yolo-auto-small` — text-only
3. `gemini-flash` — vision
4. `openai-gpt-4o-mini` — vision
5. NVIDIA vision fallbacks
6. text/local fallbacks

Skipping OCR entirely would skip the two highest-priority fast endpoints. Clean OCR also performed perfectly in the representative benchmark. But tiny text produced a concrete failure: answer-option labels were misread (for example, a `B)` marker became `8)`), which can silently corrupt a multiple-choice answer.

Therefore the right behavior is:

- pay the ~0.2–0.3 s OCR cost when OCR quality is good, then use the fast text endpoint;
- switch to vision-first when OCR confidence/option structure suggests corruption;
- preserve text-only endpoints later in the fallback chain in case vision providers are unavailable.

## Code changes from this audit

- One screen capture instead of separate OCR and vision grabs.
- One Tesseract `image_to_data` pass returns text and confidence.
- OCR quality uses confidence plus expected multiple-choice option markers.
- Weak OCR changes endpoint ordering to vision-first.
- Vision-first requests omit the weak OCR transcript.
- Explicit `supports_vision` on every endpoint.
- Gemini retains both configured keys for actual 429/auth rotation.
- Secrets are cached only in process memory and are never inserted into the config object.
- Config persistence strips runtime-only keys recursively.
- Retry behavior now retries transient failures correctly before failover.
- Static CI locks the routing/security contract.

## Remaining measurement gap

This cloud audit runner did not have the user's provider API secrets, so it could not make controlled live requests against Yolo, Gemini, OpenAI, and NVIDIA to compare full end-to-end answer latency/cost across the same question set.

The app now logs which strategy was selected and which endpoint answered, so a real local corpus can be used for a provider-level benchmark without changing architecture again.
