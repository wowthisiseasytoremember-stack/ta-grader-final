# Changelog — TA Grader

## 2026-08-01 05:30 UTC — API keys refresh + yolo-auto endpoint

### Done
- Added Yolo-Auto (qwen3.6-35b-a3b) as primary endpoint with thinking disabled
- Refreshed all API keys from Doppler (ichabod project)
- Fixed invalid GEMINI_API_KEY (was AIzaSyDOFf... which returned 400)
- Reordered endpoints: fast working ones first, broken ones as fallback
- Bumped max_tokens from 1000 to 2000
- Verified 12/12 correct across 3 working endpoints (~1-2s each)
- Created git repo, AGENTS.md, CHANGELOG.md

### In Progress
- Gemini rate limiting — all keys hitting 429, needs quota reset or new project

### Blocked
- DeepSeek account has zero balance (402) — needs top-up
- NVIDIA endpoint times out at 15s — unreliable

### For Produce
> TA Grader: yolo-auto added as primary endpoint, thinking disabled. All keys refreshed from Doppler. Gemini and DeepSeek still broken (quota/balance). 3 working endpoints verified.
