#!/usr/bin/env python3
"""run-e1.py <command> <iptables|cilium> [args]: set up and measure E1 on one cluster.

  run       preflight -> deploy -> for each N: N fake Services, wait for sync, measure RUNS times
  preflight check the cluster is the setup it claims to be; write results/env-<setup>.txt
  deploy    deploy the test apps, fortio-server/client pinned to the chosen nodes
  services  N            make exactly N fake Services (e1-svc-00001..N)
  wait      N            wait until endpoints + the client node's data plane hold N Services
  measure   N RUN        one fortio run -> one CSV row (+ raw files in <csv dir>/raw/)
  show      [SERVICE]    demo view: how one Service is stored in iptables / the eBPF LB map
  cleanup   [--namespace] remove the fake Services (and the e1-bench namespace)

Setup -> kubectl context: iptables = it2003@calico, cilium = it2003@cilium (--context to override).
Knobs are flags or the old env vars (SIZES, RUNS, CSV, QPS, ...); see e1/README.md.
Quick test:  run-e1.py run cilium --quick     (-> results/quick.csv, N = 10 100, 1 run)
"""
from __future__ import annotations

import argparse
import csv
import ipaddress
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import e1lib  # noqa: F401  (first: switches to e1/.venv if needed)
import yaml
from rich.panel import Panel
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.table import Table

from e1lib import (CSV_HEADER, parse_sizes, FAKE_LABEL, FAKE_PREFIX, FORTIO, MANIFEST, SYSTEM_NAMESPACES, Config,
                   E1Error, cilium_dbg, console, count_dataplane, count_lines, die, dump_nat, fail, kc,
                   kc_json, kc_out, log, parse_seconds, pod_on_node, select_nodes, warn)


# ------------------------------------------------------------------ cluster + nodes

def connect(cfg: Config) -> None:
    """Check the API answers and pick server/client nodes (once per Config)."""
    if cfg.server_node and cfg.client_node and cfg.ssh_target:
        return
    kc(cfg, "get", "--raw", "/readyz", "--request-timeout=10s")
    table = select_nodes(cfg)
    t = Table(title=f"nodes in {cfg.context}", title_justify="left", box=None)
    for col in ("node", "InternalIP", "role in E1", "note"):
        t.add_column(col)
    for r in table:
        role = {cfg.server_node: "[bold]server[/]", cfg.client_node: "[bold]client (counted)[/]"}.get(r["name"], "")
        t.add_row(r["name"], r["ip"] or "-", role, r["why"] or "")
    console.print(t)


# ------------------------------------------------------------------ preflight

def service_cidrs(cfg: Config) -> list[str]:
    out = kc_out(cfg, "get", "servicecidrs", "-o", "jsonpath={.items[*].spec.cidrs[*]}", check=False).split()
    if out:
        return out
    pods = kc_json(cfg, "-n", "kube-system", "get", "pod", "-l", "component=kube-apiserver", check=False)
    for p in pods.get("items", [])[:1]:
        for arg in p["spec"]["containers"][0].get("command", []):
            if arg.startswith("--service-cluster-ip-range="):
                return arg.split("=", 1)[1].split(",")
    return []


def kube_proxy_mode(cfg: Config) -> str:
    conf = kc_out(cfg, "-n", "kube-system", "get", "cm", "kube-proxy",
                  "-o", "jsonpath={.data.config\\.conf}", check=False)
    try:
        return str((yaml.safe_load(conf) or {}).get("mode") or "")
    except yaml.YAMLError:
        return ""


def preflight(cfg: Config) -> None:
    connect(cfg)
    log(f"preflight: setup={cfg.setup} context={cfg.context}")
    if cfg.ns != "e1-bench":
        fail(cfg, f"ns is '{cfg.ns}' but e1-bench.yaml hardcodes namespace e1-bench")
    if not cfg.sizes:
        die("no sizes given")
    max_n = max(cfg.sizes)

    n_kp = count_lines(cfg, "-n", "kube-system", "get", "pods", "-l", "k8s-app=kube-proxy")
    n_ci = count_lines(cfg, "-n", "kube-system", "get", "pods", "-l", "k8s-app=cilium")
    if cfg.setup == "iptables":
        if n_kp == 0:
            fail(cfg, "Setup A needs kube-proxy, none found")
        if n_ci:
            fail(cfg, "cilium agents found - this looks like Setup B")
        mode = kube_proxy_mode(cfg)
        log(f"  kube-proxy mode: '{mode or '<empty> = iptables'}'")
        if mode and mode != "iptables":
            fail(cfg, f"kube-proxy mode is '{mode}', must be iptables (Kubespray: kube_proxy_mode: iptables)")
        if count_lines(cfg, "get", "pods", "-A", "-l", "k8s-app=calico-node") == 0:
            fail(cfg, "no calico-node pods found")
        dp = kc_out(cfg, "get", "installation", "default",
                    "-o", "jsonpath={.spec.calicoNetwork.linuxDataplane}", check=False).strip()
        if dp:
            log(f"  calico dataplane (operator): {dp}")
            if dp != "Iptables":
                fail(cfg, f"Calico dataplane is '{dp}', must be Iptables")
        else:
            bpf = kc_out(cfg, "get", "felixconfigurations", "default",
                         "-o", "jsonpath={.spec.bpfEnabled}", check=False).strip()
            log(f"  calico dataplane: no Installation CR; felix bpfEnabled='{bpf or '<unset>'}'")
            if bpf == "true":
                fail(cfg, "Calico eBPF dataplane is enabled (felix bpfEnabled=true)")
    else:
        if n_ci == 0:
            fail(cfg, "Setup B needs Cilium, no agents found")
        if n_kp:
            fail(cfg, "kube-proxy is still running - Cilium must replace it")
        kpr = next((l.strip() for l in cilium_dbg(cfg, "status", check=False).splitlines()
                    if "kubeproxyreplacement" in l.lower()), "")
        log(f"  cilium: {kpr or 'could not read KubeProxyReplacement'}")
        if not any(w in kpr for w in ("True", "Strict")):
            fail(cfg, "KubeProxyReplacement does not look enabled")

    pods = kc_out(cfg, "get", "pods", "-A", "--field-selector=status.phase=Running",
                  "-o", "jsonpath={range .items[*]}{.metadata.namespace}/{.metadata.name}{\"\\n\"}{end}",
                  check=False).split()
    others = [p for p in pods if p.split("/")[0] not in SYSTEM_NAMESPACES | {cfg.ns}]
    if others:
        warn(f"{len(others)} other workload pods are running - stop them for clean numbers:")
        for p in others[:20]:
            console.print(f"    {p}")
        if len(others) > 20:
            console.print(f"    ... and {len(others) - 20} more")

    cidrs = service_cidrs(cfg)
    if cidrs:
        nets = [ipaddress.ip_network(c, strict=False) for c in cidrs]
        v4 = [n for n in nets if n.version == 4] or nets
        cap = sum(n.num_addresses - 2 for n in v4)
        need = max_n + count_lines(cfg, "get", "svc", "-A") + 50
        log(f"  service CIDR {' '.join(cidrs)}: {cap} IPs, need about {need}")
        if cap < need:
            fail(cfg, f"service CIDR too small for {max_n} Services")
    else:
        warn(f"could not detect the service CIDR - make sure it has room for {max_n} Services")

    write_env(cfg)


def write_env(cfg: Config) -> None:
    """Environment record for the report: results/env-<setup>.txt"""
    def sh(*args) -> str:
        p = kc(cfg, *args, check=False)
        return (p.stdout + p.stderr).rstrip()

    parts = [f"# setup={cfg.setup}  context={cfg.context}  date={utcnow()}  server={cfg.server_node}"
             f"  client={cfg.client_node}  ssh_target={cfg.ssh_target}",
             sh("version"), sh("get", "nodes", "-o", "wide")]
    if cfg.setup == "iptables":
        parts += ["## kube-proxy config",
                  sh("-n", "kube-system", "get", "cm", "kube-proxy", "-o", "jsonpath={.data.config\\.conf}"),
                  "## calico images",
                  sh("get", "ds", "-A", "-o",
                     'jsonpath={range .items[?(@.metadata.name=="calico-node")]}{..image}{"\\n"}{end}'),
                  "## calico installation (operator)",
                  sh("get", "installation", "default", "-o", "jsonpath={.spec.calicoNetwork}"),
                  "## felix configuration", sh("get", "felixconfigurations", "default", "-o", "yaml"),
                  "## ip pools", sh("get", "ippools.crd.projectcalico.org", "-o", "wide")]
    else:
        status = cilium_dbg(cfg, "status", "--verbose", check=False)
        parts += ["## cilium status", "\n".join(status.splitlines()[:120])]
    out = cfg.csv.parent / f"env-{cfg.setup}.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts) + "\n")
    log(f"  environment saved to {out}")


# ------------------------------------------------------------------ deploy

def render_manifest(cfg: Config) -> str:
    """e1-bench.yaml with a hard nodeSelector on the fortio pods (the manifest only has anti-affinity)."""
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    pins = {"fortio-server": cfg.server_node, "fortio-client": cfg.client_node}
    done = set()
    for d in docs:
        name = d.get("metadata", {}).get("name")
        if d.get("kind") == "Deployment" and name in pins:
            d["spec"]["template"]["spec"]["nodeSelector"] = {"kubernetes.io/hostname": pins[name]}
            done.add(name)
    if missing := set(pins) - done:
        die(f"deployments not found in {MANIFEST.name}: {', '.join(sorted(missing))}")
    return yaml.safe_dump_all(docs, sort_keys=False)


def wait_on_node(cfg: Config, selector: str, node: str) -> str:
    deadline = time.monotonic() + cfg.placement_timeout
    while time.monotonic() < deadline:
        if pod := pod_on_node(cfg, cfg.ns, selector, node):
            return pod
        time.sleep(2)
    console.print(kc_out(cfg, "-n", cfg.ns, "get", "pods", "-l", selector, "-o", "wide", check=False))
    die(f"no Running pod '{selector}' on {node} after {cfg.placement_timeout}s")


def server_url(cfg: Config) -> str:
    # The ClusterIP, not the DNS name: a DNS lookup would add its own Service hop.
    ip = kc_out(cfg, "-n", cfg.ns, "get", "svc", "fortio-server", "-o", "jsonpath={.spec.clusterIP}").strip()
    if not ip:
        die("Service fortio-server has no ClusterIP")
    return f"http://{ip}:8080/"


def deploy(cfg: Config) -> str:
    connect(cfg)
    log(f"deploying test apps (server on {cfg.server_node}, client on {cfg.client_node})")
    rendered = render_manifest(cfg)
    out = cfg.csv.parent / f"e1-bench-{cfg.setup}.rendered.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered)

    # Delete old fortio Deployments first: with required anti-affinity + new node pins, a rolling
    # update can deadlock (new server waits for old client to leave its node, and vice versa).
    kc(cfg, "-n", cfg.ns, "delete", "deploy", "fortio-server", "fortio-client",
       "--ignore-not-found", "--wait=true", check=False)
    kc(cfg, "-n", cfg.ns, "wait", "--for=delete", "pod", "-l", "role=e1-fortio", "--timeout=120s", check=False)
    kc(cfg, "apply", "-f", "-", input=rendered)
    kc(cfg, "-n", cfg.ns, "rollout", "restart", "deploy/e1-pause")   # fresh, evenly spread endpoints
    for d in ("e1-pause", "fortio-server", "fortio-client"):
        p = kc(cfg, "-n", cfg.ns, "rollout", "status", f"deploy/{d}", "--timeout=300s", check=False)
        if p.returncode != 0:
            console.print(kc_out(cfg, "-n", cfg.ns, "get", "pods", "-o", "wide", check=False))
            die(f"deployment {d} not ready")

    wait_on_node(cfg, "app=fortio-server", cfg.server_node)
    client = wait_on_node(cfg, "app=fortio-client", cfg.client_node)
    log(f"  placement OK: fortio-server@{cfg.server_node} fortio-client@{cfg.client_node} ({client})")

    url = server_url(cfg)
    for _ in range(15):
        if kc(cfg, "-n", cfg.ns, "exec", client, "--", FORTIO, "curl", url, check=False).returncode == 0:
            log(f"  sanity check OK: client -> {url}")
            return client
        time.sleep(2)
    die(f"client cannot reach fortio-server at {url}")


# ------------------------------------------------------------------ fake Services

def fake_service(name: str, ns: str) -> dict:
    # All fake Services select the pause pods, so each has real endpoints -> full KUBE-SVC/SEP chains.
    return {"apiVersion": "v1", "kind": "Service",
            "metadata": {"name": name, "namespace": ns, "labels": {"e1": "fake"}},
            "spec": {"type": "ClusterIP", "selector": {"app": "e1-pause"},
                     "ports": [{"name": "http", "port": 80, "targetPort": 8080, "protocol": "TCP"}]}}


def chunks(xs: list, n: int):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def set_services(cfg: Config, n: int) -> None:
    """Make the number of fake Services exactly n (create missing, delete extra)."""
    if kc(cfg, "get", "ns", cfg.ns, check=False).returncode != 0:
        die(f"namespace {cfg.ns} not found (deploy the test apps first)")
    have = set(kc_out(cfg, "-n", cfg.ns, "get", "svc", "-l", FAKE_LABEL,
                      "-o", "jsonpath={.items[*].metadata.name}").split())
    want = {f"{FAKE_PREFIX}{i:05d}" for i in range(1, n + 1)}
    create, delete = sorted(want - have), sorted(have - want)
    log(f"fake Services: have={len(have)} target={n} -> create={len(create)} delete={len(delete)}")

    def do_create(names):
        body = yaml.safe_dump_all([fake_service(x, cfg.ns) for x in names], sort_keys=False)
        kc(cfg, "create", "-f", "-", "-o", "name", input=body)

    def do_delete(names):
        kc(cfg, "-n", cfg.ns, "delete", "svc", "--wait=false", *names)

    for items, fn, size, verb in ((create, do_create, cfg.batch, "created"),
                                  (delete, do_delete, 200, "deleted")):
        if not items:
            continue
        t0 = time.monotonic()
        with ThreadPoolExecutor(cfg.parallel) as pool:
            list(pool.map(fn, chunks(items, size)))
        log(f"  {verb} {len(items)} Services in {time.monotonic() - t0:.0f}s")


def wait_endpoints(cfg: Config, n: int, timeout: int = 1200) -> None:
    """Until n fake Services have EndpointSlices with all pause backends."""
    if n <= 0:
        return
    jp = ("jsonpath={range .items[*]}{.metadata.labels.kubernetes\\.io/service-name}"
          "{\" \"}{.endpoints[*].addresses[0]}{\"\\n\"}{end}")
    t0 = time.monotonic()
    while True:
        ready = set()
        for line in kc_out(cfg, "-n", cfg.ns, "get", "endpointslices", "-o", jp).splitlines():
            f = line.split()
            if f and f[0].startswith(FAKE_PREFIX) and len(f) - 1 >= cfg.pause_replicas:
                ready.add(f[0])
        if len(ready) >= n:
            log(f"  endpointslices ready: {len(ready)}/{n}")
            return
        if time.monotonic() - t0 > timeout:
            die(f"timeout: only {len(ready)}/{n} Services have {cfg.pause_replicas} endpoints")
        log(f"  waiting for endpointslices: {len(ready)}/{n}")
        time.sleep(5)


def wait_dataplane(cfg: Config, n: int, timeout: int = 1200) -> None:
    """Until the client node's data plane holds >= n services and two reads 5 s apart agree."""
    t0, prev, stable = time.monotonic(), -1, 0
    while True:
        rules, ks, pos = count_dataplane(cfg)
        stable = stable + 1 if ks >= n and ks == prev else 0
        prev = ks
        if stable >= 2:
            log(f"  data plane stable: rules={rules} svc_entries={ks} target_pos={pos}")
            return
        if time.monotonic() - t0 > timeout:
            die(f"timeout waiting for data plane (svc_entries={ks}, want >= {n}). If iptables shows 0, "
                "the pod may use a different iptables backend (legacy vs nft) -> try count_via=ssh")
        log(f"  waiting for data plane: rules={rules} svc_entries={ks} (want >= {n}, stable {stable}/2)")
        time.sleep(5)


def wait_ready(cfg: Config, n: int) -> None:
    wait_endpoints(cfg, n)
    wait_dataplane(cfg, n)
    log(f"  settling {cfg.settle}s")
    time.sleep(cfg.settle)


# ------------------------------------------------------------------ measure

def parse_fortio(text: str) -> dict:
    # stdout should be pure JSON; be tolerant of any text printed before it
    idx = 0 if text.startswith("{") else text.find("\n{") + 1
    try:
        d, _ = json.JSONDecoder().raw_decode(text[idx:])
    except ValueError as e:
        die(f"cannot parse fortio JSON: {e}")
    h = d["DurationHistogram"]
    pct = {round(float(p["Percentile"]), 3): float(p["Value"]) for p in (h.get("Percentiles") or [])}
    ms = lambda v: "nan" if v is None else f"{float(v) * 1000:.4f}"
    count = int(h.get("Count", 0))
    ok = int((d.get("RetCodes") or {}).get("200", 0))
    return {"p50_ms": ms(pct.get(50.0)), "p90_ms": ms(pct.get(90.0)), "p99_ms": ms(pct.get(99.0)),
            "p999_ms": ms(pct.get(99.9)), "avg_ms": ms(h.get("Avg")), "max_ms": ms(h.get("Max")),
            "actual_qps": f'{float(d.get("ActualQPS", 0)):.1f}', "requests": str(count),
            "errors": str(count - ok)}


def measure(cfg: Config, n: int, run: int) -> dict:
    """Count the data plane, warm up, one measured fortio run -> one CSV row."""
    connect(cfg)
    cfg.raw_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{cfg.setup}-n{n}-r{run}"
    client = pod_on_node(cfg, cfg.ns, "app=fortio-client", cfg.client_node)
    if not client:
        die(f"fortio-client pod not running on {cfg.client_node} (deploy first)")
    url = server_url(cfg)

    keep = cfg.raw_dir / f"{tag}.rules.gz" if cfg.save_dumps else None
    rules, svc_entries, target_pos = count_dataplane(cfg, keep)
    log(f"\\[{tag}] rules={rules} svc_entries={svc_entries} target_pos={target_pos}")
    if cfg.setup == "iptables" and target_pos == "NA":
        warn("fortio-server rule not found in KUBE-SERVICES (wrong iptables backend? try count_via=ssh)")

    load = ["-n", cfg.ns, "exec", client, "--", FORTIO, "load", "-qps", cfg.qps, "-c", cfg.conc]
    if kc(cfg, *load, "-t", cfg.warmup, "-keepalive=false", url, check=False).returncode != 0:
        warn("warm-up run failed")

    log(f"\\[{tag}] fortio: qps={cfg.qps} c={cfg.conc} t={cfg.duration} keepalive=false -> {url}")
    p = kc(cfg, *load, "-t", cfg.duration, "-keepalive=false", "-timeout", "5s",
           "-r", cfg.resolution, "-p", "50,90,99,99.9", "-json", "-", url, check=False)
    (cfg.raw_dir / f"{tag}.fortio.json").write_text(p.stdout)
    (cfg.raw_dir / f"{tag}.fortio.log").write_text(p.stderr)
    if p.returncode != 0:
        die(f"fortio failed, see {cfg.raw_dir / f'{tag}.fortio.log'}")

    row = {"timestamp": utcnow(), "setup": cfg.setup, "n_services": n, "run": run, "rules": rules,
           "svc_entries": svc_entries, "target_pos": target_pos, **parse_fortio(p.stdout),
           "qps": cfg.qps, "conc": cfg.conc, "duration": cfg.duration}
    cfg.csv.parent.mkdir(parents=True, exist_ok=True)
    new = not cfg.csv.exists() or cfg.csv.stat().st_size == 0
    with cfg.csv.open("a", newline="") as f:
        w = csv.DictWriter(f, CSV_HEADER, lineterminator="\n")
        if new:
            w.writeheader()
        w.writerow(row)
    log(f"\\[{tag}] p50={row['p50_ms']}ms p90={row['p90_ms']}ms p99={row['p99_ms']}ms "
        f"avg={row['avg_ms']}ms qps={row['actual_qps']} requests={row['requests']} errors={row['errors']}")
    if row["errors"] != "0":
        warn(f"\\[{tag}] {row['errors']} failed requests (TIME_WAIT / ephemeral ports? lower QPS)")
    return row


# ------------------------------------------------------------------ full run

def estimate_minutes(cfg: Config) -> float:
    per_run = parse_seconds(cfg.warmup) + parse_seconds(cfg.duration) + 8
    per_step = cfg.settle + 45 + cfg.runs * per_run + (cfg.runs - 1) * cfg.cooldown
    return len(cfg.sizes) * per_step / 60


def run_all(cfg: Config) -> None:
    preflight(cfg)
    deploy(cfg)
    log(f"setup={cfg.setup} context={cfg.context} sizes={cfg.sizes} runs={cfg.runs} csv={cfg.csv} "
        f"(about {estimate_minutes(cfg):.0f} min)")
    t_all = time.monotonic()
    cols = (TextColumn("[bold]{task.description}"), BarColumn(), MofNCompleteColumn(),
            TimeElapsedColumn(), TextColumn("ETA"), TimeRemainingColumn())
    with Progress(*cols, console=console, transient=False) as prog:
        task = prog.add_task("E1 runs", total=len(cfg.sizes) * cfg.runs)
        for i, n in enumerate(cfg.sizes, 1):
            prog.update(task, description=f"step {i}/{len(cfg.sizes)}  N={n}")
            log(f"[bold]=== step {i}/{len(cfg.sizes)}: N={n} Services ===[/]")
            set_services(cfg, n)
            wait_ready(cfg, n)
            for r in range(1, cfg.runs + 1):
                measure(cfg, n, r)
                prog.advance(task)
                if r < cfg.runs:
                    time.sleep(cfg.cooldown)
    if cfg.cleanup:
        cleanup(cfg)
    log(f"done in {(time.monotonic() - t_all) / 60:.0f} min. Results: {cfg.csv} (raw files in {cfg.raw_dir})")
    log(f"next: scripts/collect-and-draw-chart.py {cfg.csv}")


def cleanup(cfg: Config, namespace: bool = False) -> None:
    log("cleanup: removing fake Services")
    set_services(cfg, 0)
    if namespace:
        kc(cfg, "delete", "ns", cfg.ns, "--ignore-not-found", "--wait=false")
        log(f"  namespace {cfg.ns} deleted")


# ------------------------------------------------------------------ demo view

def show_service(cfg: Config, svc: str | None = None) -> None:
    """How ONE Service is represented on the client node (for demo screenshots)."""
    connect(cfg)
    if not svc:
        exists = kc(cfg, "-n", cfg.ns, "get", "svc", f"{FAKE_PREFIX}00001", check=False).returncode == 0
        svc = f"{FAKE_PREFIX}00001" if exists else "fortio-server"
    spec = kc_json(cfg, "-n", cfg.ns, "get", "svc", svc, check=False).get("spec")
    if not spec:
        die(f"Service {cfg.ns}/{svc} not found")
    ip, port = spec["clusterIP"], spec["ports"][0]["port"]
    n_fake = count_lines(cfg, "-n", cfg.ns, "get", "svc", "-l", FAKE_LABEL)
    console.print(Panel(kc_out(cfg, "-n", cfg.ns, "get", "endpointslices", "-l",
                               f"kubernetes.io/service-name={svc}", "-o", "wide", check=False).rstrip(),
                        title=f"Service {cfg.ns}/{svc}  ClusterIP={ip}:{port}",
                        subtitle=f"node {cfg.client_node}, fake Services in cluster: {n_fake}"))

    def box(title, lines, style="cyan"):
        console.print(Panel("\n".join(lines) or "(not found)", title=title, title_align="left",
                            border_style=style, expand=True))

    if cfg.setup == "iptables":
        rules = [l for l in dump_nat(cfg).splitlines() if l.startswith("-A ")]
        ks = [l for l in rules if l.startswith("-A KUBE-SERVICES ")]
        mine = [l for l in ks if f"-d {ip}/32" in l]
        box("1) KUBE-SERVICES entry (matched by linear scan, one rule per Service)", mine)
        own = len(mine)
        chain = next((w for l in mine for w in l.split() if w.startswith("KUBE-SVC-")), None)
        if chain:
            svc_rules = [l for l in rules if l.startswith(f"-A {chain} ")]
            box(f"2) {chain} (load-balancing by random probability)", svc_rules)
            own += len(svc_rules)
            seps = sorted({w for l in svc_rules for w in l.split() if w.startswith("KUBE-SEP-")})
            for sep in seps:
                sep_rules = [l for l in rules if l.startswith(f"-A {sep} ")]
                box(f"3) {sep} (DNAT to one backend)", sep_rules, "magenta")
                own += len(sep_rules)
        pos = next((i for i, l in enumerate(ks, 1) if f"-d {ip}/32" in l), "?")
        box("Whole nat table on this node", [
            f"rules for this one Service: {own}",
            f"total rules (-A):           {len(rules)}",
            f"KUBE-SERVICES rules:        {len(ks)}   <- scanned one by one for every new connection",
            f"position of {svc}:   {pos}"], "red")
    else:
        lst = cilium_dbg(cfg, "service", "list").splitlines()
        box("1) cilium-dbg service list (frontend -> backends)", lst[:1] + [l for l in lst[1:] if f"{ip}:" in l])
        lb = cilium_dbg(cfg, "bpf", "lb", "list").splitlines()
        box("2) cilium-dbg bpf lb list (the eBPF hash map rows for this Service)",
            lb[:1] + [l for l in lb[1:] if l.split() and l.split()[0].startswith(f"{ip}:")])
        rows = [l.split() for l in lb[1:] if l.strip()]
        box("Whole eBPF LB map on this node", [
            f"rows (frontends + backends): {len(rows)}",
            f"distinct frontends:          {len({r[0] for r in rows})}   "
            "<- looked up by hash key (IP, port, proto), not scanned"], "blue")


# ------------------------------------------------------------------ CLI

def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("setup", choices=["iptables", "cilium"])
    g = common.add_argument_group("cluster")
    g.add_argument("--context", help="kubectl context (default: it2003@calico / it2003@cilium)")
    g.add_argument("--server-node")
    g.add_argument("--client-node")
    g.add_argument("--ssh-target")
    g.add_argument("--count-via", choices=["pod", "ssh"])
    g = common.add_argument_group("measurement")
    g.add_argument("--sizes", help='e.g. "100 2080 4060"')
    g.add_argument("--runs", type=int)
    g.add_argument("--csv")
    g.add_argument("--qps", type=int)
    g.add_argument("--conc", type=int)
    g.add_argument("--duration")
    g.add_argument("--warmup")
    g.add_argument("--settle", type=int)
    g.add_argument("--cooldown", type=int)
    g.add_argument("--force", action="store_true", default=None, help="continue despite preflight errors")

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run", parents=[common], help="full experiment")
    p.add_argument("--quick", action="store_true", help="results/quick.csv, N = 10 100, 1 run")
    p.add_argument("--cleanup", action="store_true", default=None, help="delete fake Services at the end")
    sub.add_parser("preflight", parents=[common])
    sub.add_parser("deploy", parents=[common])
    sub.add_parser("services", parents=[common]).add_argument("n", type=int)
    sub.add_parser("wait", parents=[common]).add_argument("n", type=int)
    p = sub.add_parser("measure", parents=[common])
    p.add_argument("n", type=int)
    p.add_argument("run", type=int)
    sub.add_parser("show", parents=[common]).add_argument("service", nargs="?")
    sub.add_parser("cleanup", parents=[common]).add_argument("--namespace", action="store_true",
                                                             help="also delete the e1-bench namespace")
    return ap


def config_from_args(a: argparse.Namespace) -> Config:
    cfg = Config.from_env(
        a.setup, context=a.context, server_node=a.server_node, client_node=a.client_node,
        ssh_target=a.ssh_target, count_via=a.count_via, sizes=parse_sizes(a.sizes) if a.sizes else None,
        runs=a.runs, csv=a.csv, qps=a.qps, conc=a.conc, duration=a.duration, warmup=a.warmup,
        settle=a.settle, cooldown=a.cooldown, force=a.force, cleanup=getattr(a, "cleanup", None))
    if getattr(a, "quick", False):
        cfg = cfg.quick()
    return cfg


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    try:
        cfg = config_from_args(a)
        match a.cmd:
            case "run": run_all(cfg)
            case "preflight": preflight(cfg)
            case "deploy": deploy(cfg)
            case "services": connect(cfg); set_services(cfg, a.n)
            case "wait": connect(cfg); wait_ready(cfg, a.n)
            case "measure": measure(cfg, a.n, a.run)
            case "show": show_service(cfg, a.service)
            case "cleanup": connect(cfg); cleanup(cfg, a.namespace)
    except E1Error as e:
        console.print(f"[bold red]ERROR:[/] {e}")
        return 1
    except KeyboardInterrupt:
        console.print("[yellow]interrupted[/]")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
