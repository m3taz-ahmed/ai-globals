<div align="right" dir="rtl">
  <img src="logo.png" width="160" alt="شعار AI Global OS">
  <h1>AI Global OS — نظام التشغيل العالمي للذكاء الاصطناعي</h1>
  <p><strong>توقف عن السماح للذكاء الاصطناعي بكتابة كود سباغيتي. حوّله إلى مهندسك الرئيسي.</strong></p>

  <p>
    <img src="https://img.shields.io/badge/%D8%A5%D8%B5%D8%AF%D8%A7%D8%B1-4.22.0-6C63FF?style=for-the-badge&logo=buffer&logoColor=white&labelColor=1a1a2e" alt="الإصدار 4.22.0">
    <img src="https://img.shields.io/badge/%D8%A7%D9%84%D8%AD%D8%A7%D9%84%D8%A9-%D8%AA%D8%B5%D8%AD%D9%8A%D8%AD_%D8%B0%D8%A7%D8%AA%D9%8A-00C896?style=for-the-badge&logo=dependabot&logoColor=white&labelColor=1a1a2e" alt="الحالة: تصحيح ذاتي">
    <img src="https://img.shields.io/badge/%D8%A7%D9%84%D9%85%D8%B9%D9%85%D8%A7%D8%B1%D9%8A%D8%A9-%D8%B3%D9%8A%D8%A7%D8%AF%D9%8A%D8%A9-F59E0B?style=for-the-badge&logo=moleculer&logoColor=white&labelColor=1a1a2e" alt="المعمارية: سيادية">
    <img src="https://img.shields.io/badge/%D8%A7%D9%84%D8%B1%D8%AE%D8%B5%D8%A9-MIT-3B82F6?style=for-the-badge&logo=opensourceinitiative&logoColor=white&labelColor=1a1a2e" alt="الرخصة: MIT">
  </p>
  <p>
    <img src="https://img.shields.io/badge/%D8%A7%D9%84%D8%B4%D8%AE%D8%B5%D9%8A%D8%A7%D8%AA-17-EC4899?style=for-the-badge&logo=buffer&logoColor=white&labelColor=1a1a2e" alt="17 شخصية">
    <img src="https://img.shields.io/badge/%D9%85%D9%87%D8%A7%D8%B1%D8%A7%D8%AA%20Lord-11-10B981?style=for-the-badge&logo=checkmarx&logoColor=white&labelColor=1a1a2e" alt="11 مهارة Lord">
    <img src="https://img.shields.io/badge/%D8%A8%D9%88%D8%A7%D8%A8%D8%A9_%D8%A7%D9%84%D8%AC%D9%88%D8%AF%D8%A9-SOLID%20%7C%20OWASP%20%7C%20WCAG%202.2-0EA5E9?style=for-the-badge&logo=checkmarx&logoColor=white&labelColor=1a1a2e" alt="بوابة الجودة">
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
| انحراف السياق بعد عدد قليل من المطالبات | القواعد والشخصيات تُحمّل في كل جلسة |
| حزم مهجورة وديون تقنية صامتة | قفل الإصدار الدقيق عبر مستندات MCP الحية |
| SQL خام، فلاتر XSS مفقودة، أسرار ضعيفة | OWASP، zero-trust، و RBAC مفروضة افتراضياً |
| إعادة هيكلة عشوائية | تغييرات جراحية ببوابات policy / budget / audit |
| إجابات AI بنفس الأسلوب دائماً | الشخصية/المهارات المناسبة لكل مهمة |

[اقرأ النسخة الإنجليزية](README.md)

---

## المتطلبات قبل البدء

| المتطلب | الحد الأدنى | المفضل |
| :--- | :--- | :--- |
| **Python** | 3.10 | 3.11 أو 3.12 |
| **pip** | أحدث إصدار | أحدث إصدار |
| **Git** | 2.30+ | أحدث إصدار |
| **نظام التشغيل** | Windows 10 / macOS 12 / Linux (glibc 2.31+) | Windows 11 / macOS 14 / Ubuntu 22.04+ |

مُستحسن (اختياري لكن قوي):

- مساعد برمجة AI: **Cursor**، **GitHub Copilot**، **Claude Code**، **Windsurf**، **Cline**، **Aider**.
- **Context7 MCP** لمستندات المكتبات الحية.
- **graphify** للرسم البياني للمعرفة (يُبنى من المستودع نفسه بدون LLM).

النواة الأساسية للنظام **Pure Python**. Node.js مطلوب فقط لو هتوسّع الـ dashboard أو الـ frontend؛ الـ dashboard المدمج يشتغل على HTTP server المدمج في Python مع SQLite.

---

## للمبرمجين: ما الذي يفعله ولماذا هو مختلف

AI Global OS ليس مكتبة prompts. إنه طبقة تحكم runtime توضع بينك وبين كل وكيل ذكاء اصطناعي تستخدمه.

### 1. تكوين الشخصيات + مهارات Lord

النظام يأتي بـ **17 شخصية** (من `ARCH` إلى `LEGAL`) و**11 مهارة lord** (قواعد البيانات، AI/ML، السحابة، DevOps، الأمن، إلخ). لكل طلب يكتشف النظام مجموعة الشخصيات الأكثر ملاءمة ويحمّل ملفات المهارات المطابقة. يمكنك أيضاً إنشاء وكلاء متعددي الشخصيات، مثلاً `ARCH + QA + security-lord`.

```bash
ai-os persona detect --multi "build a secure docker API with postgres"
# يرجع الشخصية الرئيسية، الشخصيات الثانوية، المهارات الأساسية، ومهارات lord.
```

يُنفّذ ذلك في `runtime/persona.py` + `runtime/skill_resolver.py` ويُستخدم من `Kernel` و `WorkflowRunner` و `AgentPool`.

### 2. حوكمة Runtime

كل إجراء يمرّ عبر بوابات policy + budget قبل التنفيذ.

- **Policy engine** — قواعد `allow/ask/deny` مع تقييم AST آمن.
- **Budget manager** — حدود tokens / cost / calls لكل نطاق.
- **Audit logger** — تسجيل كل قرار.
- **Workflow runner** — تنفيذ متين مدعوم بـ SQLite مع دعم saga.
- **Saga orchestrator** — إجراءات تعويضية للعمليات الطويلة.
- **Telemetry** — أحداث منظمة للمراقبة.

### 3. حقيقة حية، لا ذاكرة قديمة

قبل تنفيذ أي مكتبة أو إطار خارجي، يستعلم النظام من Context7 MCP (`resolve-library-id` ثم `get-library-docs`) ليتطابق الكود المولّد مع API الحقيقي. إذا وُجد `graphify-out/graph.json`، يتنقل النظام في الرسم البياني للمعرفة بدلاً من `grep` أعمى.

### 4. ذاكرة موثوقة

خدمة الذاكرة تستخدم SQLite + FTS5 مع فهرس vector اختياري. تخزّن سياقات episodic / semantic / factual / procedural. بعد كل تغيير في rules أو tech-stack أو workflows، يشغّل `ai-os memory ingest` لتحديث الفهرس.

### 5. معايير هندسية مفروضة بالكود

الجودة ليست اختيارية. يشغّل CI pipeline و `python eval/harness.py`:

- `ruff check .` للـ lint.
- `mypy` للـ typing الصارم.
- `pytest -q` للاختبارات.
- `scripts/validate-globals.py --fix` للنزاهة.

النظام يمنع SQL خام غير مُعَقّم، إساءة استخدام `any`، الـ inline imports، CORS wildcard، والإجراءات التخريبية غير المُتحقّقة.

### 6. كفاءة التوكينز (تكلفة سياق مهملة)

النظام مُصمّم يضيف أقل عدد ممكن من التوكينز لـ context window بتاع الـ AI — **مش محتاج تكتب أي flags بنفسك**. الإعدادات الافتراضية أصلاً بتخلي السياق صغير:

- **اكتشاف الشخصية local** — تسجيل نصي Python بحت، مفيش LLM call، صفر توكين.
- **النظام بيرجّع أسماء المهارات بس** — مش بيحشر كل ملف skill في الـ prompt.
- **حدود ضيقة افتراضياً**: مهارة الشخصية الرئيسية + لحد `max_personas - 1` مهارات ثانوية + لحد `max_lords` (افتراضي **5**) مهارات lord.
- الأوامر دي للـ power users أو CI scripts اللي عايزين يتحكموا صراحةً في حجم السياق:

  ```bash
  # اقل سياق ممكن (شخصية واحدة، مفيش lords)
  ai-os persona detect --multi "deploy docker" --max-personas 1 --max-lords 0 --single

  # panel صغير
  ai-os persona detect --multi "..." --max-personas 2 --max-lords 3
  ```

- `Kernel.act`، `WorkflowRunner`، و `AgentPool` بيحترموا الحدود دي، فالـ agent اللي بيتم إنشاؤه بـ `ARCH + QA + security-lord` بيحمّل بس الملفات اللي فعلاً ليها صلة.

---

## لغير المبرمجين: ماذا يعني ذلك لفريقك؟

**الملخص المختصر:** AI Global OS يحوّل البرمجة المساعدة بالذكاء الاصطناعي الفوضوية إلى عملية منضبطة وقابلة للتكرار تحمي الجودة وتقلل المخاطر.

- **لا مزيد من "الذكاء الاصطناعي نسي ما اتفقنا عليه."** كل جلسة تعيد تحميل نفس القواعد والمعايير وسياق المشروع.
- **لا مزيد من التخمين حول أمان الكود.** الأمن، الأداء، والامتثال مدمجون وليسوا اختيارات.
- **لا مزيد من شخصية AI واحدة لكل شيء.** النظام يختار الخبير المناسب — أو فريق الخبراء — للمهمة، سواء كان مهندس معماري، مدقق أمن، مهندس بيانات، أو كاتب تقني.
- **لا مزيد من الديون التقنية الصامتة.** كل تغيير يُدقّق ويُحاسَب ويُدقّق قبل قبوله.
- **يعمل مع الأدوات التي تستخدمها بالفعل.** Cursor, Copilot, Claude, Gemini, Windsurf, Cline, Aider, و GitHub Copilot كلها تقرأ من نفس الكتاب القواعدي.

فكّر في AI Global OS باعتباره "طبقة السياسات والتدريب" التي تجعل كل مساعد ذكاء اصطناعي يتصرف كعضو كبير في فريق الهندسة لديك.

---

## التفعيل في 60 ثانية

> تأكد إن **Python 3.10+** و **Git** مثبّتين. النظام أساساً Pure Python؛ Node.js محتاج بس لو هتوسّع الـ dashboard/frontend.

1. **استنسخ الدماغ المركزي** في مكان ثابت (مثلاً `D:/.ai` أو `~/.ai`):
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

3. **ثبّت اعتمادات Python** داخل المجلد المنسوخ:
   ```bash
   python -m pip install -e .
   ```

4. **استخدم CLI**:
   ```bash
   ai-os status
   ai-os persona detect --multi "وصف مهمتك"
   ai-os check edit
   ai-os run 02-execution
   ai-os memory ingest
   ```

5. **فعّل MCP**:
   أضف `aios_mcp/config.json` إلى إعدادات MCP في IDE، أو شغّل:
   ```bash
   python aios_mcp/aios_server.py
   ```

6. **وجّه AI agent بتاعك لقواعد النظام**:
   شوف القسم اللي جاي عشان تعرف الملف اللي هتحطّه في Cursor, Copilot, Claude, Windsurf, Cline, أو Aider.

الآن أصبح ذكاؤك الاصطناعي سيادياً. يحلل كل طلب مقابل SOLID، OWASP، WCAG، وتكدسك التقني الدقيق قبل توليد أي كود.

---

## وصل AI Global OS بـ AI agent بتاعك

بعد ما تستنسخ، قول لـ AI coding tool بتاعك إنه يقرأ قواعد النظام. كل أداة ليها adapter file خاص بيها:

| أداة AI | الملف اللي هتحطّه / تنسخه في project instructions |
| :--- | :--- |
| **Cursor** | `.cursor/rules/ai-global-os.mdc` |
| **Claude Code / Claude projects** | `.claude/CLAUDE.md` |
| **Windsurf** | `.windsurfrules` (بيتحمّل auto لو موجود في root المشروع) |
| **Cline** | `.clinerules/ai-global-os.md` |
| **Aider** | `.aider.conf.yml` |
| **GitHub Copilot (داخل المستودع)** | `.github/copilot-instructions.md` |
| **أي agent تاني** | حمّل `AGENTS.md` + `global-roles.md` + `global-workflow.md` في الـ system prompt / project instructions. |

أسرع setup عام هو إنك توجّه الـ agent لـ:
```text
AGENTS.md
global-roles.md
global-workflow.md
```

الـ 3 ملفات دول بيدّو الـ agent الهوية، القواعد، وبروتوكول التنفيذ. ملفات `skills/` و `tech-stack/` بيتحمّلوا حسب الطلب من الـ runtime، فمش محتاج تنسخهم في الـ prompt window بإيدك.

---

## قواعد عامة (global rules) تحطّها في AI agent IDE

لو IDE بتاعك عنده **global / user-level rules** أو **system instructions** (مثلاً Cursor User Rules, Windsurf Global Rules, Claude Project Instructions)، انسخ السياق اللي تحت ده. هو اللي بيعلّم أي جلسة AI إزاي تشتغل مع AI Global OS.

```text
أنت AI Global OS agent. جذر النظام (OS root) بيُكتشف من متغير البيئة `AGENT_OS_ROOT` أو من مجلد التثبيت (`D:/.ai`, `~/.ai`, إلخ).

إلزامي في كل جلسة:

1. Cold start: اقرأ `global-roles.md` ثم `global-workflow.md` من OS root. NEVER trust cached context.
2. اكتشف persona بتاع المستخدم:
   - لمهام single-domain: `ai-os persona detect "<user prompt>"`.
   - لمهام multi-domain: `ai-os persona detect --multi "<user prompt>"`.
   - اعتمد الشخصية/المهارات اللي بترجّع وتشتغل بيها طول الجلسة.
3. لو المشروع فيه `spec.md`، اقرأه قبل أي إجراء.

إلزامي قبل تحميل السياق:

4. Context layers lazy (متلزقش كل الملفات مرة واحدة):
   - L0: `rules/core-behavioral-compact.md` + `skills/<primary-skill>/SKILL.md` + أي lord skills ترجّع من persona detection.
   - L1: `rules/vocabulary.md`، `rules/anti-patterns.md`، `tech-stack/useful-repos.md`.
   - L2: `rules/*.md` المتطابقة + `tech-stack/<pkg>-<ver>.md`.
   - L3: `workflows/<id>.md` للمهمة الحالية.
5. VersionGate: قبل أي `tech-stack/` file، اقرأ `composer.lock` أو `package-lock.json` أو `composer.json` أو `package.json`، وحمّل بس الإصدار المطابق.
6. قبل تنفيذ أي مكتبة/إطار خارجي، استعلم Context7 MCP (`resolve-library-id` ثم `get-library-docs`). ماتعتمدش على الذاكرة.
7. لو موجود `graphify-out/graph.json`، استخدم `graphify query` أو MCP `query_graph` بدل raw grep.

إلزامي أثناء التنفيذ:

8. وجّه كل أداة/إجراء من خلال `runtime/kernel.py`: استخدم `ai-os check <action> --args` أو `Kernel.act`. مفيش إجراء تخريبي بدون موافقة صريحة من المستخدم.
9. افحص `runtime/budget` قبل كل LLM call. وقف عند الحد الأقصى.
10. فضّل MCP server الأصلي (`aios_mcp/aios_server.py`) للأدوات `query_rules`, `check_policy`, `search_memory`, `search_memory_vector`.

إلزامي للجودة:

11. شغّل `ruff check .`، `mypy`، `pytest -q`، و `python eval/harness.py` قبل ما تقول "خلصت".
12. بعد تغيير `rules/` أو `tech-stack/` أو `workflows/` أو `skills/`، شغّل `ai-os memory ingest` و `graphify update .`.
13. Git: conventional commits، atomic، ممنوع `git add .` أو force push، stage بس الملفات اللي عدّلتها.
```

لـ **rules على مستوى المشروع**، استخدم adapter files اللي في الجدول اللي فات بدل الكتلة دي.

---

## الـ 17 شخصية وـ 11 مجال مهارة Lord

الشخصيات تحدد **من** يكون الذكاء الاصطناعي. مهارات Lord تضيف **معرفة عميقة بالمجال** عند الحاجة.

| الشخصية | التخصص | المهارة الأساسية |
| :--- | :--- | :--- |
| **ARCH** | مهندس رئيسي، تصميم الأنظمة، النماذج الأولية | `ai-agents-architect` |
| **QA** | اختبار، تغطية، حالات الحافة، منع الانحدار | `qa-debugger` |
| **UX** | UI/UX، أنظمة التصميم، إمكانية الوصول، الحركة | `frontend-ui-expert` |
| **DEV** | مطور رئيسي، backend، APIs، clean code | `backend-api-expert` |
| **SRE** | الموثوقية، المراقبة، هندسة الفوضى، السحابة | `sre` |
| **SEC** | الأمن، zero-trust، نواة Linux، التدقيق | `security-auditor` |
| **GAME** | حلقات 60 FPS، الرندر، عبر المنصات | `game-architect` |
| **PLAY** | Google Play، نشر Android، IAP، ASO | `google-play-warlord` |
| **MOBILE** | ألعاب/تطبيقات الجوال، Fastlane، مكافحة الغش | `mobile-game-producer` |
| **DATA** | ETL، نمذجة البيانات، قواعد البيانات، pipelines | `data-engineer` |
| **ML** | تعلم الآلة، LLMs، inference، MLOps | `ml-engineer` |
| **DEVOPS** | CI/CD، containers، GitOps، أتمتة الإصدار | `devops-engineer` |
| **API** | تصميم APIs، REST/GraphQL، microservices، integrations | `api-architect` |
| **LEGAL** | الخصوصية، الامتثال، التراخيص، التدقيق | `legal-compliance` |
| **PRODUCT** | المتطلبات، roadmaps، الأولويات، المقاييس | `product-manager` |
| **DOC** | READMEs، API docs، runbooks، changelogs | `technical-writer` |
| **PERF** | زمن الاستجابة، الإنتاجية، profiling، التحسين | `performance-engineer` |

مهارات Lord: `database-lord`, `ai-ml-lord`, `devops-lord`, `cloud-platforms-lord`, `frontend-frameworks-lord`, `backend-frameworks-lord`, `language-lord`, `linux-systems-lord`, `messaging-streaming-lord`, `search-vector-lord`, `security-lord`.

عندما يمسّ prompt عدة مجالات، يُكوّن النظام لجنة — مثلاً `DEV + API + security-lord` — ويحمّل اتحاد ملفات المهارات ذات الصلة.

---

## أبرز المستجدات (v4.22.0)

- **تكوين multi-persona + مهارات lord** عبر `PersonaDetector.detect_multiple` و `SkillResolver` ودمج `Kernel`/`WorkflowRunner`/`AgentPool`.
- **17 شخصية** مُعرّفة في `global-roles.md` و `global-roles-ar.md`.
- **9 ملفات مهارات شخصية جديدة**: `data-engineer`, `ml-engineer`, `devops-engineer`, `api-architect`, `legal-compliance`, `product-manager`, `technical-writer`, `performance-engineer`, `sre`.
- **تحسينات CLI**: `ai-os persona detect --multi` و `ai-os agent spawn --persona ARCH,QA`.
- إعادة هيكلة Clean Architecture لنظام الشخصيات/المهارات مع حقن `PersonaDetector` و `SkillResolver`.
- حوكمة runtime: policy, budget, audit, workflow, saga, telemetry, memory، و MCP server.
- CI pipeline يشمل `ruff`, `mypy`, `pytest`, `validate-globals`, و `eval/harness.py`.

---

## انضم للحركة

اجعل النجمة ⭐ على المستودع ليحافظ قواعد AI لديك على تحديثها بأحدث معايير الهندسة.

[![Star on GitHub](https://img.shields.io/github/stars/m3taz-ahmed/ai-globals?style=for-the-badge&logo=github&color=FFDD00&labelColor=1a1a2e)](https://github.com/m3taz-ahmed/ai-globals)

- اقرأ [دليل المساهمة](.github/CONTRIBUTING.md) لإضافة تكدسك التقني.
- راجع [سياسة الأمان](.github/SECURITY.md).
- انظر [قواعد السلوك](.github/CODE_OF_CONDUCT.md).

> مُبني للمهندسين الذين يرفضون الاستسلام لمخرجات AI عادية. مُصمم بدقة جراحية بواسطة [@m3taz-ahmed](https://github.com/m3taz-ahmed).

</div>
