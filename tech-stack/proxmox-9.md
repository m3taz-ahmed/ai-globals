[TECH] Proxmox VE 9
[OBJ] Bare-metal virtualization platform — KVM VMs + LXC containers + ZFS/Ceph storage + clustering; the standard self-hosting foundation.
[RULES]
1. [REQ] VM vs LXC: LXC for Linux services (near-native perf, tiny overhead, shared kernel); VM only when you need different kernel/OS, strong isolation, or Windows. Default to LXC for homelab/prod services.
2. [REQ] Install base: Debian 13 base (PVE 9 line); ZFS mirror for the host OS when possible; enable IOMMU + correct repos (`no-subscription` repo for non-enterprise, or enterprise key); update via web UI/`apt`.
3. [REQ] Networking: `vmbr0` bridge default; VLAN-aware bridge for segmented nets; NAT bridge (vmbr1) + masquerade for private CT ranges; SDN module for overlay networks (v9 mature).
4. [REQ] Storage: ZFS for everything unless shared storage needed → Ceph only ≥3 nodes; thin-provisioning caution on shared pools; `zfs snapshot` before risky changes; monitor `zpool status`/`arc_summary`.
5. [REQ] Permissions/isolation: unprivileged LXC default (`unprivileged: 1`); Docker inside LXC needs `nesting=1` + `keyctl=1` (features flag) — prefer VM for production Docker fleets; PCI passthrough for GPU/SATA controllers with `vfio` modules.
6. [REQ] Backups: Proxmox Backup Server (PBS) for dedup+verify+prune backups; `vzdump` schedules per-VM/CT; TEST restores (PBS verify jobs + periodic boot-test on an isolated network).
7. [REQ] HA/cluster: quorum needs ≥3 nodes or a QDevice; HA groups only when you actually need auto-failover — a standalone node with solid backups beats a badly-tuned cluster.
8. [REQ] Firewall: enable Datacenter→Node→Guest firewall layers deliberately; `Security Groups` for reusable rules; API tokens per service for automation (terraform `bpg/proxmox` provider).
9. [REQ] Templates: build cloud-init VM templates (qemu-guest-agent, ssh keys via ci) and LXC templates per distro — never clone-and-fix snowflakes.
10. [REQ] Monitoring: node metrics via `pve` dashboard + node_exporter; watch SMART (`smartctl`), ZFS ARC hit rate, RAM ballooning; alert on `pvesm` storage usage >80%.
11. [PROHIBIT] Never run production services inside the PVE host itself — guests only.
12. [PROHIBIT] Never skip `qemu-guest-agent`/`lxc` agent setup — backups and shutdowns depend on it.
13. [PROHIBIT] Never expose :8006 web UI publicly — VPN/Tailscale or allowlist.
14. [CMD] Community scripts (community-scripts/ProxmoxVE) for one-command app LXCs — read the script before piping to bash.
[COMPAT]
- Current: PVE 9.x (Debian 13 base, released 2025); PBS 4.x pairs with it.
- Docs: https://pve.proxmox.com/pve-docs/ — Context7 `/proxmox/pve-docs` when indexed.
[REFS]
- https://pve.proxmox.com/wiki/Main_Page
- https://community-scripts.github.io/ProxmoxVE/ (huge curated LXC/VM library)
