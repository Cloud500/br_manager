# AGENTS.md

## Scope

This app owns the authenticated dashboard and high-level navigation entry points.

## Rules

- `DashboardView` requires login. Do not make the dashboard public.
- Dashboard cards should link to named URLs, not hard-coded internal paths.
- Disabled cards for future modules should stay visually clear and should not imply working features.
- Dashboard changes should preserve German labels and the Bootstrap-based layout used by `templates/base.html`.
- Do not duplicate domain statistics in the dashboard without checking permissions and query cost.

## Checks

- Test unauthenticated redirect behavior if changing `DashboardView`.
- Smoke-test dashboard rendering when navigation or app URLs change.
