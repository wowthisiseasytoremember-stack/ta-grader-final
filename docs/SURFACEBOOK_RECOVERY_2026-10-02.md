# SurfaceBook Recovery — 2026-10-02

## Recovery Run

Use existing launcher `Run_TA_Grader.bat` elevated or `Start-ScheduledTask -TaskName "TA Grader - Fast Routing"`. **Do not clobber config or `.env` updates.** Windows protected `.env`, custom hotkeys, regions, and machine preferences are retained.

## Scheduled Task

On-demand task: **TA Grader - Fast Routing** — interactive Session 1, allows battery, no startup trigger.

## Backups

- `.updates/backup-20261002T115551`
- `.updates/backup-textonly-20261002T121223`

## Dependencies

```bash
pip install keyboard requests pillow pytesseract
```

Tesseract installed at Windows Program Files. Text-only mode is enabled. The live config preserves machine-specific settings and disables failed legacy routes. The canonical template is used for contract tests; routing tests exercise the client independently. All 21 tests passed. The restarted GUI ran in interactive session 1; five real captures then succeeded through Copilot mini in roughly one second each.
