# E1: Does the number of Services slow down new connections?

Calico (iptables) + kube-proxy vs Cilium (eBPF, kube-proxy replacement), each on its own
3-node cluster (1 control plane + 2 workers).

```
manifests/e1-bench.yaml             test apps: 3 pause pods, fortio server, fortio client
requirements.txt                    rich, questionary, matplotlib, numpy, pyyaml
scripts/main.py                     interactive menu: start here
scripts/run-e1.py                   setup + measurement (preflight, deploy, services, measure, show, ...)
scripts/collect-and-draw-chart.py   CSV + raw histograms -> 3 story charts, summary, suggested verdict
scripts/e1lib.py                    shared config, kubectl wrapper, data-plane counting (imported)
results/                            output (CSV, PNG, raw fortio JSON, gzipped rule dumps)
```

## Requirements

On the machine you run from: `kubectl` with the contexts `it2003@calico` and `it2003@cilium`
(the OpenVPN must be up), and a venv for the scripts:

```bash
cd e1
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

No ssh needed. The rules are read by `kubectl exec` into the kube-proxy pod (Setup A) or the
cilium agent (Setup B) on the client node. If the kube-proxy image can't see the host's rules
(legacy vs nft backend mismatch), use `COUNT_VIA=ssh`. It runs `ssh <client InternalIP> sudo iptables-save -t nat`.

Every kubectl call passes `--context` explicitly: `iptables` → `it2003@calico`,
`cilium` → `it2003@cilium` (override with `--context` or `KUBE_CONTEXT`). Your current
context doesn't matter.

### Cluster settings that matter

**Setup A.** kube-proxy **must be in iptables mode**. Kubespray defaults to `ipvs`, which uses
hash tables too and would make the test meaningless. Set `kube_proxy_mode: iptables`.
Calico must use its iptables data plane (not eBPF). The preflight refuses to start if either is wrong.

**Setup B.** No kube-proxy; Cilium with `kubeProxyReplacement=true`. The preflight checks that
kube-proxy is gone and that KubeProxyReplacement is on.

Service CIDR: the preflight checks it has room for the largest N.

### Nodes

The client and server nodes are picked automatically from the clean workers (Ready,
schedulable, not control-plane, no NoSchedule taints), sorted by name: the 1st is the server
and the 2nd is the client, whose data plane is counted. To choose them yourself, set both
`--server-node` and `--client-node` (or `SERVER_NODE` / `CLIENT_NODE`). `deploy` injects a
hard `nodeSelector` into the fortio pods. The rendered manifest is saved to
`results/e1-bench-<setup>.rendered.yaml`.

## How to run

```bash
cd e1
.venv/bin/python scripts/main.py          # menu: cluster -> quick test / full run / demo / charts ...
```

The same steps without prompts:

```bash
S=".venv/bin/python scripts/run-e1.py"
$S run iptables --quick                   # quick test -> results/quick.csv (N = 10 100, 1 run)
$S run iptables                           # full run -> results/e1.csv
$S run cilium
$S show iptables                          # demo: one Service in iptables / in the LB map
$S services cilium 5000                   # just set N fake Services (then: wait cilium 5000)
$S cleanup cilium --namespace             # remove fake Services and the e1-bench namespace
.venv/bin/python scripts/collect-and-draw-chart.py results/e1.csv
```

Keep the quick tests in a separate CSV: the chart averages every row it finds, so leftover
quick-test rows would be mixed into the full results. Re-running a step just appends rows.
Before a full run, `main.py` offers to back up the CSV and drop the old rows of that setup.

A full run is 6 sizes x 3 runs x ~45 s of load, plus Service creation and sync:
roughly 20-40 minutes per setup.

### Knobs (flags, or env vars with the same name in capitals)

| flag / env | default | meaning |
|---|---|---|
| `--context` / `KUBE_CONTEXT` | `it2003@calico` / `it2003@cilium` | cluster for the setup |
| `--sizes` / `SIZES` | `100 2080 4060 6040 8020 10000` | number of fake Services per step |
| `--runs` / `RUNS` | `3` | repeats per step |
| `--csv` / `CSV` | `results/e1.csv` | output file (raw files go to `<csv dir>/raw/`) |
| `--qps` `--conc` `--duration` | `200` / `4` / `30s` | fortio load, one new TCP connection per request |
| `--warmup` / `WARMUP` | `5s` | unrecorded warm-up before each run |
| `RESOLUTION` | `0.00001` | fortio histogram bucket (10 µs). fortio's default is 1 ms, too coarse |
| `--settle` / `--cooldown` | `20` / `10` s | wait after data plane sync / between runs |
| `--server-node` / `--client-node` | auto | where server and client run |
| `--count-via` / `COUNT_VIA` | `pod` | `pod` or `ssh` for reading iptables |
| `PLACEMENT_TIMEOUT` | `120` | s to wait for the fortio pods on their nodes |
| `--cleanup` / `CLEANUP=1` | off | delete fake Services at the end |
| `--force` / `FORCE=1` | off | continue despite preflight errors |

## What each step does

1. `services N` makes exactly N Services `e1-svc-00001..N`, all selecting the 3 pause
   pods. Every Service has 3 real endpoints, so kube-proxy writes the full chain set
   (KUBE-SERVICES entry → KUBE-SVC → 3 × KUBE-SEP), about 11 nat rules each.
2. `wait N` waits until all N EndpointSlices have 3 endpoints, then until the rule count on
   the client node stops changing (two identical reads 5 s apart), then `SETTLE` seconds.
3. `measure N RUN` reads the data plane on the client node, runs a warm-up, then the measured
   fortio run against the fortio-server **ClusterIP** (not the DNS name, to avoid an extra Service
   hop for DNS), with `-keepalive=false`, and appends one row.

## CSV columns

| column | iptables (Setup A) | cilium (Setup B) |
|---|---|---|
| `rules` | all `-A` rules in `iptables-save -t nat` | rows in `cilium-dbg bpf lb list` (frontend + backends) |
| `svc_entries` | rules in the KUBE-SERVICES chain | distinct frontends in the LB map |
| `target_pos` | position of fortio-server's rule inside KUBE-SERVICES | `NA` |
| `p50_ms` ... `p999_ms`, `avg_ms`, `max_ms` | per-request latency incl. TCP handshake | same |
| `actual_qps`, `requests`, `errors` | from fortio | same |

## Charts

`collect-and-draw-chart.py <csv>` tells the result as a short story. Each chart's title states its takeaway:

1. `<stem>-1-hero.png`: p50 latency vs number of Services, with the change at the largest N
   labelled on each line and the slope (µs per 1,000 Services) along the rising one.
   `<stem>-slide-p50.png` / `<stem>-slide-p99.png` are minimal versions for the slides: takeaway title,
   the two lines and their end values only.
2. `<stem>-2-why.png`: data-plane size vs number of Services (nat rules vs LB map entries,
   with entries per Service).
3. `<stem>-3-cdf.png`: the whole latency distribution (from the raw fortio histograms) at the
   smallest vs largest N, one panel per setup.

`<stem>.png` combines all three for the report. The script also writes `<stem>_summary.csv` (mean/SD
per step) and prints the change in p50 from the smallest to the largest N against run-to-run
noise, a linear fit (µs per 10k rules), and a *suggested* Yes/Partly/No. Treat that as a hint
and look at the charts yourself.

## Things to know when reading the numbers

- **Where the iptables cost actually happens.** On node-2 the SYN walks KUBE-SERVICES until it hits
  fortio-server's rule, so the cost depends on its position (`target_pos`), which kube-proxy doesn't
  keep fixed between syncs. On node-1 the already-DNATed packet is a new conntrack entry too and
  walks the whole KUBE-SERVICES list without matching. So the measured cost is roughly
  "part of the list on node-2 + all of it on node-1". Worth one sentence in the report.
- **Cilium socket-LB.** With kube-proxy replacement, Cilium translates the ClusterIP at `connect()`
  time in the client's socket (socket-LB), before any packet exists. That is the realistic default
  and is what this test measures. If someone asks "what about per-packet eBPF?", rerunning with
  `socketLB.enabled=false` measures the tc datapath instead.
- **Small N.** Below ~1000 Services the difference may be within noise. That is a valid result;
  write it down. If you want a clearer signal you can add `SIZES="... 10000"` (check the CIDR).
- **Errors / TIME_WAIT.** Each request uses a new ephemeral port. At 200 QPS x 35 s that is ~7000
  ports, well under the ~28k range. If you raise QPS and see errors, lower it or lengthen `COOLDOWN`.
- **Quiet cluster.** The preflight lists any non-system pods that are running. Stop them.
- **Same fortio.** The manifest pins `fortio/fortio:1.75.3`; keep the same tag for both setups.

## Demo screenshots

`run-e1.py show <setup> [service]` (or "Show one Service" in `main.py`) prints one Service (default `e1-svc-00001`, 3 backends) the way each data plane
stores it:

- iptables: its KUBE-SERVICES line → KUBE-SVC chain (random-probability load balancing) → 3 KUBE-SEP
  chains (DNAT), the rule count for that one Service, and the size of the whole list that every new
  connection scans.
- Cilium: the `cilium-dbg service list` row and the `bpf lb list` rows (1 frontend + 3 backends),
  plus the map size, looked up by hash key.

Run it at a large N (e.g. `services <setup> 10000` first) for the strongest contrast.

## Conclusion template

> **Hypothesis supported? Yes / Partly / No.**
> Setup A: nat rules grew from __ to __ (≈ __ per Service); p50 went from __ ms to __ ms
> (+__ µs, ≈ __ µs per 10k rules), p99 from __ to __ ms.
> Setup B: LB map entries grew from __ to __ (≈ __ per Service) but p50 stayed at __ ± __ ms.
> Below __ Services the difference was within noise (± __ µs).
> Reason: iptables matches KUBE-SERVICES rule by rule for the first packet of each connection,
> so cost grows with the number of Services; Cilium looks the Service up in an eBPF hash map
> (at connect() with socket-LB), so cost does not depend on map size.
