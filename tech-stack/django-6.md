[TECH] Django 6.1 (latest 6.1.1, Sep 2026)
[OBJ] Django 6.1.x — model field fetch modes (`QuerySet.fetch_mode`), `FETCH_PEERS` for N+1 fix, database-level `ForeignKey.on_delete` (`DB_CASCADE`, `DB_SET_NULL`, `DB_SET_DEFAULT`), dictionary-based `MAILERS` setting. Supports Python 3.12-3.14.
[RULES]
1. [REQ] Use `QuerySet.fetch_mode` for on-demand fetching — `FETCH_PEERS` batches sibling FK lookups to fix N+1 queries automatically.
2. [REQ] Use database-level `ForeignKey.on_delete`: `DB_CASCADE`, `DB_SET_NULL`, `DB_SET_DEFAULT` — handled by DB, not Django ORM. More efficient for large datasets.
3. [REQ] Use dictionary-based `MAILERS` setting for multiple email backends — `MAILERS = {"default": {...}, "transactional": {...}}`.
4. [REQ] Use Python 3.12-3.14 — Django 6.x requires Python 3.12+.
5. [REQ] Use `model.bases` for custom model base classes — declarative inheritance.
6. [REQ] Use `db_default` for database-side default values — computed by DB, not Python.
7. [REQ] Use `GeneratedField` for computed columns — `GeneratedField(db_persist=True, expression=...)`.
8. [REQ] Use `QuerySet.select_related()` for FK joins, `prefetch_related()` for reverse FK/M2M.
9. [REQ] Use `django.db.transaction.atomic()` for transaction management.
10. [REQ] Use `django.contrib.postgres` for PostgreSQL-specific features (ArrayField, JSONField, SearchVector).
11. [REQ] Use Django REST Framework (DRF) or Django Ninja for API development.
12. [REQ] Use `django-htmx` for HTMX integration — server-rendered partials with AJAX.
13. [PROHIBIT] Never use Django 5.x for new projects — 5.2 mainstream support ended.
14. [PROHIBIT] Never use PostgreSQL 14, MySQL < 8.4, MariaDB < 10.11 — dropped in Django 6.
[COMPAT]
- Django 6.1.1 (released Sep 2 2026).
- Django 6.0.0 released Dec 3 2025.
- Python 3.12, 3.13, 3.14 supported.
- PostgreSQL 15+, MySQL 8.4+, MariaDB 10.11+.
- Django 5.2 LTS: security fixes until Apr 2028.
[REFS]
- https://docs.djangoproject.com/en/6.0/releases/6.0/
- https://www.djangoproject.com/weblog/2025/dec/03/django-60-released/
- https://docs.djangoproject.com/en/6.1/releases/6.1/
