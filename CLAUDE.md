# CLAUDE.md

IT2003 course project (Group 12): compare Kubernetes datapaths, **iptables (Calico + kube-proxy)** vs
**eBPF (Cilium, kube-proxy replacement)**, on two equivalent 3-node clusters in a Proxmox homelab.
Three experiments: E1 Service load balancing at scale, E2 NetworkPolicy segmentation, E3 runtime security
with Tetragon (eBPF-only, no iptables equivalent). Overview, topology and quick start: `README.md`.

## Layout

- `infrastructure/`: Terraform (bpg/proxmox) for VMs/SDN, Ansible + Kubespray inventories (`inventory/calico/`, ...).
- `kubernetes/network/`: Cilium Helm values (`cilium/production.yaml`) and L2 LB config.
- `e1/`: Service-latency experiment (scripts, manifests, results). Read `e1/README.md` before running.
- `e2/`: NetworkPolicy experiment. `cilium/`: 15 `CiliumNetworkPolicy` for Online Boutique
  (`microservices-google-demo`; default deny + DNS + one file per service), `README.md`, `TEST-SCENARIOS.md`.
  `case_*.yaml`: DVWA reverse-shell / lateral-movement cases; `manifests/dvwa.yaml`: the DVWA app.
- `e3/Tetragon/`: `TracingPolicyNamespaced` that watches ServiceAccount-token reads after a DVWA exploit
  (`dvwa-token-monitor.yaml`), `examples/` (scoped monitor, `Override` enforce sample), `expoilt.php` PoC.
- `docs-latex/`: **git submodule**, the Vietnamese LaTeX report (`main.tex` preamble, `contents.tex` body,
  `ref.bib`). Teammates edit it on Overleaf ("Update on Overleaf." commits): pull before editing, commit
  inside the submodule, then bump the pointer here. LaTeX build outputs are gitignored there.
- `presentation/`: Slidev deck (`slides.md`, Vue diagrams in `components/`, screenshots in `public/`, styles in `styles/index.css`).

## Experiments

- Calico cluster's kube-proxy must be in `iptables` mode (Kubespray defaults to `ipvs`, which would invalidate E1).
- Both clusters use **direct routing** (no overlay); keep it that way so results reflect Service/policy handling.
- kubectl contexts: Cilium API `:2443`, Calico API `:2444` (Proxmox DNAT). Experiment demos need the OpenVPN.
- E1 plots average every CSV row: keep quick tests in a separate CSV.
- E2 and E3 run on the Cilium cluster. E2 evidence: `kubectl get cnp` (`Valid=True`), Hubble
  `--verdict DROPPED` and `cilium-dbg monitor --type drop` showing `Policy denied`. Still missing: endpoint/
  identity/policy-map snapshots before/after scaling a Pod, and the Calico-side equivalent.
- E3 Tetragon policies are monitor-only; the `Override` enforce sample needs kernel support, test before applying.
- In the report and slides, keep expected or illustrative results clearly separate from observed ones;
  never present a planned test as a result.
- DVWA is deliberately vulnerable: lab LB IP behind VPN only.

## Presentation (`presentation/`)

- Run: `npm run dev`; build check: `npm run build`; visual check: `npx slidev export --format png --range <n> --output <dir>` and view the PNGs.
- Node here is 20.x, so Slidev is pinned to **52.20.1** and `vue` to 3.5.44. `.npmrc` (`legacy-peer-deps=true`) and the `markdown-it` ^14 override are required for `npm install`. Don't bump these unless Node ≥ 22.12.
- Content conventions: slide text in Vietnamese, **diagram labels in English**; **keep IT/technical terms in English even in Vietnamese prose** (process, kernel, packet, connection, policy, rule, chain, table, flow, firewall, observability, load balancing, identity, encapsulation, counter…) — do not translate them; diagram-first with minimal text (details stay in the report and speaker notes); diagrams centered and large.
- All diagrams are custom Vue SFCs in `components/` (house style: rounded `#374151` boxes, palette blue `#e8eefc` / orange `#ffe9cc` iptables / green `#dcf5dc` eBPF / red `#ffd0d0`, triangle-marker arrows, monospace titles, print-safe animation only). No Mermaid — build new diagrams as components, with a matching built-in legend when colors carry meaning.
- Structure (≤ 20 slides, no section dividers; Agenda is the map): 1. Foundation (1.1–1.5: K8s model & direct routing → iptables → Calico packet path → eBPF & BPF map → Cilium packet path), then 2. Experiments (topology, then per experiment knowledge → evidence):
  2.1.x E1 mechanism → results → full distribution (no live demo); 2.2.x E2 IP vs identity → segmentation → Hubble verification → drop monitor; 2.3.x E3 Tetragon hooks → ServiceAccount-token attack flow → process log.
- Evidence slides use screenshots from `public/`; captions say what the screenshot does and does not prove.
- Scope: direct routing only (no overlay slides), no research-questions slide; framing is Calico/iptables vs Cilium/eBPF.
- A slide's `transition` applies when leaving it forward. For highlighted text prefer the `.hl` class over `v-mark`.
