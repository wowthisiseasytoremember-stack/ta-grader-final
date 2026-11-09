# TA Grader — TODO

## Active Execution Tasks
- [ ] **Restart the app** to load the v5.3 opt-in-vision build (vision OFF on boot; `alt+i` toggles for the session). Config only re-reads on boot.
- [ ] **gemini-2.5-flash rank 404s now** (was 503 high-demand before): check Google's openai-compat base URL / model id drift; it's last rank so cosmetic.
- [ ] **NVIDIA NIM rank**: `TAGRADER` key is vaulted (Doppler + `.env`) but unwired — probe `integrate.api.nvidia.com` (e.g. nemotron-3.5-lightning / llama-3.3 / qwen-flash) for a sub-2s grader model, then add as a rank behind gemma.
- [x] **OpenCode Go key solved (2026-11-09)**: the expired fleet-wide keys were bypassed — Birkinbagh account key (`oc_sk_…`, 51 chars) vaulted as `OPENCODEGO_BIRKINBAGH` and swapped into `OPENCODEGOTAGRADER` (Doppler + `.env`); mimo Go probe returned 200 with correct answer. Prior finding corrected: `OPENCODEGOTAGRADER` never existed in Doppler — the stale `.env` was the sole key source until now.
- [ ] **OmniRoute Copilot token refresh:** `no-think/github/claude-haiku-5.5` and `sonnet-5.5` 502 "empty upstream" (stale OAuth suspected). Refresh in OmniRoute settings (`:20128` on ichabod). Until then haiku-4.5 covers the route.
- [ ] Watch `ta_grader.log` for the first session on the v5 chain: confirm haiku answers rank-first in ~1.5s, 403-parked Go ranks stay dormant, and no 200-with-empty-content traps (gemini-3.8-flash class) get trusted.
- [ ] `ta_grader.log` (254KB) will rotate eventually — wire a size-cap or date rotation before it bloats the desktop overlay box.

## Done
- [x] Keys vaulted (2026-11-09): `TAGRADER` (NVIDIA NIM) + `OPENROUTERTAGRADER` (OpenRouter, user's own account) into Doppler `ichabod/prd` and untracked `.env`; OpenRouter key live-verified (200 @ 1.5s, correct answer).
- [x] Routing v5 (2026-11-09): 8-rank chain re-ordered by probe evidence — `omniroute-haiku` rank 1 (user call: fast+smart), grok rank 2 (proven 64/71), `omniroute-gemma-free` rank 3 ($0, 200 @ ~1.1s), Go trio demoted to 4–6 pending new key, anonymous `opencode-free` overflow, gemini last (0/30 record). Probe matrix logged in CHANGELOG: agy accounts deprecated-content, aug 502, oc free 429 / paid 402, kimi-k3 400, gemini-3.8-flash empty-content trap, mai-code-1.1-flash viable spare.
- [x] Behavior fixes (2026-11-08/09): auth-fail endpoint parking (1800s), key-aware stalest retry, stable per-run `ses_<64-hex>` OpenCode session + client headers, `remap_answer_letter()` display guard wired into `_run_llm` (live-verified 3 cases: mismatch→remap, consistent→unchanged, no-options→conservative).
- [x] OmniRoute container `omniroute-ichabod` restarted after it sat Exited(7) for two days (2026-11-08; port 20128 listening again; old LAN rank answered a real question at 16:31:30).
- [x] Archive retired checkouts `ta-grader`, `ta-grader-app`, `ta-grader-new` to `~/Projects/_archived/` on ichabod (2026-10-30; registry now lists only `ta-grader-final`).
