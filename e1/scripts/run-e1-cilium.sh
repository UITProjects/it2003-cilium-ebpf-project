#!/usr/bin/env bash
# run-e1.sh <iptables|cilium>
# Full E1 run for one setup: preflight -> deploy test apps -> for each size N:
# reach N fake Services, wait until the node's data plane is in sync, run measure.sh RUNS times.
#
# Env (defaults):
#   SIZES="10 100 500 1000 2000 5000"   RUNS=3        CSV=results/e1.csv
#   SETTLE=20   (s to wait after the data plane is stable)   COOLDOWN=10 (s between runs)
#   CLEANUP=0   (1 = delete fake Services at the end)        FORCE=0 (1 = ignore preflight errors)
#   SERVER_NODE / CLIENT_NODE / COUNT_VIA / QPS / CONC / DURATION ... see lib.sh and measure.sh
#
# Quick test:  CSV=results/quick.csv SIZES="10 100" RUNS=1 ./scripts/run-e1.sh iptables
set -euo pipefail
DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=lib.sh
source "$DIR/scripts/lib.sh"

SETUP=${1:?usage: run-e1.sh <iptables|cilium>}
case $SETUP in iptables|cilium) ;; *) die "setup must be iptables or cilium" ;; esac
SIZES=${SIZES:-"100 2080 4060 6040 8020 10000"}
RUNS=${RUNS:-3}
CSV=${CSV:-$DIR/results/e1.csv}
SETTLE=${SETTLE:-20}
COOLDOWN=${COOLDOWN:-10}
CLEANUP=${CLEANUP:-0}
FORCE=${FORCE:-0}
export NS SERVER_NODE CLIENT_NODE COUNT_VIA SSH_TARGET CSV
mkdir -p "$(dirname "$CSV")"
RESULTS=$(cd "$(dirname "$CSV")" && pwd)

fail() { if [[ $FORCE == 1 ]]; then warn "$* (FORCE=1, continuing)"; else die "$* (FORCE=1 to ignore)"; fi; }

# ------------------------------------------------------------------ preflight
need kubectl; need python3
kubectl get nodes >/dev/null || die "kubectl cannot reach the cluster"
for n in "$SERVER_NODE" "$CLIENT_NODE"; do
  kubectl get node "$n" >/dev/null 2>&1 || die "node $n not found (set SERVER_NODE / CLIENT_NODE)"
done
[[ $SERVER_NODE != "$CLIENT_NODE" ]] || die "SERVER_NODE and CLIENT_NODE must differ"
for n in $SIZES; do [[ $n =~ ^[0-9]+$ ]] || die "bad size '$n' in SIZES"; done
max_n=$(printf '%s\n' $SIZES | sort -n | tail -1)

n_kp=$(kubectl -n kube-system get pods -l k8s-app=kube-proxy --no-headers 2>/dev/null | wc -l | tr -d ' ')
n_ci=$(kubectl -n kube-system get pods -l k8s-app=cilium --no-headers 2>/dev/null | wc -l | tr -d ' ')
case $SETUP in
  iptables)
    (( n_kp > 0 )) || fail "Setup A needs kube-proxy, none found"
    (( n_ci == 0 )) || fail "cilium agents found - this looks like Setup B"
    n_ca=$(kubectl get pods -A -l k8s-app=calico-node --no-headers 2>/dev/null | wc -l | tr -d ' ')
    (( n_ca > 0 )) || warn "no calico-node pods found"
    mode=$(kubectl -n kube-system get cm kube-proxy -o jsonpath='{.data.config\.conf}' 2>/dev/null \
      | awk '/^mode:/ {print $2}' | tr -d "\"'" || true)
    log "kube-proxy mode: '${mode:-<empty> = iptables}'"
    if [[ -n $mode && $mode != iptables ]]; then
      fail "kube-proxy mode is '$mode', must be iptables (Kubespray defaults to ipvs: set kube_proxy_mode: iptables)"
    fi
    ;;
  cilium)
    (( n_ci > 0 )) || fail "Setup B needs Cilium, no agents found"
    (( n_kp == 0 )) || fail "kube-proxy is still running - Cilium must replace it"
    kpr=$( (cilium_dbg status 2>/dev/null | grep -i 'KubeProxyReplacement' | head -1) || true)
    log "cilium: ${kpr:-could not read KubeProxyReplacement}"
    [[ $kpr =~ True|Strict ]] || warn "KubeProxyReplacement does not look enabled"
    ;;
esac

# other workloads (anything outside system / CNI namespaces)
others=$(kubectl get pods -A --field-selector=status.phase=Running --no-headers 2>/dev/null \
  | awk -v ns="$NS" '$1 !~ /^(kube-system|kube-public|kube-node-lease|calico-system|calico-apiserver|tigera-operator|cilium|cilium-secrets|local-path-storage)$/ && $1 != ns {print $1"/"$2}' || true)
if [[ -n $others ]]; then
  warn "other workloads are running - stop them for clean numbers:"
  # shellcheck disable=SC2086
  printf '    %s\n' $others >&2
fi

# Service CIDR must fit max_n + existing Services
cidrs=$(kubectl get servicecidrs -o jsonpath='{.items[*].spec.cidrs[*]}' 2>/dev/null || true)
if [[ -z $cidrs ]]; then
  cidrs=$(kubectl -n kube-system get pod -l component=kube-apiserver \
    -o jsonpath='{.items[0].spec.containers[0].command}' 2>/dev/null \
    | grep -o 'service-cluster-ip-range=[^",]*' | head -1 | cut -d= -f2 | tr ',' ' ' || true)
fi
if [[ -n $cidrs ]]; then
  used=$(kubectl get svc -A --no-headers 2>/dev/null | wc -l | tr -d ' ')
  # shellcheck disable=SC2086
  if ! python3 - "$max_n" "$used" $cidrs <<'PY'
import ipaddress, sys
need = int(sys.argv[1]) + int(sys.argv[2]) + 50
nets = [ipaddress.ip_network(c, strict=False) for c in sys.argv[3:]]
v4 = [n for n in nets if n.version == 4]
cap = sum(n.num_addresses - 2 for n in (v4 or nets))
print(f"[preflight] service CIDR {' '.join(sys.argv[3:])}: {cap} IPs, need about {need}", file=sys.stderr)
sys.exit(0 if cap >= need else 3)
PY
  then fail "service CIDR too small for $max_n Services"; fi
else
  warn "could not detect the service CIDR - make sure it has room for $max_n Services"
fi

# environment record for the report
{
  echo "# setup=$SETUP  date=$(date -u +%FT%TZ)  server=$SERVER_NODE  client=$CLIENT_NODE"
  kubectl version 2>&1
  kubectl get nodes -o wide
  if [[ $SETUP == iptables ]]; then
    echo "## kube-proxy config"; kubectl -n kube-system get cm kube-proxy -o jsonpath='{.data.config\.conf}'; echo
    echo "## calico images"
    kubectl get ds -A -o jsonpath='{range .items[?(@.metadata.name=="calico-node")]}{..image}{"\n"}{end}' 2>/dev/null
  else
    echo "## cilium status"; cilium_dbg status --verbose 2>&1 | head -120
  fi
} >"$RESULTS/env-$SETUP.txt" 2>&1 || true
log "environment saved to $RESULTS/env-$SETUP.txt"

# ------------------------------------------------------------------ deploy test apps
log "deploying test apps (server on $SERVER_NODE, client on $CLIENT_NODE)"
sed -e 's/it-2003-ubuntu2404-1/@@SERVER@@/g' -e 's/it-2003-ubuntu2404-2/@@CLIENT@@/g' \
    -e "s/@@SERVER@@/$SERVER_NODE/g" -e "s/@@CLIENT@@/$CLIENT_NODE/g" \
    "$DIR/manifests/e1-bench.yaml" | kubectl apply -f - >/dev/null
for d in e1-pause fortio-server fortio-client; do
  kubectl -n "$NS" rollout status "deploy/$d" --timeout=300s >/dev/null || die "deployment $d not ready"
done
[[ -n $(pod_on_node "$NS" app=fortio-server "$SERVER_NODE") ]] || die "fortio-server is not on $SERVER_NODE"
client=$(pod_on_node "$NS" app=fortio-client "$CLIENT_NODE")
[[ -n $client ]] || die "fortio-client is not on $CLIENT_NODE"
ip=$(kubectl -n "$NS" get svc fortio-server -o jsonpath='{.spec.clusterIP}')
kubectl -n "$NS" exec "$client" -- $FORTIO curl "http://$ip:8080/" >/dev/null 2>&1 \
  || die "client cannot reach fortio-server at $ip:8080"
log "sanity check OK: client -> $ip:8080"

# ------------------------------------------------------------------ main loop
steps=$(wc -w <<<"$SIZES" | tr -d ' ')
log "setup=$SETUP sizes=[$SIZES] runs=$RUNS csv=$CSV"
t_all=$SECONDS
i=0
for N in $SIZES; do
  i=$((i + 1))
  log "=== step $i/$steps: N=$N Services ==="
  "$DIR/scripts/create-services.sh" "$N"
  wait_endpoints "$N"
  wait_dataplane "$SETUP" "$N"
  log "  settling ${SETTLE}s"
  sleep "$SETTLE"
  for ((r = 1; r <= RUNS; r++)); do
    "$DIR/scripts/measure.sh" "$SETUP" "$N" "$r" "$CSV"
    if (( r < RUNS )); then sleep "$COOLDOWN"; fi
  done
done

if [[ $CLEANUP == 1 ]]; then
  log "cleanup: removing fake Services"
  "$DIR/scripts/create-services.sh" 0
fi
log "done in $(( (SECONDS - t_all) / 60 )) min. Results: $CSV (raw files in $RESULTS/raw)"
log "next: python3 scripts/plot_e1.py $CSV ${CSV%.csv}.png"
