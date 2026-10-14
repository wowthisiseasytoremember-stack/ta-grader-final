# TA Grader

Canonical Windows desktop app source: [GitHub repository](https://github.com/wowthisiseasytoremember-stack/ta-grader-final). The installed Desktop shortcut starts `C:\Users\wowth\Desktop\TA-Grader\Run_TA_Grader.bat`; that checkout is the copy to run and maintain for the current Windows installation.

## Model order

1. `gemini-flash` (`gemini-2.5-flash` direct API) — ~0.93s, generous free quota, vision support
2. `yolo-auto-flash` (`qwen3.8-flash` via `yolo-auto.com`) — ~1.2s, thinking disabled, free builder tier
3. `omniroute-copilot-sonnet-5` (`github/claude-sonnet-5`) — ~1.0s, high accuracy backup across logic & math
4. `xai-grok-reasoning` (`grok-4.20-0309-reasoning`) — ~4.8s, reasoning enabled for complex logic
5. `opencode-deepseek-vision` (`deepseek-v4-flash-vision-exp` via OpenCode Go) — ~1.6s, native vision
6. `omniroute-copilot-gpt5.4` (`github/gpt-5.4`) — ~3.1s full reasoning fallback


## Run and configure

On Windows, launch with `Run_TA_Grader.bat` (the Desktop shortcut already points to this launcher). Python 3.11+, Tesseract OCR, and the dependencies listed in the launcher are required. The app reads `.env` at startup before resolving environment keys; `.env` is gitignored. The Doppler source of truth is project `ichabod`, config `dev`, secret `OPENCODEGOTAGRADER`. Restart the app after updating `.env` so the running process reloads the key.

Never commit API keys, OAuth tokens, or `.env` files. Keep `config.json` limited to endpoint names and key variable names.

## Other checkout retired

`Projects/ta-grader` is a retired, separate implementation. Use this repository and the Desktop shortcut checkout for TA Grader work.
