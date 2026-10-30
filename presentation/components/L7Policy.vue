<script setup lang="ts">
// E2 L7 case: dvwa-l7-api-policy (rules.http on TCP 80). The eBPF datapath admits
// the L3/L4 flow and redirects it to the node's Envoy proxy, which matches HTTP
// method + path. GET paths in the allowlist reach DVWA; GET to API v1 is not in
// the allowlist and is rejected (browser: "Access denied", Hubble: http-request DROPPED).
</script>

<template>
  <svg class="l7" viewBox="0 0 640 236">
    <defs>
      <marker id="l7-ok" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#16a34a" /></marker>
      <marker id="l7-no" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#dc2626" /></marker>
      <marker id="l7-in" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#374151" /></marker>
    </defs>

    <!-- client on the VPN (world identity) -->
    <rect x="2" y="92" width="126" height="52" rx="7" class="ext" />
    <text x="65" y="114" class="t-b" text-anchor="middle">client</text>
    <text x="65" y="131" class="t-xs mono" text-anchor="middle">10.8.0.10 (world)</text>
    <path d="M128,118 H148" class="edge in" marker-end="url(#l7-in)" />

    <!-- Cilium on the DVWA node: eBPF datapath + Envoy -->
    <rect x="148" y="52" width="326" height="132" rx="10" class="ns" />
    <text x="160" y="70" class="t-xs mono muted">Cilium · DVWA node</text>

    <rect x="160" y="84" width="132" height="68" rx="7" class="ebpf" />
    <text x="226" y="105" class="t-b" text-anchor="middle">eBPF datapath</text>
    <text x="226" y="122" class="t-xs" text-anchor="middle">L3/L4: TCP 80 ✓</text>
    <text x="226" y="138" class="t-xs" text-anchor="middle">redirect → proxy</text>
    <path d="M292,118 H326" class="edge ok" marker-end="url(#l7-ok)" />

    <rect x="328" y="84" width="134" height="68" rx="7" class="ebpf" />
    <text x="395" y="105" class="t-b" text-anchor="middle">Envoy (L7)</text>
    <text x="395" y="122" class="t-xs" text-anchor="middle">match HTTP</text>
    <text x="395" y="138" class="t-xs" text-anchor="middle">method + path</text>

    <text x="311" y="174" class="t-xs muted" text-anchor="middle">Hubble: flow + HTTP method/path + verdict</text>

    <!-- allowed: GET allowlist → DVWA pod -->
    <path d="M462,104 C486,104 480,48 500,48" class="edge ok" marker-end="url(#l7-ok)" />
    <rect x="502" y="24" width="136" height="48" rx="7" class="ext" />
    <text x="570" y="45" class="t-b" text-anchor="middle">DVWA pod</text>
    <text x="570" y="62" class="t-xs mono" text-anchor="middle">app=dvwa :80</text>
    <text x="634" y="14" class="t-xs mono ok-t" text-anchor="end">GET allowlist: UI · assets · API v2</text>

    <!-- denied: GET API v1 is not in the allowlist -->
    <path d="M462,132 C486,132 480,188 500,188" class="edge no" marker-end="url(#l7-no)" />
    <g class="barrier"><circle cx="476" cy="160" r="10" /><text x="476" y="164" text-anchor="middle">✕</text></g>
    <rect x="502" y="164" width="136" height="48" rx="7" class="deny" />
    <text x="570" y="185" class="t-b no-t" text-anchor="middle">Access denied</text>
    <text x="570" y="202" class="t-xxs mono" text-anchor="middle">http-request DROPPED</text>
    <text x="634" y="229" class="t-xs mono no-t" text-anchor="end">GET /vulnerabilities/api/v1/user/</text>
  </svg>

  <div class="l7-legend">
    <span class="i"><i class="ln ok"></i> Allowed by policy</span>
    <span class="i"><i class="ln no"></i> Denied by L7 rule</span>
    <span class="i"><i class="bx ebpf"></i> Cilium (eBPF + Envoy)</span>
    <span class="i"><i class="bx ext"></i> Endpoint</span>
  </div>
</template>

<style scoped>
.l7 { width: 100%; height: auto; display: block; margin: 0 auto; max-height: 185px; }
.ns { fill: #fcfdfc; stroke: #cbd5e1; stroke-dasharray: 5 4; }
.ext  { fill: #e8eefc; stroke: #374151; stroke-width: 1.2; }
.ebpf { fill: #dcf5dc; stroke: #16a34a; stroke-width: 1.4; }
.deny { fill: #ffd0d0; stroke: #dc2626; stroke-width: 1.6; }
.edge { fill: none; stroke-width: 2.2; }
.edge.in { stroke: #374151; }
.edge.ok { stroke: #16a34a; }
.edge.no { stroke: #dc2626; stroke-dasharray: 6 4; }
.barrier circle { fill: #fff; stroke: #dc2626; stroke-width: 1.6; }
.barrier text { fill: #dc2626; font-size: 11px; font-weight: 700; }
text { fill: #1f2937; }
.t-b { font-size: 13px; font-weight: 700; }
.t-xs { font-size: 11px; }
.t-xxs { font-size: 10px; }
.ok-t { fill: #15803d; font-weight: 700; }
.no-t { fill: #dc2626; font-weight: 700; }
.mono { font-family: var(--slidev-code-font-family, monospace); }
.muted { fill: #6b7280; }

.l7-legend { display: flex; justify-content: center; flex-wrap: wrap; gap: 1.3rem; font-size: 0.8rem; margin-top: 0.4rem; }
.l7-legend .i { display: inline-flex; align-items: center; gap: 0.4rem; }
.l7-legend .ln { width: 22px; height: 0; border-top: 3px solid; display: inline-block; }
.l7-legend .ln.ok { border-color: #16a34a; }
.l7-legend .ln.no { border-color: #dc2626; border-top-style: dashed; }
.l7-legend .bx { width: 13px; height: 13px; border-radius: 3px; border: 1px solid; display: inline-block; }
.l7-legend .bx.ebpf { background: #dcf5dc; border-color: #16a34a; }
.l7-legend .bx.ext { background: #e8eefc; border-color: #374151; }
</style>
