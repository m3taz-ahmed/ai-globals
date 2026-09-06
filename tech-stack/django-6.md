[TECH] Django 6.1
[OBJ] Django 6.1 (released Aug 2026). Model field fetch modes, database-level ForeignKey.on_delete, dictionary-based email settings, Python 3.12-3.14 support. Breaking: DB backend API changes, admin InclusionAdminNode signature, removed deprecations.
[RULES]
1. [REQ] Use model field fetch modes: `field.fetch_mode` controls how fields are loaded (deferred, fetched, etc.). Reduces query overhead for wide tables without manual `.defer()` / `.only()`.
2. [REQ] Use database-level `ForeignKey.on_delete`: push cascade/set-null logic to DB layer via `db_on_delete` — reduces ORM round-trips, ensures integrity even with raw SQL.
3. [REQ] Use dictionary-based email settings: `EMAIL = {"host": "...", "port": 587, ...}` in `settings.py` replaces flat `EMAIL_HOST` / `EMAIL_PORT` / etc. Flat settings still work but deprecated.
4. [REQ] Support Python 3.12-3.14 only. Python 3.11 dropped. Verify `python_requires` in `pyproject.toml`.
5. [REQ] Use async views / middleware / ORM: `async def view(request):` with `await Model.objects.afilter()`. Use `ASGI` deployment (Daphne/Uvicorn/Hypercorn).
6. [REQ] Use `ORM` async methods: `.afilter()`, `.acreate()`, `.aupdate()`, `.adelete()`, `.aiterate()`. Never mix sync + async in same request path.
7. [REQ] Use `django.db.models` `GeneratedField` for computed columns (stored/virtual). Virtual generated columns (PG 18) supported.
8. [REQ] Use `django.forms` with `ModelForm` + `fields = [...]` or `exclude = [...]`. Never `fields = "__all__"` in production (security: mass assignment).
9. [REQ] Use `django.contrib.postgres` for PG-specific features: `ArrayField`, `JSONField`, `SearchVector`, `TrigramSimilarity`.
10. [REQ] Use `select_related()` for FK / one-to-one (JOIN), `prefetch_related()` for reverse FK / many-to-many (separate query). Avoid N+1 queries.
11. [REQ] Use `django.db.transaction.atomic()` for multi-operation DB writes. Use `on_commit()` for post-commit side-effects.
12. [REQ] Use Django admin with `list_display`, `list_filter`, `search_fields`, `readonly_fields`. Customize templates via `templates/admin/`.
13. [REQ] Use `django-stubs` + `mypy` for type checking. `django-debug-toolbar` in dev only.
14. [REQ] Use `manage.py check` + `manage.py makemigrations --check` in CI to catch model drift.
15. [REQ] Migrate DB backend API changes: custom DB backends must update `get_database_version` / `get_connection` signatures. Review third-party backend compat.
16. [REQ] Update admin `InclusionAdminNode` signature if custom admin templatetags used — signature changed in 6.1.
17. [REQ] Review removed deprecations from 5.x: check upgrade guide for `assertFormError`, `assertQuerysetEqual`, old middleware, etc.
18. [CMD] `django-admin startproject myproject` scaffold new project.
19. [CMD] `python manage.py makemigrations && python manage.py migrate` create + apply migrations.
20. [CMD] `python manage.py test` run test suite.
21. [PROHIBIT] Never use `Model.objects.get()` without `try/except` (raises `DoesNotExist` / `MultipleObjectsReturned`).
22. [PROHIBIT] Never use raw `cursor.execute()` with string interpolation — use parameterized queries (`%s`).
23. [PROHIBIT] Never disable `CSRF` middleware (`django.middleware.csrf.CsrfViewMiddleware`).
[COMPAT]
- Django 6.1 (released Aug 2026).
- Python 3.12, 3.13, 3.14 supported.
- PostgreSQL 14+ recommended (18 for virtual generated columns).
- MySQL 8.0.11+, MariaDB 10.4+.
- Breaking: DB backend API changes, admin InclusionAdminNode signature, removed 5.x deprecations.
[REFS]
- https://docs.djangoproject.com/en/6.1/
- https://docs.djangoproject.com/en/6.1/releases/6.1/
- https://docs.djangoproject.com/en/6.1/topics/db/queries/
- https://docs.djangoproject.com/en/6.1/topics/async/
