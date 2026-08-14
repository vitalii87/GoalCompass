# GoalCompass

GoalCompass is a local-first personal effectiveness assistant. The current
`0.4.0` release contains the manual workflow and a copy/paste AI-assisted
configuration workflow that does not require an API key.

## Install on Windows

Download and run `GoalCompass-Setup-0.4.0.exe`. It installs GoalCompass for the
current Windows user and does not require a separate Python installation.

Installing a newer setup file over the existing installation updates program
files while preserving the local activity database and personal settings.

## Run

```powershell
python run_goalcompass.py
```

The first launch opens the setup wizard. The Control Center contains activity
rules, goals, AI-assisted proposals, operating modes, and application updates.

## Update an installed application

Open **GoalCompass Control Center** from the Start Menu or click the gear in the
overlay. Then use **Help → Check for updates...** or the **Updates** tab.

Installed builds check the latest GitHub Release, download the matching Setup
file, verify its SHA-256 digest, and start the installer after confirmation.
Profiles, settings, activity history, and proposal history remain local.

## Update a source checkout

Close the GoalCompass tracker and overlay before installing an update. Then use
the **Updates** tab in Control Center, or run:

```powershell
python update_goalcompass.py
python update_goalcompass.py --install
```

Updates use the configured Git remote and only accept a fast-forward update.
They stop when program files contain uncommitted changes. Runtime state,
personal configuration, AI proposal history, and the activity database stay
local and are not replaced by updates.

## Versioning

GoalCompass follows Semantic Versioning:

- `MAJOR`: incompatible data or behavior changes;
- `MINOR`: backward-compatible features;
- `PATCH`: backward-compatible fixes.

The installed version is stored in `VERSION`. Release history is in
`CHANGELOG.md` and Git tags use the `vMAJOR.MINOR.PATCH` form.

## Build the Windows installer

The build requires 64-bit Python 3.12 and Inno Setup 6 or 7:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_installer.ps1
```

The setup executable is written to `artifacts/`. Packaging output is intentionally
excluded from Git; source configuration for reproducing it is committed.

## Development checks

```powershell
python -m unittest discover -s tests -v
```
