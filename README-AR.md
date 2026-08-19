<div align="right" dir="rtl">
  <img src="logo.png" width="160" alt="شعار aiZee">
  <h1>aiZee — نظام التشغيل العالمي للذكاء الاصطناعي</h1>
  <p><strong>حول أي مساعد ذكاء اصطناعي إلى مهندسك الرئيسي — سيادة كاملة، جودة صفرية العيوب.</strong></p>

  <p>
    <img src="https://img.shields.io/badge/%D8%A5%D8%B5%D8%AF%D8%A7%D8%B1-5.2.0-6C63FF?style=for-the-badge&logo=buffer&logoColor=white&labelColor=1a1a2e" alt="الإصدار 5.2.0">
    <img src="https://img.shields.io/badge/%D8%A7%D8%AE%D8%AA%D8%A8%D8%A7%D8%B1%D8%A7%D8%AA-2526%20%D9%86%D8%A7%D8%AC%D8%AD-00C896?style=for-the-badge&logo=pytest&logoColor=white&labelColor=1a1a2e" alt="2526 اختبار ناجح">
    <img src="https://img.shields.io/badge/%D8%AA%D8%BA%D8%B7%D9%8A%D8%A9-91%25-10B981?style=for-the-badge&logo=codecov&logoColor=white&labelColor=1a1a2e" alt="تغطية 91%">
    <img src="https://img.shields.io/badge/%D8%A7%D9%84%D8%B1%D8%AE%D8%B5%D8%A9-MIT-3B82F6?style=for-the-badge&logo=opensourceinitiative&logoColor=white&labelColor=1a1a2e" alt="الرخصة: MIT">
  </p>
  <p>
    <img src="https://img.shields.io/badge/%D8%B4%D8%AE%D8%B5%D9%8A%D8%A7%D8%AA-20-EC4899?style=for-the-badge&logo=buffer&logoColor=white&labelColor=1a1a2e" alt="20 شخصية">
    <img src="https://img.shields.io/badge/%D9%85%D9%87%D8%A7%D8%B1%D8%A7%D8%AA-78-10B981?style=for-the-badge&logo=checkmarx&logoColor=white&labelColor=1a1a2e" alt="78 مهارة">
    <img src="https://img.shields.io/badge/%D8%B3%D9%8A%D8%B1_%D8%A7%D9%84%D8%B9%D9%85%D9%84-38-0EA5E9?style=for-the-badge&logo=checkmarx&logoColor=white&labelColor=1a1a2e" alt="38 سير عمل">
    <img src="https://img.shields.io/badge/%D9%85%D8%B1%D8%A7%D8%AC%D8%B9_%D8%AA%D9%82%D9%86%D9%8A%D8%A9-81-F59E0B?style=for-the-badge&logo=sparkles&logoColor=white&labelColor=1a1a2e" alt="81 مرجع تقنية">
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
| إجابات واحدة-للجميع | 19 شخصية + 78 مهارة تُختار تلقائيًا |

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
20 شخصية (`ARCH`، `QA`، `SEC`، `DEV`، `SRE`، `DATA`، `ML`، `DEVOPS`، `FREELANCE`، إلخ) مع 13 مهارة lord. تُكتشف تلقائيًا حسب المهمة.

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
mypy                  # 0 أخطاء (90+ ملف، strict)
pytest -q             # 2526 اختبار، 91% تغطية
python eval/harness.py  # E2E: ruff + mypy + pytest + validate-globals
```

### 6. كفاءة Tokens
كشف الشخصيات محلي (Python خالص، صفر tokens). فقط أسماء المهارات relevant تُرجع — ليس الملفات كاملة.

---

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
| تحقق AST | `runtime/ast_validator.py` | تحقق الخطة/الفرق قبل وبعد التعديل |
| محرك تقييم الوكلاء | `eval/agent_benchmark.py` | قياس أداء الشخصيات |
| OWASP Agentic Top 10 | `runtime/agentic_security.py` | 10 ضوابط أمان للأنظمة الوكلاء |
| فاحص أمان MCP | `runtime/mcp_security.py` | تحليل ثابت لخوادم/مهارات MCP |
| سوق المهارات | `runtime/skills_marketplace.py` | سجل مجتمعي مع فحص أمان |
| محرك مراجعة كود AI | `runtime/review_engine.py` | مراجعة متعددة الأبعاد بثقة |
| ذاكرة مدعومة بـ git | `memory/git_memory.py` | ذاكرة بإصدارات git لكل شخصية |
| ضغط الكود | `runtime/code_compressor.py` | ضغط AST ~70% تقليل tokens |
| مصدر OpenTelemetry | `runtime/otel_exporter.py` | تصدير OTLP/JSON مع fallback |
| وكلاء متوازيين | `runtime/worktree_pool.py` | تنفيذ متوازي عبر git worktrees |
| تطوير بمواصفات | `runtime/spec_engine.py` | 4 مراحل: Specify → Plan → Tasks → Implement |
| شخصيات ديناميكية | `runtime/dynamic_persona.py` | تطور 3-طبقات مع تتبع خبرة |
| تكامل issue trackers | `runtime/issue_tracker.py` | عميل موحد Linear/Jira/Notion |
| مركز القيادة | `runtime/command_center.py` | لوحة Kanban لإدارة الأسطول |
| كاشف AI slop | `runtime/ai_slop_detector.py` | كشف مشاكل جودة كود AI |
| واجهة صوتية | `runtime/voice_interface.py` | STT/TTS عبر الأنظمة |
| بروتوكول ACP | `runtime/acp_protocol.py` | تواصل بين الوكلاء |

### 45 تحسين جديد (من تحليل المستودعات)

تحليل عميق لـ 22 مستودع GitHub (agent-governance-toolkit، OpenMemory، metis، spec-kit، open-code-review، agent-policy-engine، sol sentinel، caracal، ouroboros، وغيرها) أنتج 45 تحسينًا في 3 مراحل:

#### المرحلة 1 — تأثير عالي، تعقيد منخفض (12 ميزة)

| الميزة | الوحدة | المصدر |
| :--- | :--- | :--- |
| شروط سياسة معاملات | `runtime/authorization.py` | DAE Standard |
| توليد lease (fencing token) | `runtime/authorization.py` | agent-policy-engine |
| 3 أوضاع تطبيق (DISABLED/OBSERVE/ENFORCE) | `runtime/authorization.py` | agent-policy-engine |
| 5 بوابات تقييم بالأدلة | `eval/harness.py` | agentic-os |
| قفل ملفات atomic لكاتب واحد | `runtime/file_lock.py` | agentic-os |
| SimHash لإزالة التكرار | `memory/simhash.py` | OpenMemory |
| ترتيب الذاكرة بالحرارة | `memory/heat.py` | MemoryOS |
| كشف توقف الوكلاء | `runtime/worktree_pool.py` | sol sentinel |
| ملفات tether للاسترجاع بعد الانهيار | `runtime/worktree_pool.py` | sol |
| 5 بوابات تصفية ملفات deterministic | `runtime/review_engine.py` | open-code-review |
| manifests بمواصفات متتبعة بـ hash | `runtime/spec_engine.py` | spec-kit |
| مواصفات delta (ADDED/MODIFIED/REMOVED) | `runtime/spec_engine.py` | OpenSpec |

#### المرحلة 2 — تأثير متوسط، تعقيد متوسط (18 ميزة)

| الميزة | الوحدة | المصدر |
| :--- | :--- | :--- |
| حلقات تنفيذ (4 مستويات صلاحية) | `runtime/execution_rings.py` | agent-governance-toolkit |
| بوابة تقييم 3-مراحل | `eval/stages.py` | ouroboros |
| saga compensation (rollback متعدد الخطوات) | `runtime/saga_compensation.py` | agent-governance-toolkit |
| primitives توحيد الذاكرة | `memory/consolidation.py` | agent-memory |
| تصنيف 5 قطاعات معرفية | `memory/sectors.py` | OpenMemory HMD v2 |
| رسم زمني للمعرفة | `memory/temporal.py` | OpenMemory |
| تفويض 3-أوضاع (inherit/narrow/none) | `runtime/authorization.py` | caracal |
| آلة حالة runtime | `runtime/authorization.py` | agent-policy-engine |
| تتبع المصدر (provenance) | `runtime/authorization.py` | agent-policy-engine |
| ضغط ذاكرة 3-مناطق | `runtime/memory_compression.py` | open-code-review |
| بناء CodeGraph (AST) | `runtime/codegraph.py` | metis |
| تحليل قابلية الوصول في CodeGraph | `runtime/codegraph.py` | metis |
| تحديد معدل الميزانية (token bucket) | `runtime/rate_limiter.py` | agent-governance-toolkit |
| runtime ذاتي الشفاء | `runtime/self_healing.py` | sol sentinel |
| تحقق دستور المواصفات | `runtime/spec_validation.py` | spec-kit |
| سيناريوهات اختبار المواصفات (Gherkin) | `runtime/spec_validation.py` | spec-kit |
| رسم ارتباط المواصفات (تحليل التأثير) | `runtime/spec_validation.py` | spec-kit |
| harness اختبار fuzz | `runtime/fuzz_testing.py` | agent-policy-engine |

#### المرحلة 3 — تأثير عالي، تعقيد عالي (15 ميزة)

| الميزة | الوحدة | المصدر |
| :--- | :--- | :--- |
| مزود رموز tree-sitter | `runtime/tree_sitter_provider.py` | metis |
| مراجعة كود delta-based | `runtime/diff_review.py` | open-code-review |
| كشف شذوذ الميزانية (z-score) | `runtime/budget_anomaly.py` | agent-governance-toolkit |
| تخزين قرارات السياسة (TTL) | `runtime/policy_cache.py` | agent-policy-engine |
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

راجع [IMPLEMENTATION-REPORT.md](IMPLEMENTATION-REPORT.md) للتفاصيل الكاملة.

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

واجهة command-center داكنة: لوحة أوامر (`Ctrl+K`)، بطاقات مقاييس، حبوب حالة. مصادقة Bearer اختيارية عبر `AGENT_OS_DASHBOARD_TOKEN`.

---

## بوابات الجودة

| البوابة | الأمر | الحالة |
| :--- | :--- | :--- |
| Lint | `ruff check .` | 0 تحذيرات |
| الأنواع | `mypy` | 0 أخطاء (90+ ملف) |
| الاختبارات | `pytest -q` | 2526 ناجح، 91% تغطية |
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
