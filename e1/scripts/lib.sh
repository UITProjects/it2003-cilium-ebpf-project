#!/usr/bin/env bash
# Shared helpers for E1. Sourced by the other scripts; not meant to be run directly.

NS=${NS:-e1-bench}
SERVER_NODE=${SERVER_NODE:-it-2003-ubuntu2404-1}
CLIENT_NODE=${CLIENT_NODE:-it-2003-ubuntu2404-2}
PAUSE_REPLICAS=${PAUSE_REPLICAS:-3}
# How to read iptables on CLIENT_NODE:
#   pod = kubectl exec into the kube-proxy pod on that node (default, no ssh needed)
#   ssh = ssh "$SSH_TARGET" 'sudo iptables-save -t nat'
COUNT_VIA=${COUNT_VIA:-pod}
SSH_TARGET=${SSH_TARGET:-$CLIENT_NODE}
# shellcheck disable=SC2034  # used by the scripts that source this file
FORTIO=/usr/bin/fortio   # the fortio image has no shell, so call the binary by full path

log()  { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*" >&2; }
warn() { log "WARN: $*"; }
die()  { log "ERROR: $*"; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "'$1' not found in PATH"; }

# pod_on_node <namespace> <label-selector> <node>  -> prints pod name (or nothing)
pod_on_node() {
  kubectl -n "$1" get pod -l "$2" \
    --field-selector "spec.nodeName=$3,status.phase=Running" \
    -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true
}

# ---------------------------------------------------------------- data plane access

# dump_nat <outfile> : iptables-save -t nat as seen on CLIENT_NODE
dump_nat() {
  local out=$1 p
  if [[ $COUNT_VIA == ssh ]]; then
    ssh -o BatchMode=yes "$SSH_TARGET" 'sudo iptables-save -t nat' >"$out"
    return
  fi
  p=$(pod_on_node kube-system k8s-app=kube-proxy "$CLIENT_NODE")
  [[ -n $p ]] || die "no running kube-proxy pod on $CLIENT_NODE (try COUNT_VIA=ssh)"
  kubectl -n kube-system exec "$p" -- iptables-save -t nat >"$out"
}

# cilium_dbg <args...> : run cilium-dbg (or the older 'cilium' CLI) in the agent on CLIENT_NODE
cilium_dbg() {
  local p
  p=$(pod_on_node kube-system k8s-app=cilium "$CLIENT_NODE")
  [[ -n $p ]] || die "no running cilium agent pod on $CLIENT_NODE"
  kubectl -n kube-system exec "$p" -c cilium-agent -- sh -c \
    'if command -v cilium-dbg >/dev/null 2>&1; then exec cilium-dbg "$@"; else exec cilium "$@"; fi' _ "$@"
}

# count_dataplane <setup> [gz-file-to-keep-the-dump]
# prints: "<rules> <svc_entries> <target_pos>"
#   iptables: rules       = all '-A' rules in the nat table
#             svc_entries = rules in the KUBE-SERVICES chain (the list scanned linearly per new conn)
#             target_pos  = position of fortio-server's rule inside KUBE-SERVICES (1 = first)
#   cilium:   rules       = rows in 'bpf lb list' (1 frontend row + 1 row per backend)
#             svc_entries = distinct frontends (≈ Services x ports)
#             target_pos  = NA (hash lookup, position is meaningless)
count_dataplane() {
  local setup=$1 keep=${2:-} tmp rules=0 ks=0 pos=NA
  tmp=$(mktemp)
  case $setup in
    iptables)
      dump_nat "$tmp"
      rules=$(grep -c '^-A ' "$tmp" || true)
      ks=$(grep -c '^-A KUBE-SERVICES ' "$tmp" || true)
      pos=$( (grep '^-A KUBE-SERVICES ' "$tmp" | grep -n -F -- "$NS/fortio-server" | head -n1 | cut -d: -f1) || true)
      ;;
    cilium)
      cilium_dbg bpf lb list >"$tmp"
      rules=$(awk 'NR>1 && NF>0 {c++} END {print c+0}' "$tmp")
      ks=$(awk 'NR>1 && NF>0 && !seen[$1]++ {c++} END {print c+0}' "$tmp")
      pos=NA
      ;;
    *) die "unknown setup '$setup'" ;;
  esac
  if [[ -n $keep ]]; then gzip -c "$tmp" >"$keep"; fi
  rm -f "$tmp"
  echo "${rules:-0} ${ks:-0} ${pos:-NA}"
}

# ---------------------------------------------------------------- waiting helpers

# wait_endpoints <N> : until N fake Services have EndpointSlices with all pause backends
wait_endpoints() {
  local want=$1 timeout=${2:-1200} t0=$SECONDS have
  [[ $want -gt 0 ]] || return 0
  while :; do
    have=$(kubectl -n "$NS" get endpointslices \
      -o jsonpath='{range .items[*]}{.metadata.labels.kubernetes\.io/service-name}{" "}{.endpoints[*].addresses[0]}{"\n"}{end}' \
      | awk -v need=$((1 + PAUSE_REPLICAS)) '$1 ~ /^e1-svc-/ && NF >= need && !seen[$1]++ {c++} END {print c+0}')
    if (( have >= want )); then
      log "  endpointslices ready: $have/$want"
      return 0
    fi
    if (( SECONDS - t0 > timeout )); then
      die "timeout: only $have/$want Services have $PAUSE_REPLICAS endpoints"
    fi
    log "  waiting for endpointslices: $have/$want"
    sleep 5
  done
}

# wait_dataplane <setup> <N> : until the node's data plane holds >= N services and stops changing
wait_dataplane() {
  local setup=$1 want=$2 timeout=${3:-1200} t0=$SECONDS prev=-1 stable=0 r ks pos
  while :; do
    read -r r ks pos < <(count_dataplane "$setup")
    if (( ks >= want )) && [[ $ks == "$prev" ]]; then
      stable=$((stable + 1))
    else
      stable=0
    fi
    prev=$ks
    if (( stable >= 2 )); then
      log "  data plane stable: rules=$r svc_entries=$ks target_pos=$pos"
      return 0
    fi
    if (( SECONDS - t0 > timeout )); then
      die "timeout waiting for data plane (svc_entries=$ks, want >= $want). If iptables shows 0, the pod may use a different iptables backend (legacy vs nft) -> try COUNT_VIA=ssh"
    fi
    log "  waiting for data plane: rules=$r svc_entries=$ks (want >= $want, stable $stable/2)"
    sleep 5
  done
}
