[TECH] environment-windows
[OBJ] Operating Environment Context (Windows/WSL).
[RULES]
1. [REQ] Paths `[ENV-02]`: Root `D:\server\.ai\`. Dev `D:\server\`. Use `\` for PS/CMD.
2. [REQ] Format `[ENV-03]`: Default to LF line endings.
3. [REQ] PowerShell `[ENV-01]`: BOM-less UTF-8. `$ErrorActionPreference = 'Stop'`. `try/catch`.
4. [REQ] WSL: Use WSL 2 for Linux tooling. Paths: `/mnt/c/` or `\\wsl$\`. Avoid cross-FS heavy IO.
