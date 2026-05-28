# Operating Environment Context
> [!NOTE]
> Trigger: CLI commands, scripting, path handling.

## OS & Filesystem `[ENV-02]`
- **OS:** Windows 11.
- **Paths:** AI root `D:\server\.ai\`. Development inside `D:\server\`. Use `\` for PowerShell/CMD, quote paths with spaces.
- **Line Endings `[ENV-03]`:** Default to `LF` for cross-platform compatibility.

## PowerShell Best Practices `[ENV-01]`
- **Encoding:** Explicitly write BOM-less UTF-8 in scripts: `[System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))`.
- **Policy:** Suggest `RemoteSigned` for local script runs, not `Unrestricted`.
- **Errors:** Mandate `$ErrorActionPreference = 'Stop'` and use `try/catch`.

## WSL & Containers `[ENV-02]`
- **WSL:** Use WSL 2 for Linux-native tooling (e.g. `wsl` command prefix).
- **Paths:** `/mnt/c/` in WSL, `\\wsl$\` in Windows. Avoid cross-filesystem I/O for heavy tasks.
- **Docker:** Integrates natively if WSL 2 backend is enabled.
