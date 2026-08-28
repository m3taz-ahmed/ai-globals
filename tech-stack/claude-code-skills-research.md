# تقرير: إضافات Claude Code — دراسة وتحليل

**التاريخ:** 2026-08-28  
**الشخصية:** UX (أساسي) + DEVX (ثانوي)  
**الـ Skills المُحمّلة:** frontend-ui-expert, context-compressor  
**الـ Lords:** frontend-frameworks-lord, flutter-design, clean-code-guard, docs-guard, arabic-dialect-lord  
**الـ Repos المُستنسخة:** `D:\server\temp\claude-skills-study\` (7 repos)

---

## 1. الخريطة الكاملة للإضافات (حسب المجال)

### 1.1 التصميم والواجهات (Design & UI) — **الأكثر تطورًا**

| الإضافة | المصدر | النجوم | الوظيفة |
|---------|--------|--------|---------|
| **Taste Skill** | senlindesign/taste-skill | ~37K | يستخرج "DNA التصميم" من أي موقع: tokens + trade-offs (لماذا هذا القرار، مش بس الأرقام). يتطلب Playwright MCP. ينتج `{domain}.md` + `{domain}.json`. |
| **Image-to-Code** | (داخل taste-skill) | — | يولّد صور تصميم أولاً، يحللها بعمق، ثم يكتب كود يطابقها. للـ hero sections والـ landing pages. |
| **Design Library Plugin** | zeta92/design-library-plugin | — | **شامل**: 58 نظام تصميم لشركات (Stripe, Linear, Vercel...) + 7 skills مدمجة. `/design <brand>` يحمّل نظام تصميم كامل. |
| **Web Design Guidelines** | vercel-labs/agent-skills | 24K | 100+ قاعدة للـ a11y, forms, dark mode, typography, i18n, performance, touch. |
| **UI/UX Pro Max** | nextlevelbuilder | 61K | 67 style, 161 palette, 57 font pairing, 99 UX guideline. يطابق نوع المنتج. |
| **Designer Skills** | Owl-Listener | 505 | 63 skill عبر دورة حياة التصميم كاملة (research → strategy → UI → interaction → handoff). |
| **Motion Design** | kylezantos | 256 | تدقيق الأنيميشن من 3 وجهات نظر مصممين. severity rankings. |
| **Accessibility Agents** | Community-Access | 214 | 11 وكيل WCAG 2.2 AA متخصص (ARIA, contrast, keyboard, cognitive...). |
| **Web Quality** | addyosmani | — | Lighthouse + Core Web Vitals (LCP, INP, CLS, SEO). |
| **Frontend Design (رسمي)** | anthropics/skills | — | يمنع "AI slop" — يجبر Claude يختار اتجاه جريء بدل Inter + purple gradient. |
| **Design Mode** | OkminLee | — | HTML/JSX artifacts مع preview + AI-slop verifier + 6 starters + Tweaks panel. |
| **Brand Guidelines** | anthropics | — | ألوان وخطوط Anthropic الرسمية. |
| **Canvas Design** | anthropics | — | فن بصري في PNG/PDF. |
| **Algorithmic Art** | anthropics | — | فن خوارزمي بـ p5.js. |
| **Web Artifacts Builder** | anthropics | — | React + Tailwind + shadcn/ui artifacts معقدة. |
| **Theme Factory** | anthropics | — | 10 ثيمات جاهزة + توليد ثيم جديد. |

### 1.2 الاختبار والأتمتة (Testing & QA)

| الإضافة | المصدر | الوظيفة |
|---------|--------|---------|
| **Webapp Testing (رسمي)** | anthropics | Playwright للاختبار المحلي: screenshots, logs, UI debugging. |
| **QA Skills** | neonwatty | 6 وكلاء QA متخصصين (smoke, ux, adversarial...) + multi-user flows + mobile audits. |
| **QA Playbooks** | nramkissoon | markdown playbooks → اختبارات Playwright قابلة للتنفيذ. |
| **Dev Browser** | mattheworiordan | تحكم بالمتصفح عبر natural language. DOM snapshots صديقة للـ LLM. |
| **Browser Skills** | Shahfarzane | Stagehand + Chrome. scraping, screenshots, form filling, design token extraction. |

### 1.3 الـ Backend والهندسة (Backend & Engineering)

| الإضافة | المصدر | الوظيفة |
|---------|--------|---------|
| **Backend Design** | sheitabrk | 13 skill + 6 agents + 5 commands + 3 hooks. reflexes مهندس senior: load, idempotency, security, observability, migration safety, N+1 detection. |
| **Full Stack 2.0** | amritmalla | 83 skill + 4 workflows. من idea → production. Spring Boot, FastAPI, Node, React, Flutter, K8s, AWS, Terraform. |
| **Clean Backend** | AllanOps | production-hardening: payment flows, deletes, background jobs, alerting. |
| **Senior Backend** | borghei | API scaffolding, DB migration, load testing, security hardening. |

### 1.4 الموبايل (Mobile)

| الإضافة | المصدر | الوظيفة |
|---------|--------|---------|
| **LibreMobileDev** | HermeticOrmus | 20 plugin: Flutter, React Native, Swift, Kotlin + CI/CD, store optimization, payments, security, performance. |
| **Flutter Claude Skills** | ImL1s | Flutter/Dart: testing, debugging, design-to-code, release, monetization. |
| **React Native Skills** | maikotrindade | RN production: core, ecosystem, Expo, performance, testing, reusables. |
| **Expo (رسمي)** | anthropics | Expo Router, SwiftUI, Jetpack Compose, CI/CD, App Store, Play Store. |

### 1.5 المهام المكتبية (Office & Documents)

| الإضافة | المصدر | الوظيفة |
|---------|--------|---------|
| **PDF** | anthropics | قراءة/كتابة/دمج/تقسيم/OCR لـ PDF. |
| **DOCX** | anthropics | Word documents كاملة. |
| **PPTX** | anthropics | عروض تقديمية. |
| **XLSX** | anthropics | جداول بيانات. |
| **Doc Co-authoring** | anthropics | سير عمل لكتابة التوثيق. |
| **Internal Comms** | anthropics | تقارير داخلية، تحديثات، FAQs. |

### 1.6 أدوات مساعدة (Utility)

| الإضافة | المصدر | الوظيفة |
|---------|--------|---------|
| **Skill Creator** | anthropics | إنشاء/تعديل/قياس skills. evals + variance analysis. |
| **MCP Builder** | anthropics | بناء MCP servers عالية الجودة. |
| **Slack GIF Creator** | anthropics | GIFs متحركة لـ Slack. |
| **Discernment Nudge** | anthropics | تحفيز الحكم النقدي. |
| **Academy Guide** | anthropics | أدلة تعليمية. |

---

## 2. الأنماط المعمارية (كيف تعمل الإضافات)

### 2.1 تنسيق SKILL.md
كل skill = مجلد فيه `SKILL.md` بـ YAML frontmatter:
```yaml
---
name: taste
description: Reverse-engineer any website's design taste...
compatibility: Requires Playwright MCP...
metadata:
  version: "1.1.0"
  author: Senlin
---
# Taste — Reverse-Engineer...
```
**aiZee يستخدم نفس التنسيق بالفعل** — توافق 100%.

### 2.2 التحميل التدريجي (Progressive Loading)
- عند البدء: الـ agent يرى `name` + `description` فقط
- عند تطابق المهمة: يُحمّل SKILL.md كامل (<5000 tokens)
- عند الحاجة: `references/` و `scripts/` تُحمّل عند الطلب
- **aiZee يعمل بنفس الطريقة** عبر `runtime/skill_routing.py`

### 2.3 الإضافات = Plugins (حزم)
الـ Plugin يجمع: skills + agents + commands + hooks + MCP servers في حزمة واحدة قابلة للتثبيت. مثال: `design-library-plugin` = 13 skill + hooks + MCP.

### 2.4 Hooks (خطافات)
- `UserPromptSubmit` — يُفعّل عند إرسال prompt
- `PreToolUse` / `PostToolUse` — قبل/بعد استدعاء أداة
- `Stop` — عند انتهاء الجلسة
- مثال من backend-design: `check_migration.py` يحذر من migrations خطرة قبل الكتابة

---

## 3. كيف نستفيد منها في aiZee

### 3.1 ما يمكن استيراده مباشرة (High Value, Low Effort)

| الإضافة | كيف نستفيد | الجهد |
|---------|------------|------|
| **Taste Skill** | تحويله لـ skill في aiZee: `skills/design-taste/SKILL.md`. يستخرج design DNA من أي URL. يتكامل مع frontend-ui-expert. | متوسط |
| **Web Design Guidelines** | استيراد الـ 100+ قاعدة كـ `skills/web-design-guidelines/SKILL.md` + `references/`. | صغير |
| **Backend Design** | استيراد الـ 13 skill كـ lord جديد: `skills/backend-design-lord/`. reflexes مهندس senior. | متوسط |
| **Image-to-Code** | دمج في `skills/image-to-code/SKILL.md`. سير عمل: صورة → تحليل → كود. | صغير |
| **Accessibility Agents** | استيراد كـ `skills/a11y-auditor/SKILL.md`. 11 وكيل WCAG 2.2 AA. | صغير |
| **Motion Design** | استيراد كـ `skills/motion-design/SKILL.md`. | صغير |
| **Web Quality** | استيراد كـ `skills/web-quality/SKILL.md`. Lighthouse + Core Web Vitals. | صغير |
| **QA Skills** | استيراد كـ `skills/qa-automation/SKILL.md`. 6 وكلاء QA. | متوسط |
| **Skill Creator (رسمي)** | استيراد كـ `skills/skill-creator/SKILL.md`. يساعد في بناء skills جديدة. | صغير |
| **MCP Builder (رسمي)** | استيراد كـ `skills/mcp-builder/SKILL.md`. | صغير |

### 3.2 ما يمكن استلهام المعمارية منه (High Value, High Effort)

| النمط | كيف نستلهمه | الأثر |
|-------|------------|------|
| **Design Library Plugin** | بناء `skills/design-library/` فيه 58 نظام تصميم. `/design <brand>` يحمّل نظام كامل. | عالي جدًا |
| **Plugin System** | aiZee لديه skills لكن ليس plugins (حزم تجمع skills+agents+hooks+MCP). إضافة `runtime/plugin_system.py`. | عالي |
| **Hooks System** | aiZee لديه `hook_lifecycle.py` لكن محدود. توسيعه لـ `PreToolUse`/`PostToolUse`/`UserPromptSubmit`. | متوسط |
| **AI-Slop Verifier** | subagent يراجع الـ screenshot ضد checklist من 7 فئات. إضافة `runtime/design_verifier.py`. | متوسط |
| **Progressive Loading** | aiZee يعمل به بالفعل لكن يمكن تحسينه: split SKILL.md لـ frontmatter + body + references. | صغير |

### 3.3 ما لدينا بالفعل ولا نحتاجه

| الإضافة | ما لدينا | التقييم |
|---------|---------|---------|
| **Skill Creator** | `runtime/spec_engine.py` + `runtime/skill_scanner.py` | لدينا أفضل |
| **MCP Builder** | `aizee_mcp/` (36 tool) | لدينا أفضل |
| **Backend Security** | `runtime/prompt_gate.py` + `runtime/injection_detector.py` + `runtime/taint.py` | لدينا أفضل |
| **QA Testing** | `eval/harness.py` + `eval/prompt_injection_suite.py` | لدينا أفضل في security، نحتاج UI testing |

---

## 4. الخطة المقترحة (مرتبة بالأولوية)

| الأولوية | المهمة | الجهد | الأثر |
|----------|--------|------|------|
| **P0** | استيراد Web Design Guidelines (100+ قاعدة) | صغير | عالي |
| **P0** | استيراد Taste Skill (design DNA extractor) | متوسط | عالي |
| **P0** | استيراد Image-to-Code workflow | صغير | عالي |
| **P1** | استيراد Backend Design (13 skill) | متوسط | عالي |
| **P1** | استيراد Accessibility Agents (11 وكيل WCAG) | صغير | عالي |
| **P1** | استيراد Web Quality (Lighthouse/CWV) | صغير | متوسط |
| **P2** | استيراد Motion Design | صغير | متوسط |
| **P2** | استيراد QA Skills (6 وكلاء) | متوسط | متوسط |
| **P2** | بناء Design Library (58 نظام تصميم) | كبير | عالي جدًا |
| **P3** | إضافة Plugin System لـ aiZee | كبير | عالي |
| **P3** | إضافة AI-Slop Verifier | متوسط | متوسط |
| **P3** | توسيع Hooks System | متوسط | متوسط |

---

## 5. الخلاصة

**الإضافات الأكثر قيمة لـ aiZee:**
1. **Taste Skill** — استخراج design DNA من أي موقع (فريد، لا يوجد بديل)
2. **Web Design Guidelines** — 100+ قاعدة جاهزة (مرجعية Vercel)
3. **Image-to-Code** — سير عمل صورة → كود (مبتكر)
4. **Backend Design** — reflexes مهندس senior (13 skill)
5. **Accessibility Agents** — 11 وكيل WCAG متخصص

**ما يميز aiZee عن Claude Code:**
- aiZee لديه **نظام حوكمة كامل** (kernel, policy, budget, audit, taint, injection defense)
- Claude Code skills = تعليمات فقط؛ aiZee skills = تعليمات + تنفيذ مُحوكَم
- aiZee لديه **prompt injection defense stack** (اللي بنيناه) — لا يوجد في Claude Code
- Claude Code أقوى في **التصميم والـ UI** — هذا ما نستورده

**التوصية:** ابدأ بـ P0 (3 مهام صغيرة الجهد، عالية الأثر) — تضيف قيمة تصميمية فورية لـ aiZee.
