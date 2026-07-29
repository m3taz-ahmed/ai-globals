[WORKFLOW] 15-page-builder-setup
[OBJ] Scaffold a section-based landing/page builder in a Laravel + Filament project.
[RULES]
1. [REQ] Confirm tech stack: Laravel, Filament, Spatie Laravel Translatable, Spatie Laravel Query Builder, MariaDB/MySQL/PostgreSQL.
2. [CMD] Run `composer require filament/filament spatie/laravel-translatable spatie/laravel-query-builder`.
3. [CMD] Publish and configure `config/filament.php` and translatable locales.
4. [CMD] Create migrations for `pages` and `static_pages` using `skills/page-sections-lord/templates/page-builder-spec.md`.
5. [CMD] Create `App\Models\Page` and `App\Models\StaticPage` with `HasTranslations`, casts, and `$fillable`.
6. [CMD] Create `App\Filament\Resources\Pages\PageResource`, `PageForm`, `PagesTable`, and CRUD pages.
7. [CMD] Implement `Builder::make("content.{$locale}")` in `PageForm` with `Block` definitions for required sections; add preview images in `public/assets/images/builder-previews/`.
8. [CMD] Create `App\Filament\Resources\StaticPages\StaticPageResource`, form, table, and navigation items.
9. [CMD] Create `App\Http\Controllers\Api\V1\PageController` and `App\Http\Resources\PageResource` with image URL transformation and static page embedding.
10. [CMD] Add API routes: `GET /api/v1/pages`, `GET /api/v1/pages/{slug}`, `GET /api/v1/pages/{slug}/sections`.
11. [CMD] Seed static pages and a default home page.
12. [CMD] Run `php artisan migrate --seed` and test API responses.
13. [REQ] For frontend, create one component per section type and render from `content` array.
14. [REQ] If multi-tenancy is required, route to `mariadb-lord` and apply tenant scope to pages, static pages, and storage paths.
15. [REQ] Quality: run `php artisan test`, `pint`, `phpstan`, and verify image URL transformation for all nested block data.
