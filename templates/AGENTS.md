# AGENTS.md

## Scope

This directory contains global Django templates. App-specific templates live under `apps/<app>/templates/`.

## Base Template Rules

- `base.html` is the global shell for navigation, flash messages, main content, and footer.
- Keep `<html lang="de">` and German navigation labels unless the product language changes explicitly.
- Use named URLs with `{% url %}` for internal navigation.
- Do not expose links to protected features solely based on UI assumptions; pair visibility with server-side permission enforcement.
- Logout must remain a POST with CSRF protection.

## Frontend Rules

- Preserve the existing Bootstrap 5 and Bootstrap Icons style unless explicitly redesigning.
- Keep mobile responsiveness when changing navigation or layout.
- Add page-specific CSS/JS through `{% block extra_css %}` and `{% block extra_js %}` rather than editing global markup unnecessarily.
- HTMX interactions still need normal Django permission and validation checks.

## Checks

- After navigation changes, verify authenticated and unauthenticated rendering paths.
- Check that changed links resolve with the expected app namespace.
