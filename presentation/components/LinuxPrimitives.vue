<script setup lang="ts">
// High-level view of the Linux primitives behind a Pod's network.
// Clicks: 1 veth pair into the root netns, 2 CNI ADD wires it up.
const ctrs = [
  { x: 70, t: 'pause', s: 'holds the netns', c: 'pause' },
  { x: 185, t: 'app', s: 'container', c: '' },
  { x: 300, t: 'sidecar', s: 'container', c: '' },
]
</script>

<template>
  <svg class="lp" viewBox="0 0 920 352">
    <defs>
      <marker id="lp-p" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#7c3aed" /></marker>
    </defs>

    <rect x="16" y="8" width="888" height="336" rx="10" class="node" />
    <text x="32" y="32" class="t-b">Node (Linux host)</text>

    <!-- Pod netns -->
    <rect x="40" y="50" width="380" height="210" rx="8" class="pod" />
    <text x="56" y="74" class="t-b blue">Pod · network namespace</text>
    <g v-for="c in ctrs" :key="c.t">
      <rect :x="c.x" y="92" width="100" height="52" rx="5" class="ctr" :class="c.c" />
      <text :x="c.x + 50" y="114" class="t-m" text-anchor="middle">{{ c.t }}</text>
      <text :x="c.x + 50" y="132" class="t-xs" text-anchor="middle">{{ c.s }}</text>
    </g>
    <text x="230" y="168" class="t-xs muted" text-anchor="middle">shared IP · ports · localhost</text>
    <line x1="235" x2="235" y1="174" y2="200" class="wire" />
    <rect x="175" y="200" width="120" height="38" rx="5" class="nic" />
    <text x="235" y="216" class="t-m mono" text-anchor="middle">eth0</text>
    <text x="235" y="231" class="t-xs mono" text-anchor="middle">10.244.1.10</text>

    <!-- root netns -->
    <rect x="450" y="50" width="430" height="210" rx="8" class="root" />
    <text x="466" y="74" class="t-b">root netns (host)</text>
    <rect x="626" y="180" width="248" height="58" rx="5" class="dp" />
    <text x="750" y="204" class="t-m" text-anchor="middle">routes · iptables / eBPF</text>
    <text x="750" y="224" class="t-xs" text-anchor="middle">Calico: iptables · Cilium: eBPF on lxc*</text>
    <line x1="750" x2="750" y1="238" y2="290" class="wire" />
    <rect x="690" y="290" width="120" height="36" rx="5" class="nic" />
    <text x="750" y="313" class="t-m mono" text-anchor="middle">eth0 (node)</text>

    <!-- 1: veth pair -->
    <g v-click>
      <line x1="295" x2="480" y1="219" y2="219" class="veth" />
      <text x="388" y="210" class="t-m b-t" text-anchor="middle">veth pair</text>
      <rect x="480" y="200" width="120" height="38" rx="5" class="nic hostend" />
      <text x="540" y="224" class="t-m mono" text-anchor="middle">lxc* / cali*</text>
      <line x1="600" x2="626" y1="219" y2="219" class="wire" />
    </g>

    <!-- 2: CNI ADD -->
    <g v-click>
      <rect x="640" y="88" width="220" height="58" rx="6" class="cni" />
      <text x="750" y="112" class="t-m" text-anchor="middle">container runtime → CNI</text>
      <text x="750" y="132" class="t-xs mono" text-anchor="middle">ADD / DEL</text>
      <path d="M640,117 H426" class="call" marker-end="url(#lp-p)" />
      <text x="533" y="108" class="t-xs p-t" text-anchor="middle">create veth · IPAM → IP</text>
      <path d="M750,146 V180" class="call" marker-end="url(#lp-p)" />
      <text x="758" y="168" class="t-xs p-t">add route</text>
    </g>
  </svg>
</template>

<style scoped>
.lp { width: 100%; height: auto; display: block; margin: 0 auto; max-height: 400px; }
.node { fill: #f8fafc; stroke: #374151; stroke-width: 1.5; }
.pod { fill: #eef2ff; stroke: #4f46e5; stroke-dasharray: 6 4; }
.root { fill: #f1f5f9; stroke: #6b7280; }
.ctr { fill: #fff; stroke: #374151; }
.ctr.pause { fill: #fdf6cc; }
.nic { fill: #fff; stroke: #374151; }
.nic.hostend { fill: #e8eefc; }
.dp { fill: #ecfdf5; stroke: #16a34a; }
.cni { fill: #f5f3ff; stroke: #7c3aed; }
.wire { stroke: #374151; stroke-width: 1.4; }
.veth { stroke: #2563eb; stroke-width: 4; stroke-linecap: round; }
.call { fill: none; stroke: #7c3aed; stroke-width: 2; stroke-dasharray: 6 4; animation: dash 0.9s linear infinite; }
@keyframes dash { to { stroke-dashoffset: -10; } }
text { fill: #1f2937; }
.t-b { font-size: 15px; font-weight: 700; }
.t-m { font-size: 13px; font-weight: 600; }
.t-xs { font-size: 11px; }
.mono { font-family: var(--slidev-code-font-family, monospace); }
.muted { fill: #6b7280; font-style: italic; }
.blue { fill: #4338ca; }
.b-t { fill: #1d4ed8; }
.p-t { fill: #6d28d9; font-weight: 600; }
</style>
