<div align="right" dir="rtl">
  <img src="logo.png" width="160" alt="شعار aiZee">
  <h1>aiZee — نظام التشغيل العالمي للذكاء الاصطناعي</h1>
  <p><strong>حول أي مساعد ذكاء اصطناعي إلى مهندسك الرئيسي — سيادة كاملة، جودة صفرية العيوب.</strong></p>

  <p>
    <img src="https://img.shields.io/badge/%D8%A5%D8%B5%D8%AF%D8%A7%D8%B1-5.8.0-6C63FF?style=for-the-badge&logo=buffer&logoColor=white&labelColor=1a1a2e" alt="الإصدار 5.8.0">
    <img src="https://img.shields.io/badge/%D8%A7%D8%AE%D8%AA%D8%A8%D8%A7%D8%B1%D8%A7%D8%AA-3687%20%D9%86%D8%A7%D8%AC%D8%AD-00C896?style=for-the-badge&logo=pytest&logoColor=white&labelColor=1a1a2e" alt="3687 اختبار ناجح">
    <img src="https://img.shields.io/badge/%D8%AA%D8%BA%D8%B7%D9%8A%D8%A9-95%25-10B981?style=for-the-badge&logo=codecov&logoColor=white&labelColor=1a1a2e" alt="تغطية 95%">
    <img src="https://img.shields.io/badge/%D8%A7%D9%84%D8%B1%D8%AE%D8%B5%D8%A9-MIT-3B82F6?style=for-the-badge&logo=opensourceinitiative&logoColor=white&labelColor=1a1a2e" alt="الرخصة: MIT">
  </p>
  <p>
    <img src="https://img.shields.io/badge/%D8%B4%D8%AE%D8%B5%D9%8A%D8%A7%D8%AA-22-EC4899?style=for-the-badge&logo=buffer&logoColor=white&labelColor=1a1a2e" alt="22 شخصية">
    <img src="https://img.shields.io/badge/%D9%85%D9%87%D8%A7%D8%B1%D8%A7%D8%AA-80-10B981?style=for-the-badge&logo=checkmarx&logoColor=white&labelColor=1a1a2e" alt="110 مهارة">
    <img src="https://img.shields.io/badge/%D8%B3%D9%8A%D8%B1_%D8%A7%D9%84%D8%B9%D9%85%D9%84-54-0EA5E9?style=for-the-badge&logo=checkmarx&logoColor=white&labelColor=1a1a2e" alt="54 سير عمل">
    <img src="https://img.shields.io/badge/%D9%85%D8%B1%D8%A7%D8%AC%D8%B9_%D8%AA%D9%82%D9%86%D9%8A%D8%A9-173-F59E0B?style=for-the-badge&logo=sparkles&logoColor=white&labelColor=1a1a2e" alt="173 مرجع تقنية">
  </p>
</div>

---

<div dir="rtl">

[اقرأ النسخة الإنجليزية](README.md) · [سجل التغييرات](CHANGELOG.md) · [دليل التثبيت](#التثبيت)

---

## ما هو aiZee؟

**نظام تشغيل محكم الإصدار** يجلس بينك وب كل مساعد ذكاء اصطناعي — Cursor، Claude، Copilot، Windsurf، Cline، Aider، Devin — ويفرض معايير الهندسة وسياسات الأمان والانضباط المعماري على كل سطر كود مولّد.

**المشكلة التي يحلها:** المساعدات الذكية تهلوس APIs، تنسى الاتفاقيات، تتجاهل الأمان، وتشحن ديونًا تقنية صامتة. aiZee يجبرها على القراءة من مصدر حقيقة مركزي *قبل* كتابة سطر واحد.

| بدون aiZee | مع aiZee |
| :--- | :--- |
| انحراف السياق بعد عدة prompts | القواعد والشخصيات تُحمّل كل جلسة |
| حزم قديمة وديون تقنية صامتة | تثبيت إصدار دقيق عبر MCP حي |
| SQL خام، XSS مفقود، أسرار ضعيفة | OWASP و zero-trust و RBAC مفروضة |
| إعادة هيكلة عشوائية | تغييرات جراحية عبر بوابات policy + budget + audit |
| إجابات واحدة-للجميع | 22 شخصية + 80 مهارة تُختار تلقائيًا |

---

## البدء السريع

### المتطلبات

| المتطلب | الحد الأدنى | الموصى به |
| :--- | :--- | :--- |
| Python | 3.10 | 3.12 |
| Git | 2.30+ | الأحدث |
| النظام | Windows 10 / macOS 12 / Ubuntu 22.04 | الأحدث |

### التثبيت

```bash
git clone https://github.com/m3taz-ahmed/ai-globals.git .ai
cd .ai
```

**Windows — واجهة رسومية** (double-click على `install.bat` أو):
```powershell
.\install.ps1 -Gui
```

**Windows — سطر أوامر:**
```powershell
.\install.ps1
```

**macOS / Linux:**
```bash
bash install.sh
```

### التحقق

```bash
aizee doctor    # فحص صحة
aizee status    # الشخصية، المهارات، الميزانية
```

---

## الأعمدة الستة

### 1. الشخصيات + المهارات
22 شخصية (`ARCH`، `QA`، `SEC`، `DEV`، `SRE`، `DATA`، `ML`، `DEVOPS`، `FREELANCE`، إلخ) مع 29 مهارة lord. تُكتشف تلقائيًا حسب المهمة.

```bash
aizee persona detect --multi "ابني API آمن مع docker و postgres"
# ← Primary: ARCH + Secondary: SEC, DEVOPS + Lords: security-lord, cloud-platforms-lord
```

### 2. حوكمة Runtime
كل إجراء يمر عبر 5 بوابات قبل التنفيذ:

```
Probity → Guardian → Policy → Budget → Audit
```

- **محرك السياسات** — قواعد YAML مع تقييم AST آمن
- **مدير الميزانية** — حدود tokens/تكلفة/استدعاءات لكل جلسة/ساعة/يوم
- **سجل التدقيق** — سلسلة SHA-256 مقاومة للتلاعب
- **مشغل سير العمل** — تنفيذ متين مدعوم بـ SQLite + saga

### 3. مصدر الحقيقة الحي
Context7 MCP يجلب توثيق المكتبات الحالي قبل التنفيذ. Graphify يستبدل `grep` الأعمى للتنقل في الكود.

### 4. ذاكرة هجينة
SQLite + FTS5 + فهرسة متجهة اختيارية. طبقات: عرضية، دلالية، واقعية، إجرائية.

### 5. بوابات الجودة (عيب صفر)
```bash
ruff check .          # 0 تحذيرات
mypy                  # 0 أخطاء (345 ملف، strict)
pytest -q             # 3561 اختبار، 95% تغطية
python eval/harness.py  # E2E: ruff + mypy + pytest + validate-globals
```

### 6. كفاءة Tokens
كشف الشخصيات محلي (Python خالص، صفر tokens). فقط أسماء المهارات relevant تُرجع — ليس الملفات كاملة.

---

## الجديد في v5.6.0

### إصلاحات أمنية حرجة (3)
- **ثغرة تصعيد صلاحيات في مُقيِّم السياسات** (`runtime/policy.py`): القيم الحرفية `true`/`false`/`null` كانت تُعامل كأسماء متغيرات → `flag == true` تطابق كل إجراء يفتقد flag (`None == None → True`) → قاعدة `reversible == true → allow` كانت توافق تلقائيًا على كل write/edit. الإصلاح بـ `_yaml_literals` + fail-closed لـ TypeError. 13 اختبار ارتداد.
- **Guardian fail-closed**: استثناء الـ guardian لم يعد يُبتلع كـ allow — يُنكر مع audit log.
- **إزالة approve-via-GET**: `GET /api/check?approve=1` يرجع 400، وGET دائمًا `dry_run=True`. أغلق ثغرة CSRF من localhost.

### Dashboard (قرارات تصميمية)
- **Open-access افتراضي**: التوكن opt-in عبر `AIZEE_DASHBOARD_TOKEN` فقط. الأمان محفوظ بربط 127.0.0.1 + CSRF header على POSTs.
- **تقديم الـ UI من `_CODE_DIR`** بدلاً من root المُكتشَف — يمنع mismatch بين server جديد وmarkup قديم.
- **CSP**: أزال `'unsafe-inline'` من script-src — كل JS انتقل لـ `dashboard/app.js` خارجي.

### إعادة هيكلة (Refactors)
- **`spec_engine.py` (876 سطر) → `runtime/spec/` package** (models/engine/scaffold/analysis/templates) مع facade للتوافق العكسي.
- **`inject_persona_context()`** — يوحّد 3 كتل مكررة (kernel/workflow_manager/workflow).
- **`READ_ACTIONS`** مصدر واحد لتصنيف read-only.
- **`LocalResponder`** (جديد) — يجاوب على intents تشغيلية من حالة kernel الحية بدون LLM tokens.

### تقوية Memory/Adapters
- `checkpoint.py`: RLock حول اتصال SQLite المشترك.
- `vector.py`: `blake2b` deterministic بدلاً من `hash()` المملّح.
- `git_memory.py`: `_safe_component` regex يمنع path traversal.
- `adapters.py`: SSL context مُ memoized + `verify_ssl=False` فعّال فعليًا + `request_timeout`.

### أدوات + توثيق
- **`scripts/sync_docs.py`** (جديد): يزامن counts + جدول workflows من filesystem. `--check` مربوط بـ CI.
- **`CONTRIBUTING.md`** (جديد): معايير الكود + وصفات module/skill/workflow.
- **CLI**: أخطاء ودودة للـ JSON تالف بدلاً من tracebacks.
- **Counts مُحدّثة**: 96 runtime modules، 80 skills، 50 workflows، 173 tech-stack refs.

---

## الجديد في v5.5.0

### تكامل SEO (دراسة 5 ريوهات + 5 أدوات → aiZee)
تحليل عميق لأفضل 5 ريوهات SEO على GitHub (claude-seo, open-seo, crawlseo, SEOmator, rustyseo) + 5 أدوات بناء SEO (GSC API, DataForSEO, Playwright, Common Crawl, Lighthouse/PSI):

- **مهارة `seo-lord`** (جديد، هيكل مجلد): SKILL.md (20 قاعدة) + 7 مراجع (technical-seo, content-eeat, schema-types, geo-aeo, cwv-thresholds, audit-rules 251 قاعدة, health-scoring) + 2 قوالب (seo-audit-report, content-brief)
- **`tech-stack/seo-1.md`** (جديد): 35 قاعدة SEO تقنية
- **`workflows/27-seo-audit.md`** (جديد): بروتوكول تدقيق SEO من 21 خطوة
- **8 أدوات MCP SEO** (جديد، stdlib فقط، مجانية): `seo_audit_page`, `seo_audit_site`, `seo_check_cwv`, `seo_validate_schema`, `seo_analyze_content`, `seo_check_geo`, `seo_get_gsc_data`, `seo_find_opportunities`
- **`useful-repos.md`**: +10 إدخالات (5 ريوهات SEO + 5 أدوات بناء)
- **`personas.yaml`**: تسجيل seo-lord (40 كلمة مفتاحية بما فيها العربية) + ربط بشخصيات ARCH/DEV/UX/DOC

### مراجعة 5 شخصيات (4 جولات: ARCH + DEV + QA + SEC + DOC)
إصلاح كل المشاكل الحرجة:
- التحقق من URL: رفض صريح لمخططات `javascript:`/`data:`/`file:`/`ftp:`/`mailto:`
- حماية SSRF: حظر IP الخاص + فحص DNS rebinding + التحقق من redirect targets (`_SsrfSafeRedirectHandler`)
- محلل HTML: التقاط نص الرابط، tag stack للوسوم المتداخلة، معالجة HTML المشوه
- `_strip_html`: معالجة CDATA + تعليقات HTML + التعليقات الشرطية + regexes مُجمّعة
- `_classify_schema`: دعم حاويات `@graph` (list + dict + empty)
- `seo_audit_site`: تطبيع URL + deque BFS + تصفية روابط case-insensitive
- `seo_audit_page`: فحص nofollow + viewport meta
- `seo_analyze_content`: تقسيم الفقرات بحدود الجمل
- `seo_find_opportunities`: empty rows → نجاح، تخطي position≤0، إزالة تكرار cannibalization
- عقد Schema: تحديث `SeoAuditSchema` لمطابقة الاستجابة الفعلية

### الاختبارات
- **132 اختبار SEO جديد** (حالات حدية، كل الـ 8 أدوات، SSRF، HTML مشوه، @graph، تطبيع URL، تقسيم فقرات، nofollow/viewport، cannibalization)
- **982 اختبار ناجح**، تغطية 97%، 0 فشل

---

## الجديد في v5.3.0

### إثراء المراجع التقنية لـ Laravel/Filament (دراسة 10 مشاريع)
تحليل عميق لـ 10 مشاريع GitHub رائدة (Bagisto, Monica, Krayin, BookStack, Koel, Filament, SuperDuper, Sky, MVPable, Filament-Blog):

- **7 ملفات مراجع تقنية** (4 محدّثة + 3 جديدة): `laravel-12`, `laravel-13`, `filament-4`, `filament-5`, `laravel-testing` (جديد), `laravel-security` (جديد), `filament-plugins` (جديد)
- **2 مهارة محدّثة**: `backend-frameworks-lord` (20 قاعدة), `page-sections-lord` (32 قاعدة)
- **3 سير عمل جديد**: `24-laravel-architecture-setup`, `25-filament-plugin-development`, `26-laravel-api-versioning`
- **`useful-repos.md`**: 10 مشاريع Laravel + Filament جديدة

### تحسينات Runtime (أنماط مستوحاة من Filament)
- **دورة حياة البلوجين ذات الطورين**: `register()` + `boot()` (نمط Filament Plugin)
- **مُقيّم الإغلاقات**: حقن تلقائي لتبعيات الإغلاقات (نمط Filament EvaluatesClosures)
- **تبعيات الصلاحيات**: التحقق من المتطلبات المسبقة في Guardian (نمط Monica BaseService)
- **مخططات استجابة MCP**: ثوابت JSON_STRUCTURE لاستجابات أدوات متناسقة (نمط Koel)
- **التحقق التلقائي في authorize()**: Guardian يتحقق تلقائياً من تبعيات الصلاحيات عند ALLOW

### إصلاحات الأخطاء + تنظيف Lint (52 → 0 خطأ)
- إصلاح 52 خطأ ruff عبر `runtime/`, `aizee_mcp/`, `memory/`, `scripts/`, `eval/`
- إصلاح 30 خطأ mypy `untyped-decorator` عبر `pyproject.toml` override
- إصلاح `asyncio.TimeoutError` غير مُلتقط في `adapters.py` (توافق Python 3.10)
- إصلاح أحرف unicode مشوهة في `migrations.py`, `spec_engine.py`, `git_memory.py`
- إضافة `UP017` لقائمة تجاهل ruff (توافق Python 3.10 — `datetime.UTC` يتطلب 3.11+)

### الاختبارات
- **45 اختبار جديد** (مُقيّم الإغلاقات، مخططات MCP، دورة حياة الطورين، تبعيات الصلاحيات)
- **2773 اختبار ناجح**، تغطية 97%، 0 فشل

### مراجعة 3 شخصيات
كل التغييرات تمت مراجعتها بواسطة شخصيات ARCH + DEV + QA-SEC — 44/44 نقطة مُتحققة.

## الجديد في v5.2.0

### تقوية وتلميع (P0-P3)
- **إصلاح Dockerfile**: `cli.py` → `aizee_cli.py`، Python 3.14
- **توحيد هرم الاستثناءات**: كل الاستثناءات ترث من `AizeeError`
- **تشفير آمن افتراضياً**: توليد مفتاح تلقائي عند عدم وجود `AIOS_ENCRYPTION_KEY`
- **تقوية token الداشبورد**: `chmod 0o600` على ملف الـ token
- **إيقاف آمن**: flush التخزين + إغلاق DB عند SIGTERM/SIGINT
- **تدوير السجلات**: audit.log + telemetry.jsonl يتدورون عند 100MB
- **تقوية CSP**: `object-src 'none'`, `base-uri 'self'`, `frame-ancestors 'none'`
- **قائمة بيضاء لـ .env**: فقط المتغيرات المعروفة تُحمّل
- **تنقيح audit**: تنقيح يعتمد على اسم المفتاح وليس القيمة فقط
- **تقوية sandbox الإضافات**: حظر builtins خطرة، `literal_eval`
- **صلاحيات الإضافات قائمة على الموارد**: أنماط glob (`Write:/tmp/*`)
- **اكتشاف تلقائي لأدوات MCP**: مسح `aizee_mcp/tools/*_tools.py`
- **rollback للهجرات**: `MigrationRunner.rollback(version)`
- **KernelBuilder**: builder fluent لحقن التبعيات
- **تجميع اتصالات DB**: `BaseRepository` يجمع اتصالات SQLite
- **أتمتة نسخ DB احتياطية**: `--schedule daily/hourly` + `--verify`
- **تكامل Self-healing**: `AgentManager.check_agents_health()` + `respawn_agent()`
- **وثائق تشغيلية**: `docs/OPERATIONS.md`, `docs/DEPLOYMENT.md`, `docs/ONBOARDING_SRE.md`
- **تنظيم الاختبارات**: نقل من `tests/runtime/` إلى `runtime/tests/`
- **اختبارات parameterized**: المزيد من `@pytest.mark.parametrize`
- **mock time في الاختبارات**: `time.sleep()` no-op في الطبقة السريعة
- **مصفوفة CI**: Python 3.13 + 3.14
- **تضييق NumPy**: `>=1.26.0,<2.0`
- **مزامنة API.md**: 5.2.0
- **تحذير K8s secret**: تعليق على placeholder

## الجديد في v5.0.0

### 18 ميزة أصلية

من تحليل تنافسي شامل لأدوات حوكمة الوكلاء الذكيين:

| الميزة | الوحدة | الغرض |
| :--- | :--- | :--- |
| سجل تدقيق بسلسلة hash | `runtime/audit.py` | مسار إجراءات مقاوم للتلاعب |
| محرك تقييم الوكلاء | `eval/agent_benchmark.py` | قياس أداء الشخصيات |
| OWASP Agentic Top 10 | `runtime/agentic_security.py` | 10 ضوابط أمان للأنظمة الوكلاء |
| ذاكرة مدعومة بـ git | `memory/git_memory.py` | ذاكرة بإصدارات git لكل شخصية |
| تطوير بمواصفات | `runtime/spec_engine.py` | 4 مراحل: Specify → Plan → Tasks → Implement |

### 45 تحسين جديد (من تحليل المستودعات)

تحليل عميق لـ 22 مستودع GitHub (agent-governance-toolkit، OpenMemory، metis، spec-kit، open-code-review، agent-policy-engine، sol sentinel، caracal، ouroboros، وغيرها) أنتج 45 تحسينًا في 3 مراحل:

#### المرحلة 1 — تأثير عالي، تعقيد منخفض (12 ميزة)

| الميزة | الوحدة | المصدر |
| :--- | :--- | :--- |
| 5 بوابات تقييم بالأدلة | `eval/harness.py` | agentic-os |
| SimHash لإزالة التكرار | `memory/simhash.py` | OpenMemory |
| ترتيب الذاكرة بالحرارة | `memory/heat.py` | MemoryOS |
| manifests بمواصفات متتبعة بـ hash | `runtime/spec_engine.py` | spec-kit |
| مواصفات delta (ADDED/MODIFIED/REMOVED) | `runtime/spec_engine.py` | OpenSpec |

#### المرحلة 2 — تأثير متوسط، تعقيد متوسط (18 ميزة)

| الميزة | الوحدة | المصدر |
| :--- | :--- | :--- |
| بوابة تقييم 3-مراحل | `eval/stages.py` | ouroboros |
| primitives توحيد الذاكرة | `memory/consolidation.py` | agent-memory |
| تصنيف 5 قطاعات معرفية | `memory/sectors.py` | OpenMemory HMD v2 |
| رسم زمني للمعرفة | `memory/temporal.py` | OpenMemory |
| بناء CodeGraph (AST) | `runtime/codegraph.py` | metis |
| تحليل قابلية الوصول في CodeGraph | `runtime/codegraph.py` | metis |
| runtime ذاتي الشفاء | `runtime/self_healing.py` | sol sentinel |

#### المرحلة 3 — تأثير عالي، تعقيد عالي (15 ميزة)

| الميزة | الوحدة | المصدر |
| :--- | :--- | :--- |
| مزود رموز tree-sitter | `runtime/tree_sitter_provider.py` | metis |
| مجدول اضمحلال الذاكرة | `memory/decay_scheduler.py` | OpenMemory |
| بحث دلالي في الكود (TF-IDF) | `runtime/semantic_search.py` | metis |

#### المرحلة 4 — أنماط معمارية من spec-kit + Floci (6 ميزات)

| الميزة | الوحدة | المصدر |
| :--- | :--- | :--- |
| قوالب SDD (spec/plan/tasks/constitution/checklist) | `tech-stack/spec-driven-templates/` | spec-kit |
| تحليل اتساق المواصفات (تغطية/غموض/دستور) | `runtime/spec_engine.py` | spec-kit |
| تقارب المواصفات مع الكود (تحليل الفجوات) | `runtime/spec_engine.py` | spec-kit |
| تجريد تخزين قابل للتبديل (memory/json/sqlite) | `runtime/storage_backend.py` | Floci |
| فهرس متعدد الخدمات/المهارات | `runtime/service_catalog.py` | Floci |
| هرم AizeeError + PaginatedResult | `runtime/schemas.py` | Floci |

راجع [CHANGELOG.md](CHANGELOG.md) للتفاصيل الكاملة.

---

## مرجع CLI

```bash
aizee status                         # صحة + إحصائات
aizee doctor                         # تشخيص كامل
aizee persona detect --multi "مهمة"  # كشف الشخصيات
aizee check edit --args '{"tokens":100}'  # بوابة policy + budget
aizee run 02-execution               # تشغيل سير عمل
aizee memory ingest                  # إعادة بناء الفهرس
aizee memory search "استعلام"        # بحث في الذاكرة
aizee skill list                     # قائمة المهارات
aizee test --full                    # اختبارات كاملة مع تغطية
```

---

## الاتصال بمساعدك الذكي

| الأداة | ملف الإعداد |
| :--- | :--- |
| Cursor | `.cursor/rules/aizee.mdc` |
| Claude Code | `.claude/CLAUDE.md` |
| Windsurf | `.windsurfrules` |
| Cline | `.clinerules/aizee.md` |
| Aider | `.aider.conf.yml` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Devin | `.devin/skills/global-os/SKILL.md` |

المثبّت يربط هذه تلقائيًا بالمواقع الصحيحة.

---

## المثبّت الرسومي

واجهة **WPF كاملة** بـ 8 صفحات، ثيم داكن، تقدم حي، وإدارة أسرار `.env`.

**تشغيل بـ double-click** (Windows): شغّل `install.bat` — لا حاجة لطرفية.

**من الطرفية:**
```powershell
.\install.ps1 -Gui                    # تشغيل الواجهة
.\installer\gui_installer.ps1 -Silent # تثبيت صامت
```

---

## لوحة التحكم

```bash
python dashboard/server.py 8080
# ← http://127.0.0.1:8080
```

واجهة command-center داكنة: لوحة أوامر (`Ctrl+K`)، بطاقات مقاييس، حبوب حالة. مصادقة Bearer اختيارية عبر `AIZEE_DASHBOARD_TOKEN`.

---

## بوابات الجودة

| البوابة | الأمر | الحالة |
| :--- | :--- | :--- |
| Lint | `ruff check .` | 0 تحذيرات |
| الأنواع | `mypy` | 0 أخطاء (90+ ملف) |
| الاختبارات | `pytest -q` | 4028 ناجح، 96% تغطية |
| السلامة | `validate-globals.py` | 0 أخطاء |
| E2E | `eval/harness.py` | all_pass: true |

---

## الرخصة

MIT — راجع [LICENSE](LICENSE).

---

</div>

<div align="center">
  <p dir="rtl"><strong>aiZee</strong> — توقف عن السماح للذكاء الاصطناعي بكتابة كود فوضوي. حوّله إلى مهندسك الرئيسي.</p>
  <p>بناه <a href="https://linkedin.com/in/moataz-ahmed">معتز أحمد</a></p>
</div>
