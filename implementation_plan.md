# خطة التطوير والصيانة الدورية — AI Global OS v4.21.0

**تاريخ التدقيق:** 2026-07-14  
**الحالة الأساسية:** `ruff check .`, `mypy .`, `pytest -q`, `python eval/harness.py` — جميعها ✅ (all_pass: true)

---

## 1. حالة الكود الحالية (Audit Summary)

- **runtime/**: `kernel.py` يعمل كبوابة موحدة للسياسة/الميزانية/التدقيق؛ `policy.py` يستخدم AST evaluator آمن؛ `budget.py` يدير الحصص في `state/budget.json`؛ `workflow.py` يتتبع حالة التشغيل في SQLite.
- **memory/**: `MemoryStore` يجمع SQLite + FTS5 + relations + بحث vectorي باستخدام `turbovec` و `sentence-transformers`؛ `ingest.py` يقرأ ويخزّن ملفات `rules/`, `workflows/`, `tech-stack/`.
- **aios_mcp/**: `aios_server.py` يُقدّم 7 tools/resources عبر FastMCP.
- **cli.py**: واجهة `ai-os` تدير `status`, `check`, `run`, `memory`, `sync`, `graphify`.
- **Quality gate:** جميع الفحوصات الحالية خضراء، لكن توجد ديون تقنية وأخطاء تصرفات (behavior) خفية.

---

## 2. أوجه القصور والديون التقنية (Findings)

### 2.1 أمن وجودة

1. **`ask` لا يُعامل كطلب موافقة.** `Kernel.act` يرجع `ok: true` لأي قرار `ask` طالما الميزانية مسموح. السياسة `require-approval-for-write` تقول `ask` لكن الواقع أن الإجراء يُنفذ بدون موافقة صريحة.
2. **تهيئة MCP فورية (eager init).** `aios_server.py` يُنشئ `Kernel` و `MemoryStore` عند `import`، مما يُحمّل نموذج `sentence-transformers` ويفتح قواعد SQLite حتى لو لم يُستدعَ أي tool.
3. **Path traversal في `get_tech_stack`.** `pkg` و `ver` يُستخدمان لبناء `Path` مباشرةً دون تطهير، مما قد يسمح بالخروج من `tech-stack/`.
4. **عدم احترام الصلاحية الزمنية.** `MemoryStore.search` لا تُفلتر السجلات المُلغاة (`valid_to IS NOT NULL`).

### 2.2 أداء

1. **إعادة الاستيعاب الكامل دائمًا.** `Ingestor.ingest_all` يقرأ كل ملف ويعيد تضمينه في كل مرة، حتى لو لم يتغير. هذا يُضيع تكلفة التضمين.
2. **كتابة الفهرس Vector في كل سجل.** `VectorMemory.add` يستدعي `index.write(str(self.index_path))` بعد كل `add` فردي. مع `ingest_all` تُكتب القرص عشرات المرات.
3. **اتصال SQLite لكل ملف.** `Ingestor` يستدعي `delete_by_source` ثم `store.add` لكل ملف على حدة، وكل عملية تفتح اتصالًا جديدًا.
4. **استهلاك الميزانية قبل الفحص.** `BudgetManager.check` يزيد `usage` ثم يتحقق من الحدود، فإذا أُرجع `block` يظل الاستهلاك مُسجّلاً.

### 2.3 صيانة ومرونة

1. **نسخة مُعَدّة في أكثر من مكان.** `Kernel.status`, `runtime/__init__.py`, `memory/__init__.py` تحتوي على `"4.21.0"` يدويًا.
2. **كود ميت.** `MemoryStore._escape_like` غير مستخدم.
3. **`WorkflowRunner` بلا حالة فشل.** لا يُرجع `status` للتشغيل ولا يتوقف عند خطوة فاشلة.
4. **كتابة `budget.json` غير ذرية.** `state/budget.json` يُكتب مباشرة، قد يُتلف عند انقطاع التشغيل.

---

## 3. مقترحات التطوير (Ponytail Filter Applied)

> فلتر Ponytail: لا Postgres/Redis، لا واجهات رسومية، لا تبعيات ضخمة. الأفكار المُختارة جراحية، تعتمد على Python الأصلي + SQLite + الأدوات الموجودة.

### الفكرة 1: تفعيل بوابة الموافقة `ask` (Strict Rule Validation)

- **الهدف:** لا يمكن السماح بإجراء `ask` إلا بإرسال `approved=True` صريح.
- **التغييرات:**
  - `runtime/policy.py`: أضف `requires_approval: bool` للنتيجة عندما `decision == "ask"`.
  - `runtime/kernel.py`: في `act`، عند `requires_approval` تأكد من `kwargs.get("approved") is True`؛ إذا لا، أرجع `ok: False` مع `requires_approval: True`.
  - `cli.py`: أضف `ai-os check <action> --approve` (تُرسل `approved: true` في الـ args).
  - `dashboard/server.py`: `/api/check` يدعم `?approve=1` ويرفض `ask` بدونه.
  - `aios_mcp/aios_server.py`: `check_policy` يُمرّر `approved` من `args`.
  - تحديث الاختبارات: `test_kernel`, `test_cli`, `test_mcp_server` تتوقع `ok=False` للـ `ask` بدون `approved`.

### الفكرة 2: الاستيعاب المتزايد والمتجمع للذاكرة (Memory Ingestion Efficiency)

- **الهدف:** تجنب إعادة تضمين الملفات غير المتغيرة وتقليل كتابات القرص.
- **التغييرات:**
  - `memory/ingest.py`:
    - إنشاء `brain/ingest_manifest.json` يُخزن SHA-256 + mtime لكل `source`.
    - `ingest_all` يتخطى الملفات غير المتغيرة، يجمع المحتويات الجديدة/المتغيرة فقط، يحذف المصادر المتغيرة/المفقودة دفعة واحدة، ثم يُضيف دفعة واحدة.
  - `memory/store.py`:
    - `add_batch` تفتح اتصالًا واحدًا، تستخدم `executemany`، وتفلتر `valid_to IS NULL` في `search`.
    - `delete_by_source_batch` تحذف مجموعة من المصادر وتُعدّ أرقام `mem_ids` للـ vector.
  - `memory/vector.py`:
    - `add_batch(ids, texts)` يُشفّر النصوص دفعة واحدة، يستدعي `add_with_ids` بالبُعد (n, d) ثم يكتب الفهرس مرة واحدة.
    - `remove_batch(ids)` يحذف مجموعة ويكتب الفهرس مرة واحدة.

### الفكرة 3: MCP Lazy Init + Tools محسّنة + Path Protection

- **الهدف:** تسريع بدء MCP server وتوفير أدوات أغنى وأكثر أمانًا.
- **التغييرات:**
  - `aios_mcp/aios_server.py`:
    - `get_kernel()` و `get_memory()` باستخدام `functools.lru_cache(maxsize=None)` — لا يُحمل النموذج عند الاستيراد.
    - `get_tech_stack`: التحقق من `pkg` و `ver` بـ `re.fullmatch(r"[A-Za-z0-9_.-]+")` قبل بناء `Path`.
    - `query_rules`: استخدام `MemoryStore.search` (FTS5) بدلاً من `str.lower()` على كل ملف.
    - أضف `list_rules`, `get_rule`, `list_workflows`, `get_workflow` tools.
  - `cli.py`:
    - أضف `ai-os version` و `ai-os doctor`.
    - `doctor` يتحقق من النسخة، الملفات الأساسية، الحصص، توفر vector، ويعرض نتيجة `validate-globals`.
  - `config.py`:
    - أضف `VERSION` يُقرأ من `pyproject.toml` (regex) مع fallback.
    - `runtime/kernel.py` و `runtime/__init__.py` و `memory/__init__.py` يستخدمون `config.VERSION`.

---

## 4. خطة التنفيذ (Execution Plan)

### المرحلة 1: Foundation fixes
1. `config.py` — إضافة `VERSION` من `pyproject.toml`.
2. `runtime/kernel.py`, `runtime/__init__.py`, `memory/__init__.py` — استخدام `config.VERSION`.
3. `runtime/budget.py` — إصلاح استهلاك الميزانية قبل الفحص + كتابة JSON ذرية.
4. `memory/store.py` — إزالة `_escape_like`، إضافة فلتر `valid_to` في `search`.

### المرحلة 2: Strict Policy (`ask` gate)
1. `runtime/policy.py` — `requires_approval` في النتيجة.
2. `runtime/kernel.py` — رفض `ask` بدون `approved=True`.
3. `cli.py` — `ai-os check <action> --approve`.
4. `dashboard/server.py` — دعم `?approve=1`.
5. `aios_mcp/aios_server.py` — `check_policy` يمرّر `approved`.
6. تحديث الاختبارات.

### المرحلة 3: Memory efficiency
1. `memory/ingest.py` — manifest + incremental + batch delete.
2. `memory/store.py` — `add_batch` و `delete_by_source_batch`.
3. `memory/vector.py` — `add_batch` و `remove_batch`.
4. `cli.py` — `memory ingest` يستفيد من التحسينات تلقائيًا.

### المرحلة 4: MCP & DevEx
1. `aios_mcp/aios_server.py` — lazy init، path validation، أدوات جديدة.
2. `cli.py` — `version` و `doctor`.

### المرحلة 5: Validation
- `ruff check .`
- `mypy .`
- `pytest -q`
- `python eval/harness.py` (يجب أن يُعيد `all_pass: true`)

---

## 5. التأثيرات والكسر المحتمل (Risks)

- **Breaking:** إجراءات `ask` لن تُعيد `ok=True` إلا عند `approved=True`. هذا يُصلح سلوكًا خاطئًا، لكنه يتطلب تحديث اختبارات `ask`.
- **Performance:** تقليل وقت `ai-os memory ingest` بشكل كبير عند تكرار التشغيل، وتقليل كتابات vector إلى مرة واحدة لكل استيعاب.
- **Security:** `get_tech_stack` محمي من path traversal، و `ask` يحتاج موافقة صريحة.
- **No new infra:** لا يُضاف Postgres/Redis/واجهات رسومية/تبعيات جديدة.

---

## 6. موافقة المستخدم (Approval Checklist)

- [ ] الموافقة على هذه الخطة.
- [ ] الموافقة على تعديل اختبارات `ask` لتعكس السلوك الجديد.
- [ ] أولوية البدء: **المرحلة 2 أم المرحلة 3؟** (المقترح: 1 → 2 → 3 → 4)

---

*الخطة مكتوبة بالعربية حسب طلب المستخدم. سيتم البدء في التنفيذ فقط بعد الموافقة الصريحة.*
