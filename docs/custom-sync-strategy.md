# Custom Sync Strategy

This repository tracks the official TrendRadar project as `upstream` and keeps local development on `master`.

## Remotes

```bash
origin   https://github.com/TalvezzZ/TrendRadar.git
upstream https://github.com/Sansan0/TrendRadar.git
```

## Daily Sync

```bash
git fetch upstream
git switch master
git merge upstream/master
git push origin master
```

## Conflict Reduction Rules

- Keep `config/config.yaml` close to upstream.
- Put local configuration in `config/config.custom.yaml`.
- Put new custom Python code in `trendradar_custom/`.
- Add separate custom workflows instead of editing upstream workflows when possible.
- Keep upstream package edits limited to small integration points.

## Current Custom Areas

- Memory system
- Finance tracking
- Persistence and OSS sync
- Custom workflows and reports

These areas are already deeply integrated. Do not mechanically move them without tests; isolate new work first and gradually migrate stable pieces later.
