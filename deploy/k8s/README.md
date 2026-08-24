# aiZee Dashboard — Kubernetes Deployment

## Threat Model

The aiZee dashboard is a **governance control plane** — it exposes policy
evaluation, workflow execution, audit logs, and chat endpoints. An
unauthenticated network-exposed dashboard is a critical security hole.

**SEC-W1 invariant:** the dashboard refuses to bind a non-loopback host
without a token. In K8s, `AGENT_OS_HOST=0.0.0.0` is required so pod probes
reach the container, but this means a token is **mandatory**.

## Token Management

### Generate a token

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Create the secret

```bash
kubectl create secret generic aizee-dashboard-token \
  --from-literal=token=<your-token> -n aizee
```

### Rotation

1. Generate a new token.
2. Update the secret: `kubectl edit secret aizee-dashboard-token -n aizee`
   (or use `kubectl create secret --dry-run=client -o yaml | kubectl apply -f -`).
3. Restart the pod: `kubectl rollout restart deployment/aizee-dashboard -n aizee`.
4. Update any clients (dashboard UI, MCP) with the new token.

For GitOps, use **sealed-secrets** or **external-secrets** — never commit
the plaintext token to git.

## TLS

TLS is terminated at the **Ingress** layer, not in the container. The
dashboard serves plaintext HTTP on port 8080 inside the pod. Configure
your Ingress with TLS certificates (cert-manager recommended).

## Network Policy

The NetworkPolicy in `deployment.yaml` restricts:
- **Ingress**: only pods with label `app.kubernetes.io/name: aizee` in the
  same namespace can reach port 8080.
- **Egress**: DNS (UDP 53 to kube-system) + HTTPS (TCP 443 to anywhere).

Adjust egress if your deployment needs additional outbound access (e.g.,
to an LLM provider API).

## Probes

Readiness and liveness probes target `/api/system` (a public path that
does not require authentication), so they pass even when token auth is
enabled.
