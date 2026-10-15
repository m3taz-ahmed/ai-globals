# aiZee — خطة التطوير الدوري: implementation_plan.md

**التاريخ:** 2026-10-15 · **الأساس:** main @ `dde73b2` (شجرة نظيفة عدا MAINTENANCE_PROMPT.md)
**الشخصيات:** ARCH + QA + SEC + DEV · **النطاق:** ترقيات تطويرية جراحية — بلا تغيير هوية، بلا كسر سلوك، بلا بنية ثقيلة.

> الدورة السابقة (2026-10-11) نُفّذت بالكامل في `dde73b2`: lazy `runtime/__init__.py`،
> خدمات kernel كسولة، manifest lock، advisory lint، auto-compact. هذه الخطة تغطي ما تبقّى وما ظهر جديدًا.

---

## 1. خط الأساس — ما هو أخضر الآن (مقاس مباشرة)

| البوابة | النتيجة |
|---|---|
| `ruff check .` | ✅ 0 تحذير |
| `aizee doctor` | ✅ 49/49 ok + جدول توصيل صادق (25 orphan / 18 lazy بلا callers) |
| `aizee security scan runtime/` | ✅ PASS — 0 blockers / 0 high / 69 medium / 69 low (+9 suppressed) |
| الاستيراد/الإقلاع | `import runtime` ≈0.01s · `Kernel()` ≈0.13s (v6.3 تم ذلك) |
| Memory ingest | sha256 manifest dedup + حذف المصادر القديمة + IDs حتمية + vectors للجديد فقط — محسّن أصلًا |
| التغطية | 100% enforced (`--cov-fail-under=100`)، 7731 اختبارًا أخضر عند آخر release |

## 2. المكتشفات الجديدة (Findings)

| # | الخطورة | المكتشفة | الدليل |
|---|---------|----------|--------|
| F1 | **عالية (صدق)** | **انحراف إصدار:** commit `dde73b2` يدّعي "bump to 6.3.0" لكن `pyproject.toml` ما زال `6.2.0` ← `config.VERSION`← mcp clientInfo ← `aizee version` ← doctor كلها تقول 6.2.0. والعمل كله تحت `[Unreleased]` في CHANGELOG — لا قسم `[6.3.0]`. | `git show HEAD:pyproject.toml`، `grep "^## \[" CHANGELOG.md` |
| F2 | **متوسطة (أمن)** | **بصمة manifest lock تغطي الوصف فقط.** `_verify_manifest_lock` يبصم `tool.description` — تغيير `inputSchema`/`parameters` (rug-pull عبر إعادة تعريف الوسائط) يمر دون كشف. الحل متاح: `Tool.parameters` موجود في mcp 2.x. | `aizee_server.py:309-311`، `mcp_manifest_lock.py:39` |
| F3 | **متوسطة (دين)** | **محركان جاهزان بلا call site:** `supply_chain_guard` (794 سطرًا — يكشف `import` غير معلن في lockfile: صميم مهمة aiZee ضد وكلاء يضيفون تبعيات صامتة) و`mcp_auditor` (658 سطرًا — 14 كاشفًا حتميًا لإعدادات خوادم MCP). كلاهما orphan/lazy اليوم. | doctor wiring table |
| F4 | **منخفضة (نظافة)** | ترقيات **ضمن الـpins** معلقة: mcp 2.2.0→2.3.0 · pydantic 2.13.5→2.14.1 · cryptography 50.0.1→50.0.2 (patch أمني) · turbovec 1.0.0→1.1.2 · graphifyy 0.9.72→0.9.91 · ruff 0.16.9→0.17.1 · mypy 2.3.1→2.4.0 | `pip list --outdated` |
| F5 | **منخفضة (ضجيج)** | الفحص الأمني يعدّ النتيجة مرتين: bandit+ruff يُبلغان نفس السطر (مثل `storage_backend.py:248`). إزالة التكرار بـ(file,line,category) تقطع الضجيج. الفحص نفسه سليم — `_TABLE_RE.fullmatch` يجعل إنذارات SQL في storage_backend إيجابيات كاذبة مُتحقق منها. | تقرير الفحص المباشر |
| F6 | **تجميلية** | `ACTIVE_CONTEXT.md` متقادم (5.15.0 / checkpoint 2026-09-25) — يُحدَّث آخر الجلسة على أي حال. | قراءة الملف |

## 3. الترقيات المقترحة (مفلترة بـ Ponytail)

### P0 — الصدق والأمن (جراحي، كل ملف ≤ ~15 سطرًا)

- **P0-a. إصلاح انحراف الإصدار:** `pyproject.toml` → `6.3.0` + قص قسم `## [6.3.0] - 2026-10-11` في CHANGELOG (نقل عناصر `[Unreleased]` إليه) ليتطابق reality مع ادعاء الـcommit. mcp clientInfo يقرأ `config.VERSION` تلقائيًا — لا لمس إضافي.
- **P0-b. بصمة الـmanifest تشمل الـschema:** في `_verify_manifest_lock` البصمة تصبح `sha256(description ‖ json.dumps(tool.parameters, sort_keys=True))` — يُكتشف rug-pull عبر الوسائط. بلا تغيير API (القيمة تبقى نصًا). اختبار: تعديل schema أداة → drift يظهر.
- **P0-c. توصيل `supply_chain_guard` ← `aizee security scan`:** مرحلة كاشف مدمجة تمشي على `*.{py,ts,tsx,js,php,go,rs}` وتنادي `check_file` — بلا API جديد. نتائج `UndeclaredImport` تصبح findings بفئة A03-supply-chain. يقلب orphan → cli-wired ويغلق فجوة "وكيل يضيف تبعية غير معلنة".
- **P0-d. توصيل `mcp_auditor` ← `aizee security mcp`:** أمر فرعي جديد يمرّر `aizee_mcp/config.json` + إعدادات MCP العامة المكتشفة إلى `McpAuditor.scan_config` ويطبع الـ14 كاشفًا. يقلب lazy → cli-wired.

### P1 — قدرات MCP (حداثة بلا تكلفة)

- **P1-a. Tool annotations (معيار MCP الحديث):** `ToolAnnotations` مدعومة في mcp 2.x المثبت (`read_only_hint`/`destructive_hint`/`idempotent_hint`/`open_world_hint`) و`MCPServer.tool()` يقبل `annotations=`. خريطة مركزية في `tools/common.py` (بحث/قراءة/سرد → `readOnlyHint=True`؛ كتابة → `idempotent/destructive=False`) تُطبَّق بعد التسجيل في pass واحد بجانب `_apply_rbac_guard`. النتيجة: عملاء IDE يميّزون القراءة الآمنة من الكتابة — موافقة-تلقائية أذكى. ~40 سطرًا، صفر تغيير سلوك.
- **P1-b. (اختياري) كشف imports غير معلنة داخل `lint_python`:** إضافة `scan_source(source, suffix)` (~10 أسطر — فصل استخراج imports عن قراءة الملف في `scan_imports`) ثم سطر واحد في advisory block بجانب hallucination/stale-api. الفرق عن hallucination detector: ذاك يمسك حزمًا غير موجودة، وهذا يمسك حزمًا موجودة لكن **غير معلنة** في المشروع.

### P2 — نظافة وDevEx

- **P2-a. ترقية التبعيات ضمن الـpins** (القائمة في F4) + إعادة تشغيل البوابات كاملة.
- **P2-b. dedupe في `security_scanner`:** نفس (file,line) من ماسحين → نتيجة واحدة (تفضيل الأعلى severity أو الأول).
- **P2-c. تحديث `ACTIVE_CONTEXT.md` + Memory.md** (milestones، عادات الجلسة الطبيعية).

### استُبعد بفلتر Ponytail
حذف الـorphans الجماعي بلا قرارك الصريح · `dual_llm`/LLM-judge حي (يتطلب مفاتيح LLM) · قواعد vector خارجية/Postgres/Redis · واجهات dashboard جديدة · تقسيم god-classes (MemoryStore/Kernel/DashboardHandler — متوسط المخاطر، يُؤجّل لحين جراحة فعلية) · spec-converge CI (لا `specs/` في هذا الريبو) · `output_gate` كـhook افتراضي (hook `output.pre_send` موجود لمن يريد تسجيله؛ فرضه يغيّر سلوك chat).

## 4. خطة التنفيذ (عند الموافقة)

| الترتيب | البند | نصف قطر الانفجار | التحقق |
|---|---|---|---|
| 1 | P0-a إصلاح الإصدار | `pyproject.toml` + `CHANGELOG.md` | `aizee version` يطبع 6.3.0 |
| 2 | P0-b بصمة schema | `aizee_mcp/aizee_server.py` + اختباران | drift على تغيير schema |
| 3 | P0-c supply_chain في scan | `runtime/security_scanner.py` (+ ~30 سطرًا) | مشروع تجريبي بـimport غير معلن → finding |
| 4 | P0-d `security mcp` | `aizee_cli.py` (+ ~40 سطرًا) | يكشف config تجريبيًا ملوثًا |
| 5 | P1-a annotations | `tools/common.py` + pass واحد | smoke: `list_tools` يعرض hints |
| 6 | P1-b lint_python (إن وُقعّت) | `supply_chain_guard.py` + `policy_tools.py` | كود بـimport غير معلن → advisory |
| 7 | P2-a ترقية التبعيات | `pip install` ضمن pins | كل البوابات خضراء |
| 8 | P2-b dedupe الفاحص | `security_scanner.py` (~10 أسطر) | تعداد findings ينخفض دون فقد |

**البوابات بعد التنفيذ:** `ruff check .` · `mypy` (strict) · اختبارات موجّهة لكل تغيير · `aizee test --full` + `python eval/harness.py` قبل إعلان الإنجاز · `aizee security scan` نظيف · بلا commit دون موافقتك.

## 5. قرارات مطلوبة منك

1. **مصير الـ23 orphan المتبقية** (بعد توصيل supply_chain_guard + mcp_auditor):
   - **A (الأكثر أمانًا):** إبقاء مُعلَّمة كما اليوم — صفر مخاطرة، الدين يبقى مرئيًا.
   - **B:** حذفها + اختباراتها (~7k LOC أقل، coverage تبقى 100% لأن الاختبارات تُحذف معها) — أقصى تدمير للدين، والكود محفوظ في تاريخ git.
   - **C:** توصيل المزيد أولًا (مثل `service_catalog` ← `search_skills`، `output_gate` ← `output.pre_send`) قبل أي حذف.
2. **P1-b** (imports غير معلنة داخل lint_python): أُدرج أم أكتفِ بـ scan؟
3. **P2-a نطاق الترقيات:** الكل ضمن الـpins، أم الأمني فقط (cryptography/mcp/pydantic)؟
4. **أدوات MCP جديدة** (`aizee doctor`/`security scan` كأداتين — أُجّلتا الدورة الماضية): السطح 39→41، موافق؟

---

# خطة تكميلية — تكامل أبحاث خارجية (2026-10-15)

المصادر: `affaan-m/ecc` (AgentShield/GateGuard/unified-memory/instincts)،
`Panniantong/agent-reach` (router+doctor+install-contract)،
`roundly-consulting/auth-for-laravel` (مرجع stack)، `ecc.tools` (أفكار منتج).
المبدأ: أفكار فقط فوق بنية aiZee — لا vendored code، لا تبعيات جديدة.

## التنفيذ (معتمد بالكامل A–F)

| # | البند | الملفات |
|---|-------|---------|
| A | تعميق فحص أسرار `security mcp` (args + بادئات + unpinned + writable) | `runtime/mcp_auditor.py`, `tests/runtime/test_mcp_auditor.py` |
| B | `fact_force` guardrail للعمليات القابلة للاسترداد | `runtime/agent_gateway.py`, `tests/runtime/test_agent_gateway_gaps.py` |
| C | نطاقات ذاكرة + fail-closed vault guard + handoffs | `memory/handoff.py` (جديد), `aizee_cli.py`, `tests/test_memory_handoff.py` |
| D | prompt-defense baseline في القواعد المُصدَّرة | `runtime/rules_materializer.py`, `tests/test_rules_materializer.py` |
| E | مرجع auth-for-laravel + عقد تثبيت agent-readable | `tech-stack/auth-for-laravel.md`, `docs/INSTALL_CONTRACT.md` |
| F | instincts (scope+confidence+promote) فوق MemoryStore | `memory/instincts.py` (جديد), `memory/store.py` (`update_meta`), `aizee_cli.py`, `tests/test_memory_instincts.py` |

## مرفوض صراحةً (Ponytail)
- Plan Canvas / Control Pane (UI متصفح، بنية ثقيلة)
- GitHub App / SaaS layer
- استيراد دفعة 311 سكيل — جوهر aiZee قليل-ومكثّف
- تبعية npm/Node

## حادثة مسجّلة
اختبار يدوي بـ`AIZEE_ROOT` يشير لمرآة النشر كتب handoff في `aizee\brain\` —
نُظّف فورًا. القاعدة: اختبارات scoped تمرّر `--root`/`--project` للريبو العامل.
