# GoalCompass

GoalCompass is a local-first personal effectiveness assistant. The current
`0.2.0` release contains the manual workflow and the foundation of AI-assisted
configuration.

## Run

```powershell
python run_goalcompass.py
```

The first launch opens the setup wizard. The Control Center contains activity
rules, goals, AI-assisted proposals, operating modes, and application updates.

## Update a local installation

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

## Development checks

```powershell
python -m unittest discover -s tests -v
```
