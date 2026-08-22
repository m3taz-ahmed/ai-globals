[TECH] Flask 3.x
[OBJ] Lightweight WSGI micro-framework with blueprints, extensions, application factory pattern, and optional async support.
[RULES]
1. [REQ] Use the application factory pattern: `def create_app(config_name="dev"): app = Flask(__name__); ...; return app` — never instantiate `Flask` at module level.
2. [REQ] Organize routes into `Blueprint` objects (`bp = Blueprint("auth", __name__, url_prefix="/auth")`) and register them in the factory.
3. [REQ] Load configuration from a class (`app.config.from_object(Config)`) or environment (`app.config.from_envvar("APP_SETTINGS")`); never hardcode secrets in source.
4. [REQ] Use Flask-SQLAlchemy 3.x with the application factory: initialize `db = SQLAlchemy()` at module level and call `db.init_app(app)` inside the factory.
5. [REQ] Use `@app.teardown_appcontext` to remove SQLAlchemy sessions; never leave DB sessions open across requests.
6. [REQ] Use Jinja2 autoescaping (enabled by default for `.html` / `.jinja` templates); never render user input with `Markup()` or `|safe` without sanitization.
7. [REQ] Use `flask.ctx` / `g` object for per-request shared state; never use module-level globals for request data.
8. [REQ] Register error handlers with `@app.errorhandler(404)` etc.; return a consistent JSON or template error response.
9. [REQ] Use `async def` view functions with `async_mode="auto"` (Flask 3 supports `asyncio.run` wrapper); prefer ASGI-to-WSGI bridge (asgiref) for production async.
10. [REQ] Use `flask.cli` commands (`@app.cli.command("init-db")`) for management tasks; never use ad-hoc scripts that bypass the app context.
11. [REQ] Enable `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, `REMEMBER_COOKIE_SECURE`, and `PREFERRED_URL_SCHEME = "https"` in production.
12. [REQ] Use Flask-Login for session auth or Flask-JWT-Extended for token auth; never implement custom session management without signed cookies.
13. [REQ] Run with a WSGI server (Gunicorn / uWSGI) in production; never use `app.run()` (development server) in production.
14. [PROHIBIT] Never set `DEBUG = True` in production. Never use `app.secret_key = "dev"` — load from environment.
15. [PROHIBIT] Never use `db.session.execute(text(f"...{user_input}..."))` — always use parameterized queries or ORM methods.
[COMPAT]
- v3.0: Python 3.8+, async view support, `flask --app` CLI, removed deprecated APIs.
- v3.1: Python 3.9+, `async_mode` config, improved `send_file` security, SSE helper.
[REFS]
- https://flask.palletsprojects.com/en/stable/
- https://flask-sqlalchemy.palletsprojects.com/en/stable/
- https://flask-login.readthedocs.io/en/latest/
