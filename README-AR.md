<div align="right" dir="rtl">
  <img src="logo.png" width="160" alt="شعار AI Global OS">
  <h1>AI Global OS — نظام التشغيل العالمي للذكاء الاصطناعي</h1>
  <p><strong>حول أي مساعد ذكاء اصطناعي إلى مهندسك الرئيسي — سيادة كاملة، جودة صفرية العيوب.</strong></p>

  <p>
    <img src="https://img.shields.io/badge/%D8%A5%D8%B5%D8%AF%D8%A7%D8%B1-5.0.0-6C63FF?style=for-the-badge&logo=buffer&logoColor=white&labelColor=1a1a2e" alt="الإصدار 5.0.0">
    <img src="https://img.shields.io/badge/%D8%A7%D8%AE%D8%AA%D8%A8%D8%A7%D8%B1%D8%A7%D8%AA-1121%20%D9%86%D8%A7%D8%AC%D8%AD-00C896?style=for-the-badge&logo=pytest&logoColor=white&labelColor=1a1a2e" alt="1121 اختبار ناجح">
    <img src="https://img.shields.io/badge/%D8%AA%D8%BA%D8%B7%D9%8A%D8%A9-91%25-10B981?style=for-the-badge&logo=codecov&logoColor=white&labelColor=1a1a2e" alt="تغطية 91%">
    <img src="https://img.shields.io/badge/%D8%A7%D9%84%D8%B1%D8%AE%D8%B5%D8%A9-MIT-3B82F6?style=for-the-badge&logo=opensourceinitiative&logoColor=white&labelColor=1a1a2e" alt="الرخصة: MIT">
  </p>
  <p>
    <img src="https://img.shields.io/badge/%D8%B4%D8%AE%D8%B5%D9%8A%D8%A7%D8%AA-20-EC4899?style=for-the-badge&logo=buffer&logoColor=white&labelColor=1a1a2e" alt="20 شخصية">
    <img src="https://img.shields.io/badge/%D9%85%D9%87%D8%A7%D8%B1%D8%A7%D8%AA-66-10B981?style=for-the-badge&logo=checkmarx&logoColor=white&labelColor=1a1a2e" alt="66 مهارة">
    <img src="https://img.shields.io/badge/%D8%B3%D9%8A%D8%B1_%D8%A7%D9%84%D8%B9%D9%85%D9%84-31-0EA5E9?style=for-the-badge&logo=checkmarx&logoColor=white&labelColor=1a1a2e" alt="31 سير عمل">
    <img src="https://img.shields.io/badge/%D9%85%D9%8A%D8%B2%D8%A7%D8%AA_%D8%AC%D8%AF%D9%8A%D8%AF%D8%A9-18-F59E0B?style=for-the-badge&logo=sparkles&logoColor=white&labelColor=1a1a2e" alt="18 ميزة جديدة">
  </p>
</div>

---

<div dir="rtl">

[اقرأ النسخة الإنجليزية](README.md) · [سجل التغييرات](CHANGELOG.md) · [دليل التثبيت](#التثبيت)

---

## ما هو AI Global OS؟

**نظام تشغيل محكم الإصدار** يجلس بينك وب كل مساعد ذكاء اصطناعي — Cursor، Claude، Copilot، Windsurf، Cline، Aider، Devin — ويفرض معايير الهندسة وسياسات الأمان والانضباط المعماري على كل سطر كود مولّد.

**المشكلة التي يحلها:** المساعدات الذكية تهلوس APIs، تنسى الاتفاقيات، تتجاهل الأمان، وتشحن ديونًا تقنية صامتة. AI Global OS يجبرها على القراءة من مصدر حقيقة مركزي *قبل* كتابة سطر واحد.

| بدون AI Global OS | مع AI Global OS |
| :--- | :--- |
| انحراف السياق بعد عدة prompts | القواعد والشخصيات تُحمّل كل جلسة |
| حزم قديمة وديون تقنية صامتة | تثبيت إصدار دقيق عبر MCP حي |
| SQL خام، XSS مفقود، أسرار ضعيفة | OWASP و zero-trust و RBAC مفروضة |
| إعادة هيكلة عشوائية | تغييرات جراحية عبر بوابات policy + budget + audit |
| إجابات واحدة-للجميع | 20 شخصية + 66 مهارة تُختار تلقائيًا |

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
ai-os doctor    # فحص صحة
ai-os status    # الشخصية، المهارات، الميزانية
```

---

## الأعمدة الستة

### 1. الشخصيات + المهارات
20 شخصية (`ARCH`، `QA`، `SEC`، `DEV`، `SRE`، `DATA`، `ML`، `DEVOPS`، `FREELANCE`، إلخ) مع 13 مهارة lord. تُكتشف تلقائيًا حسب المهمة.

```bash
ai-os persona detect --multi "ابني API آمن مع docker و postgres"
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
mypy                  # 0 أخطاء (73 ملف، strict)
pytest -q             # 1121 اختبار، 91% تغطية
python eval/harness.py  # E2E: ruff + mypy + pytest + validate-globals
```

### 6. كفاءة Tokens
كشف الشخصيات محلي (Python خالص، صفر tokens). فقط أسماء المهارات relevant تُرجع — ليس الملفات كاملة.

---

## الجديد في v5.0.0

18 ميزة جديدة من تحليل تنافسي شامل:

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

---

## مرجع CLI

```bash
ai-os status                         # صحة + إحصائات
ai-os doctor                         # تشخيص كامل
ai-os persona detect --multi "مهمة"  # كشف الشخصيات
ai-os check edit --args '{"tokens":100}'  # بوابة policy + budget
ai-os run 02-execution               # تشغيل سير عمل
ai-os memory ingest                  # إعادة بناء الفهرس
ai-os memory search "استعلام"        # بحث في الذاكرة
ai-os skill list                     # قائمة المهارات
ai-os test --full                    # اختبارات كاملة مع تغطية
```

---

## الاتصال بمساعدك الذكي

| الأداة | ملف الإعداد |
| :--- | :--- |
| Cursor | `.cursor/rules/ai-global-os.mdc` |
| Claude Code | `.claude/CLAUDE.md` |
| Windsurf | `.windsurfrules` |
| Cline | `.clinerules/ai-global-os.md` |
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
| الأنواع | `mypy` | 0 أخطاء (73 ملف) |
| الاختبارات | `pytest -q` | 1121 ناجح، 91% تغطية |
| السلامة | `validate-globals.py` | 0 أخطاء |
| E2E | `eval/harness.py` | all_pass: true |

---

## الرخصة

MIT — راجع [LICENSE](LICENSE).

---

</div>

<div align="center">
  <p dir="rtl"><strong>AI Global OS</strong> — توقف عن السماح للذكاء الاصطناعي بكتابة كود فوضوي. حوّله إلى مهندسك الرئيسي.</p>
  <p>بناه <a href="https://linkedin.com/in/moataz-ahmed">معتز أحمد</a></p>
</div>
