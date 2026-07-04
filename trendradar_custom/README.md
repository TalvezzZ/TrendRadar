# TrendRadar Custom Layer

Use this package for project-specific extensions that should not live in the upstream `trendradar` package.

Preferred placement:

- Custom scripts and adapters: `trendradar_custom/`
- Local-only configuration: `config/config.custom.yaml`
- Custom workflows: `.github/workflows/custom-*.yml`
- Custom docs: `docs/custom/`

Avoid editing upstream-heavy files unless a small integration point is required.
