[TECH] FastAPI 1.x
[OBJ] Modern async Python web framework with Pydantic v2 validation, dependency injection, and automatic OpenAPI generation.
[RULES]
1. [REQ] Define request/response models with Pydantic v2 `BaseModel`; use `Field` for constraints, `model_config = ConfigDict` for config — never use v1 `Config` class.
2. [REQ] Use `Depends()` for dependency injection; keep dependencies composable and testable by returning typed objects.
3. [REQ] Use `async def` for I/O-bound endpoints (DB, HTTP, file) and `def` (sync) for CPU-bound work; run CPU-bound tasks in `run_in_threadpool` or `BackgroundTasks`.
4. [REQ] Structure the project with routers: `APIRouter(prefix="/api/v1", tags=[...])` and include via `app.include_router()` — never put all routes on the main `app` instance.
5. [REQ] Use the lifespan context manager (`@asynccontextmanager`) for startup/shutdown events; do not use deprecated `@app.on_event("startup")`.
6. [REQ] Use `BackgroundTasks` for lightweight fire-and-forget jobs; use Celery / ARQ / Dramatiq for durable, retryable, or distributed tasks.
7. [REQ] Configure CORS with an explicit origin allowlist (`allow_origins=[...]`), never `["*"]` in production.
8. [REQ] Use `HTTPException(status_code=..., detail=...)` for expected errors; register a global exception handler for unhandled exceptions that logs context and returns a sanitized 500.
9. [REQ] Enable OpenAPI docs only in non-production or behind auth: set `docs_url=None, redoc_url=None, openapi_url=None` in production.
10. [REQ] Use `Security()` with OAuth2PasswordBearer or API key dependencies; validate JWT with `python-jose` or `pyjwt` and check expiry in a dependency.
11. [REQ] Use `WebSocket` route for real-time bidirectional communication; implement heartbeat/ping and graceful disconnect handling.
12. [REQ] Run behind ASGI server (Uvicorn or Hypercorn) with `--workers N` for production; use `gunicorn -k uvicorn.workers.UvicornWorker` for process management.
13. [REQ] Use `TestClient` (httpx-based) for sync tests and `httpx.AsyncClient` with `ASGITransport` for async tests.
14. [PROHIBIT] Never call blocking I/O (requests, time.sleep, sync DB drivers) inside `async def` endpoints — use async libraries or `run_in_threadpool`.
15. [PROHIBIT] Never disable Pydantic validation or use `Any` as a field type in public API schemas.
[COMPAT]
- v0.115+: Pydantic v2 native, lifespan handlers, OpenAPI 3.1.
- v1.0: Stabilized API surface, Pydantic v2 only, Python 3.9+.
[REFS]
- https://fastapi.tiangolo.com/
- https://docs.pydantic.dev/latest/
- https://www.uvicorn.org/
