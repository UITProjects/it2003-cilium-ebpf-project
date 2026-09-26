#!/usr/bin/env bash
# create-services.sh <N>
# Makes the number of fake Services (e1-svc-00001 .. e1-svc-NNNNN, label e1=fake) exactly N.
# Missing ones are created, extra ones deleted. N=0 removes them all.
# All fake Services select the 3 pause pods, so each one has real endpoints.
#
# Env: BATCH (Services per kubectl call, default 250), PARALLEL (parallel kubectl calls, default 8)
set -euo pipefail
DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=lib.sh
source "$DIR/scripts/lib.sh"

N=${1:?usage: create-services.sh <N>}
[[ $N =~ ^[0-9]+$ ]] || die "N must be a non-negative integer"
BATCH=${BATCH:-250}
PARALLEL=${PARALLEL:-8}
export LC_ALL=C

need kubectl
kubectl get ns "$NS" >/dev/null 2>&1 || die "namespace $NS not found (apply manifests/e1-bench.yaml first)"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

kubectl -n "$NS" get svc -l e1=fake \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sed '/^$/d' | sort >"$tmp/existing"
if (( N > 0 )); then
  for ((i = 1; i <= N; i++)); do printf 'e1-svc-%05d\n' "$i"; done | sort >"$tmp/desired"
else
  : >"$tmp/desired"
fi
comm -13 "$tmp/existing" "$tmp/desired" >"$tmp/create"
comm -23 "$tmp/existing" "$tmp/desired" >"$tmp/delete"

n_have=$(wc -l <"$tmp/existing" | tr -d ' ')
n_create=$(wc -l <"$tmp/create" | tr -d ' ')
n_delete=$(wc -l <"$tmp/delete" | tr -d ' ')
log "fake Services: have=$n_have target=$N -> create=$n_create delete=$n_delete"

if (( n_create > 0 )); then
  split -l "$BATCH" "$tmp/create" "$tmp/chunk."
  for chunk in "$tmp"/chunk.*; do
    while read -r name; do
      cat <<EOF
---
apiVersion: v1
kind: Service
metadata:
  name: $name
  namespace: $NS
  labels:
    e1: fake
spec:
  type: ClusterIP
  selector:
    app: e1-pause
  ports:
    - name: http
      port: 80
      targetPort: 8080
      protocol: TCP
EOF
    done <"$chunk" >"$chunk.yaml"
  done
  t0=$SECONDS
  printf '%s\n' "$tmp"/chunk.*.yaml \
    | xargs -P "$PARALLEL" -I{} kubectl create -f {} -o name >/dev/null
  log "created $n_create Services in $((SECONDS - t0))s"
fi

if (( n_delete > 0 )); then
  t0=$SECONDS
  xargs -P "$PARALLEL" -n 200 kubectl -n "$NS" delete svc --wait=false <"$tmp/delete" >/dev/null
  log "deleted $n_delete Services in $((SECONDS - t0))s"
fi

now=$(kubectl -n "$NS" get svc -l e1=fake --no-headers 2>/dev/null | wc -l | tr -d ' ')
log "fake Services now: $now"
