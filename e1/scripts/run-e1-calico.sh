#!/usr/bin/env bash
# run-e1-calico.sh
# Full E1 run for Setup A (Calico + kube-proxy iptables) on the Calico cluster:
# preflight -> auto-detect nodes -> deploy test apps (pinned) -> for each size N:
# reach N fake Services, wait until the node's data plane is in sync, run measure.sh RUNS times.
#
# Always targets the Calico cluster, whatever your current kubectl context is:
# it writes a temporary kubeconfig for KUBE_CONTEXT and exports KUBECONFIG, so lib.sh,
# create-services.sh and measure.sh all talk to the same cluster.
#
# Node selection (automatic):
#   Candidates = Ready, schedulable nodes that are not control-plane and have no
#   NoSchedule/NoExecute taints, sorted by name. SERVER_NODE = 1st, CLIENT_NODE = 2nd.
#   Set SERVER_NODE and CLIENT_NODE yourself to override (both must be set).
#   SSH_TARGET defaults to the CLIENT node's InternalIP (the node whose rules are counted).
#
# Placement: e1-bench.yaml only has podAntiAffinity, so the script injects a hard
#   nodeSelector (kubernetes.io/hostname) into fortio-server / fortio-client before applying.
#   The rendered manifest is saved to results/e1-bench-<setup>.rendered.yaml.
#
# Env (defaults):
#   KUBE_CONTEXT=it2003@calico
#   SERVER_NODE / CLIENT_NODE = auto     SSH_TARGET = auto (client InternalIP)
#   SIZES="100 2080 4060 6040 8020 10000"   RUNS=3        CSV=results/e1.csv
#   SETTLE=20   (s to wait after the data plane is stable)   COOLDOWN=10 (s between runs)
#   CLEANUP=0   (1 = delete fake Services at the end)        FORCE=0 (1 = ignore preflight errors)
#   PLACEMENT_TIMEOUT=120 (s to wait for test pods to be Running on the pinned nodes)
#   COUNT_VIA / QPS / CONC / DURATION ... see lib.sh and measure.sh
#
# Quick test:  CSV=results/quick.csv SIZES="10 100" RUNS=1 ./scripts/run-e1-calico.sh
set -euo pipefail
DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SETUP=iptables
MANIFEST=$DIR/manifests/e1-bench.yaml

_msg() { echo "[$(date +%T)] $*" >&2; }
_die() { echo "[$(date +%T)] ERROR: $*" >&2; exit 1; }
command -v kubectl >/dev/null || _die "kubectl not found"
command -v python3 >/dev/null || _die "python3 not found"

# ------------------------------------------------------------------ Calico cluster context
KUBE_CONTEXT=${KUBE_CONTEXT:-it2003@calico}
kubectl config get-contexts "$KUBE_CONTEXT" >/dev/null 2>&1 \
  || _die "kubectl context '$KUBE_CONTEXT' not found"
KCFG=$(mktemp "${TMPDIR:-/tmp}/kubeconfig-e1-calico.XXXXXX")   # mode 600
trap 'rm -f "$KCFG"' EXIT
kubectl config view --minify --flatten --context "$KUBE_CONTEXT" >"$KCFG"
export KUBECONFIG=$KCFG
kubectl get nodes >/dev/null || _die "kubectl cannot reach the cluster ($KUBE_CONTEXT)"

# ------------------------------------------------------------------ auto-detect nodes
# Done before sourcing lib.sh so its ${VAR:-default} values do not point at the Cilium nodes.
# One line per node: "<name> <internal-ip> <ok|skip> <reason>"
NODE_TABLE=$(kubectl get nodes -o json | python3 -c '
import json, sys
for n in sorted(json.load(sys.stdin)["items"], key=lambda n: n["metadata"]["name"]):
    name = n["metadata"]["name"]
    labels = n["metadata"].get("labels", {})
    spec, st = n.get("spec", {}), n.get("status", {})
    ip = next((a["address"] for a in st.get("addresses", []) if a["type"] == "InternalIP"), "-")
    why = []
    if not any(c["type"] == "Ready" and c["status"] == "True" for c in st.get("conditions", [])):
        why.append("not-ready")
    if spec.get("unschedulable"):
        why.append("cordoned")
    if "node-role.kubernetes.io/control-plane" in labels or "node-role.kubernetes.io/master" in labels:
        why.append("control-plane")
    t = [x["key"] for x in spec.get("taints", []) if x.get("effect") in ("NoSchedule", "NoExecute")]
    if t:
        why.append("taints:" + ",".join(t))
    print(name, ip, "skip" if why else "ok", ";".join(why) or "-")
')
_msg "nodes:"
while read -r n a s w; do printf '    %-28s %-16s %-4s %s\n' "$n" "$a" "$s" "$w" >&2; done <<<"$NODE_TABLE"

node_field() { awk -v n="$1" -v f="$2" '$1 == n {print $f}' <<<"$NODE_TABLE"; }
mapfile -t CANDIDATES < <(awk '$3 == "ok" {print $1}' <<<"$NODE_TABLE")

if [[ -n ${SERVER_NODE:-} || -n ${CLIENT_NODE:-} ]]; then
  [[ -n ${SERVER_NODE:-} && -n ${CLIENT_NODE:-} ]] || _die "set both SERVER_NODE and CLIENT_NODE, or neither"
  for n in "$SERVER_NODE" "$CLIENT_NODE"; do
    [[ -n $(node_field "$n" 1) ]] || _die "node $n not found"
    [[ $(node_field "$n" 3) == ok ]] || _msg "WARN: node $n is not a clean candidate ($(node_field "$n" 4))"
  done
  _msg "using nodes from env: server=$SERVER_NODE client=$CLIENT_NODE"
else
  (( ${#CANDIDATES[@]} >= 2 )) \
    || _die "need 2 schedulable worker nodes, found ${#CANDIDATES[@]} (${CANDIDATES[*]:-none}); set SERVER_NODE/CLIENT_NODE"
  SERVER_NODE=${CANDIDATES[0]}
  CLIENT_NODE=${CANDIDATES[1]}
  _msg "auto-detected nodes: server=$SERVER_NODE client=$CLIENT_NODE"
fi
[[ $SERVER_NODE != "$CLIENT_NODE" ]] || _die "SERVER_NODE and CLIENT_NODE must differ"
SSH_TARGET=${SSH_TARGET:-$(node_field "$CLIENT_NODE" 2)}
[[ -n $SSH_TARGET && $SSH_TARGET != - ]] || _die "could not find InternalIP of $CLIENT_NODE; set SSH_TARGET"
_msg "SSH_TARGET=$SSH_TARGET (rules counted on $CLIENT_NODE)"
export KUBE_CONTEXT SERVER_NODE CLIENT_NODE SSH_TARGET

# shellcheck source=lib.sh
source "$DIR/scripts/lib.sh"

SIZES=${SIZES:-"100 2080 4060 6040 8020 10000"}
RUNS=${RUNS:-3}
CSV=${CSV:-$DIR/results/e1.csv}
SETTLE=${SETTLE:-20}
COOLDOWN=${COOLDOWN:-10}
CLEANUP=${CLEANUP:-0}
FORCE=${FORCE:-0}
PLACEMENT_TIMEOUT=${PLACEMENT_TIMEOUT:-120}
export NS SERVER_NODE CLIENT_NODE COUNT_VIA SSH_TARGET CSV
mkdir -p "$(dirname "$CSV")"
RESULTS=$(cd "$(dirname "$CSV")" && pwd)

fail() { if [[ $FORCE == 1 ]]; then warn "$* (FORCE=1, continuing)"; else die "$* (FORCE=1 to ignore)"; fi; }

# ------------------------------------------------------------------ preflight
log "context: $KUBE_CONTEXT"
[[ $NS == e1-bench ]] || fail "NS is '$NS' but e1-bench.yaml hardcodes namespace e1-bench"
for n in $SIZES; do [[ $n =~ ^[0-9]+$ ]] || die "bad size '$n' in SIZES"; done
max_n=$(printf '%s\n' $SIZES | sort -n | tail -1)

# kube-proxy must be running, in iptables mode
n_kp=$(kubectl -n kube-system get pods -l k8s-app=kube-proxy --no-headers 2>/dev/null | wc -l | tr -d ' ')
n_ci=$(kubectl -n kube-system get pods -l k8s-app=cilium --no-headers 2>/dev/null | wc -l | tr -d ' ')
(( n_kp > 0 )) || fail "Setup A needs kube-proxy, none found"
(( n_ci == 0 )) || fail "cilium agents found - this looks like Setup B"
mode=$(kubectl -n kube-system get cm kube-proxy -o jsonpath='{.data.config\.conf}' 2>/dev/null \
  | awk '/^mode:/ {print $2}' | tr -d "\"'" || true)
log "kube-proxy mode: '${mode:-<empty> = iptables}'"
if [[ -n $mode && $mode != iptables ]]; then
  fail "kube-proxy mode is '$mode', must be iptables (Kubespray defaults to ipvs: set kube_proxy_mode: iptables)"
fi

# Calico must be running, with the iptables dataplane (not BPF / nftables)
n_ca=$(kubectl get pods -A -l k8s-app=calico-node --no-headers 2>/dev/null | wc -l | tr -d ' ')
(( n_ca > 0 )) || fail "no calico-node pods found"
dp=$(kubectl get installation default -o jsonpath='{.spec.calicoNetwork.linuxDataplane}' 2>/dev/null || true)
if [[ -n $dp ]]; then
  log "calico dataplane (operator): $dp"
  [[ $dp == Iptables ]] || fail "Calico dataplane is '$dp', must be Iptables"
else
  # manifest install (no operator): check FelixConfiguration instead
  bpf=$(kubectl get felixconfigurations default -o jsonpath='{.spec.bpfEnabled}' 2>/dev/null || true)
  log "calico dataplane: no Installation CR; felix bpfEnabled='${bpf:-<unset>}'"
  [[ $bpf != true ]] || fail "Calico eBPF dataplane is enabled (felix bpfEnabled=true)"
fi

# other workloads (anything outside system / CNI namespaces)
others=$(kubectl get pods -A --field-selector=status.phase=Running --no-headers 2>/dev/null \
  | awk -v ns="$NS" '$1 !~ /^(kube-system|kube-public|kube-node-lease|calico-system|calico-apiserver|tigera-operator|local-path-storage)$/ && $1 != ns {print $1"/"$2}' || true)
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
  echo "# setup=$SETUP  context=$KUBE_CONTEXT  date=$(date -u +%FT%TZ)  server=$SERVER_NODE  client=$CLIENT_NODE  ssh_target=$SSH_TARGET"
  kubectl version 2>&1
  kubectl get nodes -o wide
  echo "## kube-proxy config"; kubectl -n kube-system get cm kube-proxy -o jsonpath='{.data.config\.conf}'; echo
  echo "## calico images"
  kubectl get ds -A -o jsonpath='{range .items[?(@.metadata.name=="calico-node")]}{..image}{"\n"}{end}' 2>/dev/null
  echo "## calico installation (operator)"
  kubectl get installation default -o jsonpath='{.spec.calicoNetwork}' 2>/dev/null; echo
  echo "## felix configuration"
  kubectl get felixconfigurations default -o yaml 2>/dev/null
  echo "## ip pools"
  kubectl get ippools.crd.projectcalico.org -o wide 2>/dev/null
} >"$RESULTS/env-$SETUP.txt" 2>&1 || true
log "environment saved to $RESULTS/env-$SETUP.txt"

# ------------------------------------------------------------------ deploy test apps
log "deploying test apps (server on $SERVER_NODE, client on $CLIENT_NODE)"

# Inject a hard nodeSelector into the fortio pod templates (the manifest only has anti-affinity).
rendered=$(python3 - "$MANIFEST" "$SERVER_NODE" "$CLIENT_NODE" <<'PY'
import re, sys
path, server, client = sys.argv[1:4]
pins = {"fortio-server": server, "fortio-client": client}
docs = open(path).read().split("\n---")
done = set()
for i, d in enumerate(docs):
    if not re.search(r"^kind:\s*Deployment\s*$", d, re.M):
        continue
    m = re.search(r"^  name:\s*(\S+)\s*$", d, re.M)
    name = m.group(1) if m else None
    if name not in pins:
        continue
    if "nodeSelector:" in d:
        sys.exit(f"deploy/{name} already has a nodeSelector in the manifest; remove it")
    sel = f"      nodeSelector:\n        kubernetes.io/hostname: {pins[name]}\n"
    new, n = re.subn(r"^(    spec:\n)", lambda mm: mm.group(1) + sel, d, count=1, flags=re.M)
    if n != 1:
        sys.exit(f"could not find the pod template spec of deploy/{name}")
    docs[i] = new
    done.add(name)
missing = sorted(set(pins) - done)
if missing:
    sys.exit("deployments not found in manifest: " + ", ".join(missing))
sys.stdout.write("\n---".join(docs))
PY
) || die "could not render $MANIFEST"
printf '%s\n' "$rendered" >"$RESULTS/e1-bench-$SETUP.rendered.yaml"

# Delete old fortio Deployments first. With required anti-affinity + new node pins, a rolling
# update can deadlock (new server waits for old client to leave its node, and vice versa).
kubectl -n "$NS" delete deploy fortio-server fortio-client --ignore-not-found --wait=true >/dev/null 2>&1 || true
kubectl -n "$NS" wait --for=delete pod -l role=e1-fortio --timeout=120s >/dev/null 2>&1 || true

kubectl apply -f - <<<"$rendered" >/dev/null
kubectl -n "$NS" rollout restart deploy/e1-pause >/dev/null   # fresh, evenly spread endpoints
for d in e1-pause fortio-server fortio-client; do
  kubectl -n "$NS" rollout status "deploy/$d" --timeout=300s >/dev/null || {
    kubectl -n "$NS" get pods -o wide >&2 || true
    die "deployment $d not ready"
  }
done

# Wait until a Running pod with the label is on the expected node; show placement on failure.
wait_on_node() {  # label node
  local label=$1 node=$2 p deadline=$((SECONDS + PLACEMENT_TIMEOUT))
  while (( SECONDS < deadline )); do
    p=$(pod_on_node "$NS" "$label" "$node" || true)
    if [[ -n $p ]]; then echo "$p"; return 0; fi
    sleep 2
  done
  warn "no Running pod '$label' on $node after ${PLACEMENT_TIMEOUT}s; actual placement:"
  kubectl -n "$NS" get pods -l "$label" -o wide >&2 || true
  return 1
}

wait_on_node app=fortio-server "$SERVER_NODE" >/dev/null || die "fortio-server is not on $SERVER_NODE"
client=$(wait_on_node app=fortio-client "$CLIENT_NODE") || die "fortio-client is not on $CLIENT_NODE"
log "placement OK: fortio-server@$SERVER_NODE fortio-client@$CLIENT_NODE ($client)"

ip=$(kubectl -n "$NS" get svc fortio-server -o jsonpath='{.spec.clusterIP}')
ok=0
for _ in $(seq 15); do
  if kubectl -n "$NS" exec "$client" -- $FORTIO curl "http://$ip:8080/" >/dev/null 2>&1; then ok=1; break; fi
  sleep 2
done
(( ok == 1 )) || die "client cannot reach fortio-server at $ip:8080"
log "sanity check OK: client -> $ip:8080"

# ------------------------------------------------------------------ main loop
steps=$(wc -w <<<"$SIZES" | tr -d ' ')
log "setup=$SETUP context=$KUBE_CONTEXT sizes=[$SIZES] runs=$RUNS csv=$CSV"
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