#!/usr/bin/env python3
"""collect-and-draw-chart.py [e1.csv] [--out e1.png]: turn E1 results into a 3-chart story.

Reads the CSV written by run-e1.py (every row is averaged per setup and N, so keep quick tests
in a separate CSV) plus the raw fortio histograms in <csv dir>/raw/, then writes:

  <stem>.png           all charts in one figure (for the report)
  <stem>-1-hero.png    1. what happens: p50 latency vs number of Services
  <stem>-slide-p50.png  minimal versions of chart 1 for the slides (p50 and p99):
  <stem>-slide-p99.png  takeaway title, the two lines and their end values only
  <stem>-2-why.png     2. why: data-plane size vs number of Services
  <stem>-3-cdf.png     3. the whole distribution: latency CDF, smallest vs largest N
  <stem>_summary.csv   mean / SD per setup and N

and prints the summary table, the change from smallest to largest N against run-to-run noise,
a linear fit (us per 10k rules) and a *suggested* Yes/Partly/No verdict. Treat it as a hint.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import e1lib  # noqa: F401  (first: switches to e1/.venv if needed)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator  # noqa: E402
from rich.table import Table  # noqa: E402

from e1lib import RESULTS, SETUP_LABEL, console  # noqa: E402

# ------------------------------------------------------------------ visual tokens
# Two series: iptables red, Cilium blue (validated: CVD dE 21.6, normal-vision dE 32.3, both >= 3:1).
# Marker shape is the secondary encoding. Text uses ink tokens, never the series colour.
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#a3a29c", "#e6e5e1"
SERIES = {"iptables": dict(color="#e34948", marker="o"), "cilium": dict(color="#2a78d6", marker="s")}
ORDER = ["iptables", "cilium"]
SHORT = {"iptables": "iptables", "cilium": "Cilium eBPF"}
SLIDE_NAME = {"iptables": "Calico (iptables)", "cilium": "Cilium (eBPF)"}
# Hero chart metric -> (short name, subtitle lead).
METRIC = {"p50_ms": ("p50", "Median time per HTTP request"),
          "p99_ms": ("p99", "99th-percentile time per HTTP request")}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "DejaVu Sans", "font.size": 10.5, "text.color": INK,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "axes.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "grid.linestyle": "-",
    "xtick.color": INK2, "ytick.color": INK2, "xtick.major.size": 0, "ytick.major.size": 0,
    "legend.frameon": False, "legend.fontsize": 9.5,
})


# ------------------------------------------------------------------ collect

def num(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


def mean_sd(values) -> tuple[float, float]:
    v = [x for x in values if not math.isnan(x)]
    if not v:
        return math.nan, math.nan
    return statistics.fmean(v), (statistics.stdev(v) if len(v) > 1 else 0.0)


def linfit(xs, ys):
    """least squares y = a*x + b -> (a, b, r) or None"""
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
    return a, my - a * mx, (sxy / math.sqrt(sxx * syy) if syy > 0 else 0.0)


def load(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("setup")]
    if not rows:
        sys.exit(f"no rows in {path}")
    return rows


def aggregate(rows) -> dict[str, list[dict]]:
    groups = defaultdict(list)
    for r in rows:
        groups[(r["setup"], int(float(r["n_services"])))].append(r)
    agg = defaultdict(list)
    for (setup, n), rs in groups.items():
        d = {"n": n, "runs": len(rs),
             "errors": sum(int(e) for e in (num(r.get("errors")) for r in rs) if not math.isnan(e))}
        for col in ("rules", "svc_entries", "p50_ms", "p90_ms", "p99_ms", "avg_ms"):
            d[col] = mean_sd([num(r.get(col)) for r in rs])
        agg[setup].append(d)
    for s in agg:
        agg[s].sort(key=lambda d: d["n"])
    return dict(agg)


def setups_in(agg) -> list[str]:
    return [s for s in ORDER if s in agg] + sorted(s for s in agg if s not in ORDER)


def style(setup) -> dict:
    return SERIES.get(setup, dict(color=MUTED, marker="^"))


def analyse(agg, rows, metric: str = "p50_ms") -> dict[str, dict]:
    """Per setup: change in `metric` from smallest to largest N, noise, fits, 'clear growth' flag."""
    out = {}
    for s in setups_in(agg):
        pts = agg[s]
        lo, hi = pts[0], pts[-1]
        d = hi[metric][0] - lo[metric][0]
        rs = [r for r in rows if r["setup"] == s]
        out[s] = {
            "lo": lo, "hi": hi, "delta_ms": d,
            "rel": d / lo[metric][0] * 100 if lo[metric][0] else math.nan,
            "noise_ms": max(lo[metric][1], hi[metric][1]),
            "fit_rules": linfit([num(r["rules"]) for r in rs], [num(r[metric]) for r in rs]),
            "fit_n": linfit([p["n"] for p in pts], [p[metric][0] for p in pts]),
            "per_svc": linfit([p["n"] for p in pts], [p["rules"][0] for p in pts]),
        }
        out[s]["grew"] = len(pts) > 1 and d > 2 * out[s]["noise_ms"] and out[s]["rel"] > 10
    return out


def verdict(st) -> tuple[str, str] | None:
    """(short headline, suggested verdict) when both setups are present."""
    if "iptables" not in st or "cilium" not in st:
        return None
    a, b = st["iptables"]["grew"], st["cilium"]["grew"]
    if a and not b:
        return ("iptables gets slower with every Service, Cilium stays flat",
                "Yes - iptables latency grows with rules, Cilium stays flat")
    if a and b:
        return ("Both get slower as Services grow, compare the slopes",
                "Partly - both grow; compare the slopes in the hero chart")
    if not a and not b:
        return ("No latency change above noise at these sizes",
                "No / Partly - no difference above noise at these sizes (try bigger N or more runs)")
    return ("Cilium grows but iptables does not, check the setup",
            "No - Cilium grows but iptables does not; check the setup")


def load_cdf(raw: Path, setup: str, n: int):
    """Mean CDF over runs from fortio's histogram buckets -> (x_ms, y_fraction) or None."""
    curves = []
    for f in sorted(raw.glob(f"{setup}-n{n}-r*.fortio.json")):
        try:
            txt = f.read_text(errors="replace")
            d, _ = json.JSONDecoder().raw_decode(txt[txt.find("{"):])
            data = d["DurationHistogram"]["Data"]
        except (ValueError, KeyError):
            continue
        if not data:
            continue
        edges = [data[0]["Start"]] + [b["End"] for b in data]
        cum = np.cumsum([0] + [b["Count"] for b in data], dtype=float)
        curves.append((np.array(edges) * 1000, cum / cum[-1]))
    if not curves:
        return None
    grid = np.linspace(min(c[0][0] for c in curves), max(c[0][-1] for c in curves), 600)
    return grid, np.mean([np.interp(grid, x, y) for x, y in curves], axis=0)


# ------------------------------------------------------------------ drawing helpers

def fmt_int(v, _=None) -> str:
    return f"{v:,.0f}"


def fmt_k(v, _=None) -> str:
    return f"{v / 1000:,.0f}k" if v >= 1000 else f"{v:,.0f}"


def n_axis(ax, ns) -> None:
    """x = number of Services; log scale only when the sizes span > 2 decades."""
    ns = sorted(set(ns))
    if ns and ns[0] > 0 and ns[-1] / ns[0] > 100:
        ax.set_xscale("log")
    ax.xaxis.set_major_locator(FixedLocator(ns))
    ax.xaxis.set_major_formatter(FuncFormatter(fmt_int))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xlabel("number of Services in the cluster")
    ax.grid(axis="x", visible=False)


def titled(ax, title: str, subtitle: str) -> None:
    ax.set_title(title, loc="left", fontsize=13, fontweight="bold", color=INK,
                 pad=14 + 13 * (subtitle.count("\n") + 1))
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=9.5, color=INK2, va="bottom")


def line(ax, xs, ys, sds, s, label, band: bool = True) -> None:
    st = style(s)
    ys, sds = np.array(ys), np.array(sds)
    if band:
        ax.fill_between(xs, ys - sds, ys + sds, color=st["color"], alpha=0.14, lw=0)
    ax.plot(xs, ys, color=st["color"], lw=2, marker=st["marker"], ms=7, mec=SURFACE, mew=1.5,
            label=label, zorder=3)


def end_labels(ax, items) -> None:
    """Direct labels right of the last point; nudged apart if they would collide."""
    lo, hi = ax.get_ylim()
    gap = (hi - lo) * 0.13
    items = sorted(items, key=lambda it: it[1])
    ys = [it[1] for it in items]
    for i in range(1, len(ys)):
        ys[i] = max(ys[i], ys[i - 1] + gap)
    for (x, _, head, body), y in zip(items, ys):
        ax.annotate(head, (x, y), xytext=(12, 4), textcoords="offset points", fontsize=10.5,
                    fontweight="bold", color=INK, va="bottom")
        ax.annotate(body, (x, y), xytext=(12, 2), textcoords="offset points", fontsize=9.5,
                    color=INK2, va="top")


# ------------------------------------------------------------------ the three charts

def draw_hero(ax, agg, st, head, metric: str = "p50_ms", minimal: bool = False) -> None:
    """minimal=True is the slide version: takeaway title, the two lines and their end values only."""
    name, lead = METRIC[metric]
    ns = [p["n"] for s in agg for p in agg[s]]
    items = []
    for s in setups_in(agg):
        pts = agg[s]
        xs = [p["n"] for p in pts]
        line(ax, xs, [p[metric][0] for p in pts], [p[metric][1] for p in pts], s, SETUP_LABEL.get(s, s),
             band=not minimal)
        a = st[s]
        hi = a["hi"][metric][0]
        if minimal:
            items.append((xs[-1], hi, f"{SLIDE_NAME.get(s, s)}  {hi:.2f} ms", ""))
            continue
        body = f"{a['delta_ms'] * 1000:+,.0f} µs ({a['rel']:+.0f}%) vs {a['lo']['n']:,} Services"
        items.append((xs[-1], hi, f"{SHORT.get(s, s)}  {hi:.2f} ms", body))
        if a["grew"] and a["fit_n"] and len(xs) > 2:   # slope written along the rising line
            mid = len(xs) // 2
            ax.annotate(f"≈ {a['fit_n'][0] * 1e6:+,.0f} µs per 1,000 Services",
                        (xs[mid], pts[mid][metric][0]), xytext=(10, -14), textcoords="offset points",
                        fontsize=9.5, color=INK2, ha="left", va="top")
    n_axis(ax, ns)
    top = max(p[metric][0] + (0 if minimal else p[metric][1]) for s in agg for p in agg[s])
    ax.set_ylim(0, top * 1.18)
    ax.set_xlim(*draw_xlim(ax, ns))
    end_labels(ax, items)
    if minimal:
        ax.set_ylabel(f"{name} latency (ms)")
        ax.set_xlabel("number of Services")
        ax.set_title(head, loc="left", fontsize=14, fontweight="bold", color=INK, pad=14)
        return
    ax.set_ylabel(f"{name} latency per request (ms)")
    ax.legend(loc="lower left")
    titled(ax, head, f"{lead}, each on a new TCP connection (fortio, keepalive=false).\n"
                     "Client → ClusterIP → server on another node; band = ± SD over runs.")


def draw_why(ax, agg, st, prefix: str = "") -> None:
    ns = [p["n"] for s in agg for p in agg[s]]
    items = []
    what = {"iptables": ("nat rules", "walked rule by rule on a new connection"),
            "cilium": ("LB map entries", "found by one hash lookup")}
    for s in setups_in(agg):
        pts = agg[s]
        xs = [p["n"] for p in pts]
        unit, how = what.get(s, ("entries", ""))
        line(ax, xs, [p["rules"][0] for p in pts], [p["rules"][1] for p in pts], s,
             f"{SETUP_LABEL.get(s, s)}: {unit}")
        per = st[s]["per_svc"]
        items.append((xs[-1], pts[-1]["rules"][0], f"{fmt_int(pts[-1]['rules'][0])} {unit}",
                      (f"≈ {per[0]:.1f} per Service, " if per else "") + how))
    n_axis(ax, ns)
    top = max(p["rules"][0] for s in agg for p in agg[s])
    ax.set_ylim(0, top * 1.18)
    ax.set_xlim(*draw_xlim(ax, ns))
    ax.yaxis.set_major_formatter(FuncFormatter(fmt_k))
    ax.set_ylabel("entries on the client node")
    end_labels(ax, items)
    ax.legend(loc="upper left")
    titled(ax, prefix + "Both grow with every Service; only iptables scans its list",
           "iptables: -A rules in iptables-save -t nat.  Cilium: rows in cilium-dbg bpf lb list.\n"
           "The size alone is not the cost; how a packet finds its Service is.")


def draw_xlim(ax, ns):
    if ax.get_xscale() == "linear":
        span = max(ns) - min(ns)
        return min(ns) - span * 0.04, max(ns) + span * 0.62
    return min(ns) / 1.3, max(ns) * 12


def draw_cdf(ax, s, agg, st, raw: Path) -> bool:
    a = st[s]
    lo, hi = a["lo"]["n"], a["hi"]["n"]
    c_lo, c_hi = load_cdf(raw, s, lo), load_cdf(raw, s, hi)
    if not (c_lo and c_hi):
        ax.text(0.5, 0.5, f"no raw fortio histograms for {s}\nin {raw}", ha="center", va="center",
                transform=ax.transAxes, color=INK2)
        ax.set_axis_off()
        return False
    col = style(s)["color"]
    ax.plot(*c_lo, color=MUTED, lw=2, label=f"{lo:,} Services")
    ax.plot(*c_hi, color=col, lw=2, label=f"{hi:,} Services")
    ax.axhline(0.5, color=GRID, lw=1, zorder=0)
    m_lo, m_hi = a["lo"]["p50_ms"][0], a["hi"]["p50_ms"][0]
    if a["grew"]:
        ax.annotate("", (m_hi, 0.5), (m_lo, 0.5),
                    arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.4, shrinkA=0, shrinkB=0))
        ax.text((m_lo + m_hi) / 2, 0.53, f"median {a['delta_ms'] * 1000:+,.0f} µs", ha="center",
                va="bottom", fontsize=10, fontweight="bold", color=INK)
        sub = "The whole curve moves right: every connection pays, not only the tail."
    else:
        ax.text(max(m_lo, m_hi), 0.47, f"  median {a['delta_ms'] * 1000:+,.0f} µs", ha="left",
                va="top", fontsize=10, fontweight="bold", color=INK)
        sub = "The two curves lie on top of each other: the map size does not matter."
    # x range: from the fastest request to the 99.5th percentile of the slower curve
    x995 = max(float(np.interp(0.995, c[1], c[0])) for c in (c_lo, c_hi))
    ax.set_xlim(min(c_lo[0][0], c_hi[0][0]), x995)
    ax.set_ylim(0, 1.02)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_xlabel("latency per request (ms)")
    ax.set_ylabel("requests faster than x")
    ax.legend(loc="lower right")
    titled(ax, SETUP_LABEL.get(s, s), sub)
    return True


# ------------------------------------------------------------------ outputs

def write_summary(agg, out_csv: Path) -> None:
    cols = ["setup", "n_services", "runs", "rules", "svc_entries", "p50_ms", "p50_sd", "p90_ms",
            "p99_ms", "p99_sd", "avg_ms", "errors"]
    with out_csv.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cols)
        for s in setups_in(agg):
            for p in agg[s]:
                w.writerow([s, p["n"], p["runs"], f"{p['rules'][0]:.0f}", f"{p['svc_entries'][0]:.0f}",
                            f"{p['p50_ms'][0]:.4f}", f"{p['p50_ms'][1]:.4f}", f"{p['p90_ms'][0]:.4f}",
                            f"{p['p99_ms'][0]:.4f}", f"{p['p99_ms'][1]:.4f}", f"{p['avg_ms'][0]:.4f}",
                            p["errors"]])
    console.print(f"table  -> {out_csv}")


def print_report(agg, st) -> None:
    t = Table(title="E1 summary (mean ± SD over runs)", title_justify="left")
    for c in ("setup", "N", "runs", "rules", "p50 ms", "p99 ms", "avg ms", "err"):
        t.add_column(c, justify="left" if c == "setup" else "right")
    for s in setups_in(agg):
        for p in agg[s]:
            t.add_row(s, f"{p['n']:,}", str(p["runs"]), f"{p['rules'][0]:,.0f}",
                      f"{p['p50_ms'][0]:.3f} ± {p['p50_ms'][1]:.3f}",
                      f"{p['p99_ms'][0]:.3f} ± {p['p99_ms'][1]:.3f}", f"{p['avg_ms'][0]:.3f}",
                      str(p["errors"]))
    console.print(t)
    for s, a in st.items():
        fit = a["fit_rules"]
        fit_txt = f", fit {fit[0] * 1e7:+.1f} µs per 10k rules (r={fit[2]:.2f})" if fit else ""
        console.print(
            f"{s}: p50 {a['lo']['p50_ms'][0]:.3f} → {a['hi']['p50_ms'][0]:.3f} ms from N={a['lo']['n']} "
            f"to N={a['hi']['n']} ({a['delta_ms'] * 1000:+.0f} µs, {a['rel']:+.1f}%, noise "
            f"±{a['noise_ms'] * 1000:.0f} µs){fit_txt} -> "
            + ("[bold]clear growth[/]" if a["grew"] else "no clear growth"))
    if v := verdict(st):
        console.print(f"\nSuggested verdict (check the charts before writing it down): [bold]{v[1]}[/]")


def headline(st, metric: str = "p50_ms") -> str:
    name = METRIC[metric][0]
    if metric != "p50_ms" and "iptables" in st and "cilium" in st \
            and st["iptables"]["grew"] and not st["cilium"]["grew"]:
        return f"{name}: iptables grows with Services, Cilium does not"
    if v := verdict(st):
        return v[0] if metric == "p50_ms" else f"{name}: {v[0]}"
    (s, a), = st.items()
    return f"{SETUP_LABEL.get(s, s)}: {name} {'grows' if a['grew'] else 'stays flat'} as Services grow"


def save(fig, path: Path) -> None:
    fig.savefig(path, dpi=150, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    console.print(f"chart  -> {path}")


def draw_all(agg, st, raw: Path, out: Path, split: bool = True, st99=None) -> list[Path]:
    head = headline(st)
    setups = setups_in(agg)
    written = []

    fig = plt.figure(figsize=(17, 12.5))
    gs = fig.add_gridspec(2, 2 * max(1, len(setups)), hspace=0.55, wspace=0.75)
    half = max(1, len(setups))
    draw_hero(fig.add_subplot(gs[0, :half]), agg, st, "1. " + head)
    draw_why(fig.add_subplot(gs[0, half:]), agg, st, "2. ")
    for i, s in enumerate(setups):
        draw_cdf(fig.add_subplot(gs[1, 2 * i:2 * i + 2]), s, agg, st, raw)
    fig.text(0.07, 0.465, "3. The whole latency distribution, smallest vs largest number of Services",
             fontsize=13, fontweight="bold", color=INK)
    fig.suptitle("E1: does the number of Services slow down new connections?", x=0.07, y=0.995,
                 ha="left", fontsize=16, fontweight="bold", color=INK)
    save(fig, out)
    written.append(out)
    if not split:
        return written

    base = out.with_suffix("")
    fig, ax = plt.subplots(figsize=(11, 6))
    draw_hero(ax, agg, st, head)
    save(fig, p := Path(f"{base}-1-hero.png"))
    written.append(p)

    for metric, mst in (("p50_ms", st), ("p99_ms", st99)):
        if not mst:
            continue
        fig, ax = plt.subplots(figsize=(11, 6))
        draw_hero(ax, agg, mst, headline(mst, metric), metric, minimal=True)
        save(fig, p := Path(f"{base}-slide-{METRIC[metric][0]}.png"))
        written.append(p)

    fig, ax = plt.subplots(figsize=(11, 6))
    draw_why(ax, agg, st)
    save(fig, p := Path(f"{base}-2-why.png"))
    written.append(p)

    fig, axes = plt.subplots(1, len(setups), figsize=(6.5 * len(setups), 5.4), squeeze=False)
    for ax, s in zip(axes[0], setups):
        draw_cdf(ax, s, agg, st, raw)
    fig.suptitle("The whole latency distribution, smallest vs largest number of Services", x=0.02,
                 ha="left", fontsize=14, fontweight="bold", color=INK, y=1.04)
    fig.tight_layout()
    save(fig, p := Path(f"{base}-3-cdf.png"))
    written.append(p)
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="?", default=str(RESULTS / "e1.csv"))
    ap.add_argument("--out", help="combined PNG (default: <csv without .csv>.png)")
    ap.add_argument("--raw", help="raw fortio dir (default: <csv dir>/raw)")
    ap.add_argument("--no-split", action="store_true", help="only the combined figure")
    a = ap.parse_args(argv)

    path = Path(a.csv).resolve()
    rows = load(path)
    agg = aggregate(rows)
    st = analyse(agg, rows)
    out = Path(a.out).resolve() if a.out else path.with_suffix(".png")
    raw = Path(a.raw).resolve() if a.raw else path.parent / "raw"
    draw_all(agg, st, raw, out, split=not a.no_split, st99=analyse(agg, rows, "p99_ms"))
    write_summary(agg, path.with_name(path.stem + "_summary.csv"))
    print_report(agg, st)
    return 0


if __name__ == "__main__":
    sys.exit(main())
