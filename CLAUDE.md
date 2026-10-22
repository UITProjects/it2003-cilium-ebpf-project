# CLAUDE.md

IT2003 course project (Group 12): compare Kubernetes datapaths, **iptables (Calico + kube-proxy)** vs
**eBPF (Cilium, kube-proxy replacement)**, on two equivalent 3-node clusters in a Proxmox homelab.
Overview, topology and quick start: `README.md`.

## Layout

- `infrastructure/`: Terraform (bpg/proxmox) for VMs/SDN, Ansible + Kubespray inventories (`inventory/calico/`, ...).
- `kubernetes/network/`: Cilium Helm values (`cilium/production.yaml`) and L2 LB config.
- `e1/`: Service-latency experiment (scripts, manifests, results). Read `e1/README.md` before running.
- `e2/`: NetworkPolicy experiment (DVWA target, in progress). E3 (drop diagnosis, Hubble) is planned.
- `docs-latex/`: **git submodule**, the Vietnamese LaTeX report (`contents.tex`). Commit inside the submodule, then bump the pointer here.
- `presentation/`: Slidev deck (`slides.md`, SVG/Vue diagrams in `components/`, styles in `styles/index.css`).

## Experiments

- Calico cluster's kube-proxy must be in `iptables` mode (Kubespray defaults to `ipvs`, which would invalidate E1).
- Both clusters use **direct routing** (no overlay); keep it that way so results reflect Service/policy handling.
- kubectl contexts: Cilium API `:2443`, Calico API `:2444` (Proxmox DNAT). Experiment demos need the OpenVPN.
- E1 plots average every CSV row: keep quick tests in a separate CSV.
- DVWA is deliberately vulnerable: lab LB IP behind VPN only.

## Presentation (`presentation/`)

- Run: `npm run dev`; build check: `npm run build`; visual check: `npx slidev export --format png --range <n> --output <dir>` and view the PNGs.
- Node here is 20.x, so Slidev is pinned to **52.20.1** and `vue` to 3.5.44. `.npmrc` (`legacy-peer-deps=true`) and the `markdown-it` ^14 override are required for `npm install`. Don't bump these unless Node ≥ 22.12.
- Content conventions: slide text in Vietnamese, **diagram labels in English**; diagram-first with minimal text (details stay in the report); diagrams centered and large; demo slides are only a "LIVE DEMO" title plus command cues.
- Scope: direct routing only (no overlay slides), no research-questions slide; framing is Calico/iptables vs Cilium/eBPF.
- A slide's `transition` applies when leaving it forward. Avoid `v-mark` on text below a Mermaid diagram (it is positioned before the async render); use the `.hl` class instead.
