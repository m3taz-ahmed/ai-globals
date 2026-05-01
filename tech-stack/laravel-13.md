# Laravel 13.x Strict Standards
- **Native Types:** Rely entirely on PHP 8.5 native types; strip redundant validation rules if handled by DTOs/Value Objects.
- **Context API:** Utilize the native `Context` API deeply for logging and tracing across background jobs and requests.
- **Lean Core:** Exploit the minimal skeleton. Keep all infrastructure bindings in `bootstrap/app.php` and service providers strictly compartmentalized.
- **AI/LLM Routing:** If integrating AI, use standard Laravel pipeline routing for prompt engineering and vector DB interactions.