#!/usr/bin/env python3
"""main.py: interactive entry point for E1.

Pick a setup (iptables = Calico cluster, cilium = Cilium cluster), then choose what to do from
a menu: quick test, full run, single steps, the demo view, charts, cleanup. Everything it does
is also available without prompts through run-e1.py and collect-and-draw-chart.py.
"""
from __future__ import annotations

import csv
import shutil
import sys
from dataclasses import fields, replace
from datetime import datetime
from pathlib import Path

import e1lib  # noqa: F401  (first: switches to e1/.venv if needed)
import questionary
from rich.panel import Panel
from rich.table import Table

from e1lib import (DEFAULT_CONTEXT, RESULTS, SETUP_LABEL, Config, E1Error, console, load_script,
                   parse_sizes, reachable)

run_e1 = load_script("run-e1.py")
chart = load_script("collect-and-draw-chart.py")

# knobs shown in the "edit" form: field -> (label, cast)
KNOBS = {
    "sizes": ("Service counts (space separated)", parse_sizes),
    "runs": ("runs per size", int),
    "csv": ("output CSV", Path),
    "qps": ("fortio QPS", int),
    "conc": ("fortio connections", int),
    "duration": ("measured duration", str),
    "warmup": ("warm-up", str),
    "settle": ("settle after sync (s)", int),
    "cooldown": ("cooldown between runs (s)", int),
}


def show_config(cfg: Config, title: str = "configuration") -> None:
    t = Table(title=title, title_justify="left", show_header=False, box=None)
    t.add_column(style="bold")
    t.add_column()
    for f in fields(cfg):
        v = getattr(cfg, f.name)
        if isinstance(v, list):
            v = " ".join(map(str, v))
        t.add_row(f.name, str(v))
    t.add_row("estimate", f"about {run_e1.estimate_minutes(cfg):.0f} min")
    console.print(t)


def edit_knobs(cfg: Config) -> Config:
    changes = {}
    for name, (label, cast) in KNOBS.items():
        cur = getattr(cfg, name)
        cur_s = " ".join(map(str, cur)) if isinstance(cur, list) else str(cur)
        ans = questionary.text(f"{label}:", default=cur_s).ask()
        if ans is None:
            raise KeyboardInterrupt
        if ans.strip() != cur_s:
            changes[name] = cast(ans.strip())
    cleanup = questionary.confirm("delete the fake Services at the end?", default=cfg.cleanup).ask()
    cfg = replace(cfg, **changes, cleanup=bool(cleanup))
    cfg.csv = Path(cfg.csv).resolve()
    return cfg


def existing_rows(cfg: Config) -> int:
    if not cfg.csv.exists():
        return 0
    with cfg.csv.open(newline="") as f:
        return sum(1 for r in csv.DictReader(f) if r.get("setup") == cfg.setup)


def handle_existing(cfg: Config) -> bool:
    """Re-runs append to the CSV, and the plot averages every row: ask what to do. False = cancel."""
    n = existing_rows(cfg)
    if not n:
        return True
    choice = questionary.select(
        f"{cfg.csv.name} already has {n} rows for {cfg.setup}. The chart averages every row.",
        choices=["append (more runs of the same setup)",
                 f"back up the CSV, then drop the old {cfg.setup} rows",
                 "cancel"]).ask()
    if choice is None or choice == "cancel":
        return False
    if choice.startswith("back up"):
        bak = cfg.csv.with_name(f"{cfg.csv.stem}.{datetime.now():%Y%m%d-%H%M%S}.bak.csv")
        shutil.copy2(cfg.csv, bak)
        with cfg.csv.open(newline="") as f:
            rows = list(csv.reader(f))
        keep = [rows[0]] + [r for r in rows[1:] if len(r) > 1 and r[1] != cfg.setup]
        with cfg.csv.open("w", newline="") as f:
            csv.writer(f, lineterminator="\n").writerows(keep)
        console.print(f"backup -> {bak}; kept {len(keep) - 1} rows of other setups")
    return True


def pick_csv() -> Path | None:
    files = sorted(p for p in RESULTS.glob("*.csv")
                   if not p.stem.endswith("_summary") and ".bak" not in p.name)
    if not files:
        console.print(f"[yellow]no CSV in {RESULTS}[/]")
        return None
    default = next((p.name for p in files if p.name == "e1.csv"), files[0].name)
    ans = questionary.select("which results?", choices=[p.name for p in files], default=default).ask()
    return RESULTS / ans if ans else None


def choose_setup() -> Config | str | None:
    """A Config, "charts" (no cluster), "retry" (cluster unreachable) or None (quit)."""
    setup = questionary.select(
        "Which cluster?",
        choices=[questionary.Choice(f"{SETUP_LABEL[s]}   [{DEFAULT_CONTEXT[s]}]", s) for s in ("iptables", "cilium")]
        + [questionary.Choice("only draw charts (no cluster)", "charts"), questionary.Choice("quit", None)],
    ).ask()
    if setup in (None, "charts"):
        return setup
    cfg = Config.from_env(setup)
    ok, msg = reachable(cfg)
    if not ok:
        console.print(f"[red]{msg}[/]\nHint: connect the OpenVPN, or set KUBE_CONTEXT to the right context.")
        return "retry"
    run_e1.connect(cfg)
    return cfg


def menu(cfg: Config) -> bool:
    """One menu round. False = back to cluster selection."""
    q = cfg.quick()
    actions = {
        f"Quick test  ({q.csv.name}, N = {' '.join(map(str, q.sizes))}, {q.runs} run)": "quick",
        "Full run": "full",
        "Preflight checks only": "preflight",
        "Deploy test apps": "deploy",
        "Set the number of fake Services": "services",
        "Show one Service (demo)": "show",
        "Draw charts": "charts",
        "Cleanup": "cleanup",
        "Switch cluster": "switch",
        "Quit": "quit",
    }
    ans = questionary.select(f"[{cfg.setup} @ {cfg.context}] what next?", choices=list(actions)).ask()
    act = actions.get(ans, "quit")
    if act == "switch":
        return False
    if act == "quit":
        sys.exit(0)
    match act:
        case "quick":
            show_config(q, "quick test")
            if questionary.confirm("start?", default=True).ask():
                run_e1.run_all(q)
        case "full":
            show_config(cfg, "full run")
            if questionary.confirm("edit the knobs first?", default=False).ask():
                cfg2 = edit_knobs(cfg)
                cfg.__dict__.update(cfg2.__dict__)
                show_config(cfg, "full run")
            if handle_existing(cfg) and questionary.confirm(
                    f"start? (about {run_e1.estimate_minutes(cfg):.0f} min)", default=True).ask():
                run_e1.run_all(cfg)
        case "preflight":
            run_e1.preflight(cfg)
        case "deploy":
            run_e1.deploy(cfg)
        case "services":
            n = questionary.text("how many fake Services?", default="100",
                                 validate=lambda s: s.isdigit() or "a non-negative integer").ask()
            if n is not None:
                run_e1.set_services(cfg, int(n))
                if questionary.confirm("wait until the data plane is in sync?", default=True).ask():
                    run_e1.wait_ready(cfg, int(n))
        case "show":
            svc = questionary.text("Service name (empty = e1-svc-00001, else fortio-server):").ask()
            run_e1.show_service(cfg, svc or None)
        case "charts":
            draw_charts()
        case "cleanup":
            ns = questionary.confirm(f"also delete the namespace {cfg.ns}?", default=False).ask()
            if questionary.confirm(f"remove all fake Services on {cfg.context}?", default=True).ask():
                run_e1.cleanup(cfg, bool(ns))
    return True


def draw_charts() -> None:
    if p := pick_csv():
        chart.main([str(p)])


def main() -> int:
    console.print(Panel("E1: does the number of Services slow down new connections?\n"
                        "Calico + kube-proxy (iptables)  vs  Cilium eBPF (kube-proxy replacement)",
                        border_style="cyan"))
    try:
        while True:
            cfg = choose_setup()
            if cfg is None:
                return 0
            if cfg == "retry":
                continue
            if cfg == "charts":
                draw_charts()
                continue
            while True:
                try:
                    if not menu(cfg):
                        break
                except E1Error as e:
                    console.print(f"[bold red]ERROR:[/] {e}")
                except KeyboardInterrupt:
                    console.print("[yellow]interrupted, back to the menu[/]")
    except E1Error as e:
        console.print(f"[bold red]ERROR:[/] {e}")
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
