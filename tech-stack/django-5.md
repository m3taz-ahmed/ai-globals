[TECH] Django 5.x
[OBJ] High-level Python web framework with async views, ORM, admin, and batteries-included tooling.
[RULES]
1. [REQ] Use the application factory pattern via `django.setup()` and split settings (`base.py`, `dev.py`, `prod.py`) with `DJANGO_SETTINGS_MODULE` env var.
2. [REQ] Define async views with `async def` and use `async-to-sync` safe ORM access via `django.db.connections` or `sync_to_async` wrappers; never call the ORM directly inside async views.
3. [REQ] Use class-based views (CBVs) for CRUD operations and override `get_queryset` / `get_context_data` rather than duplicating logic in `get` / `post`.
4. [REQ] Keep models thin: business logic belongs in `models.py` methods, managers, or service modules — never in views or templates.
5. [REQ] Use `select_related` for FK / one-to-one and `prefetch_related` for reverse FK / many-to-many to eliminate N+1 queries.
6. [REQ] Apply migrations with `python manage.py makemigrations` then `migrate`; never edit migration files manually after they have been applied to a shared environment.
7. [REQ] Configure middleware order carefully: `SecurityMiddleware` first, `SessionMiddleware` before `AuthenticationMiddleware`, custom middleware last unless it must run early.
8. [REQ] Use `signals.py` for decoupled side-effects (post_save, pre_delete) but keep handlers lightweight; never put transaction-critical logic in signals — use `transaction.on_commit` instead.
9. [REQ] Enable `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, and `SECURE_HSTS_SECONDS` in production settings.
10. [REQ] Use Django REST Framework serializers with `fields = "__all__"` only for prototyping; explicitly list fields in production serializers and validate with `serializer.is_valid(raise_exception=True)`.
11. [REQ] Integrate Celery with `django_celery_results` and `django_celery_beat`; define tasks in `tasks.py` per app and always pass serializable args (PKs not model instances).
12. [REQ] Use `django.template.loaders.app_directories.Loader` and enable template caching (`APP_DIRS` or cached loader) in production.
13. [REQ] Run `python manage.py collectstatic --noinput` with `WhiteNoiseMiddleware` for static file serving in production without a reverse proxy.
14. [PROHIBIT] Never use `DEBUG = True` in production. Never hardcode `SECRET_KEY` — load from environment.
15. [PROHIBIT] Never use `raw()` SQL with f-string interpolation; always use parameterized queries or ORM.
[COMPAT]
- v5.0: Python 3.10+, async ORM improvements, database defaults, computed field rendering in admin.
- v5.1: Python 3.10+, async `ORM` query enhancements, `LoginRequiredMiddleware` added by default.
- v5.2: Python 3.10+, async `get_or_create` / `update_or_create`, `db_table` comment support.
[REFS]
- https://docs.djangoproject.com/en/5.2/
- https://www.django-rest-framework.org/
- https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html
