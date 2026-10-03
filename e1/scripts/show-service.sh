#!/usr/bin/env bash
# show-service.sh <iptables|cilium> [service-name]
# For the demo screenshots: prints how ONE Service is represented on CLIENT_NODE.
#   iptables: its line in KUBE-SERVICES -> KUBE-SVC-* chain -> KUBE-SEP-* chains (DNAT)
#   cilium:   its frontend + backend rows in the eBPF LB map
# Default service: e1-svc-00001 (3 backends), falls back to fortio-server.
set -euo pipefail
DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=lib.sh
source "$DIR/scripts/lib.sh"

SETUP=${1:?usage: show-service.sh <iptables|cilium> [service-name]}
SVC=${2:-}
if [[ -z $SVC ]]; then
  if kubectl -n "$NS" get svc e1-svc-00001 >/dev/null 2>&1; then SVC=e1-svc-00001; else SVC=fortio-server; fi
fi
ip=$(kubectl -n "$NS" get svc "$SVC" -o jsonpath='{.spec.clusterIP}')
[[ -n $ip ]] || die "Service $NS/$SVC not found"
port=$(kubectl -n "$NS" get svc "$SVC" -o jsonpath='{.spec.ports[0].port}')
n_fake=$(kubectl -n "$NS" get svc -l e1=fake --no-headers 2>/dev/null | wc -l | tr -d ' ')

bold() { printf '\n\033[1m%s\033[0m\n' "$*"; }
bold "Service $NS/$SVC  ClusterIP=$ip:$port  (node $CLIENT_NODE, fake Services in cluster: $n_fake)"
kubectl -n "$NS" get endpointslices -l "kubernetes.io/service-name=$SVC" -o wide

tmp=$(mktemp); trap 'rm -f "$tmp"' EXIT
case $SETUP in
  iptables)
    dump_nat "$tmp"
    bold "1) KUBE-SERVICES entry (matched by linear scan, one rule per Service)"
    grep '^-A KUBE-SERVICES ' "$tmp" | grep -F -- "-d $ip/32" || echo "(not found)"
    svc_chain=$( (grep '^-A KUBE-SERVICES ' "$tmp" | grep -F -- "-d $ip/32" | grep -o 'KUBE-SVC-[A-Z0-9]*' | head -1) || true)
    if [[ -n $svc_chain ]]; then
      bold "2) $svc_chain (load-balancing by random probability)"
      grep -- "^-A $svc_chain " "$tmp"
      n_own=$( (grep '^-A KUBE-SERVICES ' "$tmp" | grep -cF -- "-d $ip/32") || true)
      n_own=$((n_own + $(grep -c -- "^-A $svc_chain " "$tmp")))
      for sep in $(grep -- "^-A $svc_chain " "$tmp" | grep -o 'KUBE-SEP-[A-Z0-9]*' | sort -u); do
        bold "3) $sep (DNAT to one backend)"
        grep -- "^-A $sep " "$tmp"
        n_own=$((n_own + $(grep -c -- "^-A $sep " "$tmp")))
      done
      bold "Rules for this one Service: $n_own"
    fi
    bold "Whole nat table on this node"
    echo "total rules (-A):      $(grep -c '^-A ' "$tmp")"
    echo "KUBE-SERVICES rules:   $(grep -c '^-A KUBE-SERVICES ' "$tmp")   <- scanned one by one for every new connection"
    pos=$( (grep '^-A KUBE-SERVICES ' "$tmp" | grep -n -F -- "-d $ip/32" | head -1 | cut -d: -f1) || true)
    echo "position of $SVC:      ${pos:-?}"
    ;;
  cilium)
    bold "1) cilium-dbg service list (frontend -> backends)"
    cilium_dbg service list | awk -v ip="$ip:" 'NR==1 || index($0, ip)'
    bold "2) cilium-dbg bpf lb list (the eBPF hash map rows for this Service)"
    cilium_dbg bpf lb list >"$tmp"
    awk -v ip="$ip:" 'NR==1 || index($1, ip) == 1' "$tmp"
    bold "Whole eBPF LB map on this node"
    echo "rows (frontends + backends): $(awk 'NR>1 && NF>0 {c++} END {print c+0}' "$tmp")"
    echo "distinct frontends:          $(awk 'NR>1 && NF>0 && !seen[$1]++ {c++} END {print c+0}' "$tmp")   <- looked up by hash key (IP, port, proto), not scanned"
    ;;
  *) die "setup must be iptables or cilium" ;;
esac
