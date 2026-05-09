## Pull Request Checklist

> [!IMPORTANT]
> Please complete all items before requesting review. Incomplete PRs will be returned.

### Type of Change

- [ ] 🐛 Bug fix (corrects a factual error or broken reference)
- [ ] ✨ New tech-stack rule file (`tech-stack/`)
- [ ] 📋 New or updated global rule (`rules/`)
- [ ] 🔄 New or updated workflow (`workflows/`)
- [ ] 📖 New or updated example (`EXAMPLES.md`)
- [ ] 🧰 Script / tooling change (`scripts/`)
- [ ] 📄 Documentation (README, CONTRIBUTING, etc.)

---

### Quality Gates

**Validation:**
- [ ] Ran `.\scripts\validate-globals.ps1` — all checks pass
- [ ] If issues were found, ran `.\scripts\validate-globals.ps1 -Fix` and verified output

**Content:**
- [ ] Every new standard has a concrete code example (❌ wrong vs ✅ correct)
- [ ] No personal or project-specific information included
- [ ] All cross-references use correct notation (`§N` or `ref: filename.md §N`)
- [ ] Speculative/unreleased versions are marked with `[!SPECULATIVE]`
- [ ] Tech-stack files follow naming convention: `{tech}-{version}.md`

**Changelog:**
- [ ] Updated `CHANGELOG.md` under the appropriate version
- [ ] Used Conventional Commit format for commit messages

---

### What Changed and Why

<!-- Describe your changes with surgical precision. Don't say "improved X". Say "changed §3 rule from X to Y because Z". -->

**Files modified:**

| File | Change |
|---|---|
| `tech-stack/xxx.md` | Added §3 Query Standards with N+1 guard |
| `CHANGELOG.md` | Logged change under v4.6.0 |

**Reasoning / Reference:**
<!-- Link to official docs, RFC, or provide your reasoning -->

---

### Testing

<!-- How did you verify this is correct? -->

- [ ] Verified against official documentation: [link]
- [ ] Tested by applying to a real project
- [ ] Cross-referenced with related files to avoid conflicts

---

*By submitting this PR, I confirm that my contributions align with the [Code of Conduct](../CODE_OF_CONDUCT.md) and [Contributing Guidelines](../CONTRIBUTING.md).*
