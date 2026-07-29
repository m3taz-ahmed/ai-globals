# Page Builder Standard Spec

## Goal
A single `Page` entity managed by Filament admin, built from composable sections/blocks, returned via API as structured content, and rendered by the frontend using per-section components.

## Database

### `pages` table
- `id` primary key
- `image` string (default page hero/share image)
- `title` json (translatable)
- `description` json (translatable)
- `slug` json (translatable, unique per locale)
- `content` json (translatable; builder payload)
- `meta_title` json
- `meta_desc` json
- `meta_keywords` json (cast to array)
- `is_home` boolean (default false)
- `is_header` boolean (default false)
- `is_footer` boolean (default false)
- `page_id` nullable unsigned integer (self-reference for parent pages)
- `timestamps`
- foreign key `page_id` references `pages(id)` on delete set null

### `static_pages` table
- `id`
- `type` string (unique, e.g. `privacy-policy`, `terms-of-service`, `faqs`, `ai-ethics`, `about-us`)
- `slug` json (translatable)
- `title` json (translatable)
- `content` json (translatable)
- `timestamps`

## Eloquent

### `Page` model
- `HasTranslations` from Spatie
- `$translatable = ['title', 'slug', 'description', 'content', 'meta_title', 'meta_desc', 'meta_keywords'];`
- `$fillable = ['slug', 'image', 'title', 'description', 'is_header', 'is_footer', 'is_home', 'content', 'page_id', 'meta_title', 'meta_desc', 'meta_keywords'];`
- casts: `content` => array, `meta_keywords` => array, booleans => boolean
- relation: `parent()` belongsTo `Page`

### `StaticPage` model
- `HasTranslations`
- `$translatable = ['title', 'content', 'slug'];`
- `$fillable = ['type', 'title', 'slug', 'content'];`

## Filament Admin

### `PageResource`
- Navigation group: `Content Management`
- Form: `PageForm::configure($schema)`
- Table: `PagesTable::configure($table)`

### `PageForm`
- Wizard steps:
  1. `General Information` — `image` FileUpload, `parent_id` Select
  2. `Content` — translatable tabs per locale with `Builder::make("content.{$locale}")`
  3. `Configurations` — `is_home`, `is_header`, `is_footer` Toggles
  4. `SEO Meta` — translatable `meta_title`, `meta_desc`, `meta_keywords`

### Builder Blocks
Each `Block::make('{name}_section')` has:
- Label with preview image `public/assets/images/builder-previews/{name}_section.png`
- Schema relevant to the section (title, description, image, repeater, etc.)
- `collapsible()` and `collapsed()` for long pages

### Static Page Resource
- Group: `Legal & Info`
- Auto-register navigation items per static page
- Form with translatable `title`, `slug`, `content`

## API

### Endpoints
- `GET /api/v1/pages` — list pages with Spatie QueryBuilder filters (`title`, `slug`, `is_home`, `is_header`, `is_footer`)
- `GET /api/v1/pages/{slug}` — full page with transformed `content`
- `GET /api/v1/pages/{slug}/sections` — content blocks only, with image URLs transformed

### Image URL Transformation
Recursive helper that transforms any string value whose key contains `image`, `icon`, `banner`, `video`, or `logo` into a full `Storage` or `asset` URL.

### Static Page Embedding
Map block types `privacy_policy_section`, `terms_of_service_section`, `faqs_section`, `ai_ethics_section`, `about_us_section` to `StaticPage::where('type', $slug)->first()` and replace `data` with the static page title/content.

## Frontend

- Fetch `/api/v1/pages/{slug}/sections`
- Render each block by `type` using a switch/map to section components
- Props come from `data`
- Images are already full URLs from API

## Reusability / Scale Path

When blocks need to be shared across pages or managed by non-devs:
1. Add `block_types` table with `name`, `schema` JSON, and optional Blade/React component name.
2. Add `page_sections` pivot: `page_id`, `block_type_id`, `order`, `data` JSON.
3. Keep block shape `type`/`data` so existing content can be migrated easily.

## Seeding

- Seed at least `privacy-policy`, `terms-of-service`, `faqs`, `ai-ethics`, `about-us` in `StaticPageSeeder`.
- Seed one `Home` page (`is_home = true`) with default hero section.
