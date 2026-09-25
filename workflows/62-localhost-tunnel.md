[WORKFLOW] 62-localhost-tunnel
[OBJ] Expose a local dev server to the internet for webhooks, agent loops, screenshots, and human review — via Cloudflare Quick Tunnels (ephemeral, no account, no open ports).
[TRIGGER] localhost tunnel, expose localhost, public url, webhook test, cloudflared, quick tunnel, share local server, افتح localhost, لينك عام, تجربة webhook
[RULES]

## 1. When to use

External services can't reach `localhost`: Stripe/GitHub webhook callbacks, OAuth redirects, screenshot services, eval harness loops, or a human who wants to click around a work-in-progress build. Quick Tunnels give a real `https://<rand>.trycloudflare.com` URL that dies with the process — ephemeral by design, zero cleanup.

## 2. The command

```bash
cloudflared tunnel --url http://localhost:<port>
```

- Prints the URL on stdout; `--loglevel info`/JSON mode emits `{hostname, edge, health}` lines — parse stdout, never regex-scrape human logs.
- Outbound-only connection to Cloudflare edge; **no inbound ports opened**, TLS + DDoS filtering included.
- Any framework, any port, any stack. No account, no DNS, no config file.
- Install: `winget install cloudflare.cloudflared` / `brew install cloudflared` / GitHub releases. No login for quick tunnels.

## 3. The loop (agents)

1. Start the app locally; verify `localhost:<port>` responds.
2. `cloudflared tunnel --url http://localhost:<port>` in a background process; capture stdout for the URL.
3. Hand the URL to the webhook provider / screenshot service / reviewer.
4. Kill the process when done — the tunnel dies with it. No leftover public exposure.

## 4. Security gates (SEC persona — non-negotiable)

1. [PROHIBIT] Never tunnel a port serving unauthenticated admin/debug panels, `.env` endpoints, or databases. The URL is public on Cloudflare's edge.
2. [REQ] If the app has auth (e.g. aiZee dashboard's `AIZEE_DASHBOARD_TOKEN`), confirm it's enforced BEFORE tunneling.
3. [REQ] Treat the tunnel URL as a bearer secret for the task duration — share it only with the intended consumer; it grants full access to whatever the port serves.
4. [PROHIBIT] No long-lived tunnels from dev machines for production traffic — that's a different product (named tunnels + Access policies), not a quick tunnel.
5. [REQ] Kernel gate: expose actions go through `aizee check` — record the exposed port + URL + TTL in the audit trail.
6. [REQ] Verify the tunnel forwards to the intended port before handing the URL out (`curl <url>/health` or equivalent).

## 5. aiZee uses

- Webhook development for integrations (payment, git providers, ESP callbacks).
- `dashboard/server.py` remote preview for a human reviewer — with token auth enforced.
- Agent eval loops: give a subagent/browser skill a real reachable address.
- Task-contract evidence: a live URL is stronger `aizee task verify --evidence` than "it works locally".

## 6. Alternatives (same pattern, pick per constraints)

`ngrok http <port>` (account + reserved domains), `localtunnel`, `zrok` (self-hostable), Tailscale Funnel (tailnet-first). Prefer Quick Tunnels when zero-setup ephemeral exposure is the need.
