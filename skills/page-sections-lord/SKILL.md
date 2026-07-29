---
name: page-sections-lord
description: Design and build section-based landing and content pages with Filament Builder in Laravel.
---
[SKILL] page-sections-lord
[OBJ] Design, scaffold, and operate reusable page sections and landing pages via Filament/Laravel.
[RULES]
1. [CMD] IDs: Filament `/filamentphp/filament`; Filament Spatie Translatable Plugin `/filamentphp/spatie-laravel-translatable-plugin`; Spatie Translatable `/spatie/laravel-translatable`; Spatie Query Builder `/spatie/laravel-query-builder`; Filament Fabricator `/z3d0x/filament-fabricator` (block-based alternative).
2. [REQ] Tourx pattern core: `Page` model with JSON `content`; translatable `title`, `slug`, `description`, `content`, `meta_title`, `meta_desc`, `meta_keywords`; parent `page_id` self-reference; `is_home`, `is_header`, `is_footer` flags.
3. [REQ] Filament `Builder` for `content.{locale}`; one `Block::make('X_section')` per section with a unique type key and a schema that matches the frontend component props.
4. [REQ] Standard block shape: `{ "type": "hero_section", "data": { ... } }`; keep `data` flat; use consistent image key names (`image`, `background_image`, `*_image`, `logo`, `icon`).
5. [REQ] Static pages: `StaticPage` model with `type` and translatable `title`/`content`/`slug`; seed `privacy-policy`, `terms-of-service`, `faqs`, `ai-ethics`, `about-us`; embed via a `static_*_section` block that maps type to slug.
6. [REQ] API: `PageController` with index (`Spatie\QueryBuilder`), `show($slug)` by locale, and `sections($slug)`; cast `content` to array; recursively transform image keys to full `Storage::disk('s3')->url()` or `asset(Storage::url(...))` URLs.
7. [REQ] i18n: Spatie `HasTranslations` on `Page` and `StaticPage`; Filament translatable tabs; lookup by `slug->{locale}` with fallback to default locale; `app()->getLocale()` in controller.
8. [REQ] Common blocks: hero, destinations, testimonials, vision, mission, story_stats, tech_features, team, cta, contact, global_presence, faqs, privacy_policy, terms_of_service, ai_ethics, about_us. Add new blocks via new `Block` in `PageForm` and a matching frontend component.
9. [REQ] Image handling: `FileUpload::image()` with directory `assets/images/pages/{section}`; store only relative paths in DB; API returns absolute URLs; preview images under `public/assets/images/builder-previews/{section}.png` for Filament block labels.
10. [REQ] Reusability: when blocks need cross-page reuse, tenant-scoping, or user-defined block types, migrate to `page_sections` pivot or `filament-fabricator` block registry; keep block shape `type`/`data` to ease migration.
11. [REQ] New projects: start from `skills/page-sections-lord/templates/page-builder-spec.md`; follow the scaffold order: migrations → models → Filament resource/form → API controller/resource → routes → frontend section components → static pages seeder.
12. [REQ] Security/RBAC: use `filament-shield` for admin permissions; validate `slug` uniqueness per locale; never expose one tenant's page/section to another; apply tenant scope if multi-tenancy.
13. [REQ] Cross-stack questions query `page-sections-lord`, `backend-frameworks-lord`, `frontend-frameworks-lord`, and `mariadb-lord` if database-specific; explain the rationale.
