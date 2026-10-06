# TA Grader

Canonical Windows desktop app source: [GitHub repository](https://github.com/wowthisiseasytoremember-stack/ta-grader-final). The installed Desktop shortcut starts `C:\Users\wowth\Desktop\TA-Grader\Run_TA_Grader.bat`; that checkout is the copy to run and maintain for the current Windows installation.

## Model order

1. OpenCode Go `longcat-2.5-preview-free` (free preview)
2. OpenCode Go `mimo-v2.6-flash`
3. Existing configured endpoints, including GitHub Copilot, Gemini Flash, and Yolo

Both OpenCode models use `https://opencode.ai/zen/go/v1/chat/completions` and the `OPENCODEGOTAGRADER` secret. LongCat and MiMo were verified with successful OpenCode Go responses.

## Run and configure

On Windows, launch with `Run_TA_Grader.bat` (the Desktop shortcut already points to this launcher). Python 3.11+, Tesseract OCR, and the dependencies listed in the launcher are required. The app reads `.env` at startup before resolving environment keys; `.env` is gitignored. The Doppler source of truth is project `ichabod`, config `dev`, secret `OPENCODEGOTAGRADER`. Restart the app after updating `.env` so the running process reloads the key.

Never commit API keys, OAuth tokens, or `.env` files. Keep `config.json` limited to endpoint names and key variable names.

## Other checkout retired

`Projects/ta-grader` is a retired, separate implementation. Use this repository and the Desktop shortcut checkout for TA Grader work.
