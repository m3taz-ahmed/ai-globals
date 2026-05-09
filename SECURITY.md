# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 4.5.x (current) | ✅ Active |
| 4.4.x | ✅ Security fixes only |
| 4.3.x | ⚠️ Critical fixes only |
| < 4.3 | ❌ Unsupported |

---

## Scope

The AI Global OS is a collection of Markdown rule files, PowerShell scripts, and configuration files. The attack surface is narrow but real:

**In Scope:**
- Vulnerabilities in `scripts/validate-globals.ps1` that could lead to unintended file system access or code execution
- Rule files that encode insecure architectural advice (e.g., recommending `$guarded = []`, raw SQL, or disabled CSRF)
- Examples in `EXAMPLES.md` that demonstrate patterns which could mislead engineers into writing insecure code

**Out of Scope:**
- Security issues in projects that *use* this system (report those to the respective project)
- Theoretical threats with no realistic exploit path

---

## Reporting a Vulnerability

> [!CAUTION]
> **Do NOT file a public GitHub Issue for security vulnerabilities.** This exposes the issue to everyone before a fix is available.

### Private Disclosure Process

1. **Email:** Send a detailed report to the maintainer via the contact information on the [GitHub profile](https://github.com/m3taz-ahmed).
2. **Subject line:** `[SECURITY] AI Global OS — [Short Description]`
3. **Include in your report:**
   - Affected file(s) and version
   - Description of the vulnerability
   - Steps to reproduce (if applicable)
   - Potential impact
   - Suggested fix (optional but appreciated)

### Response Timeline

| Stage | Timeline |
|---|---|
| Acknowledgement | Within 48 hours |
| Initial assessment | Within 5 business days |
| Fix & disclosure | Within 30 days (critical: ASAP) |

---

## Security Hall of Fame

*Researchers who have responsibly disclosed vulnerabilities will be credited here with their permission.*

*(No entries yet — be the first!)*

---

## Secure Engineering Commitment

This repository enforces its own security standards:

- All rule files are scanned for credential leakage by `validate-globals.ps1 -SecretScan`
- `.gitignore` prevents `.env` files and secrets from being committed
- All commits are verified against the integrity manifest

*If you find that we're violating our own standards, that's definitely worth reporting.*
