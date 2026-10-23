"""Shared helpers for E1: config, kubectl access, logging, data-plane counting.

Imported by main.py, run-e1.py and collect-and-draw-chart.py; not meant to be run directly.
Every kubectl call goes through kc(), which always passes --context, so a script can never
talk to the wrong cluster because of whatever context happens to be current.
"""
from __future__ import annotations

import gzip
import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

# Started with a python that is not e1/.venv (e.g. ./run-e1.py via /usr/bin/env python3)?
# Re-exec the same command with the venv's python, so the scripts work however they are called.
_VENV = Path(__file__).resolve().parent.parent / ".venv"
if (_VENV / "bin" / "python").exists() and Path(sys.prefix).resolve() != _VENV.resolve():
    os.execv(str(_VENV / "bin" / "python"), [str(_VENV / "bin" / "python"), *sys.argv])

from rich.console import Console  # noqa: E402

E1_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = E1_DIR / "scripts"
MANIFEST = E1_DIR / "manifests" / "e1-bench.yaml"
RESULTS = E1_DIR / "results"

SETUPS = ("iptables", "cilium")
DEFAULT_CONTEXT = {"iptables": "it2003@calico", "cilium": "it2003@cilium"}
SETUP_LABEL = {
    "iptables": "Calico + kube-proxy (iptables)",
    "cilium": "Cilium eBPF (no kube-proxy)",
}
FORTIO = "/usr/bin/fortio"  # the fortio image has no shell, so call the binary by full path
FAKE_PREFIX = "e1-svc-"
FAKE_LABEL = "e1=fake"
# Namespaces that may run pods during a measurement (system + CNI); anything else is "noise".
SYSTEM_NAMESPACES = {
    "kube-system", "kube-public", "kube-node-lease", "local-path-storage",
    "calico-system", "calico-apiserver", "tigera-operator", "cilium", "cilium-secrets",
}
CSV_HEADER = [
    "timestamp", "setup", "n_services", "run", "rules", "svc_entries", "target_pos",
    "p50_ms", "p90_ms", "p99_ms", "p999_ms", "avg_ms", "max_ms",
    "actual_qps", "requests", "errors", "qps", "conc", "duration",
]

console = Console(stderr=True, highlight=False, log_path=False)


class E1Error(Exception):
    """Raised by die(); scripts exit 1, main.py returns to its menu."""


def log(msg: str) -> None:
    console.log(msg)


def warn(msg: str) -> None:
    console.log(f"[yellow]WARN:[/] {msg}")


def die(msg: str):
    raise E1Error(msg)


def fail(cfg: "Config", msg: str) -> None:
    """A preflight error: fatal unless cfg.force."""
    if cfg.force:
        warn(f"{msg} (force=1, continuing)")
    else:
        die(f"{msg} (use --force / FORCE=1 to ignore)")


# ------------------------------------------------------------------ config

def _env(name, default, cast=str):
    v = os.environ.get(name)
    return default if v in (None, "") else cast(v)


def parse_sizes(s: str) -> list[int]:
    out = []
    for tok in s.replace(",", " ").split():
        if not tok.isdigit():
            die(f"bad size '{tok}' (sizes must be non-negative integers)")
        out.append(int(tok))
    return out


@dataclass
class Config:
    setup: str
    context: str = ""
    ns: str = "e1-bench"
    server_node: str | None = None
    client_node: str | None = None
    ssh_target: str | None = None
    count_via: str = "pod"          # pod = exec into kube-proxy pod; ssh = ssh <ssh_target> iptables-save
    pause_replicas: int = 3
    sizes: list[int] = field(default_factory=lambda: [100, 2080, 4060, 6040, 8020, 10000])
    runs: int = 3
    csv: Path = RESULTS / "e1.csv"
    qps: int = 200
    conc: int = 4
    duration: str = "30s"
    warmup: str = "5s"
    resolution: str = "0.00001"     # 10 us histogram buckets; fortio's default 1 ms is too coarse
    settle: int = 20
    cooldown: int = 10
    placement_timeout: int = 120
    batch: int = 250
    parallel: int = 8
    save_dumps: bool = True
    cleanup: bool = False
    force: bool = False

    @classmethod
    def from_env(cls, setup: str, **overrides) -> "Config":
        """Defaults <- env vars (same names as the old shell knobs) <- explicit overrides."""
        if setup not in SETUPS:
            die(f"setup must be one of {', '.join(SETUPS)}, got '{setup}'")
        c = cls(
            setup=setup,
            context=_env("KUBE_CONTEXT", DEFAULT_CONTEXT[setup]),
            ns=_env("NS", "e1-bench"),
            server_node=_env("SERVER_NODE", None),
            client_node=_env("CLIENT_NODE", None),
            ssh_target=_env("SSH_TARGET", None),
            count_via=_env("COUNT_VIA", "pod"),
            pause_replicas=_env("PAUSE_REPLICAS", 3, int),
            sizes=parse_sizes(_env("SIZES", "100 2080 4060 6040 8020 10000")),
            runs=_env("RUNS", 3, int),
            csv=Path(_env("CSV", str(RESULTS / "e1.csv"))),
            qps=_env("QPS", 200, int),
            conc=_env("CONC", 4, int),
            duration=_env("DURATION", "30s"),
            warmup=_env("WARMUP", "5s"),
            resolution=_env("RESOLUTION", "0.00001"),
            settle=_env("SETTLE", 20, int),
            cooldown=_env("COOLDOWN", 10, int),
            placement_timeout=_env("PLACEMENT_TIMEOUT", 120, int),
            batch=_env("BATCH", 250, int),
            parallel=_env("PARALLEL", 8, int),
            save_dumps=_env("SAVE_DUMPS", "1") == "1",
            cleanup=_env("CLEANUP", "0") == "1",
            force=_env("FORCE", "0") == "1",
        )
        c = replace(c, **{k: v for k, v in overrides.items() if v is not None})
        c.csv = Path(c.csv).resolve()
        if c.count_via not in ("pod", "ssh"):
            die("count_via must be 'pod' or 'ssh'")
        return c

    @property
    def raw_dir(self) -> Path:
        return self.csv.parent / "raw"

    def quick(self) -> "Config":
        """The quick-test variant: separate CSV (the plot averages every row it finds)."""
        return replace(self, csv=self.csv.parent / "quick.csv", sizes=[10, 100], runs=1)


# ------------------------------------------------------------------ kubectl

def kc(cfg: Config, *args, input: str | None = None, check: bool = True,
       timeout: float | None = None) -> subprocess.CompletedProcess:
    cmd = ["kubectl", "--context", cfg.context, *map(str, args)]
    try:
        p = subprocess.run(cmd, input=input, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        die("kubectl not found in PATH")
    except subprocess.TimeoutExpired:
        die(f"timeout: {' '.join(cmd[:8])} ...")
    if check and p.returncode != 0:
        die(f"{' '.join(cmd[3:8])} ... failed: {p.stderr.strip()[-400:]}")
    return p


def kc_out(cfg: Config, *args, check: bool = True, **kw) -> str:
    p = kc(cfg, *args, check=check, **kw)
    return p.stdout if p.returncode == 0 else ""


def kc_json(cfg: Config, *args, check: bool = True) -> dict:
    out = kc_out(cfg, *args, "-o", "json", check=check)
    return json.loads(out) if out.strip() else {}


def reachable(cfg: Config) -> tuple[bool, str]:
    """Can we talk to the cluster? (context exists + API answers)"""
    p = subprocess.run(["kubectl", "config", "get-contexts", cfg.context],
                       capture_output=True, text=True)
    if p.returncode != 0:
        return False, f"kubectl context '{cfg.context}' not found"
    p = subprocess.run(["kubectl", "--context", cfg.context, "get", "--raw", "/readyz",
                        "--request-timeout=5s"], capture_output=True, text=True)
    if p.returncode != 0:
        return False, f"API of '{cfg.context}' not reachable (OpenVPN up?): {p.stderr.strip()[-200:]}"
    return True, "ok"


def pod_on_node(cfg: Config, ns: str, selector: str, node: str) -> str:
    """Name of a Running pod with the label on that node, or ''."""
    return kc_out(cfg, "-n", ns, "get", "pod", "-l", selector,
                  "--field-selector", f"spec.nodeName={node},status.phase=Running",
                  "-o", "jsonpath={.items[0].metadata.name}", check=False).strip()


def count_lines(cfg: Config, *args) -> int:
    out = kc_out(cfg, *args, "--no-headers", check=False)
    return sum(1 for line in out.splitlines() if line.strip())


# ------------------------------------------------------------------ nodes

def node_table(cfg: Config) -> list[dict]:
    """One dict per node: name, ip, ok (clean worker candidate), why (reasons it is not)."""
    rows = []
    items = kc_json(cfg, "get", "nodes").get("items", [])
    for n in sorted(items, key=lambda n: n["metadata"]["name"]):
        labels = n["metadata"].get("labels", {})
        spec, st = n.get("spec", {}), n.get("status", {})
        ip = next((a["address"] for a in st.get("addresses", []) if a["type"] == "InternalIP"), None)
        why = []
        if not any(c["type"] == "Ready" and c["status"] == "True" for c in st.get("conditions", [])):
            why.append("not-ready")
        if spec.get("unschedulable"):
            why.append("cordoned")
        if "node-role.kubernetes.io/control-plane" in labels or "node-role.kubernetes.io/master" in labels:
            why.append("control-plane")
        taints = [t["key"] for t in spec.get("taints", []) if t.get("effect") in ("NoSchedule", "NoExecute")]
        if taints:
            why.append("taints:" + ",".join(taints))
        rows.append({"name": n["metadata"]["name"], "ip": ip, "ok": not why, "why": ";".join(why)})
    return rows


def select_nodes(cfg: Config) -> list[dict]:
    """Fill cfg.server_node / client_node / ssh_target.
    Auto: clean workers sorted by name, 1st = server, 2nd = client. Or both set explicitly."""
    table = node_table(cfg)
    by_name = {r["name"]: r for r in table}
    if cfg.server_node or cfg.client_node:
        if not (cfg.server_node and cfg.client_node):
            die("set both server and client node, or neither")
        for n in (cfg.server_node, cfg.client_node):
            if n not in by_name:
                die(f"node {n} not found in {cfg.context}")
            if not by_name[n]["ok"]:
                warn(f"node {n} is not a clean candidate ({by_name[n]['why']})")
    else:
        cands = [r["name"] for r in table if r["ok"]]
        if len(cands) < 2:
            die(f"need 2 schedulable worker nodes, found {len(cands)} ({', '.join(cands) or 'none'})")
        cfg.server_node, cfg.client_node = cands[0], cands[1]
    if cfg.server_node == cfg.client_node:
        die("server and client node must differ")
    if not cfg.ssh_target:
        cfg.ssh_target = by_name[cfg.client_node]["ip"]
    return table


# ------------------------------------------------------------------ data plane

def dump_nat(cfg: Config) -> str:
    """iptables-save -t nat as seen on the client node."""
    if cfg.count_via == "ssh":
        p = subprocess.run(["ssh", "-o", "BatchMode=yes", cfg.ssh_target, "sudo iptables-save -t nat"],
                           capture_output=True, text=True)
        if p.returncode != 0:
            die(f"ssh {cfg.ssh_target} iptables-save failed: {p.stderr.strip()}")
        return p.stdout
    pod = pod_on_node(cfg, "kube-system", "k8s-app=kube-proxy", cfg.client_node)
    if not pod:
        die(f"no running kube-proxy pod on {cfg.client_node} (try count_via=ssh)")
    return kc_out(cfg, "-n", "kube-system", "exec", pod, "--", "iptables-save", "-t", "nat")


def cilium_dbg(cfg: Config, *args, check: bool = True) -> str:
    """cilium-dbg (or the older 'cilium' CLI) in the agent on the client node."""
    pod = pod_on_node(cfg, "kube-system", "k8s-app=cilium", cfg.client_node)
    if not pod:
        die(f"no running cilium agent pod on {cfg.client_node}")
    script = 'if command -v cilium-dbg >/dev/null 2>&1; then exec cilium-dbg "$@"; else exec cilium "$@"; fi'
    return kc_out(cfg, "-n", "kube-system", "exec", pod, "-c", "cilium-agent", "--",
                  "sh", "-c", script, "_", *args, check=check)


def nat_counts(text: str, ns: str) -> tuple[int, int, str]:
    rules = [l for l in text.splitlines() if l.startswith("-A ")]
    ks = [l for l in rules if l.startswith("-A KUBE-SERVICES ")]
    pos = next((str(i) for i, l in enumerate(ks, 1) if f"{ns}/fortio-server" in l), "NA")
    return len(rules), len(ks), pos


def lb_counts(text: str) -> tuple[int, int, str]:
    rows = [l.split() for l in text.splitlines()[1:] if l.strip()]
    return len(rows), len({r[0] for r in rows}), "NA"


def count_dataplane(cfg: Config, keep: Path | None = None) -> tuple[int, int, str]:
    """(rules, svc_entries, target_pos) on the client node.
    iptables: rules = all '-A' nat rules, svc_entries = KUBE-SERVICES rules (scanned linearly
              per new connection), target_pos = fortio-server's position in KUBE-SERVICES.
    cilium:   rules = rows of 'bpf lb list' (frontend + backend rows), svc_entries = distinct
              frontends, target_pos = NA (hash lookup, position is meaningless)."""
    if cfg.setup == "iptables":
        text = dump_nat(cfg)
        counts = nat_counts(text, cfg.ns)
    else:
        text = cilium_dbg(cfg, "bpf", "lb", "list")
        counts = lb_counts(text)
    if keep:
        keep.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(keep, "wt") as f:
            f.write(text)
    return counts


# ------------------------------------------------------------------ misc

def load_script(filename: str):
    """Import a sibling script with a hyphen in its name (run-e1.py, collect-and-draw-chart.py)."""
    path = SCRIPTS / filename
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse_seconds(s: str) -> float:
    """'30s' / '2m' / '500ms' / '10' -> seconds"""
    s = s.strip()
    for unit, mul in (("ms", 0.001), ("s", 1), ("m", 60), ("h", 3600)):
        if s.endswith(unit) and s[: -len(unit)].replace(".", "", 1).isdigit():
            return float(s[: -len(unit)]) * mul
    return float(s)
