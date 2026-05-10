# Tech-Stack: Laravel Reverb

> [!NOTE]
> **TRIGGER:** LOAD ON real-time features, WebSockets, event broadcasting.
> **SCOPE:** Laravel Reverb WebSockets (Laravel 12/13).

## 1. Channels & Broadcasting
- Use **Public** channels for global broadcasts (e.g., system announcements).
- Use **Private** channels for user/tenant specific events (e.g., `user.{id}.notifications`).
- Use **Presence** channels for features requiring user awareness (e.g., active viewers, chat rooms).

## 2. Authentication & Security
- Secure private and presence channels using route authorization callbacks.
- Ensure Reverb connection limits and heartbeat configurations are set to prevent abuse.
- Broadcast data using strict typed DTOs to avoid leaking sensitive model properties.

## 3. Scaling & Architecture
- Scale Reverb horizontally by integrating with Redis pub/sub.
- Use Laravel 12/13 broadcasting patterns natively.
- Utilize the Context API for connection and event tracing.

## 4. Hard Constraints
- NEVER broadcast raw Eloquent models without filtering; always use API resources or DTOs.
- NEVER expose sensitive data on public channels.
- ALWAYS verify channel authorization logic rigorously.

---

## ✅ LARAVEL REVERB COMPLIANCE CHECK (Mandatory)
- [ ] **Security:** Are private channels properly authorized and data sanitized?
- [ ] **Scaling:** Is Redis configured for horizontal scaling of WebSocket connections?
- [ ] **Traceability:** Is the Context API implemented for WebSocket event tracking?
