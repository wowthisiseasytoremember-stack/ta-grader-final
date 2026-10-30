# TA Grader — TODO

## Active Execution Tasks
- [ ] Watch `%LOCALAPPDATA%\Temp\ta_grader.log` for the first day of routing v3 — confirm gpt5.4-mini's re-enable holds (844 historical wins) and provider-scoped cooldowns behave during the next OmniRoute quota storm.
- [ ] Operator decisions pending: delete retired checkouts `~/Projects/ta-grader`, `~/Projects/ta-grader-app`, `~/Projects/ta-grader-new` on ichabod (not registered; `ta-grader` marked archived in the vault registry 2026-10-30).
- [ ] Consider a `config.json` health probe script that pings each enabled endpoint's origin at startup and logs which providers are reachable before the first question.

## Done
- [x] Routing v3: provider-interleaved 10-rank chain, exponential provider-scoped cooldowns, keyless skip, stalest-retry, vision consensus + escalation, per-endpoint token budgets (commit `7416748`, 36/36 tests green).
