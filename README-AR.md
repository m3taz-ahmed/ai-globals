<div align="right" dir="rtl">
  <img src="logo.png" width="160" alt="شعار aiZee">
  <h1>aiZee — نظام التشغيل العالمي للذكاء الاصطناعي</h1>
  <p><strong>حول أي مساعد ذكاء اصطناعي إلى مهندسك الرئيسي — سيادة كاملة، جودة صفرية العيوب.</strong></p>

  <p>
    <img src="https://img.shields.io/badge/%D8%A5%D8%B5%D8%AF%D8%A7%D8%B1-6.0.0-6C63FF?style=for-the-badge&logo=buffer&logoColor=white&labelColor=1a1a2e" alt="الإصدار 6.0.0">
    <img src="https://img.shields.io/badge/%D8%A7%D8%AE%D8%AA%D8%A8%D8%A7%D8%B1%D8%A7%D8%AA-7653%20%D9%86%D8%A7%D8%AC%D8%AD-00C896?style=for-the-badge&logo=pytest&logoColor=white&labelColor=1a1a2e" alt="7653 اختبار ناجح">
    <img src="https://img.shields.io/badge/%D8%AA%D8%BA%D8%B7%D9%8A%D8%A9-100%25-10B981?style=for-the-badge&logo=codecov&logoColor=white&labelColor=1a1a2e" alt="تغطية 100%">
    <img src="https://img.shields.io/badge/%D8%A7%D9%84%D8%B1%D8%AE%D8%B5%D8%A9-MIT-3B82F6?style=for-the-badge&logo=opensourceinitiative&logoColor=white&labelColor=1a1a2e" alt="الرخصة: MIT">
  </p>
  <p>
    <img src="https://img.shields.io/badge/%D8%B4%D8%AE%D8%B5%D9%8A%D8%A7%D8%AA-29-EC4899?style=for-the-badge&logo=buffer&logoColor=white&labelColor=1a1a2e" alt="29 شخصية">
    <img src="https://img.shields.io/badge/%D9%85%D9%87%D8%A7%D8%B1%D8%A7%D8%AA-139-10B981?style=for-the-badge&logo=checkmarx&logoColor=white&labelColor=1a1a2e" alt="139 مهارة">
    <img src="https://img.shields.io/badge/%D8%B3%D9%8A%D8%B1_%D8%A7%D9%84%D8%B9%D9%85%D9%84-63-0EA5E9?style=for-the-badge&logo=checkmarx&logoColor=white&labelColor=1a1a2e" alt="63 سير عمل">
    <img src="https://img.shields.io/badge/%D9%85%D8%B1%D8%A7%D8%AC%D8%B9_%D8%AA%D9%82%D9%86%D9%8A%D8%A9-265-F59E0B?style=for-the-badge&logo=sparkles&logoColor=white&labelColor=1a1a2e" alt="265 مرجع تقنية">
  </p>
</div>

---

<div dir="rtl">

[اقرأ النسخة الإنجليزية](README.md) · [سجل التغييرات](CHANGELOG.md) · [دليل التثبيت](#التثبيت)

---

## ما هو aiZee؟

**نظام تشغيل محكم الإصدار** يجلس بينك وبين كل مساعد ذكاء اصطناعي — Cursor، Claude، Copilot، Windsurf، Cline، Aider، Devin — ويفرض معايير الهندسة وسياسات الأمان والانضباط المعماري على كل سطر كود مولّد.

**المشكلة التي يحلها:** المساعدات الذكية تهلوس APIs، تنسى الاتفاقيات، تتجاهل الأمان، وتشحن ديونًا تقنية صامتة. aiZee يجبرها على القراءة من مصدر حقيقة مركزي *قبل* كتابة سطر واحد — وفي v6 يتحقق من كل إجراء *أثناء* تنفيذه، لا مجرد توثيق بعده.

| بدون aiZee | مع aiZee |
| :--- | :--- |
| انحراف السياق بعد عدة prompts | القواعد والشخصيات تُحمّل كل جلسة |
| حزم قديمة وديون تقنية صامتة | تثبيت إصدار دقيق عبر MCP حي |
| SQL خام، XSS مفقود، أسرار ضعيفة | OWASP و zero-trust و RBAC مفروضة |
| إعادة هيكلة عشوائية | تغييرات جراحية عبر بوابات policy + budget + audit |
| حواجز حماية موجودة لكن خارج المسار | **v6: الإنفاذ مربوط بـ `Kernel.act()` وكل استدعاء MCP** |

---

## الجديد في v6.0.0 — Runtime محكوم فعليًا

التغيير الجوهري: **الإنفاذ صار على مسار التنفيذ**. وحدات الحماية التي كانت مستقلة (مختبرة لكن غير مربوطة) تعمل الآن داخل خط الأنابيب الفعلي.

### الإنفاذ على مسار التنفيذ

- **`runtime/enforcement.py`** — مكوّن إنفاذ موحّد: جدار MCP → فحص AgentGateway للطلب → التنفيذ → فحص الاستجابة → التدقيق. مشترك بين كل مسارات الاستدعاء.
- **`Kernel.act()`** — أحكام AgentGateway (ALLOW / REDACT / BLOCK) تحكم الإجراءات الحقيقية؛ فحوص الحقن وتسريب الأسرار تطبّق على حقول الشكل النصي دون حظر كتابة الملفات العادية.
- **MCP الصادر** — `McpClient` (متزامن + غير متزامن) و`McpAgent` يشغّلان الجدار والبوابة حول كل استدعاء خارجي.
- **MCP الوارد** — أدوات aiZee الـ98 تحتفظ بـ RBAC *وتُغلّف* بفحوص البوابة.

### عمق الكشف

- **كاشف الحقن L1→L3** — 13 تقنية بأنماط + طبقة تشابه دلالي (embeddings) + خيار LLM-judge. حتمي بدون نماذج افتراضيًا.
- **Dual-LLM مقوّى** — مخرجات العامل المعزول مُقيدة بمخطط Pydantic؛ فشل التحليل آمن (fail-safe).
- **MCP 2026-07-28 عديم الحالة** — تفاوض `protocolVersion` لكل طلب + توجيه بترويسات `Mcp-Method`/`Mcp-Name`.

### عمق الحوكمة

- **أحكام APL** — يمكن للسياسات الآن `modify` (إعادة كتابة الحمولة، مدقّقة) و`observe` (سماح + تسجيل) بجانب allow/ask/deny.
- **خطافات دورة الحياة** — طورا `output.pre_send` و`memory.pre_write`؛ الخطافات تستطيع النقض أو التعديل.
- **`aizee heal`** — منسّق إصلاح آمن (dry-run افتراضيًا، `--apply` بتأكيد، تدقيق في `state/heal.log`).
- **ميزانيات لكل PR** — حدود إنفاق تراكمية بمفتاح PR (`AIZEE_PR_ID`) فوق نوافذ الجلسة/الساعة/اليوم.
- **بوابة الإصدار** — `eval/release_gate.py` يشغّل سلم الأولويات للموثوقية على rollouts المسجلة؛ مربوط بـ `aizee ci`.
- **جناح الفوضى** — `eval/chaos.py` سيناريوهات حقن أعطال + حساب موازنات الأخطاء.

### الذاكرة وأسطح البروتوكول

- **ذاكرة ثنائية الزمن** — `store.as_of(as_of=..., valid_at=...)` تفرّق بين "ماذا عرفنا وقتها" و"ما الذي كان صحيحًا وقتها"؛ تثبيت، حذف ناعم بختم زمني، علاقات تناقض.
- **`aizee memory compact`** — ضغط تلقائي لـ Memory.md (سقف 500 سطر، إنقاذ `[PINNED]`، أرشفة في `memory/archive/`).
- **Code Mode** — `aizee codemode` ينفّذ مقاطع Python معزولة تستدعي أدوات MCP مباشرة (فحص AST + builtins مقيّدة + جسر محكوم + مهلة).
- **خادم A2A** — يعرض aiZee كندّ A2A: `/.well-known/agent-card.json` + JSON-RPC `tasks/send|get|cancel` (loopback + bearer).
- **`aizee bootstrap`** — يبني جذر OS أدنى بعد `pip install aizee` (idempotent، dry-run افتراضيًا).
- **تدقيقات استشارية** — `aizee task overcheck` (إشارات الهندسة الزائدة من الخطة + الرسم)، `aizee task curriculum` (خطة تعلّم مرحلية من مراجع tech-stack).

التفاصيل الكاملة: [CHANGELOG.md](CHANGELOG.md)

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

**PyPI:**
```bash
pip install aizee
aizee bootstrap --target ~/.aizee --yes   # بناء جذر OS أدنى
export AIZEE_ROOT=~/.aizee
```

### التحقق

```bash
aizee doctor    # فحص صحة (46 فحصًا)
aizee heal      # تشخيص + إصلاح آمن (dry-run؛ --apply للتنفيذ)
aizee status    # الشخصية، المهارات، الميزانية
```

---

## المعمارية الأساسية

```
.ai/                         # الجذر السيادي (يُكتشف عبر AIZEE_ROOT)
├── AGENTS.md                # البوتلودر المرجعي لكل الأدوات
├── global-roles.md          # 29 شخصية + قواعد تشغيلية
├── global-workflow.md       # بروتوكول التحميل المعرفي والتنفيذ
├── runtime/                 # النواة: policy، budget، audit، 142 وحدة حوكمة
│   ├── kernel.py            # الواجهة — Probity → Guardian → Policy → Loop → Budget → Audit
│   ├── enforcement.py       # مكوّن إنفاذ موحّد (firewall + gateway)
│   ├── agent_gateway.py     # حواجز طلب/استجابة (ALLOW/REDACT/BLOCK)
│   ├── injection_detector.py# L1 أنماط + L2 دلالي + L3 حكم LLM
│   ├── codemode/            # تنفيذ code-mode معزول فوق أدوات MCP
│   ├── a2a_server.py        # كشف كندّ A2A (agent card + tasks)
│   └── policies/            # YAMLs: default/guardian/probity/mcp_firewall
├── memory/                  # SQLite + FTS5 + vector، استعلامات ثنائية الزمن
├── aizee_mcp/               # خادم MCP (98 أداة، 3 موارد)
├── eval/                    # معايير، فوضى، موثوقية، بوابة إصدار
├── skills/                  # 139 مهارة شخصية + lord
├── workflows/               # 63 بروتوكول تنفيذ بالمحفزات
├── rules/                   # قواعد سلوكية مضغوطة
├── tech-stack/              # مراجع مثبتة بالإصدار
├── dashboard/               # لوحة ويب (Python stdlib HTTP)
├── scripts/                 # مثبتات، مدققون، أغلفة MCP
└── pyproject.toml           # بيانات الحزمة + إعدادات الجودة
```

---

## الأعمدة الستة

### 1. تركيب الشخصية + المهارة
29 شخصية (`ARCH`، `QA`، `SEC`، `DEV`، `SRE`، `DATA`، `ML`، `DEVOPS`، `API`…) مع مهارات lord للمجالات. تُكتشف تلقائيًا لكل مهمة — بلا اختيار يدوي.

```bash
aizee persona detect --multi "build a secure docker API with postgres"
# → Primary: ARCH + Secondary: SEC, DEVOPS + Lords: security-lord, cloud-platforms-lord
```

### 2. حوكمة وقت التشغيل
كل إجراء يمر بخط البوابات قبل التنفيذ:

```
Probity → Guardian → Policy → Loop Detector → Budget → Audit
        └─ AgentGateway: أحكام حقن + تسريب أسرار (v6)
```

- **محرك السياسات** — قواعد YAML `allow/ask/deny/modify/observe` بتقييم آمن
- **جدار MCP** — بوابة قائمة على القواعد لاستدعاءات الأدوات الصادرة
- **AgentGateway** — حواجز طلب/استجابة على كل مسار مُنفَّذ
- **مدير الميزانية** — حدود tokens/cost/calls لكل جلسة/ساعة/يوم/أسبوع/شهر **ولكل PR**
- **سجل التدقيق** — مربوط بتجزئة SHA-256 وموقّع Ed25519، كاشف للعبث
- **منفّذ سير العمل** — تنفيذ durable مدعوم بـ SQLite مع تعويض saga

### 3. حقيقة أرضية حية
Context7 MCP يجلب وثائق المكتبات الحالية قبل التنفيذ. رسم المعرفة graphify يحل محل `grep` الأعمى للتنقل في الكود.

### 4. ذاكرة هجينة
SQLite + FTS5 بحث نصي كامل + فهرس vector اختياري (SentenceTransformers). طبقات episodic وsemantic وfactual وprocedural — الآن مع تثبيت، حذف ناعم، روابط تناقض، سلامة HMAC، واستعلامات `as_of` ثنائية الزمن.

```bash
aizee memory ingest                # إعادة بناء الفهرس بعد التغييرات
aizee memory search "docker"       # بحث نصي + دلالي
aizee memory compact               # إبقاء Memory.md ضمن سقف الأسطر
```

### 5. بوابات الجودة (صفر عيوب)
```bash
ruff check .                 # 0 تحذيرات
mypy                         # كتابة صارمة
aizee test --full            # المجموعة الكاملة + التغطية (fail-under=100)
python eval/harness.py       # تقييم E2E: ruff + mypy + pytest + validate-globals
```

### 6. كفاءة الرموز
كشف الشخصيات محلي (Python خالص، صفر tokens LLM). Code Mode يستبدل ذهاب-إياب JSON لاستدعاء الأدوات بمقاطع معزولة تستدعي الأدوات مباشرة — tokens تنسيقية أقل بشكل ملموس في مهام الأدوات المتعددة.

---

## خريطة الإنفاذ في وقت التشغيل

| المسار | البوابات المطبقة |
| :--- | :--- |
| `Kernel.act()` | Probity → Guardian → Policy → Loop → Budget → Audit + فحوص prompt لـ AgentGateway |
| MCP الصادر (`McpClient`، `McpAgent`، `aizee mcp call`) | mcp_firewall → طلب البوابة → تنفيذ → استجابة البوابة |
| MCP الوارد (أدوات `aizee_mcp`) | RBAC + تغليف طلب/استجابة بالبوابة |
| الدردشة (`kernel.chat_message`) | prompt_gate → … → خطافات `output.pre_send` |
| كتابات الذاكرة | خطافات `memory.pre_write` (نقض/تعديل) + سلامة HMAC |
| Code Mode (`aizee codemode`) | فحص AST + builtins مقيّدة + `call_tool` محكوم |
| مهام A2A | Bearer auth + معالج مهام محكوم |

---

## لوحة القيادة

```bash
python dashboard/server.py 8080
# → http://127.0.0.1:8080
```

واجهة مركز قيادة داكنة أولًا: لوحة أوامر (`Ctrl+K`)، مقاييس bento، حبوب حالة، ألواح زجاجية. مصادقة Bearer اختيارية عبر `AIZEE_DASHBOARD_TOKEN`.

**التبويبات:** نظرة عامة · مستكشف الذاكرة · رمل السياسات · سير العمل · Sagas · دردشة · Tech Stack · قياسات · صحة النظام · سجلات التدقيق · **الإعدادات**

> **مهم — عطّل خوادم MCP التي لا تستخدمها.** كل خادم مفعّل يستهلك ذاكرة وقد يولّد عملية فرعية عند أول استدعاء. بعد التثبيت، افتح **Settings → MCP Servers**، ألغِ ما لا تحتاجه (**Uncheck All** ثم أعد تحديد المطلوب)، واضغط **Save Changes**. النواة تعيد التحميل تلقائيًا عند الحفظ.

الإعدادات تُحفظ في `state/settings.json` (gitignored، تنجو من التحديثات). ترحيلات المخطط تعمل تلقائيًا — النسخ القديمة تُحفظ كنسخة احتياطية.

---

## الأوامر الرئيسية

| الأمر | الوظيفة |
| :--- | :--- |
| `aizee doctor` | صحة البيئة (46 فحصًا) |
| `aizee heal [--apply] [-y]` | تشخيص + إصلاحات آمنة (dry-run افتراضيًا) |
| `aizee check <action>` | حكم السياسة على إجراء |
| `aizee memory compact [--apply]` | ضغط Memory.md إلى سقف الأسطر |
| `aizee codemode --code/--file` | مقطع معزول يستدعي أدوات MCP |
| `aizee task overcheck` | تدقيق الهندسة الزائدة للخطة النشطة |
| `aizee task curriculum --stack …` | خطة تعلم مرحلية من مراجع tech-stack |
| `aizee bootstrap --target DIR` | بناء جذر OS (بعد `pip install`) |
| `aizee ci` | بوابات CI كاملة تشمل بوابة موثوقية الإصدار |
| `aizee security scan <path>` | SAST + تنسيق الماسحات الخارجية |

---

## بوابات الجودة

| البوابة | الأمر | الحالة |
| :--- | :--- | :--- |
| Lint | `ruff check .` | 0 تحذيرات |
| Types | `mypy` | 0 أخطاء (صارم) |
| Tests (سريعة) | `aizee test` | طبقة سريعة بدون تغطية |
| Tests (كاملة) | `aizee test --full` | المجموعة الكاملة، تغطية بحد أدنى 100% |
| السلامة | `scripts/validate-globals.py` | 539 ملفًا، 0 أخطاء |
| مزامنة الوثائق | `scripts/sync_docs.py --check` | متزامنة |
| E2E | `python eval/harness.py` | كل البوابات تنجح |
| الإصدار | `python eval/release_gate.py` | سلم موثوقية على أدلة rollouts |

---

## حزمة التقنيات

- **النواة:** Python خالص 3.10+ (لا حاجة لـ Node.js لنواة OS)
- **الذاكرة:** SQLite + FTS5 + vectors اختيارية بـ SentenceTransformers
- **MCP:** خادم FastMCP بـ 98 أداة
- **لوحة القيادة:** خادم HTTP من stdlib + SQLite
- **رسم المعرفة:** graphify (اختياري)
- **التبعيات:** pyyaml، pydantic، rich، cryptography، numpy، turbovec

---

## المساهمة

1. Fork ← فرع feature (`feature/*`)
2. اكتب الاختبارات أولًا (نمط AAA، سلوك واحد لكل اختبار)
3. شغّل `ruff check . && mypy && pytest -q && python eval/harness.py`
4. كل البوابات يجب أن تنجح — لا PR بدون أخضر
5. Commits اتفاقية: `type(scope): subject`
6. PR ≤ 400 سطر، اختبارات مستهدفة فقط

---

## الرخصة

MIT — انظر [LICENSE](LICENSE).

---

<div align="center" dir="ltr">
  <p><strong>aiZee</strong> — The policy layer for AI coding.</p>
  <p>Built by <a href="https://linkedin.com/in/moataz-ahmed">Moataz Ahmed</a></p>
</div>
