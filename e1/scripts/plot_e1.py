#!/usr/bin/env python3
"""plot_e1.py <e1.csv> <e1.png> [--logx-c]

Draws the 3 E1 charts from the CSV written by measure.sh:
  (a) rules / eBPF entries vs number of Services
  (b) latency (p50, p99) vs number of Services
  (c) latency (p50, p99) vs rules / entries   <- main chart
Each point is the mean over runs, error bars are the standard deviation.
Also writes <e1>_summary.csv and prints a summary + a *suggested* verdict for the conclusion.
Needs: python3, matplotlib.
"""
import argparse
import csv
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

STYLE = {
    "iptables": dict(color="#d62728", marker="o", label="Calico + kube-proxy (iptables)"),
    "cilium": dict(color="#1f77b4", marker="s", label="Cilium eBPF (no kube-proxy)"),
}
ORDER = ["iptables", "cilium"]


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


def mean_sd(values):
    v = [x for x in values if not math.isnan(x)]
    if not v:
        return math.nan, math.nan
    return statistics.fmean(v), (statistics.stdev(v) if len(v) > 1 else 0.0)


def linfit(xs, ys):
    """least squares y = a*x + b, returns (a, b, r) or None"""
    pts = [(x, y) for x, y in zip(xs, ys) if not (math.isnan(x) or math.isnan(y))]
    if len(pts) < 2:
        return None
    mx = statistics.fmean(p[0] for p in pts)
    my = statistics.fmean(p[1] for p in pts)
    sxx = sum((x - mx) ** 2 for x, _ in pts)
    syy = sum((y - my) ** 2 for _, y in pts)
    sxy = sum((x - mx) * (y - my) for x, y in pts)
    if sxx == 0:
        return None
    a = sxy / sxx
    r = sxy / math.sqrt(sxx * syy) if syy > 0 else 0.0
    return a, my - a * mx, r


def load(path):
    with open(path, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("setup")]
    if not rows:
        sys.exit(f"no rows in {path}")
    return rows


def aggregate(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[(r["setup"], int(float(r["n_services"])))].append(r)
    agg = defaultdict(list)
    for (setup, n), rs in groups.items():
        d = {"n": n, "runs": len(rs), "errors": sum(int(e) for e in (num(r.get("errors")) for r in rs) if not math.isnan(e))}
        for col in ("rules", "svc_entries", "p50_ms", "p90_ms", "p99_ms", "avg_ms"):
            d[col] = mean_sd([num(r.get(col)) for r in rs])
        agg[setup].append(d)
    for setup in agg:
        agg[setup].sort(key=lambda d: d["n"])
    return agg


def setups_in(agg):
    return [s for s in ORDER if s in agg] + sorted(s for s in agg if s not in ORDER)


def style(setup):
    return STYLE.get(setup, dict(color="gray", marker="^", label=setup))


def ebar(ax, xs, ys, yerr, st, ls="-", label=None, alpha=1.0):
    ax.errorbar(xs, ys, yerr=yerr, color=st["color"], marker=st["marker"], ls=ls,
                capsize=3, ms=5, lw=1.6, label=label, alpha=alpha)


def plot(agg, rows, out_png, logx_c):
    fig, axes = plt.subplots(1, 3, figsize=(19, 5.8))
    ax_a, ax_b, ax_c = axes

    # (a) rules vs Services
    for s in setups_in(agg):
        st, pts = style(s), agg[s]
        n = [p["n"] for p in pts]
        fit = linfit(n, [p["rules"][0] for p in pts])
        per = f" (≈ {fit[0]:.1f} per Service)" if fit else ""
        ebar(ax_a, n, [p["rules"][0] for p in pts], [p["rules"][1] for p in pts], st,
             label=st["label"] + (": nat rules" if s == "iptables" else ": bpf lb rows") + per)
    ax_a.set_xscale("log")
    ax_a.set_yscale("log")
    ax_a.set_xlabel("number of Services")
    ax_a.set_ylabel("rules (iptables nat) / entries (eBPF LB map)")
    ax_a.set_title("(a) Rules / entries vs Services")

    # (b) latency vs Services
    for s in setups_in(agg):
        st, pts = style(s), agg[s]
        n = [p["n"] for p in pts]
        ebar(ax_b, n, [p["p50_ms"][0] for p in pts], [p["p50_ms"][1] for p in pts], st, "-",
             f"{s} p50")
        ebar(ax_b, n, [p["p99_ms"][0] for p in pts], [p["p99_ms"][1] for p in pts], st, "--",
             f"{s} p99", alpha=0.7)
    ax_b.set_xscale("log")
    ax_b.set_xlabel("number of Services")
    ax_b.set_ylabel("latency per request, new connection (ms)")
    ax_b.set_title("(b) Latency vs Services")

    # (c) latency vs rules  (main chart) + linear fit on p50 from all runs
    for s in setups_in(agg):
        st, pts = style(s), agg[s]
        x = [p["rules"][0] for p in pts]
        ebar(ax_c, x, [p["p50_ms"][0] for p in pts], [p["p50_ms"][1] for p in pts], st, "-",
             f"{s} p50")
        ebar(ax_c, x, [p["p99_ms"][0] for p in pts], [p["p99_ms"][1] for p in pts], st, "--",
             f"{s} p99", alpha=0.7)
        rs = [r for r in rows if r["setup"] == s]
        fit = linfit([num(r["rules"]) for r in rs], [num(r["p50_ms"]) for r in rs])
        if fit and len(x) > 1:
            a, b, r = fit
            xs = [min(x), max(x)]
            ax_c.plot(xs, [a * v + b for v in xs], ls=":", color=st["color"], lw=1.2,
                      label=f"{s} p50 fit: {a * 1e7:+.1f} µs / 10k rules (r={r:.2f})")
    if logx_c:
        ax_c.set_xscale("log")
    ax_c.set_xlabel("rules (iptables nat) / entries (eBPF LB map) on the client node")
    ax_c.set_ylabel("latency per request, new connection (ms)")
    ax_c.set_title("(c) Latency vs rules / entries  [main chart]", fontweight="bold")

    for ax in axes:
        ax.grid(True, which="both", alpha=0.3)
        ax.legend(fontsize=8)
    for ax in (ax_b, ax_c):
        ax.set_ylim(bottom=0)
    fig.suptitle("E1 - Does latency grow with the number of Services?  "
                 "(fortio, keepalive=false, node-2 → Service → node-1)", fontsize=12)
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    print(f"chart  -> {out_png}")


def summary(agg, rows, out_csv):
    cols = ["setup", "n_services", "runs", "rules", "svc_entries", "p50_ms", "p50_sd", "p90_ms",
            "p99_ms", "p99_sd", "avg_ms", "errors"]
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for s in setups_in(agg):
            for p in agg[s]:
                w.writerow([s, p["n"], p["runs"], f"{p['rules'][0]:.0f}", f"{p['svc_entries'][0]:.0f}",
                            f"{p['p50_ms'][0]:.4f}", f"{p['p50_ms'][1]:.4f}", f"{p['p90_ms'][0]:.4f}",
                            f"{p['p99_ms'][0]:.4f}", f"{p['p99_ms'][1]:.4f}", f"{p['avg_ms'][0]:.4f}",
                            p["errors"]])
    print(f"table  -> {out_csv}\n")

    print(f"{'setup':9} {'N':>6} {'runs':>4} {'rules':>8} {'p50 ms':>16} {'p99 ms':>16} {'avg ms':>8} {'err':>5}")
    for s in setups_in(agg):
        for p in agg[s]:
            print(f"{s:9} {p['n']:>6} {p['runs']:>4} {p['rules'][0]:>8.0f} "
                  f"{p['p50_ms'][0]:>8.3f} ±{p['p50_ms'][1]:<6.3f} {p['p99_ms'][0]:>8.3f} ±{p['p99_ms'][1]:<6.3f} "
                  f"{p['avg_ms'][0]:>8.3f} {p['errors']:>5}")
    print()

    # growth from smallest to largest N, compared with run-to-run noise
    grew = {}
    for s in setups_in(agg):
        pts = agg[s]
        if len(pts) < 2:
            continue
        lo, hi = pts[0], pts[-1]
        d = hi["p50_ms"][0] - lo["p50_ms"][0]
        rel = d / lo["p50_ms"][0] * 100 if lo["p50_ms"][0] else math.nan
        noise = max(lo["p50_ms"][1], hi["p50_ms"][1])
        rs = [r for r in rows if r["setup"] == s]
        fit = linfit([num(r["rules"]) for r in rs], [num(r["p50_ms"]) for r in rs])
        sig = d > 2 * noise and rel > 10
        grew[s] = sig
        fit_txt = f", fit {fit[0] * 1e4 * 1e3:+.1f} µs per 10k rules (r={fit[2]:.2f})" if fit else ""
        print(f"{s}: p50 {lo['p50_ms'][0]:.3f} → {hi['p50_ms'][0]:.3f} ms from N={lo['n']} to N={hi['n']} "
              f"({d * 1000:+.0f} µs, {rel:+.1f}%, noise ±{noise * 1000:.0f} µs){fit_txt}"
              f" -> {'clear growth' if sig else 'no clear growth'}")

    if "iptables" in grew and "cilium" in grew:
        if grew["iptables"] and not grew["cilium"]:
            v = "Yes - iptables latency grows with rules, Cilium stays flat"
        elif grew["iptables"] and grew["cilium"]:
            v = "Partly - both grow; compare the slopes in chart (c)"
        elif not grew["iptables"] and not grew["cilium"]:
            v = "No / Partly - no difference above noise at these sizes (try bigger N or more runs)"
        else:
            v = "No - Cilium grows but iptables does not; check the setup"
        print(f"\nSuggested verdict (check the charts before writing it down): {v}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("png")
    ap.add_argument("--logx-c", action="store_true", help="log x-axis for chart (c)")
    a = ap.parse_args()
    rows = load(a.csv)
    agg = aggregate(rows)
    plot(agg, rows, a.png, a.logx_c)
    summary(agg, rows, str(Path(a.csv).with_name(Path(a.csv).stem + "_summary.csv")))


if __name__ == "__main__":
    main()
