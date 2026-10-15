# aiZee — Agent-Readable Install Contract

Machine-readable boundaries for any agent installing, updating, or uninstalling
aiZee. Read this BEFORE running `install.bat`, `update.bat`, or `uninstall.bat`.

## Contract: `aizee.install.v1`

```yaml
schema: aizee.install.v1
entry_points:
  install: install.bat      # first-time install into the deployment root
  update: update.bat        # sync working repo -> deployment root
  uninstall: uninstall.bat  # remove deployment root
  backup: backup.bat        # snapshot deployment root
  restore: restore.bat      # restore a snapshot
boundaries:
  # Hard limits — violating any of these aborts the operation.
  - DO NOT run any script with elevation (sudo / Run-As-Administrator).
  - DO NOT modify files inside the deployment root directly — it is read-only;
    changes land via update.bat from the working repo only.
  - DO NOT pass user-supplied paths to any script; scripts take no arguments.
  - DO NOT run install.bat when the deployment root already exists — back up
    first, then decide.
  - DO NOT run uninstall.bat without explicit human approval — it deletes the
    deployment root.
  - DO NOT interrupt update.bat mid-run; partial sync leaves the deployment
    root inconsistent.
workspace:
  writes_allowed:
    - <deployment_root>            # the scripts' own target
    - <repo>/state/                # runtime state
    - <repo>/brain/                # project memory (gitignored, fail-closed)
  writes_forbidden:
    - anywhere outside the two roots above
    - system directories, PATH entries, shell profiles
verify:
  # Run AFTER install/update — must all pass before declaring done.
  - aizee doctor                  # 49/49 checks
  - aizee version                 # matches pyproject.toml
  - aizee security scan --quick   # 0 blockers
secrets:
  # Scripts never prompt for or echo secrets. If a step asks for a token or
  # prints one, abort and report.
  - NEVER set AIZEE_INTEGRITY_KEY inside the deployment root state dir.
```

## Human notes

- The working repo and the deployment root are different directories; only
  `update.bat` may copy between them.
- These boundaries apply to agents AND humans. If a script violates one, the
  script has a bug — do not work around it.
