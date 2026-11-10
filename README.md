# TA Grader

Canonical Windows desktop app source: [GitHub repository](https://github.com/wowthisiseasytoremember-stack/ta-grader-final). The installed Desktop shortcut starts `C:\Users\wowth\Desktop\TA-Grader\Run_TA_Grader.bat`; that checkout is the copy to run and maintain for the current Windows installation.

## Model order (v5, 2026-11-09 — verified-live ranks first)

Provider diversity is deliberate: quota exhaustion or an outage takes down every model on one provider at once, so ranks interleave providers where possible. The live source of truth is `config.json`; the list below matches it as of 2026-11-09 23:4x UTC.

1. `opencodego-haiku5.5` (`claude-haiku-5-5` via OpenCode Go, `OPENCODEGOTAGRADER`) — rank 1 by user call: fast + smart (~0.95s warm)
2. `openrouter-haiku5.5` (`anthropic/claude-haiku-5.5` via OpenRouter, `OPENROUTERTAGRADER`) — same model, second route through the user's own account
3. `omniroute-haiku` (`no-think/github/claude-haiku-4.5` via OmniRoute Tailscale `100.122.158.123:20128`, `OMNIROUTE_API_KEY`) — free Copilot insurance
4. `xai-grok-fast` (`grok-4.20-0309-non-reasoning` via xAI, `XAI_API_KEY`) — proven workhorse (~0.85s)
5. `openrouter-direct` (`google/gemma-4-26b-a4b-it:free`, `OPENROUTERTAGRADER`) — $0, no middle hop; text-only
6. `omniroute-gemma-free` (same model via OmniRoute's shared OpenRouter accounts) — same-model insurance
7. `opencode-mimo-flash` (`mimo-v2.6-flash` via OpenCode Go, `OPENCODEGOTAGRADER`)
8. `opencode-deepseek-flash` (`deepseek-v4.1-flash` via OpenCode Go, `thinking: disabled`)
9. `opencode-glm-flash` (`glm-5.3-flash` via OpenCode Go)
10. `opencode-free` (anonymous overflow, `deepseek-v4.1-flash-free` via `opencode.ai/zen/v1` — bearer-less by design)
11. `gemini-2.5-flash` (Google AI Studio, 2 rotating keys) — last resort; currently 404 on Google's openai-compat path (see CHANGELOG/TODO)

Vision is opt-in: OFF on boot, `alt+i` toggles it for the session only (see CHANGELOG v5.3).


## Run and configure

On Windows, launch with `Run_TA_Grader.bat` (the Desktop shortcut already points to this launcher). Python 3.11+, Tesseract OCR, and the dependencies listed in the launcher are required. The app reads `.env` at startup before resolving environment keys; `.env` is gitignored. The Doppler source of truth is project `ichabod`, config `prd` (secrets: `OPENCODEGOTAGRADER`, `OPENROUTERTAGRADER`, `TAGRADER`, `OMNIROUTE_API_KEY`, `XAI_API_KEY`, `GEMINI_API_KEY`/`GEMINI_FLASH_KEY_2`). Restart the app after updating `.env` so the running process reloads the key.

Never commit API keys, OAuth tokens, or `.env` files. Keep `config.json` limited to endpoint names and key variable names.

## Other checkout retired

`Projects/ta-grader` is a retired, separate implementation. Use this repository and the Desktop shortcut checkout for TA Grader work.
