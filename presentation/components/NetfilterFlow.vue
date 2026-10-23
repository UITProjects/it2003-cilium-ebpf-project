<script setup lang="ts">
// Netfilter packet path: one left→right flow with a single fork (local vs forward),
// both landing on POSTROUTING. Minimal labels — the raw/mangle/nat table detail lives
// in the bullets, so the fork is the only thing to read.
</script>

<template>
  <svg class="nf" viewBox="0 0 860 260">
    <defs>
      <marker id="nf-a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#1f2937" /></marker>
    </defs>

    <!-- ingress -->
    <rect x="12" y="104" width="96" height="52" rx="7" class="end" />
    <text x="60" y="134" class="t" text-anchor="middle">NIC / veth</text>
    <path d="M108,130 H150" class="edge" marker-end="url(#nf-a)" />

    <!-- PREROUTING -->
    <rect x="150" y="104" width="120" height="52" rx="7" class="hook" />
    <text x="210" y="134" class="t-b" text-anchor="middle">PREROUTING</text>

    <!-- routing decision -->
    <path d="M270,130 H318" class="edge" marker-end="url(#nf-a)" />
    <g class="dia"><path d="M360,100 L404,130 L360,160 L316,130 Z" /></g>
    <text x="360" y="134" class="t-b" text-anchor="middle">routing</text>

    <!-- local branch: INPUT → OUTPUT -->
    <path d="M360,100 V58 H446" class="edge" marker-end="url(#nf-a)" />
    <text x="396" y="50" class="t-s muted" text-anchor="middle">local</text>
    <rect x="446" y="34" width="104" height="48" rx="7" class="hook" />
    <text x="498" y="63" class="t-b" text-anchor="middle">INPUT</text>
    <path d="M550,58 H600" class="edge" marker-end="url(#nf-a)" />
    <text x="575" y="50" class="t-s muted" text-anchor="middle">process</text>
    <rect x="600" y="34" width="104" height="48" rx="7" class="hook" />
    <text x="652" y="63" class="t-b" text-anchor="middle">OUTPUT</text>
    <path d="M652,82 V130 H736" class="edge" marker-end="url(#nf-a)" />

    <!-- forward branch: FORWARD -->
    <path d="M404,130 H446" class="edge" marker-end="url(#nf-a)" />
    <text x="425" y="150" class="t-s muted" text-anchor="middle">forward</text>
    <rect x="446" y="150" width="104" height="48" rx="7" class="hook" />
    <text x="498" y="179" class="t-b" text-anchor="middle">FORWARD</text>
    <path d="M550,174 H652 V144" class="edge" marker-end="url(#nf-a)" />

    <!-- POSTROUTING → egress -->
    <rect x="736" y="104" width="112" height="52" rx="7" class="hook" />
    <text x="792" y="128" class="t-b" text-anchor="middle">POSTROUTING</text>
    <text x="792" y="144" class="t-s muted" text-anchor="middle">→ NIC / veth</text>
  </svg>
</template>

<style scoped>
.nf { width: 100%; height: auto; display: block; margin: 0 auto; max-height: 256px; }
.hook { fill: #ffe9cc; stroke: #374151; stroke-width: 1.4; }
.end  { fill: #f8fafc; stroke: #9ca3af; }
.dia path { fill: #e8eefc; stroke: #374151; stroke-width: 1.4; }
.edge { fill: none; stroke: #1f2937; stroke-width: 2; }
text { fill: #1f2937; }
.t   { font-size: 13px; }
.t-b { font-size: 13px; font-weight: 700; }
.t-s { font-size: 11px; }
.muted { fill: #6b7280; }
</style>
