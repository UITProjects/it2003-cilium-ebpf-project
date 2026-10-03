# E1: Does the number of Services slow down new connections?

Calico (iptables) + kube-proxy vs Cilium (eBPF, kube-proxy replacement), same 3 nodes
`it-2003-ubuntu2404-0/1/2`, cluster reinstalled between setups.

```
manifests/e1-bench.yaml      test apps: 3 pause pods, fortio server (node-1), fortio client (node-2)
scripts/lib.sh               shared helpers (sourced, not run)
scripts/create-services.sh   create/delete fake Services so exactly N exist
scripts/measure.sh           count rules + one fortio run -> one CSV row
scripts/run-e1.sh            all sizes x runs for one setup
scripts/plot_e1.py           3 charts + summary table + suggested verdict
scripts/show-service.sh      demo screenshots: one Service in iptables vs in Cilium
results/                     output (CSV, PNG, raw fortio JSON, gzipped rule dumps)
```

## Requirements

On the machine you run from: `kubectl` pointing at the cluster, `bash`, `python3`, and
`matplotlib` for the plot (`pip install matplotlib`). No ssh needed: rules are read by
`kubectl exec` into the kube-proxy pod (Setup A) or the cilium agent (Setup B) on node-2.
If the kube-proxy image can't see the host's rules (legacy vs nft backend mismatch), use
`COUNT_VIA=ssh` (runs `ssh it-2003-ubuntu2404-2 sudo iptables-save -t nat`).

### Cluster settings that matter

**Setup A.** kube-proxy **must be in iptables mode**. Kubespray defaults to `ipvs`, which uses
hash tables too and would make the test meaningless. Set `kube_proxy_mode: iptables`.
Calico should use its iptables data plane (not eBPF). `run-e1.sh` refuses to start if the mode is wrong.

**Setup B.** No kube-proxy; Cilium with `kubeProxyReplacement=true` (Kubespray: something like
`kube_network_plugin: cilium`, `cilium_kube_proxy_replacement: true`, `kube_proxy_remove: true`;
Helm: `--set kubeProxyReplacement=true --set k8sServiceHost=<api-ip> --set k8sServicePort=6443`).
`run-e1.sh` checks that kube-proxy is gone and prints the KubeProxyReplacement status.

Service CIDR: the preflight checks it has room for the largest N (Kubespray's default /18 = 16k IPs is fine).

## How to run

```bash
chmod +x scripts/*.sh scripts/*.py

# Setup A
CSV=results/quick.csv SIZES="10 100" RUNS=1 ./scripts/run-e1.sh iptables   # quick test, separate CSV
./scripts/run-e1.sh iptables                                              # full run -> results/e1.csv
./scripts/show-service.sh iptables > results/demo-iptables.txt            # screenshot material

# reinstall cluster with Cilium, copy results/ along if you change machines

# Setup B
CSV=results/quick.csv SIZES="10 100" RUNS=1 ./scripts/run-e1.sh cilium
./scripts/run-e1.sh cilium
./scripts/show-service.sh cilium > results/demo-cilium.txt

python3 scripts/plot_e1.py results/e1.csv results/e1.png
```

Keep the quick tests in a separate CSV: the plot averages every row it finds, so leftover
quick-test rows would be mixed into the full results. Re-running a step just appends rows;
delete them from the CSV if you want a clean redo.

A full run is roughly 6 sizes x 3 runs x ~50 s of load, plus Service creation and sync:
about 30-40 minutes per setup.

### Knobs (env vars)

| var | default | meaning |
|---|---|---|
| `SIZES` | `10 100 500 1000 2000 5000` | number of fake Services per step |
| `RUNS` | `3` | repeats per step |
| `CSV` | `results/e1.csv` | output file (raw files go to `<csv dir>/raw/`) |
| `QPS` / `CONC` / `DURATION` | `200` / `4` / `30s` | fortio load, one new TCP connection per request |
| `WARMUP` | `5s` | unrecorded warm-up before each run |
| `RESOLUTION` | `0.00001` | fortio histogram bucket (10 µs). fortio's default is 1 ms, too coarse |
| `SETTLE` / `COOLDOWN` | `20` / `10` s | wait after data plane sync / between runs |
| `SERVER_NODE` / `CLIENT_NODE` | `...-1` / `...-2` | where server and client run |
| `COUNT_VIA` | `pod` | `pod` or `ssh` for reading iptables |
| `CLEANUP` | `0` | `1` = delete fake Services at the end |
| `FORCE` | `0` | `1` = continue despite preflight errors |

## What each step does

1. `create-services.sh N` makes exactly N Services `e1-svc-00001..N`, all selecting the 3 pause
   pods. Every Service has 3 real endpoints, so kube-proxy writes the full chain set
   (KUBE-SERVICES entry → KUBE-SVC → 3 × KUBE-SEP), about 11 nat rules each.
2. The script waits until all N EndpointSlices have 3 endpoints, then until the rule count on
   node-2 stops changing (two identical reads 5 s apart), then `SETTLE` seconds.
3. `measure.sh` reads the data plane on node-2, runs a warm-up, then the measured fortio run
   against the fortio-server **ClusterIP** (not the DNS name, to avoid an extra Service hop for DNS),
   with `-keepalive=false`, and appends one row.

## CSV columns

| column | iptables (Setup A) | cilium (Setup B) |
|---|---|---|
| `rules` | all `-A` rules in `iptables-save -t nat` | rows in `cilium-dbg bpf lb list` (frontend + backends) |
| `svc_entries` | rules in the KUBE-SERVICES chain | distinct frontends in the LB map |
| `target_pos` | position of fortio-server's rule inside KUBE-SERVICES | `NA` |
| `p50_ms` ... `p999_ms`, `avg_ms`, `max_ms` | per-request latency incl. TCP handshake | same |
| `actual_qps`, `requests`, `errors` | from fortio | same |

`plot_e1.py` also writes `results/e1_summary.csv` (mean/std per step) and prints the change in
p50 from the smallest to the largest N against run-to-run noise, a linear fit (µs per 10k rules),
and a *suggested* Yes/Partly/No. Treat that as a hint and look at the charts yourself.

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
- **Pin fortio.** The manifest uses `fortio/fortio:latest`; pin one tag before the final runs so both
  setups use the same client.

## Demo screenshots

`show-service.sh` prints one Service (default `e1-svc-00001`, 3 backends) the way each data plane
stores it:

- iptables: its KUBE-SERVICES line → KUBE-SVC chain (random-probability load balancing) → 3 KUBE-SEP
  chains (DNAT), the rule count for that one Service, and the size of the whole list that every new
  connection scans.
- Cilium: the `cilium-dbg service list` row and the `bpf lb list` rows (1 frontend + 3 backends),
  plus the map size, looked up by hash key.

Run it at N=5000 for the strongest contrast.

## Conclusion template

> **Hypothesis supported? Yes / Partly / No.**
> Setup A: nat rules grew from __ to __ (≈ __ per Service); p50 went from __ ms to __ ms
> (+__ µs, ≈ __ µs per 10k rules), p99 from __ to __ ms.
> Setup B: LB map entries grew from __ to __ (≈ __ per Service) but p50 stayed at __ ± __ ms.
> Below __ Services the difference was within noise (± __ µs).
> Reason: iptables matches KUBE-SERVICES rule by rule for the first packet of each connection,
> so cost grows with the number of Services; Cilium looks the Service up in an eBPF hash map
> (at connect() with socket-LB), so cost does not depend on map size.
