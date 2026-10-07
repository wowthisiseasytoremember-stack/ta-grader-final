---
title: TA Grader Floating Answer-Key Overlay Architecture & Script Improvements
source: Arena.ai Audit Session
extracted_at: 2026-08-28 06:35 UTC
evidence_type: REFERENCE_DATA
status: AUDITED
---

# TA Grader Floating Answer-Key Overlay Improvements

## System Architecture
- **Platform**: Windows / Cross-platform overlay hotkeys.
- **Functionality**: Transparent floating answer-key HUD for rapid assessment grading.
- **Audit Findings & Implementation Status**:
  - **Hotkey event handling responsiveness improvements**: Evaluated as integrated/reference data. Implemented via threaded event queue (`_events.Queue`) decoupling hotkey hooks from UI updates and background streaming LLM client.
  - **Window state persistence across grading batches**: Evaluated as integrated/reference data. Implemented via `config.json` persistence of `fixed_ocr_region` and rolling in-memory cache of recent answers (`_last_answers`).
  - **Multi-monitor coordinate normalization**: Evaluated as integrated/reference data. Implemented via Windows per-monitor v2 DPI awareness (`SetProcessDpiAwareness(2)`) and boundary clamping in `_place()`.

## Classification
- **Category**: Reference Data (Architectural audit record confirming overlay HUD optimizations implemented in `ta_grader.py`).

