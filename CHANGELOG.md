# Changelog

All notable GoalCompass changes are recorded here. Versions follow Semantic
Versioning: `MAJOR.MINOR.PATCH`.

## 0.4.1 - 2026-08-14

- Made creation of the GoalCompass desktop shortcut part of every Windows
  installation and update.

## 0.4.0 - 2026-08-14

- Completed the API-free AI-assisted intake workflow using copy/paste or an
  imported JSON, text, or Markdown answer file.
- Added a versioned AI intake response with user context, goals, subgoals, first
  actions, assumptions, missing information, and data-confidence metadata.
- Added tolerant structured-response parsing and a readable review before data
  is saved or an AI proposal is applied.
- Added installed-app update checks through GitHub Releases, versioned installer
  download, mandatory SHA-256 verification, and installer launch.
- Added Control Center and update shortcuts to the Windows Start Menu, plus
  **Help → Check for updates...** inside Control Center.

## 0.3.1 - 2026-08-12

- Replaced the empty AI-assisted setup screen with a guided wishes intake.
- Added ready-made starting options for work, languages, health, and projects.
- Added life-area, realistic-effort, and obstacle context for AI planning.
- Prevented copying an empty AI request and added one-click answer pasting.
- Required AI proposals to include concrete success criteria and practical subgoals.

## 0.3.0 - 2026-08-12

- Added a self-contained Windows application bundle and setup executable.
- Added per-user installation, Start Menu and optional desktop shortcuts.
- Preserved the local database, runtime state, and personal configuration during
  upgrades and uninstall by default.
- Added a unified packaged entry point for the tracker, overlay, setup wizard,
  and Control Center processes.

## 0.2.0 - 2026-08-12

- Added Manual and AI-assisted automation modes.
- Added Silent, Standard, Proactive, and Intensive interaction policies.
- Added independent coach enablement and communication styles.
- Added validated AI proposals with preview, confirmation, and local audit history.
- Added application version reporting and safe GitHub-based local updates.
- Kept runtime state, personal configuration, and the activity database outside Git.
