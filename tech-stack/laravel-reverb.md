[TECH] laravel-reverb
[OBJ] Laravel Reverb WebSockets.
[RULES]
1. [REQ] Channels: Public (global), Private (tenant/user), Presence (active viewers).
2. [REQ] Security: Secure Private/Presence via route auth callbacks. Set heartbeat/connection limits. Broadcast strict DTOs.
3. [REQ] Scaling: Redis pub/sub horizontal scaling.
4. [PROHIBIT] Constraints: NEVER broadcast raw Eloquent models (filter via Resource/DTO). NEVER expose PII on public channels.
