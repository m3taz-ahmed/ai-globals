<div align="right" dir="rtl">
  <img src="logo.png" width="160" alt="شعار AI Global OS">
  <h1>AI Global OS — نظام التشغيل العالمي للذكاء الاصطناعي</h1>
  <p><strong>توقف عن السماح للذكاء الاصطناعي بكتابة كود سباغيتي. حوّله إلى مهندسك الرئيسي.</strong></p>

  <p>
    <img src="https://img.shields.io/badge/%D8%A7%D9%84%D8%A5%D8%B5%D8%AF%D8%A7%D8%B1-4.21.0-6C63FF?style=for-the-badge&logo=buffer&logoColor=white&labelColor=1a1a2e" alt="الإصدار 4.21.0">
    <img src="https://img.shields.io/badge/%D8%A7%D9%84%D8%AD%D8%A7%D9%84%D8%A9-%D8%AA%D8%B5%D8%AD%D9%8A%D8%AD_%D8%B0%D8%A7%D8%AA%D9%8A-00C896?style=for-the-badge&logo=dependabot&logoColor=white&labelColor=1a1a2e" alt="الحالة: تصحيح ذاتي">
    <img src="https://img.shields.io/badge/%D8%A7%D9%84%D9%85%D8%B9%D9%85%D8%A7%D8%B1%D9%8A%D8%A9-%D8%B3%D9%8A%D8%A7%D8%AF%D9%8A%D8%A9-F59E0B?style=for-the-badge&logo=moleculer&logoColor=white&labelColor=1a1a2e" alt="المعمارية: سيادية">
    <img src="https://img.shields.io/badge/%D8%A7%D9%84%D8%B1%D8%AE%D8%B5%D8%A9-MIT-3B82F6?style=for-the-badge&logo=opensourceinitiative&logoColor=white&labelColor=1a1a2e" alt="الرخصة: MIT">
  </p>
  <p>
    <img src="https://img.shields.io/badge/%D8%A7%D9%84%D8%AA%D9%82%D9%86%D9%8A%D8%A7%D8%AA-Next.js%2015%20%7C%20Laravel%2013%20%7C%20PostgreSQL%2017-EC4899?style=for-the-badge&logo=nextdotjs&logoColor=white&labelColor=1a1a2e" alt="التقنيات">
    <img src="https://img.shields.io/badge/%D8%A8%D9%88%D8%A7%D8%A8%D8%A9_%D8%A7%D9%84%D8%AC%D9%88%D8%AF%D8%A9-SOLID%20%7C%20OWASP%20%7C%20WCAG%202.2-10B981?style=for-the-badge&logo=checkmarx&logoColor=white&labelColor=1a1a2e" alt="بوابة الجودة">
  </p>

  <p><i>نظام تشغيل محكم الإصدار، غير قابل للمساومة، يقضي نهائياً على انحراف السياق (Context Drift)، ويفرض أحدث معايير الهندسة، ويحكم كل سطر كود مولّد.</i></p>
</div>

---

<div dir="rtl">

## لماذا AI Global OS؟

معظم الفرق تستخدم الذكاء الاصطناعي كمبرمج مبتدئ عالي السرعة. يكتب بسرعة، لكنه يتخيل واجهات برمجة (APIs)، وينسى اتفاقيات التسمية، ويتجاهل مشاكل N+1، ويدخل ديوناً تقنية بصمت.

**AI Global OS** هو محرك معماري سيادي. يجبر Cursor, Copilot, Claude, Gemini, Windsurf, Cline, Aider, و GitHub Copilot على القراءة من مصدر حقيقة مركزي ومحكم الإصدار *قبل* كتابة أي سطر كود.

| بدون النظام | مع النظام |
| :--- | :--- |
| انحراف السياق بعد عدد قليل من المطالبات | القواعد تُحمّل في كل جلسة |
| حزم مهجورة وديون تقنية صامتة | قفل الإصدار الدقيق عبر مستندات MCP الحية |
| SQL خام، فلاتر XSS مفقودة، أسرار ضعيفة | OWASP، zero-trust، و RBAC مفروضة افتراضياً |
| إعادة هيكلة عشوائية | تغييرات جراحية ببوابات policy / budget / audit |

[اقرأ النسخة الإنجليزية](README.md)

---

## فعّله في 60 ثانية

1. **استنسخ العقل المركزي** في مكان ثابت (مثلاً `D:/.ai` أو `~/.ai`):
   ```bash
   git clone https://github.com/m3taz-ahmed/ai-globals.git D:/.ai
   ```

2. **ثبّت النظام**:
   ```powershell
   # Windows
   .\install.ps1

   # macOS / Linux
   bash install.sh
   ```

3. **ثبّت متطلبات Python** داخل المجلد المستنسخ:
   ```bash
   python -m pip install -e .
   ```

4. **استخدم الـ CLI**:
   ```bash
   ai-os status
   ai-os check edit
   ai-os run 02-execution
   ai-os memory ingest
   ```

5. **فعّل MCP**:
   أضف `aios_mcp/config.json` لإعدادات MCP في IDE، أو شغّل:
   ```bash
   python aios_mcp/aios_server.py
   ```

الآن أصبح ذكاؤك الاصطناعي سيادياً. يحلل كل طلب مقابل SOLID، OWASP، وتقنيتك المحددة بدقة قبل إنشاء الكود.

---

## ماذا تحصل عليه؟

### تسع شخصيات محكمة

يأتي AI Global OS بتسع شخصيات مهنية محكمة تحدد النبرة، العمق، وأولويات كل مهمة. حمّل `global-roles.md` (الإنجليزية) أو `global-roles-ar.md` (العربية) في agent أو IDE لتفعيلها.

- **Principal 10x Engineer & Chief Architect** — قابلية توسع لانهائية، نماذج أولية سريعة، تسليم خالٍ من العيوب.
- **Software Tester** — أقصى تغطية اختبار، اصطياد حالات الحافة، منع الانحدار.
- **Principal Full-Stack Designer & UX Architect** — رحلات مثالية، نماذج أولية سريعة، تناسق بكسل-مثالي.
- **Master Developer** — تصميم أنظمة، بنية تحتية آمنة، أقصى أداء.
- **God-Tier SRE & Cloud Dictator** — active-active متعدد المناطق، أتمتة GitOps، هندسة الفوضى.
- **Hardcore Linux Kernel Master & SecOps Warlord** — تتبع eBPF، زمن استجابة مايكروثانية، شبكات zero-trust.
- **Principal Game Architect & JavaScript Engine Master** — حلقات ألعاب 60 FPS، Capacitor/WebView متعدد المنصات، غوص Babylon.js.
- **Google Play Ecosystem Warlord** — سياسات Play، تحقيق من IAP وإعلانات، تحسين AAB، إبادة ANR والأعطال.
- **Elite Mobile Game Producer & Full-Stack Innovator** — ميكانيكيات gameplay addictive، تكامل Laravel، Fastlane CI/CD، مكافحة الغش.

### حوكمة تشغيلية

- **محرك السياسات** مع سياسات YAML `allow/ask/deny` وتقييم AST آمن.
- **مدير الميزانيات** للرموز، التكلفة، والاستدعاءات لكل نطاق.
- **مشغّل سير العمل** المتين مع حالة SQLite، دعم Saga، وتسجيل audit.
- **خدمة الذاكرة** مع SQLite + FTS5، طبقات episodic/semantic/factual/procedural، علاقات جراف، وفهرس متجهي اختياري.
- **خادم MCP** يعرض `query_rules`, `run_workflow`, `check_policy`, `search_memory`, `search_memory_vector`, `get_tech_stack`.
- **CLI `ai-os`** ولوحة dashboard ويب مع CORS، Bearer auth اختياري، وtelemetry مباشر.

### معايير هندسية

- **Telegraphic Pseudo-Code** للقواعد، سير العمل، المهارات، والتقنيات — أقصى توجيه بأقل توكنز.
- **طبقات سياق محملة عند الطلب** — فقط المعايير ذات الصلة تُحمّل لكل مهمة.
- **Ground-Truth الحية** عبر Context7 MCP قبل أي تنفيذ إطار عمل.
- **صفر `any` types**، لا inline imports، لا downgrade للاعتماديات.
- **بوابات إلزامية**: `ruff`, `mypy`, `pytest`, و `python eval/harness.py` يجب أن تمر كلها.

---

## معمارية النظام

```text
.ai/                              # الجذر السيادي
├── AGENTS.md                     # تعليمات مشتركة عبر الأدوات
├── global-roles.md               # [الطبقة 0] الشخصيات والهوية (إنجليزي)
├── global-roles-ar.md            # [الطبقة 0] ميثاق الشخصيات (عربي)
├── global-workflow.md            # [الجوهر] بروتوكول التحميل والتنفيذ
├── README.md                     # الباب الأمامي للقارئ الإنجليزي
├── README-AR.md                  # الباب الأمامي للقارئ العربي (هذا الملف)
├── Memory.md                     # السياق قصير المدى عبر الجلسات
├── CHANGELOG.md                  # ملاحظات الإصدار
│
├── .cursor/rules/                # محولات قواعد Cursor
├── .claude/                      # إعداد Claude Code، مهارات، agents
├── .clinerules/                  # قواعد Cline
├── .windsurfrules                # قواعد Windsurf
├── .aider.conf.yml               # إعداد Aider
├── .github/copilot-instructions.md # تعليمات GitHub Copilot
│
├── rules/                        # قواعد سلوكية وبنيوية مضغوطة
├── tech-stack/                   # تقنيات RAG خاصة بالنطاق مضغوطة
├── workflows/                    # بروتوكولات تنفيذ معتمدة على المحفزات
├── skills/                       # أدوات AI وشخصيات agents مضغوطة
│
├── state/                        # سجلات والحالة المستمرة
├── brain/                        # قاعدة بيانات الذاكرة
├── graphify-out/                 # رسم بياني معرفي
│
├── runtime/                      # نواة التشغيل (policy, budget, workflow, chat, telemetry)
├── memory/                       # خدمة الذاكرة
├── aios_mcp/                     # خادم MCP
├── dashboard/                    # لوحة التحكم الويب
├── cli.py                        # نقطة دخول CLI
├── config.py                     # اكتشاف الجذر
├── install.ps1 / install.sh      # مثبت النظام
├── plugins.yaml                  # ملف Plugin manifest
└── scripts/                      # عمليات التصحيح الذاتي
    ├── validate-globals.py       # مدقق النزاهة
    ├── sync-agent-configs.py     # مزامنة الإعدادات عبر الأدوات
    └── graphify_mcp_wrapper.py   # جسر Graphify MCP
```

---

## أبرز التحديثات (v4.21.0)

- نواة التشغيل مع policy، budget، workflow، saga، chat، telemetry، و plugin.
- استيعاب الذاكرة SQLite + FTS5 + فهرس متجهي اختياري.
- خادم MCP مع 12+ أداة وتسجيل plugin ديناميكي.
- CLI `ai-os` مع `status`, `check`, `run`, `memory`, `sync`, `policy`, `budget`, `project`, `doctor`.
- Dashboard بتحديث تلقائي، CORS، Bearer auth اختياري، وأكثر من 10 نقاط API.
- تصليب Docker مع مستخدم غير root، healthchecks، ودعم compose.
- 11 مهارة lord-level تغطي database، language، cloud، devops، frontend، backend، messaging، search/vector، AI/ML، Linux، و security.
- 9 شخصيات محكمة في `global-roles.md` و `global-roles-ar.md`.
- CI pipeline مع SHA pinned للـ actions، `ruff`, `mypy`, `pytest`, و `python eval/harness.py`.

---

## انضم للحركة

ضع نجمة على المستودع لإبقاء قواعد الذكاء الاصطناعي محدثة تلقائياً بأحدث معايير الهندسة.

[![Star on GitHub](https://img.shields.io/github/stars/m3taz-ahmed/ai-globals?style=for-the-badge&logo=github&color=FFDD00&labelColor=1a1a2e)](https://github.com/m3taz-ahmed/ai-globals)

- اقرأ [دليل المساهمة](.github/CONTRIBUTING.md) لإضافة تقنياتك.
- راجع [سياسة الأمان](.github/SECURITY.md).
- شاهد [مدونة قواعد السلوك](.github/CODE_OF_CONDUCT.md).

> بُني للمهندسين الذين يرفضون قبول مخرجات ذكاء اصطناعي متوسطة. هندس بدقة جراحية بواسطة [@m3taz-ahmed](https://github.com/m3taz-ahmed).

</div>
