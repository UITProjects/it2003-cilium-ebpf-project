<script setup lang="ts">
// How one E1 number is produced: request -> run percentiles -> mean over runs -> ratio.
// Details (fortio flags, settle times) stay in the report.
const steps = [
  { t: '1 request', s: ['= 1 new TCP connection', 'incl. handshake'] },
  { t: '1 run ≈ 6 000 req', s: ['fortio histogram (10 µs)', '→ p50 · p99'] },
  { t: '3 runs per N', s: ['N = number of Services', '→ mean ± SD'] },
  { t: 'iptables ÷ Cilium', s: ['p50 ratio at each N'], last: true },
]
const w = 172
const x = (i: number) => 9 + i * 210
</script>

<template>
  <svg class="em" viewBox="0 0 820 170">
    <defs>
      <marker id="em-a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#1f2937" /></marker>
    </defs>

    <template v-for="(st, i) in steps" :key="st.t">
      <rect :x="x(i)" y="20" :width="w" height="96" rx="8" :class="st.last ? 'bpf' : 'box'" />
      <text :x="x(i) + w / 2" y="54" class="t-b" text-anchor="middle">{{ st.t }}</text>
      <text v-for="(l, j) in st.s" :key="l" :x="x(i) + w / 2" :y="78 + j * 18" class="t-s" text-anchor="middle">{{ l }}</text>
      <path v-if="i < steps.length - 1" :d="`M${x(i) + w + 2},68 H${x(i + 1) - 4}`" class="edge" marker-end="url(#em-a)" />
    </template>

    <text x="410" y="152" class="t-note" text-anchor="middle">table size read on client node: iptables-save -t nat · cilium-dbg bpf lb list</text>
  </svg>
</template>

<style scoped>
.em { width: 100%; height: auto; display: block; margin: 0 auto; max-height: 230px; }
.box { fill: #e8eefc; stroke: #374151; stroke-width: 1.4; }
.bpf { fill: #dcf5dc; stroke: #374151; stroke-width: 1.4; }
.edge { fill: none; stroke: #1f2937; stroke-width: 2; }
text { fill: #1f2937; }
.t-b { font-size: 14px; font-weight: 700; font-family: var(--slidev-code-font-family, monospace); }
.t-s { font-size: 12.5px; }
.t-note { font-size: 12px; fill: #6b7280; font-family: var(--slidev-code-font-family, monospace); }
</style>
