# TA Grader

Canonical Windows desktop app source: [GitHub repository](https://github.com/wowthisiseasytoremember-stack/ta-grader-final). The installed Desktop shortcut starts `C:\Users\wowth\Desktop\TA-Grader\Run_TA_Grader.bat`; that checkout is the copy to run and maintain for the current Windows installation.

## Model order (routing v3 — provider-interleaved, knowledge-speed first)

Provider diversity is deliberate: quota exhaustion or an outage takes down every model on one provider at once, so ranks alternate across provider backends. Deep-reasoning models sit at the back because algebra questions are rare; they cost seconds and quota.

1. `omniroute-copilot-terra` (`no-think/github/gpt-5.6-terra`) — ~1.4s, native vision, chemistry/math accuracy
2. `omniroute-copilot-gpt5.4-mini` (`github/gpt-5.4-mini`) — ~0.9–1.4s, 844 historical wins, native vision (re-enabled)
3. `omniroute-copilot-haiku` (`no-think/github/claude-haiku-4.5`) — ~0.9s, light mini quota, native vision
4. `yolo-auto-flash` (`qwen3.8-flash` via `yolo-auto.com`) — ~1.2s, thinking disabled, free builder tier, independent provider
5. `opencode-deepseek-vision` (`deepseek-v4-flash-vision-exp` via OpenCode Go) — ~1.6s, native vision, independent provider
6. `omniroute-generalist` (`generalist` via OmniRoute) — 889 historical wins (most), most resilient Copilot alias
7. `omniroute-copilot-gemini-flash` (`github/gemini-3.7-flash`) — ~3.5s, unmetered, vision support
8. `omniroute-copilot-sonnet-5` (`github/claude-sonnet-5`) — deep reasoning, `max_tokens` 1536
9. `omniroute-copilot-gpt5.4` (`github/gpt-5.4`) — full reasoning, `max_tokens` 2048
10. `xai-grok-reasoning` (`grok-4.20-0309-reasoning`) — deep-reasoning emergency rank, `max_tokens` 4096, 16s/22s timeouts, algebra-only by position


## Run and configure

On Windows, launch with `Run_TA_Grader.bat` (the Desktop shortcut already points to this launcher). Python 3.11+, Tesseract OCR, and the dependencies listed in the launcher are required. The app reads `.env` at startup before resolving environment keys; `.env` is gitignored. The Doppler source of truth is project `ichabod`, config `dev`, secret `OPENCODEGOTAGRADER`. Restart the app after updating `.env` so the running process reloads the key.

Never commit API keys, OAuth tokens, or `.env` files. Keep `config.json` limited to endpoint names and key variable names.

## Other checkout retired

`Projects/ta-grader` is a retired, separate implementation. Use this repository and the Desktop shortcut checkout for TA Grader work.
