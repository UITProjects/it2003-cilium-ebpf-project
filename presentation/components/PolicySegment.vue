<script setup lang="ts">
// E2 microsegmentation: a compromised `frontend` is contained by least-privilege
// CiliumNetworkPolicy. Allowed hops flow green; the two direct shortcuts to the
// sensitive services are denied by default (red dashed, stopped at a barrier).
// The compromised `frontend` node pulses gently (see .entry) to draw the eye.
</script>

<template>
  <svg class="ps" viewBox="0 0 640 300">
    <defs>
      <marker id="ps-ok" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#16a34a" /></marker>
      <marker id="ps-no" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#dc2626" /></marker>
    </defs>

    <!-- namespace: default-deny scope -->
    <rect x="8" y="30" width="624" height="210" rx="10" class="ns" />
    <text x="20" y="50" class="t-xs mono muted">microservices-google-demo · default deny ingress + egress</text>

    <!-- frontend: compromised entry -->
    <rect x="248" y="64" width="144" height="46" rx="7" class="entry" />
    <text x="320" y="84" class="t-b" text-anchor="middle">frontend</text>
    <text x="320" y="101" class="t-xs" text-anchor="middle">⚠ bị chiếm quyền</text>

    <!-- left allowed chain: frontend → cartservice → redis-cart -->
    <path d="M300,110 V140 H120 V162" class="edge ok" marker-end="url(#ps-ok)" />
    <rect x="52" y="162" width="136" height="42" rx="7" class="ok" />
    <text x="120" y="188" class="t-b" text-anchor="middle">cartservice</text>
    <path d="M120,204 V224" class="edge ok" marker-end="url(#ps-ok)" />
    <text x="150" y="219" class="t-xs mono muted">:6379</text>
    <rect x="62" y="224" width="116" height="40" rx="7" class="sens" />
    <text x="120" y="249" class="t-b" text-anchor="middle">redis-cart</text>

    <!-- right allowed chain: frontend → checkoutservice → paymentservice -->
    <path d="M340,110 V140 H520 V162" class="edge ok" marker-end="url(#ps-ok)" />
    <rect x="446" y="162" width="148" height="42" rx="7" class="ok" />
    <text x="520" y="188" class="t-b" text-anchor="middle">checkoutservice</text>
    <path d="M520,204 V224" class="edge ok" marker-end="url(#ps-ok)" />
    <text x="550" y="219" class="t-xs mono muted">:50051</text>
    <rect x="446" y="224" width="148" height="40" rx="7" class="sens" />
    <text x="520" y="249" class="t-b" text-anchor="middle">paymentservice</text>

    <!-- blocked direct shortcuts (red dashed), stopped by a barrier ✕ -->
    <path d="M296,110 C250,150 210,200 190,236" class="edge no" marker-end="url(#ps-no)" />
    <path d="M344,110 C398,150 440,200 452,236" class="edge no" marker-end="url(#ps-no)" />
    <g class="barrier"><circle cx="243" cy="180" r="10" /><text x="243" y="184" text-anchor="middle">✕</text></g>
    <g class="barrier"><circle cx="400" cy="180" r="10" /><text x="400" y="184" text-anchor="middle">✕</text></g>
  </svg>

  <div class="ps-legend">
    <span class="i"><i class="ln ok"></i> Được phép (least privilege)</span>
    <span class="i"><i class="ln no"></i> Bị chặn (default deny)</span>
    <span class="i"><i class="bx entry"></i> Bị chiếm quyền</span>
    <span class="i"><i class="bx sens"></i> Dịch vụ nhạy cảm</span>
  </div>
</template>

<style scoped>
.ps { width: 100%; height: auto; display: block; margin: 0 auto; max-height: 300px; }
.ns { fill: #fcfdfc; stroke: #cbd5e1; stroke-dasharray: 5 4; }
.entry { fill: #ffe9cc; stroke: #d97706; stroke-width: 1.6; animation: pulse 2.6s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { stroke-width: 1.6; } 50% { stroke-width: 3; } }
.ok   { fill: #dcf5dc; stroke: #16a34a; stroke-width: 1.4; }
.sens { fill: #ffd0d0; stroke: #dc2626; stroke-width: 1.6; }
.edge { fill: none; stroke-width: 2.2; }
.edge.ok { stroke: #16a34a; }
.edge.no { stroke: #dc2626; stroke-dasharray: 6 4; }
.barrier circle { fill: #fff; stroke: #dc2626; stroke-width: 1.6; }
.barrier text { fill: #dc2626; font-size: 11px; font-weight: 700; }
text { fill: #1f2937; }
.t-b { font-size: 13px; font-weight: 700; }
.t-xs { font-size: 11px; }
.no-t { fill: #dc2626; font-weight: 700; }
.mono { font-family: var(--slidev-code-font-family, monospace); }
.muted { fill: #6b7280; }

.ps-legend { display: flex; justify-content: center; flex-wrap: wrap; gap: 1.3rem; font-size: 0.8rem; margin-top: 0.5rem; }
.ps-legend .i { display: inline-flex; align-items: center; gap: 0.4rem; }
.ps-legend .ln { width: 22px; height: 0; border-top: 3px solid; display: inline-block; }
.ps-legend .ln.ok { border-color: #16a34a; }
.ps-legend .ln.no { border-color: #dc2626; border-top-style: dashed; }
.ps-legend .bx { width: 13px; height: 13px; border-radius: 3px; border: 1px solid; display: inline-block; }
.ps-legend .bx.entry { background: #ffe9cc; border-color: #d97706; }
.ps-legend .bx.sens { background: #ffd0d0; border-color: #dc2626; }
</style>
