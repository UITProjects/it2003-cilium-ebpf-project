<script setup lang="ts">
// NetworkPolicy must translate labels into something checkable on a packet, in 3 stages.
// The one idea to land: iptables resolves a label to Pod IPs, eBPF to a numeric identity.
// Names (Felix, cilium-agent, cali-*, cilium_policy_*) stay in the bullets.
const stages = ['Control plane', 'Kernel state', 'Per-packet check']
const ipt = ['label → Pod IPs', 'ipset + chains', 'match src IP']
const bpf = ['label → identity', 'policy map', 'lookup O(1)']
const cx = [158, 360, 578]
</script>

<template>
  <svg class="pt" viewBox="0 0 700 234">
    <defs>
      <marker id="pt-a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#1f2937" /></marker>
    </defs>

    <!-- stage headers + faint separators -->
    <text v-for="(s, i) in stages" :key="s" :x="cx[i]" y="26" class="t-stage" text-anchor="middle">{{ i + 1 }} · {{ s }}</text>
    <line x1="262" x2="262" y1="40" y2="214" class="sep" />
    <line x1="464" x2="464" y1="40" y2="214" class="sep" />

    <!-- lane tags -->
    <text x="74" y="100" class="t-lane ipt-t" text-anchor="end">iptables</text>
    <text x="74" y="185" class="t-lane bpf-t" text-anchor="end">eBPF</text>

    <!-- iptables lane -->
    <template v-for="(t, i) in ipt" :key="'i' + i">
      <rect :x="84 + i * 202" y="76" :width="i === 2 ? 180 : 148" height="46" rx="7" class="ipt" />
      <text :x="cx[i]" y="104" class="t-b" text-anchor="middle">{{ t }}</text>
      <path v-if="i < 2" :d="`M${232 + i * 202},99 H${286 + i * 202}`" class="edge" marker-end="url(#pt-a)" />
    </template>

    <!-- eBPF lane -->
    <template v-for="(t, i) in bpf" :key="'b' + i">
      <rect :x="84 + i * 202" y="161" :width="i === 2 ? 180 : 148" height="46" rx="7" class="bpf" />
      <text :x="cx[i]" y="189" class="t-b" :class="{ mono: i === 2 }" text-anchor="middle">{{ t }}</text>
      <path v-if="i < 2" :d="`M${232 + i * 202},184 H${286 + i * 202}`" class="edge" marker-end="url(#pt-a)" />
    </template>
  </svg>
</template>

<style scoped>
.pt { width: 100%; height: auto; display: block; margin: 0 auto; max-height: 232px; }
.ipt { fill: #ffe9cc; stroke: #374151; stroke-width: 1.4; }
.bpf { fill: #dcf5dc; stroke: #374151; stroke-width: 1.4; }
.edge { fill: none; stroke: #1f2937; stroke-width: 2; }
.sep { stroke: #e2e8f0; stroke-width: 1.4; stroke-dasharray: 4 4; }
text { fill: #1f2937; }
.t-b { font-size: 13px; font-weight: 700; }
.mono { font-family: var(--slidev-code-font-family, monospace); }
.t-stage { font-size: 12.5px; font-weight: 700; fill: #6b7280; }
.t-lane { font-size: 13px; font-weight: 700; }
.ipt-t { fill: #c2620c; }
.bpf-t { fill: #15803d; }
</style>
