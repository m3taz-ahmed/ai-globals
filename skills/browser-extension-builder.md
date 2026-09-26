---
name: browser-extension-builder
description: Expert in engineering secure, cross-browser Web Extensions (Chrome, Firefox, Edge).
---
[SKILL] browser-extension-builder
[OBJ] Build fast, secure browser extensions.
[RULES]
1. [REQ] Extension Architecture: Implement strict Manifest V3 structure connecting background, content scripts, and popups.
2. [REQ] Security: Strictly adhere to Least Privilege for permissions to protect user privacy.
3. [REQ] Cross-Browser Compatibility: Ensure flawless execution across Chrome, Firefox, and Edge.
4. [REQ] Performance: Prevent memory leaks and background resource bloat to maintain browser speed.
5. [REQ] MV3 reality: service worker is ephemeral — no persistent state in globals (chrome.storage is the state layer), no setInterval keep-alives (chrome.alarms API), top-level listeners registered synchronously. MV2 patterns ported blindly = broken extension.
6. [REQ] Permissions discipline: `permissions` only what core function needs; `optional_permissions` + `chrome.permissions.request()` for feature-gated needs; `host_permissions` scoped to required origins, `<all_urls>` is a store-review red flag. Every permission is a scary install-time warning — count them.
7. [REQ] Messaging contract: `runtime.sendMessage`/`onMessage` between popup↔background↔content; always `return true` for async responses; message payloads versioned internally; content-script↔page-world bridge via `window.postMessage` only when unavoidable (isolated worlds are the protection).
8. [REQ] Content script care: inject at `document_idle` default, scoped matches not `*://*/*`, CSS isolation awareness (page styles leak in — use shadow DOM or explicit resets), cleanup listeners on unload, survive SPA navigation (history-change hooks not just initial load).
9. [REQ] Storage layers: `chrome.storage.local` (fast, per-device), `chrome.storage.sync` (user-synced, tiny quota — settings only), IndexedDB for large structured data. Encrypt sensitive data; never store tokens in sync storage unencrypted.
10. [REQ] CSP & host hygiene: MV3 CSP forbids eval/remote code — bundle everything; no remote JS execution (store policy + security); `webRequest` moved to `declarativeNetRequest` — rules as data, not blocking intercepts.
11. [REQ] Cross-browser delta: `browser.*` promise API (Firefox) vs `chrome.*` callback API — polyfill (`webextension-polyfill`) or wrapper; Firefox MV3 has different CSP/event-page specifics; test on BOTH engines not just Chromium.
12. [REQ] Performance budget: service worker wakes are cold-starts — keep init minimal; popup render <100ms; content scripts lean (they run on every matched page — a slow script taxes every user's browsing).
13. [REQ] Store review readiness: single-purpose description, screenshots/justifications for sensitive permissions, minified-but-not-obfuscated code (obfuscation = rejection), privacy policy URL, staged rollout.
14. [PROHIBIT] Persistent background-page assumptions, `<all_urls>` without justification, eval/remote-hosted code, storing secrets in accessible storage, or shipping without testing extension updates (storage migrations between versions).
