[TECH] OpenSSH 10.x
[OBJ] SSH client/server — the admin plane of every server; hardening + key management + config discipline.
[RULES]
1. [REQ] Keys: `ssh-keygen -t ed25519 -C "purpose-host-date"`; per-purpose keypairs (per service/CI); passphrase on private keys; `ssh-agent`/`AddKeysToAgent yes`; NEVER reuse one key everywhere.
2. [REQ] Server hardening (`/etc/ssh/sshd_config` or `/etc/ssh/sshd_config.d/*.conf`): `PasswordAuthentication no`, `KbdInteractiveAuthentication no`, `PermitRootLogin no`, `PubkeyAuthentication yes`, `MaxAuthTries 3`, `AllowUsers`/`AllowGroups` allowlist, `X11Forwarding no` on servers, `ClientAliveInterval 300` + `ClientAliveCountMax 2`.
3. [REQ] Validate before reload: `sshd -t` then `systemctl reload ssh` — a broken sshd config can lock you out; keep a second session open until verified.
4. [REQ] Client config (`~/.ssh/config`): `Host alias → HostName/User/Port/IdentityFile`; `IdentitiesOnly yes` with explicit keys; `ServerAliveInterval 60` for NATs; ProxyJump for bastions (`ssh -J`/`ProxyJump bastion`).
5. [REQ] Reduce exposure: fail2ban `sshd` jail, firewall limit-source where possible, or close public :22 entirely behind Tailscale SSH (`tailscale up --ssh`) / WireGuard. Port-moving is cosmetic; keys+allowlists are the control.
6. [REQ] Bastion/fleet pattern: one hardened entry point, `ProxyJump`, per-host keys, `ssh -A` (agent fwd) avoided — prefer ProxyJump over agent forwarding.
7. [REQ] `scp`/`rsync -e ssh`/`sftp` for transfers; `sshfs` for mounts; `ssh -L/-R/-D` tunnels for ad-hoc port access (never permanently exposed services).
8. [REQ] Auditing: `auth.log`/`journalctl -u ssh` for attempts; `ssh -vvv` debug on client side first; `sshd -T` dumps effective config (after drop-ins).
9. [REQ] Certificates: `ssh-keygen -s ca_key` host/user certs for fleets — scalable alternative to distributing authorized_keys.
10. [PROHIBIT] Never `PasswordAuthentication yes` on internet-facing hosts.
11. [PROHIBIT] Never share/copy private keys between hosts or into images/CI logs.
12. [PROHIBIT] Never run sshd config changes untested — always `sshd -t` + keep existing session.
13. [CMD] Windows: `OpenSSH.Server` optional feature + `ssh.exe` built-in; `sshd_config` at `%ProgramData%\ssh\`; PowerShell Remoting over SSH for cross-platform mgmt.
[COMPAT]
- Current line: OpenSSH 10.x (10.0 Apr 2025+). Ed25519/DSA removal-era: RSA-SHA1 long deprecated — use ed25519/rsa-sha2.
- Config drop-ins `sshd_config.d/*.conf` override the main file — check both.
- Docs: https://man.openbsd.org/sshd_config — Context7 `/openssh/openssh-portable` when indexed.
[REFS]
- https://www.ssh.com/academy/ssh (concept reference)
- https://infosec.mozilla.org/guidelines/openssh (MozSSC hardening baseline)
