# TA Grader — TODO

## Active Execution Tasks
- [ ] Watch `%LOCALAPPDATA%\Temp\ta_grader.log` for the first day of routing v3 — confirm gpt5.4-mini's re-enable holds (844 historical wins) and provider-scoped cooldowns behave during the next OmniRoute quota storm.
- [x] Archive retired checkouts `ta-grader`, `ta-grader-app`, `ta-grader-new` to `~/Projects/_archived/` on ichabod (2026-10-30; registry now lists only `ta-grader-final`).
- [ ] Consider a `config.json` health probe script that pings each enabled endpoint's origin at startup and logs which providers are reachable before the first question.

## Done
- [x] Routing v3: provider-interleaved 10-rank chain, exponential provider-scoped cooldowns, keyless skip, stalest-retry, vision consensus + escalation, per-endpoint token budgets (commit `7416748`, 36/36 tests green).
