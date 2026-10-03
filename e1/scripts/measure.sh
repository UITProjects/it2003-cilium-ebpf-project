#!/usr/bin/env bash
# measure.sh <setup> <n_services> <run> [csv]
#   setup: iptables | cilium
# 1. counts rules/entries on CLIENT_NODE
# 2. runs fortio from the client pod (node-2) to fortio-server's ClusterIP (backend on node-1),
#    one NEW TCP connection per request (-keepalive=false)
# 3. appends one row to the CSV; raw fortio output + rule dump go to <csv dir>/raw/
#
# Env: QPS (200) CONC (4) DURATION (30s) WARMUP (5s) RESOLUTION (0.00001 s = 10us histogram buckets)
#      SAVE_DUMPS (1 = keep gzipped iptables-save / bpf lb list per run)
set -euo pipefail
DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=lib.sh
source "$DIR/scripts/lib.sh"

SETUP=${1:?usage: measure.sh <iptables|cilium> <n_services> <run> [csv]}
N=${2:?missing n_services}
RUN=${3:?missing run}
CSV=${4:-${CSV:-$DIR/results/e1.csv}}
QPS=${QPS:-200}
CONC=${CONC:-4}
DURATION=${DURATION:-30s}
WARMUP=${WARMUP:-5s}
RESOLUTION=${RESOLUTION:-0.00001}   # fortio default is 1ms buckets: far too coarse here
SAVE_DUMPS=${SAVE_DUMPS:-1}

case $SETUP in iptables|cilium) ;; *) die "setup must be iptables or cilium" ;; esac
need kubectl; need python3

RAW_DIR="$(dirname "$CSV")/raw"
mkdir -p "$RAW_DIR"
tag="${SETUP}-n${N}-r${RUN}"

client=$(pod_on_node "$NS" app=fortio-client "$CLIENT_NODE")
[[ -n $client ]] || die "fortio-client pod not running on $CLIENT_NODE"
ip=$(kubectl -n "$NS" get svc fortio-server -o jsonpath='{.spec.clusterIP}')
[[ -n $ip ]] || die "Service fortio-server has no ClusterIP"
# Use the ClusterIP, not the DNS name: a DNS lookup would add its own Service hop.
url="http://${ip}:8080/"

# ---- 1. rules
keep=""
[[ $SAVE_DUMPS == 1 ]] && keep="$RAW_DIR/$tag.rules.gz"
read -r rules svc_entries target_pos < <(count_dataplane "$SETUP" "$keep")
log "[$tag] rules=$rules svc_entries=$svc_entries target_pos=$target_pos"
if [[ $SETUP == iptables && $target_pos == NA ]]; then
  warn "fortio-server rule not found in KUBE-SERVICES (wrong iptables backend? try COUNT_VIA=ssh)"
fi

# ---- 2. warm-up (not recorded)
kubectl -n "$NS" exec "$client" -- $FORTIO load -qps "$QPS" -c "$CONC" -t "$WARMUP" \
  -keepalive=false "$url" >/dev/null 2>&1 || warn "warm-up run failed"

# ---- 3. measured run
out="$RAW_DIR/$tag.fortio.json"
log "[$tag] fortio: qps=$QPS c=$CONC t=$DURATION keepalive=false -> $url"
kubectl -n "$NS" exec "$client" -- $FORTIO load \
  -qps "$QPS" -c "$CONC" -t "$DURATION" \
  -keepalive=false -timeout 5s \
  -r "$RESOLUTION" -p "50,90,99,99.9" \
  -json - "$url" >"$out" 2>"$RAW_DIR/$tag.fortio.log" \
  || die "fortio failed, see $RAW_DIR/$tag.fortio.log"

stats=$(python3 - "$out" <<'PY'
import json, sys
txt = open(sys.argv[1], encoding="utf-8", errors="replace").read()
# stdout should be pure JSON; be tolerant of any text printed before it
idx = 0 if txt.startswith("{") else txt.find("\n{") + 1
try:
    d, _ = json.JSONDecoder().raw_decode(txt[idx:])
except Exception as e:
    sys.exit(f"cannot parse fortio JSON: {e}")
h = d["DurationHistogram"]
pct = {round(float(p["Percentile"]), 3): float(p["Value"]) for p in (h.get("Percentiles") or [])}
ms = lambda v: "nan" if v is None else f"{float(v) * 1000:.4f}"
count = int(h.get("Count", 0))
ok = int((d.get("RetCodes") or {}).get("200", 0))
print(",".join([
    ms(pct.get(50.0)), ms(pct.get(90.0)), ms(pct.get(99.0)), ms(pct.get(99.9)),
    ms(h.get("Avg")), ms(h.get("Max")),
    f'{float(d.get("ActualQPS", 0)):.1f}', str(count), str(count - ok),
]))
PY
)

header="timestamp,setup,n_services,run,rules,svc_entries,target_pos,p50_ms,p90_ms,p99_ms,p999_ms,avg_ms,max_ms,actual_qps,requests,errors,qps,conc,duration"
[[ -s $CSV ]] || echo "$header" >"$CSV"
echo "$(date -u +%FT%TZ),$SETUP,$N,$RUN,$rules,$svc_entries,$target_pos,$stats,$QPS,$CONC,$DURATION" >>"$CSV"

IFS=, read -r p50 p90 p99 _ avg _ aqps reqs errs <<<"$stats"
log "[$tag] p50=${p50}ms p90=${p90}ms p99=${p99}ms avg=${avg}ms qps=$aqps requests=$reqs errors=$errs"
if [[ $errs != 0 ]]; then warn "[$tag] $errs failed requests (check TIME_WAIT / ephemeral ports, lower QPS)"; fi
