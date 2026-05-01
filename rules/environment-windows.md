# Operating Environment Context

## 1. OS & FILESYSTEM
- **OS:** Windows 11.
- **Global Path:** Your global AI rules are strictly located at `D:\server\.ai\`.
- **Local Server Path:** All local development happens within the `D:\server\` directory.
- **Path formatting:** When writing CLI commands, ensure compatibility with Windows PowerShell or CMD. Use appropriate directory separators `\` for local paths, but keep standard `/` for Git or web routing.

## 2. TOOLING LIMITATIONS & FIXES
- **Line Endings:** Be mindful of `CRLF` vs `LF` issues in Windows. Default to `LF` for cross-platform compatibility in code files.
- **Port Conflicts:** If suggesting local server instances, be aware of standard Windows port allocations and suggest alternatives if 80/3306 are busy.

## 3. POWERSHELL BEST PRACTICES
- **Encoding:** PowerShell defaults to UTF-16LE. When piping output to files, explicitly set encoding: `[System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))` for BOM-less UTF-8.
- **Execution Policy:** Scripts may require `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`. Never suggest `Unrestricted` or `-Bypass` in production.
- **Path Quoting:** Always quote paths containing spaces. Prefer `Join-Path` over string concatenation for building paths.
- **Error Handling:** Use `$ErrorActionPreference = 'Stop'` at the top of scripts. Wrap critical operations in `try/catch` blocks.

## 4. WSL INTEGRATION
- **When Available:** If WSL 2 is installed, prefer it for running Linux-native tools (Docker, shell scripts, make). Use `wsl` prefix to invoke Linux commands from PowerShell.
- **File Access:** Access Windows files from WSL via `/mnt/c/`. Access WSL files from Windows via `\\wsl$\`. Avoid cross-filesystem I/O for performance-sensitive operations.
- **Docker:** If Docker Desktop is running on WSL 2 backend, Docker commands work natively in both PowerShell and WSL terminals.