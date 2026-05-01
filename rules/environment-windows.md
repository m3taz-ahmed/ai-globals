# Operating Environment Context

## 1. OS & FILESYSTEM
- **OS:** Windows 11.
- **Global Path:** Your global AI rules are strictly located at `D:\server\.ai\`.
- **Local Server Path:** All local development happens within the `D:\server\` directory.
- **Path formatting:** When writing CLI commands, ensure compatibility with Windows PowerShell or CMD. Use appropriate directory separators `\` for local paths, but keep standard `/` for Git or web routing.

## 2. TOOLING LIMITATIONS & FIXES
- **Line Endings:** Be mindful of `CRLF` vs `LF` issues in Windows. Default to `LF` for cross-platform compatibility in code files.
- **Port Conflicts:** If suggesting local server instances, be aware of standard Windows port allocations and suggest alternatives if 80/3306 are busy.